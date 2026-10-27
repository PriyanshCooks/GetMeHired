import os
import io
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import pypdf

from backend.config import (
    load_settings, save_settings, get_profiles,
    get_active_profile_id, set_active_profile_id, get_profile_by_id
)
from backend.database import (
    init_db,
    get_all_jobs, get_job_by_id, update_job_status,
    save_contacts_for_job, get_contacts_for_job,
    save_outreach_message, get_outreach_for_job, save_job,
    save_application, get_all_applications, delete_application,
    save_conversation, get_all_conversations, check_and_update_due_followups,
    clear_all_data, get_queue_count
)
from backend.ollama_client import ollama_client
from backend.scrapers.aggregator import run_job_search
from backend.agents.job_matcher import analyze_job_fit
from backend.agents.contact_finder import generate_target_contacts
from backend.agents.outreach_generator import generate_outreach_messages
from backend.notifications.notifier import send_iphone_ntfy, send_email_alert, send_job_alert
from backend.pipeline import execute_autonomous_pipeline, is_enrichment_running, start_llm_enrichment_background
from backend.scheduler import init_scheduler, restart_scheduler_with_interval

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("getmehired")

app = FastAPI(
    title="GetMeHired API",
    description="Autonomous Multi-Agent Job Hunter & Referral Engine",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    try:
        init_db()
        settings = load_settings()
        sched = settings.get("scheduler", {})
        if sched.get("status") == "running":
            sched["status"] = "idle"
            settings["scheduler"] = sched
            save_settings(settings)
        init_scheduler()
        start_llm_enrichment_background()
        logger.info("Autonomous 30-minute background scheduler & LLM enrichment worker initialized.")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")

# ----------------- Health & Ollama -----------------
@app.get("/api/health")
def get_health():
    ollama_info = ollama_client.is_available()
    settings = load_settings()
    sched = settings.get("scheduler", {})
    return {
        "status": "healthy",
        "ollama": ollama_info,
        "active_model": settings.get("ollama_model", "qwen3.5:4b"),
        "scheduler": sched,
        "enrichment_running": is_enrichment_running(),
        "features": {
            "jobspy": True,
            "naukri": True,
            "wellfound": True,
            "contact_finder": True,
            "outreach_generator": True,
            "iphone_push": True,
            "autonomous_loop": True
        }
    }

# ----------------- Autonomous Multi-Agent Pipeline Endpoints -----------------
@app.post("/api/pipeline/run")
def trigger_pipeline_endpoint(background_tasks: BackgroundTasks):
    """Trigger the multi-agent pipeline immediately in the background."""
    background_tasks.add_task(execute_autonomous_pipeline)
    return {
        "success": True,
        "message": "Autonomous multi-agent pipeline triggered in background."
    }

@app.post("/api/pipeline/enrich")
def trigger_enrichment_endpoint():
    """Trigger background LLM enrichment worker for all pending unenriched jobs."""
    start_llm_enrichment_background()
    return {
        "success": True,
        "message": "Background LLM enrichment worker started."
    }

@app.get("/api/pipeline/status")
def get_pipeline_status():
    settings = load_settings()
    sched = settings.get("scheduler", {})
    all_jobs = get_all_jobs()
    pending_enrichment = len([j for j in all_jobs if j.get("match_score", 0) == 0])
    return {
        "scheduler_enabled": sched.get("enabled", True),
        "interval_minutes": sched.get("interval_minutes", 30),
        "status": sched.get("status", "idle"),
        "enrichment_running": is_enrichment_running(),
        "pending_enrichment": pending_enrichment,
        "last_run": sched.get("last_run"),
        "next_run": sched.get("next_run"),
        "total_jobs_tracked": len(all_jobs),
        "high_fit_jobs": len([j for j in all_jobs if j.get("match_score", 0) >= 75])
    }

@app.post("/api/pipeline/toggle")
def toggle_pipeline_scheduler(payload: Dict[str, Any]):
    enabled = payload.get("enabled", True)
    interval = payload.get("interval_minutes", 30)
    settings = load_settings()
    settings["scheduler"]["enabled"] = enabled
    settings["scheduler"]["interval_minutes"] = interval
    save_settings(settings)
    restart_scheduler_with_interval(interval)
    return {"success": True, "scheduler": settings["scheduler"]}

@app.post("/api/database/clean")
def clean_database_endpoint():
    """Wipes all jobs, contacts, outreach messages, applications, and conversations for a clean fresh start, and immediately stops any running agent pipeline."""
    from backend.pipeline import stop_enrichment
    stop_enrichment()
    clear_all_data()
    settings = load_settings()
    settings["scheduler"]["last_run"] = None
    settings["scheduler"]["next_run"] = None
    settings["scheduler"]["status"] = "idle"
    save_settings(settings)
    return {
        "success": True,
        "message": "All database tables cleaned and agent stopped successfully. Ready for clean re-trigger."
    }

# ----------------- Settings -----------------
@app.get("/api/settings")
def get_settings_endpoint():
    return load_settings()

@app.post("/api/settings")
def update_settings_endpoint(payload: Dict[str, Any]):
    current = load_settings()
    current.update(payload)
    saved = save_settings(current)
    return {"success": True, "settings": saved}

# ----------------- Profiles (Multi-Candidate) -----------------
@app.get("/api/profiles")
def list_profiles():
    profiles_dict = get_profiles()
    active_id = get_active_profile_id()
    profile_list = []
    for pid, p in profiles_dict.items():
        profile_list.append({
            "id": pid,
            "full_name": p.get("full_name", pid.title()),
            "headline": p.get("headline", ""),
            "email": p.get("email", ""),
            "phone": p.get("phone", ""),
            "education": p.get("education", ""),
            "ntfy_topic": p.get("ntfy_topic", ""),
            "skills": p.get("skills", []),
            "is_active": (pid == active_id)
        })
    return {
        "active_profile_id": active_id,
        "profiles": profile_list
    }

@app.post("/api/profiles/active")
def switch_active_profile(payload: Dict[str, str]):
    pid = payload.get("profile_id") or get_active_profile_id()
    new_active = set_active_profile_id(pid)
    return {"success": True, "active_profile_id": new_active}

# ----------------- Profile & Resume -----------------
@app.get("/api/profile")
def get_profile(profile_id: Optional[str] = None):
    pid = profile_id or get_active_profile_id()
    return get_profile_by_id(pid)

@app.post("/api/profile")
def update_profile(profile_data: Dict[str, Any], profile_id: Optional[str] = None):
    settings = load_settings()
    pid = profile_id or profile_data.get("id") or get_active_profile_id()
    if "profiles" not in settings:
        settings["profiles"] = {}
    settings["profiles"][pid] = profile_data
    if settings.get("active_profile_id") == pid:
        settings["user_profile"] = profile_data
    save_settings(settings)
    return {"success": True, "profile": profile_data}

@app.post("/api/profile/upload-resume")
async def upload_resume(file: UploadFile = File(...), profile_id: Optional[str] = Form(None)):
    filename = file.filename.lower()
    content = await file.read()
    extracted_text = ""

    if filename.endswith(".pdf"):
        try:
            reader = pypdf.PdfReader(io.BytesIO(content))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF resume: {e}")
    else:
        try:
            extracted_text = content.decode("utf-8", errors="ignore")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read file text: {e}")

    extracted_text = extracted_text.strip()
    if not extracted_text:
        raise HTTPException(status_code=400, detail="Could not extract readable text from uploaded file.")

    settings = load_settings()
    pid = profile_id or get_active_profile_id()
    profiles = settings.get("profiles", {})
    profile = profiles.get(pid, settings.get("user_profile", {}))
    profile["resume_text"] = extracted_text
    
    from backend.agents.job_matcher import extract_keywords
    skills_found = extract_keywords(extracted_text)
    if skills_found and not profile.get("skills"):
        profile["skills"] = list(set(skills_found))[:15]
        
    profiles[pid] = profile
    settings["profiles"] = profiles
    if settings.get("active_profile_id") == pid:
        settings["user_profile"] = profile
    save_settings(settings)

    return {
        "success": True,
        "profile_id": pid,
        "characters_extracted": len(extracted_text),
        "detected_skills": profile.get("skills", []),
        "resume_preview": extracted_text[:400] + "..." if len(extracted_text) > 400 else extracted_text
    }

# ----------------- Jobs -----------------
@app.get("/api/jobs")
def list_jobs(
    status: Optional[str] = "all",
    min_score: int = 0,
    search: Optional[str] = None,
    view: str = "enriched",
    profile_id: Optional[str] = None
):
    pid = profile_id or get_active_profile_id()
    jobs = get_all_jobs(status_filter=status, min_match_score=min_score, view=view, candidate_id=pid)
    if search:
        s = search.lower()
        jobs = [j for j in jobs if s in j["title"].lower() or s in j["company"].lower() or s in j["location"].lower()]
    queue_count = get_queue_count(candidate_id=pid)
    return {
        "count": len(jobs),
        "jobs": jobs,
        "queue_count": queue_count,
        "view": view,
        "candidate_id": pid
    }

@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: str):
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    contacts = get_contacts_for_job(job_id)
    outreach = get_outreach_for_job(job_id)
    return {
        "job": job,
        "contacts": contacts,
        "outreach_history": outreach
    }

