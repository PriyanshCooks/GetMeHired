import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.config import DATABASE_FILE, get_active_profile_id

def get_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Jobs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT,
        source TEXT,
        job_url TEXT,
        date_posted TEXT,
        description TEXT,
        salary TEXT,
        match_score INTEGER DEFAULT 0,
        match_rationale TEXT,
        matching_skills TEXT,     -- JSON array
        missing_skills TEXT,      -- JSON array
        tailored_bullets TEXT,    -- JSON array
        experience_required TEXT, -- e.g. '0-1 Years', '0-3 Years'
        status TEXT DEFAULT 'new', -- new, saved, applied, interviewed, rejected
        is_high_priority INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)
    
    # Contacts table (Hiring Managers, Referrers, Recruiters)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id TEXT PRIMARY KEY,
        job_id TEXT,
        company TEXT NOT NULL,
        name TEXT,
        role TEXT NOT NULL,
        search_query TEXT,
        linkedin_search_url TEXT,
        profile_url TEXT,
        is_verified_person INTEGER DEFAULT 0,
        google_search_url TEXT,
        twitter_search_url TEXT,
        github_search_url TEXT,
        hunter_url TEXT,
        twitter_dm_draft TEXT,
        contact_type TEXT,
        potential_score INTEGER DEFAULT 80,
        why_contact TEXT,
        notes TEXT,
        created_at TEXT,
        FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
    )
    """)
    
    # Outreach Messages generated
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS outreach_messages (
        id TEXT PRIMARY KEY,
        job_id TEXT,
        contact_id TEXT,
        message_type TEXT,        -- connection_note, dm, referral_request, cold_email, follow_up_note
        subject TEXT,
        content TEXT NOT NULL,
        status TEXT DEFAULT 'draft', -- draft, sent
        created_at TEXT,
        FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
    )
    """)
    
    # CRM: Tracked Applications
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id TEXT PRIMARY KEY,
        company TEXT NOT NULL,
        role TEXT NOT NULL,
        job_url TEXT,
        location TEXT,
        salary TEXT,
        status TEXT DEFAULT 'Applied', -- Saved, Applied, Outreach Sent, Follow-up Due, Interviewing, Offer, Rejected
        date_applied TEXT,
        notes TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    # CRM: Conversations & Follow-Up Tracker
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        application_id TEXT,
        company TEXT NOT NULL,
        person_name TEXT NOT NULL,
        person_role TEXT,
        profile_url TEXT,
        message_sent TEXT,
        date_sent TEXT,
        follow_up_due_date TEXT,
        status TEXT DEFAULT 'Waiting Reply', -- Waiting Reply, Follow-up Due, Follow-up Sent, Replied, Call Scheduled
        follow_up_note TEXT,
        notes TEXT,
        created_at TEXT,
        FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE SET NULL
    )
    """)
    
    conn.commit()
    # Schema migrations
    _migrate_schema(cursor)
    conn.commit()
    conn.close()

def _migrate_schema(cursor):
    """Add new columns to existing tables safely."""
    contact_cols = [
        ("google_search_url", "TEXT"),
        ("twitter_search_url", "TEXT"),
        ("github_search_url", "TEXT"),
        ("hunter_url", "TEXT"),
        ("twitter_dm_draft", "TEXT"),
        ("profile_url", "TEXT"),
        ("is_verified_person", "INTEGER DEFAULT 0"),
    ]
    cursor.execute("PRAGMA table_info(contacts)")
    existing_contact_cols = {row[1] for row in cursor.fetchall()}
    for col_name, col_type in contact_cols:
        if col_name not in existing_contact_cols:
            try:
                cursor.execute(f"ALTER TABLE contacts ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    job_cols = [
        ("experience_required", "TEXT"),
        ("candidate_id", "TEXT DEFAULT 'default'"),
        ("is_disqualified", "INTEGER DEFAULT 0"),
    ]
    cursor.execute("PRAGMA table_info(jobs)")
    existing_job_cols = {row[1] for row in cursor.fetchall()}
    for col_name, col_type in job_cols:
        if col_name not in existing_job_cols:
            try:
                cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    app_cols = [("candidate_id", "TEXT DEFAULT 'default'")]
    cursor.execute("PRAGMA table_info(applications)")
    existing_app_cols = {row[1] for row in cursor.fetchall()}
    for col_name, col_type in app_cols:
        if col_name not in existing_app_cols:
            try:
                cursor.execute(f"ALTER TABLE applications ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    conv_cols = [("candidate_id", "TEXT DEFAULT 'default'")]
    cursor.execute("PRAGMA table_info(conversations)")
    existing_conv_cols = {row[1] for row in cursor.fetchall()}
    for col_name, col_type in conv_cols:
        if col_name not in existing_conv_cols:
            try:
                cursor.execute(f"ALTER TABLE conversations ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

def save_job(job_data: Dict[str, Any]) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.utcnow().isoformat()
    job_id = job_data.get("id") or f"{job_data.get('company','').lower().replace(' ', '_')}_{hash(job_data.get('title','')+job_data.get('job_url',''))}"
    candidate_id = job_data.get("candidate_id") or get_active_profile_id()
    
    matching_skills_str = json.dumps(job_data.get("matching_skills", []))
    missing_skills_str = json.dumps(job_data.get("missing_skills", []))
    tailored_bullets_str = json.dumps(job_data.get("tailored_bullets", []))
    
    is_disq = 1 if job_data.get("is_disqualified", False) else 0

    cursor.execute("""
    INSERT INTO jobs (
        id, title, company, location, source, job_url, date_posted,
        description, salary, match_score, match_rationale,
        matching_skills, missing_skills, tailored_bullets, experience_required, status, is_high_priority, candidate_id, is_disqualified, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        match_score=excluded.match_score,
        match_rationale=excluded.match_rationale,
        matching_skills=excluded.matching_skills,
        missing_skills=excluded.missing_skills,
        tailored_bullets=excluded.tailored_bullets,
        experience_required=excluded.experience_required,
        is_high_priority=excluded.is_high_priority,
        candidate_id=excluded.candidate_id,
        is_disqualified=excluded.is_disqualified
    """, (
        job_id,
        job_data.get("title", "Untitled Role"),
        job_data.get("company", "Unknown"),
        job_data.get("location", "Not specified"),
        job_data.get("source", "jobspy"),
        job_data.get("job_url", ""),
        job_data.get("date_posted", now[:10]),
        job_data.get("description", ""),
        job_data.get("salary", "Not disclosed"),
        job_data.get("match_score", 0),
        job_data.get("match_rationale", ""),
        matching_skills_str,
        missing_skills_str,
        tailored_bullets_str,
        job_data.get("experience_required", ""),
        job_data.get("status", "new"),
        1 if job_data.get("match_score", 0) >= 75 and not is_disq else 0,
        candidate_id,
        is_disq,
        now
    ))
    conn.commit()
    conn.close()
    return job_id

def get_all_jobs(status_filter: Optional[str] = None, min_match_score: int = 0, view: str = "enriched", candidate_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    if view == "queue":
        query = "SELECT * FROM jobs WHERE match_score = 0"
        params: List[Any] = []
    elif view == "all":
        query = "SELECT * FROM jobs WHERE match_score >= ?"
        params: List[Any] = [min_match_score]
    else:  # "enriched" (default) - ONLY qualified AI analyzed & scored jobs (filter out senior / disqualified)
        threshold = max(40, min_match_score)
        query = "SELECT * FROM jobs WHERE match_score >= ? AND (is_disqualified IS NULL OR is_disqualified = 0) AND match_rationale IS NOT NULL AND match_rationale != ''"
        params = [threshold]

    if candidate_id:
        query += " AND (candidate_id = ? OR candidate_id IS NULL OR candidate_id = '')"
        params.append(candidate_id)
    
    if status_filter and status_filter != "all":
        query += " AND status = ?"
        params.append(status_filter)
        
    query += " ORDER BY match_score DESC, created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    jobs = []
    for r in rows:
        job = dict(r)
        job["matching_skills"] = json.loads(job["matching_skills"] or "[]")
        job["missing_skills"] = json.loads(job["missing_skills"] or "[]")
        job["tailored_bullets"] = json.loads(job["tailored_bullets"] or "[]")
        job_id = job["id"]
        # Fetch associated decision-maker contacts for this job
        c_cur = conn.cursor()
        c_cur.execute("""
            SELECT * FROM contacts 
            WHERE job_id = ? OR company = ? OR ? LIKE '%' || company || '%' OR company LIKE '%' || ? || '%'
            ORDER BY is_verified_person DESC, potential_score DESC
        """, (job_id, job["company"], job["company"], job["company"]))
        job["contacts"] = [dict(c) for c in c_cur.fetchall()]
        jobs.append(job)
        
    conn.close()
    return jobs

def get_queue_count(candidate_id: Optional[str] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    if candidate_id:
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE match_score = 0 AND (candidate_id = ? OR candidate_id IS NULL)", (candidate_id,))
    else:
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE match_score = 0")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_job_by_id(job_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    job = dict(row)
    job["matching_skills"] = json.loads(job["matching_skills"] or "[]")
    job["missing_skills"] = json.loads(job["missing_skills"] or "[]")
    job["tailored_bullets"] = json.loads(job["tailored_bullets"] or "[]")
    job["is_hidden_startup"] = (job.get("source") == "Hidden Startup Lead" or "startup" in str(job.get("id", "")))
    return job

def update_job_status(job_id: str, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    conn.commit()
    conn.close()

def save_contacts_for_job(job_id: str, contacts: List[Dict[str, Any]]):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    for c in contacts:
        contact_id = c.get("id") or f"cnt_{job_id[:8]}_{hash(c.get('role','')+c.get('contact_type','')+c.get('name',''))}"
        profile_url = c.get("profile_url") or c.get("linkedin_search_url") or ""
        is_verified = 1 if c.get("is_verified_person") else (1 if "linkedin.com/in/" in profile_url else 0)
        cursor.execute("""
        INSERT INTO contacts (
            id, job_id, company, name, role, search_query,
            linkedin_search_url, profile_url, is_verified_person,
            google_search_url, twitter_search_url,
            github_search_url, hunter_url, twitter_dm_draft,
            contact_type, potential_score, why_contact, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            potential_score=excluded.potential_score,
            why_contact=excluded.why_contact,
            profile_url=excluded.profile_url,
            is_verified_person=excluded.is_verified_person,
            linkedin_search_url=excluded.linkedin_search_url,
            google_search_url=excluded.google_search_url,
            twitter_search_url=excluded.twitter_search_url,
            github_search_url=excluded.github_search_url,
            hunter_url=excluded.hunter_url,
            twitter_dm_draft=excluded.twitter_dm_draft,
            notes=excluded.notes
        """, (
            contact_id,
            job_id,
            c.get("company", ""),
            c.get("name", ""),
            c.get("role", "Key Team Member"),
            c.get("search_query", ""),
            c.get("linkedin_search_url", ""),
            profile_url,
            is_verified,
            c.get("google_search_url", ""),
            c.get("twitter_search_url", ""),
            c.get("github_search_url", ""),
            c.get("hunter_url", ""),
            c.get("twitter_dm_draft", ""),
            c.get("contact_type", "Internal Referrer / Peer"),
            c.get("potential_score", 85),
            c.get("why_contact", ""),
            c.get("notes", ""),
            now
        ))
    conn.commit()
    conn.close()


def get_contacts_for_job(job_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT company FROM jobs WHERE id = ?", (job_id,))
    job_row = cursor.fetchone()
    company = job_row["company"] if job_row else ""
    cursor.execute("""
        SELECT * FROM contacts 
        WHERE job_id = ? OR (company != '' AND (company = ? OR ? LIKE '%' || company || '%' OR company LIKE '%' || ? || '%'))
        ORDER BY is_verified_person DESC, potential_score DESC
    """, (job_id, company, company, company))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_outreach_message(msg: Dict[str, Any]) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    msg_id = msg.get("id") or f"msg_{datetime.utcnow().timestamp()}"
    cursor.execute("""
    INSERT INTO outreach_messages (
        id, job_id, contact_id, message_type, subject, content, status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        content=excluded.content,
        subject=excluded.subject,
        status=excluded.status
    """, (
        msg_id,
        msg.get("job_id"),
        msg.get("contact_id"),
        msg.get("message_type", "dm"),
        msg.get("subject", ""),
        msg.get("content", ""),
        msg.get("status", "draft"),
        now
    ))
    conn.commit()
    conn.close()
    return msg_id

def get_outreach_for_job(job_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM outreach_messages WHERE job_id = ? ORDER BY created_at DESC", (job_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ----------------- CRM: Applications -----------------
def save_application(app_data: Dict[str, Any]) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    app_id = app_data.get("id") or f"app_{abs(hash(app_data.get('company','')+app_data.get('role','')))}"
    
    candidate_id = app_data.get("candidate_id") or get_active_profile_id()
    cursor.execute("""
    INSERT INTO applications (
        id, company, role, job_url, location, salary, status, date_applied, notes, candidate_id, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        company=excluded.company,
        role=excluded.role,
        status=excluded.status,
        date_applied=excluded.date_applied,
        notes=excluded.notes,
        candidate_id=excluded.candidate_id,
        updated_at=excluded.updated_at
    """, (
        app_id,
        app_data.get("company", ""),
        app_data.get("role", ""),
        app_data.get("job_url", ""),
        app_data.get("location", ""),
        app_data.get("salary", "₹7-10 LPA"),
        app_data.get("status", "Applied"),
        app_data.get("date_applied", now[:10]),
        app_data.get("notes", ""),
        candidate_id,
        now,
        now
    ))
    conn.commit()
    conn.close()
    return app_id

def get_all_applications(candidate_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if candidate_id:
        cursor.execute("SELECT * FROM applications WHERE candidate_id = ? OR candidate_id IS NULL ORDER BY updated_at DESC", (candidate_id,))
    else:
        cursor.execute("SELECT * FROM applications ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_application(app_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()

# ----------------- CRM: Conversations & Follow-ups -----------------
def save_conversation(conv_data: Dict[str, Any]) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    conv_id = conv_data.get("id") or f"conv_{abs(hash(conv_data.get('company','')+conv_data.get('person_name','')))}"
    candidate_id = conv_data.get("candidate_id") or get_active_profile_id()
    
    # Default follow-up due in 3 days
    from datetime import timedelta
    due_date = conv_data.get("follow_up_due_date")
    if not due_date:
        due_date = (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d")

    cursor.execute("""
    INSERT INTO conversations (
        id, application_id, company, person_name, person_role, profile_url,
        message_sent, date_sent, follow_up_due_date, status, follow_up_note, notes, candidate_id, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        person_name=excluded.person_name,
        person_role=excluded.person_role,
        status=excluded.status,
        follow_up_due_date=excluded.follow_up_due_date,
        follow_up_note=excluded.follow_up_note,
        notes=excluded.notes,
        candidate_id=excluded.candidate_id
    """, (
        conv_id,
        conv_data.get("application_id"),
        conv_data.get("company", ""),
        conv_data.get("person_name", ""),
        conv_data.get("person_role", ""),
        conv_data.get("profile_url", ""),
        conv_data.get("message_sent", ""),
        conv_data.get("date_sent", now[:10]),
        due_date,
        conv_data.get("status", "Waiting Reply"),
        conv_data.get("follow_up_note", ""),
        conv_data.get("notes", ""),
        candidate_id,
        now
    ))
    conn.commit()
    conn.close()
    return conv_id

def get_all_conversations(status_filter: Optional[str] = None, candidate_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM conversations WHERE 1=1"
    params = []
    if candidate_id:
        query += " AND (candidate_id = ? OR candidate_id IS NULL)"
        params.append(candidate_id)
    if status_filter and status_filter != "all":
        query += " AND status = ?"
        params.append(status_filter)
    query += " ORDER BY follow_up_due_date ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def check_and_update_due_followups(candidate_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Checks conversations and flags items where today >= follow_up_due_date as 'Follow-up Due'."""
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    cursor.execute("""
    UPDATE conversations 
    SET status = 'Follow-up Due'
    WHERE status = 'Waiting Reply' AND follow_up_due_date <= ?
    """, (today,))
    conn.commit()
    
    if candidate_id:
        cursor.execute("SELECT * FROM conversations WHERE status = 'Follow-up Due' AND (candidate_id = ? OR candidate_id IS NULL)", (candidate_id,))
    else:
        cursor.execute("SELECT * FROM conversations WHERE status = 'Follow-up Due'")
    due_items = cursor.fetchall()
    conn.close()
    return [dict(r) for r in due_items]

def clear_all_data():
    """Wipes all rows from jobs, contacts, outreach_messages, applications, and conversations tables."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations")
    cursor.execute("DELETE FROM applications")
    cursor.execute("DELETE FROM outreach_messages")
    cursor.execute("DELETE FROM contacts")
    cursor.execute("DELETE FROM jobs")
    conn.commit()
    conn.close()

# Initialize tables when module is imported
init_db()
