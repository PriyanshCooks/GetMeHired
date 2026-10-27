"""
Two-Phase Multi-Agent Pipeline
==============================
Phase 1 (FAST - runs every 30 min):
    - Scrape jobs from all sources
    - Save raw jobs to DB immediately
    - No LLM involvement → completes in ~60 seconds

Phase 2 (SLOW - runs in background thread, never times out):
    - Pick un-enriched jobs one at a time
    - Run LLM scoring → LLM bullets → LLM outreach → save
    - Sequential, no parallelism (local model hates concurrent calls)
    - No timeout — let the model finish at its own pace
    - Pushes iPhone alert when a high-fit job is enriched

Key principle: Never couple scraping speed to LLM speed.
"""

import logging
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

from backend.config import load_settings, save_settings
from backend.database import (
    save_job, get_job_by_id, save_contacts_for_job,
    save_outreach_message, get_all_jobs, get_connection
)
from backend.scrapers.aggregator import run_job_search
from backend.scrapers.deep_jd_fetcher import fetch_deep_job_details
from backend.agents.job_matcher import analyze_job_fit
from backend.agents.contact_finder import generate_target_contacts
from backend.agents.outreach_generator import generate_outreach_messages
from backend.notifications.notifier import send_job_alert

logger = logging.getLogger("getmehired.pipeline")

# Background LLM enrichment thread — only one runs at a time
_enrichment_thread: threading.Thread = None
_enrichment_running = False
_stop_enrichment_requested = False

def stop_enrichment():
    """Immediately halts any running LLM enrichment loop."""
    global _stop_enrichment_requested, _enrichment_running
    _stop_enrichment_requested = True
    _enrichment_running = False
    logger.info("[Pipeline] Stop signal received: Halting LLM enrichment loop immediately.")

def reset_stop_flag():
    global _stop_enrichment_requested
    _stop_enrichment_requested = False


# ─────────────────────────────────────────────
# PHASE 1: Fast scrape — no LLM, no blocking
# ─────────────────────────────────────────────
def phase1_scrape_jobs() -> Dict[str, Any]:
    """
    Scrape all job sources and save raw jobs to DB immediately.
    No LLM calls. Completes in ~30-90 seconds.
    """
    settings = load_settings()
    target_roles = settings.get("target_roles", ["Agentic AI Engineer", "Generative AI Engineer", "AIML Engineer"])
    target_locations = settings.get("target_locations", ["Gurugram", "Pune", "Surat", "Dehradun", "Remote"])

    logger.info(f"[Phase 1] Scraping jobs: {target_roles} in {target_locations}")

    scraped = run_job_search(
        roles=target_roles,
        locations=target_locations,
        max_results=settings.get("max_results_per_source", 10)
    )

    logger.info(f"[Phase 1] Scraped {len(scraped)} jobs — saved to DB. Starting LLM enrichment in background.")
    return {"jobs_scraped": len(scraped), "jobs": scraped}