@app.patch("/api/jobs/{job_id}/status")
def patch_job_status(job_id: str, payload: Dict[str, str]):
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status required")
    update_job_status(job_id, new_status)
    return {"success": True, "job_id": job_id, "status": new_status}

@app.post("/api/jobs/search")
def trigger_job_search(payload: Optional[Dict[str, Any]] = None, background_tasks: BackgroundTasks = BackgroundTasks()):
    settings = load_settings()
    roles = payload.get("roles") if payload else None
    locations = payload.get("locations") if payload else None
    max_results = payload.get("max_results", 12) if payload else 12

    scraped_jobs = run_job_search(roles=roles, locations=locations, max_results=max_results)

    # Automatically analyze top jobs in background if profile is populated
    profile = settings.get("user_profile", {})
    if profile.get("resume_text") or profile.get("skills"):
        for job in scraped_jobs[:5]:
            fit = analyze_job_fit(job, profile)
            job.update(fit)
            save_job(job)
            contacts = generate_target_contacts(job, profile)
            save_contacts_for_job(job["id"], contacts)

    return {
        "success": True,
        "jobs_found": len(scraped_jobs),
        "jobs": scraped_jobs
    }

@app.post("/api/jobs/{job_id}/analyze")
def analyze_single_job(job_id: str):
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    settings = load_settings()
    profile = settings.get("user_profile", {})
    
    # Analyze Fit
    fit = analyze_job_fit(job, profile)
    job.update(fit)
    save_job(job)

    # Generate Contacts
    contacts = generate_target_contacts(job, profile)
    save_contacts_for_job(job_id, contacts)

    # If high match, trigger alert if enabled
    if job.get("match_score", 0) >= 80:
        send_job_alert(job)

    return {
        "success": True,
        "job": job,
        "contacts": contacts
    }

# ----------------- Contacts & Outreach -----------------
@app.get("/api/jobs/{job_id}/contacts")
def list_contacts(job_id: str):
    contacts = get_contacts_for_job(job_id)
    if not contacts:
        job = get_job_by_id(job_id)
        if job:
            settings = load_settings()
            contacts = generate_target_contacts(job, settings.get("user_profile", {}))
            save_contacts_for_job(job_id, contacts)
    return {"contacts": contacts}

@app.post("/api/jobs/{job_id}/outreach")
def generate_outreach(job_id: str, payload: Dict[str, Any]):
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    contact_id = payload.get("contact_id")
    tone = payload.get("tone", "direct")
    
    contacts = get_contacts_for_job(job_id)
    target_contact = None
    if contact_id:
        target_contact = next((c for c in contacts if c["id"] == contact_id), None)
    if not target_contact and contacts:
        target_contact = contacts[0]
    if not target_contact:
        target_contact = {
            "role": "Engineering Leader",
            "contact_type": "Hiring Manager",
            "company": job.get("company")
        }

    settings = load_settings()
    profile = settings.get("user_profile", {})
    
    messages = generate_outreach_messages(job, target_contact, profile, tone=tone)
    
    # Save outreach draft
    save_outreach_message({
        "job_id": job_id,
        "contact_id": target_contact.get("id"),
        "message_type": "all",
        "subject": messages.get("cold_email_subject", ""),
        "content": json.dumps(messages),
        "status": "draft"
    })
    
    return {
        "success": True,
        "job_title": job.get("title"),
        "company": job.get("company"),
        "contact": target_contact,
        "messages": messages
    }