# ─────────────────────────────────────────────
# PHASE 2: LLM Enrichment — background thread
# ─────────────────────────────────────────────
def _get_unenriched_jobs(limit: int = 5) -> List[Dict[str, Any]]:
    """Get jobs that have match_score = 0, prioritizing AI startups and skipping excluded companies."""
    settings = load_settings()
    excluded = [c.lower() for c in settings.get("excluded_companies", [])]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM jobs 
        WHERE match_score = 0 
        ORDER BY 
            CASE WHEN source = 'Hidden Startup Lead' THEN 1 ELSE 2 END,
            created_at DESC 
        LIMIT ?
        """,
        (limit * 3,)
    )
    rows = cursor.fetchall()
    conn.close()

    jobs = []
    for r in rows:
        job = dict(r)
        comp_lower = job.get("company", "").lower()
        if any(ex in comp_lower for ex in excluded):
            continue
        job["matching_skills"] = json.loads(job.get("matching_skills") or "[]")
        job["missing_skills"] = json.loads(job.get("missing_skills") or "[]")
        job["tailored_bullets"] = json.loads(job.get("tailored_bullets") or "[]")
        jobs.append(job)
        if len(jobs) >= limit:
            break
    return jobs


def _enrich_single_job(job: Dict[str, Any], profile: Dict[str, Any], sched_cfg: Dict[str, Any]) -> bool:
    """
    Run full LLM enrichment on a single job:
    0. Deep JD Fetching from live URL (resolves full text from LinkedIn/Keka/Greenhouse/Lever)
    1. Fit scoring with strict disqualification for senior / >3 yrs roles
    2. Contact discovery (for qualified roles only)
    3. Outreach drafting (for qualified roles only)
    4. iPhone alert if high fit and NOT disqualified
    """
    if _stop_enrichment_requested:
        return False

    job_id = job.get("id", "unknown")
    company = job.get("company", "?")
    title = job.get("title", "?")

    logger.info(f"[Phase 2] Enriching: {title} @ {company} (id={job_id})")

    # 0. Deep JD Fetching: ensure we evaluate against real web description
    job_url = job.get("job_url", "")
    desc = job.get("description", "")
    if job_url:
        try:
            deep_res = fetch_deep_job_details(job_url)
            if deep_res.get("is_generic_url"):
                logger.warning(f"[Phase 2] Job {job_id} ({company}) links to a generic homepage ({job_url}). Disqualifying.")
                job["is_disqualified"] = True
                job["match_score"] = 15
                job["match_rationale"] = f"Generic homepage link ({job_url}). Not a verified direct job posting."
                save_job(job)
                return False
            elif deep_res.get("fetched") and deep_res.get("full_description"):
                job["description"] = deep_res["full_description"]
                if deep_res.get("extracted_title") and len(deep_res["extracted_title"]) > 3:
                    job["title"] = deep_res["extracted_title"]
                logger.info(f"[Phase 2] Deep JD verified ({len(job['description'])} chars) for {company}")

            # If Playwright discovered specific open job links on a careers page, enqueue the relevant ones
            discovered = deep_res.get("discovered_job_links") or []
            if discovered:
                target_keywords = ["ai", "ml", "generative", "agentic", "engineer", "developer", "python"]
                for d in discovered:
                    d_title = d.get("text", "").strip().split("\n")[0]
                    d_url = d.get("href", "").strip()
                    d_lower = d_title.lower()
                    is_tech = any(re.search(r"\b" + re.escape(kw) + r"\b", d_lower) for kw in target_keywords)
                    is_non_tech = any(k in d_lower for k in ["sales", "account management", "director", "product manager", "marketing", "hr"])
                    if is_tech and not is_non_tech and d_url.startswith("http"):
                        new_job = {
                            "id": f"ats_{abs(hash(d_url))}",
                            "title": d_title,
                            "company": company,
                            "location": job.get("location", "India"),
                            "source": "Direct ATS",
                            "job_url": d_url,
                            "date_posted": "Active Job",
                            "description": "",
                            "status": "new",
                            "candidate_id": job.get("candidate_id", "priyansh")
                        }
                        save_job(new_job)
                        logger.info(f"[Phase 2] Enqueued specific open role discovered by Playwright: {d_title} -> {d_url}")
        except Exception as e:
            logger.warning(f"[Phase 2] Deep JD fetch notice for {job_id}: {e}")

    # LLM Call: Analyze fit — with strict senior / 3-6 yr disqualification
    try:
        fit = analyze_job_fit(job, profile)
        job.update(fit)
        save_job(job)
        logger.info(f"[Phase 2] Fit scored: {fit.get('match_score')} (disqualified={fit.get('is_disqualified', False)}) for {company}")
    except Exception as e:
        logger.error(f"[Phase 2] Fit analysis failed for {job_id}: {e}")
        return False

    # If disqualified (e.g. senior role / 3-6 years), do NOT generate contacts or alert iPhone
    if job.get("is_disqualified", False):
        logger.info(f"[Phase 2] Disqualified role ignored for outreach/alerts: {title} @ {company}")
        return True

    # Contact Discovery (pure deterministic logic — instant, no LLM)
    contacts = []
    try:
        contacts = generate_target_contacts(job, profile)
        save_contacts_for_job(job_id, contacts)
        logger.info(f"[Phase 2] {len(contacts)} contacts discovered for {company}")
    except Exception as e:
        logger.error(f"[Phase 2] Contact discovery failed for {job_id}: {e}")

    # LLM Call: Draft outreach for top contact (Founder/CEO first)
    if sched_cfg.get("auto_draft_outreach", True) and contacts:
        try:
            top_contact = contacts[0]
            messages = generate_outreach_messages(job, top_contact, profile, tone="direct")
            save_outreach_message({
                "job_id": job_id,
                "contact_id": top_contact.get("id"),
                "message_type": "auto_draft",
                "subject": messages.get("cold_email_subject", ""),
                "content": json.dumps(messages),
                "status": "draft"
            })
            logger.info(f"[Phase 2] Outreach drafted for {company}")
        except Exception as e:
            logger.error(f"[Phase 2] Outreach drafting failed for {job_id}: {e}")

    # Push iPhone alert ONLY IF score clears threshold AND not disqualified
    threshold = sched_cfg.get("auto_notify_threshold", 75)
    if job.get("match_score", 0) >= threshold and not job.get("is_disqualified", False):
        try:
            topic = profile.get("ntfy_topic")
            send_job_alert(job, topic=topic)
            logger.info(f"[Phase 2] iPhone alert sent to {topic}: {title} @ {company} ({job.get('match_score')}%)")
        except Exception as e:
            logger.error(f"[Phase 2] Alert dispatch failed: {e}")

    return True


def _run_llm_enrichment_loop():
    """
    Background thread: process un-enriched jobs in alternating round-robin for configured profiles.
    Enforces the 45-minute autonomous window guard and immediately terminates upon stop signal.
    """
    global _enrichment_running
    reset_stop_flag()
    _enrichment_running = True
    start_time = time.time()
    max_duration_seconds = 45 * 60  # 45 minutes strict cap
    logger.info("[Phase 2] Candidate LLM enrichment thread started (45-min window).")

    settings = load_settings()
    profiles = settings.get("profiles", {})
    if not profiles:
        active_id = settings.get("active_profile_id", "default")
        profiles = {active_id: settings.get("user_profile", {})}
    candidates = [(pid, pdata) for pid, pdata in profiles.items() if pdata]
    if not candidates:
        candidates = [(settings.get("active_profile_id", "default"), settings.get("user_profile", {}))]
    sched_cfg = settings.get("scheduler", {})

    enriched_count = 0
    try:
        while True:
            if _stop_enrichment_requested:
                logger.info("[Phase 2] Stop requested. Terminating enrichment loop immediately.")
                break

            # Check 45-minute time window
            elapsed = time.time() - start_time
            if elapsed >= max_duration_seconds:
                logger.warning(f"[Phase 2] 45-minute window reached ({int(elapsed/60)} mins). Pausing enrichment until next scheduled cycle.")
                break

            max_evals = max(20, len(candidates) * 20)
            if enriched_count >= max_evals:
                logger.info(f"[Phase 2] Reached {max_evals} total job evaluations. Finishing cycle.")
                break

            pending = _get_unenriched_jobs(limit=2)
            if not pending:
                logger.info(f"[Phase 2] All pending jobs enriched. Total processed this session: {enriched_count}")
                break

            for raw_job in pending:
                if _stop_enrichment_requested:
                    break

                base_id = raw_job.get("id", "job")
                
                # Evaluate for each active configured candidate
                for cand_id, cand_profile in candidates:
                    if _stop_enrichment_requested:
                        break

                    if not cand_profile:
                        continue

                    # Check time limit before each candidate evaluation
                    if time.time() - start_time >= max_duration_seconds:
                        logger.warning("[Phase 2] 45-minute window reached mid-batch. Halting.")
                        break

                    cand_job = dict(raw_job)
                    # Unique isolated ID per candidate
                    if not base_id.endswith(f"_{cand_id}"):
                        cand_job["id"] = f"{base_id}_{cand_id}"
                    cand_job["candidate_id"] = cand_id

                    logger.info(f"[Phase 2] Evaluating {cand_job['title']} @ {cand_job['company']} for {cand_profile.get('full_name', cand_id)}")
                    success = _enrich_single_job(cand_job, cand_profile, sched_cfg)
                    if success:
                        enriched_count += 1

                    # Small breath for Ollama
                    time.sleep(2)

                # Mark base raw job as handled so it doesn't get picked up repeatedly
                candidate_suffixes = tuple(f"_{cid}" for cid, _ in candidates)
                if not any(base_id.endswith(sfx) for sfx in candidate_suffixes):
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("UPDATE jobs SET match_score = 1 WHERE id = ?", (base_id,))
                    conn.commit()
                    conn.close()

            # Refresh settings
            settings = load_settings()
            profiles = settings.get("profiles", {})
            if not profiles:
                active_id = settings.get("active_profile_id", "default")
                profiles = {active_id: settings.get("user_profile", {})}
            candidates = [(pid, pdata) for pid, pdata in profiles.items() if pdata]
            if not candidates:
                candidates = [(settings.get("active_profile_id", "default"), settings.get("user_profile", {}))]
            sched_cfg = settings.get("scheduler", {})

    except Exception as e:
        logger.error(f"[Phase 2] Enrichment loop crashed: {e}")
    finally:
        _enrichment_running = False
        duration_mins = int((time.time() - start_time) / 60)
        logger.info(f"[Phase 2] LLM enrichment thread finished. Enriched {enriched_count} evaluations in {duration_mins} mins.")


def start_llm_enrichment_background():
    """
    Launch the LLM enrichment thread if not already running.
    Safe to call multiple times — only one thread ever runs.
    """
    global _enrichment_thread, _enrichment_running

    if _enrichment_running:
        logger.info("[Phase 2] Enrichment thread already running — skipping duplicate start.")
        return

    _enrichment_thread = threading.Thread(
        target=_run_llm_enrichment_loop,
        name="llm-enrichment",
        daemon=True  # dies with main process — no orphan threads
    )
    _enrichment_thread.start()
    logger.info("[Phase 2] LLM enrichment thread launched in background.")


def is_enrichment_running() -> bool:
    return _enrichment_running


# ─────────────────────────────────────────────
# Main entrypoint (called by scheduler + API)
# ─────────────────────────────────────────────
def execute_autonomous_pipeline() -> Dict[str, Any]:
    """
    Two-phase pipeline:
    - Phase 1 runs synchronously (fast scrape, ~60s)
    - Phase 2 runs in a daemon background thread (LLM enrichment, no timeout)
    Returns immediately after Phase 1 with a status dict.
    """
    settings = load_settings()
    sched_cfg = settings.get("scheduler", {})

    now_iso = datetime.utcnow().isoformat()
    logger.info(f"[Pipeline] Starting autonomous pipeline at {now_iso}")

    # Update status
    sched_cfg["status"] = "running"
    sched_cfg["last_run"] = now_iso
    interval = sched_cfg.get("interval_minutes", 45)
    sched_cfg["next_run"] = (datetime.utcnow() + timedelta(minutes=interval)).isoformat()
    settings["scheduler"] = sched_cfg
    save_settings(settings)

    results = {
        "timestamp": now_iso,
        "jobs_scraped": 0,
        "jobs_queued_for_enrichment": 0,
        "enrichment_running": False,
        "errors": []
    }

    try:
        # PHASE 1: Fast scrape
        phase1_result = phase1_scrape_jobs()
        results["jobs_scraped"] = phase1_result["jobs_scraped"]

        # Count how many need enrichment
        pending = _get_unenriched_jobs(limit=50)
        results["jobs_queued_for_enrichment"] = len(pending)

        # PHASE 2: Kick off background LLM enrichment (non-blocking)
        start_llm_enrichment_background()
        results["enrichment_running"] = True

    except Exception as e:
        logger.error(f"[Pipeline] Error: {e}")
        results["errors"].append(str(e))
    finally:
        # Phase 1 done — mark scheduler as idle again
        # (Phase 2 runs independently in background)
        sched_cfg["status"] = "idle"
        settings["scheduler"] = sched_cfg
        save_settings(settings)

    logger.info(f"[Pipeline] Phase 1 complete: {results}")
    return results