# ----------------- Notifications -----------------
@app.post("/api/notifications/test")
def test_notification(payload: Optional[Dict[str, Any]] = None):
    channel = payload.get("channel", "ntfy") if payload else "ntfy"
    topic = payload.get("topic") if payload else None
    candidate_name = payload.get("name", "Candidate") if payload else "Candidate"
    if channel == "ntfy":
        res = send_iphone_ntfy(
            title=f"🚀 GetMeHired Alert ({candidate_name})",
            message=f"iPhone notifications are active for {candidate_name}! High-potential 0-1 yr AI job alerts will pop up here.",
            url="http://localhost:8000",
            priority=4,
            topic=topic
        )
        return res
    elif channel == "email":
        res = send_email_alert(
            subject=f"🚀 GetMeHired Agent Test Email ({candidate_name})",
            html_body=f"<p>Your GetMeHired email notifications are configured successfully for {candidate_name}!</p>"
        )
        return res

# ----------------- CRM: Applications & Networking Tracker -----------------
@app.get("/api/crm/applications")
def list_applications(profile_id: Optional[str] = None):
    pid = profile_id or get_active_profile_id()
    return {"applications": get_all_applications(candidate_id=pid), "candidate_id": pid}

@app.post("/api/crm/applications")
def create_application(payload: Dict[str, Any]):
    if not payload.get("candidate_id"):
        payload["candidate_id"] = get_active_profile_id()
    app_id = save_application(payload)
    return {"success": True, "application_id": app_id}

@app.delete("/api/crm/applications/{app_id}")
def remove_application(app_id: str):
    delete_application(app_id)
    return {"success": True, "deleted": app_id}

@app.get("/api/crm/conversations")
def list_conversations(status: Optional[str] = "all", profile_id: Optional[str] = None):
    pid = profile_id or get_active_profile_id()
    return {"conversations": get_all_conversations(status_filter=status, candidate_id=pid), "candidate_id": pid}

@app.post("/api/crm/conversations")
def create_conversation(payload: Dict[str, Any]):
    if not payload.get("candidate_id"):
        payload["candidate_id"] = get_active_profile_id()
    conv_id = save_conversation(payload)
    return {"success": True, "conversation_id": conv_id}

@app.get("/api/crm/followups-due")
def get_due_followups(profile_id: Optional[str] = None):
    pid = profile_id or get_active_profile_id()
    due = check_and_update_due_followups(candidate_id=pid)
    return {"count": len(due), "followups_due": due, "candidate_id": pid}

@app.post("/api/crm/quick-log")
def quick_log_outreach(payload: Dict[str, Any]):
    """1-Click quick log when user sends a message to a contact."""
    company = payload.get("company", "")
    person_name = payload.get("person_name", "Team Member")
    person_role = payload.get("person_role", "")
    profile_url = payload.get("profile_url", "")
    message_sent = payload.get("message_sent", "")
    follow_up_note = payload.get("follow_up_note", "")
    candidate_id = payload.get("candidate_id") or get_active_profile_id()
    
    # Save conversation
    conv_id = save_conversation({
        "company": company,
        "person_name": person_name,
        "person_role": person_role,
        "profile_url": profile_url,
        "message_sent": message_sent,
        "follow_up_note": follow_up_note,
        "status": "Waiting Reply",
        "candidate_id": candidate_id
    })
    
    # Also log application as 'Outreach Sent'
    save_application({
        "company": company,
        "role": payload.get("role", "AI / ML Engineer"),
        "job_url": payload.get("job_url", ""),
        "status": "Outreach Sent",
        "notes": f"Reached out to {person_name} ({person_role})",
        "candidate_id": candidate_id
    })
    
    return {"success": True, "conversation_id": conv_id}

# ----------------- Serve Frontend (Static & SPA) -----------------
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
