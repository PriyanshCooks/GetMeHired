import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from typing import Dict, Any, Optional
from backend.config import load_settings

def send_iphone_ntfy(title: str, message: str, url: Optional[str] = None, priority: int = 3, topic: Optional[str] = None) -> Dict[str, Any]:
    """
    Send push notification to iPhone via ntfy.sh (100% free, no sign-up required).
    Uses ntfy's JSON publishing API to natively support full UTF-8 emojis, tags, and clickable links.
    """
    settings = load_settings()
    notif_cfg = settings.get("notifications", {})
    target_topic = (topic or notif_cfg.get("ntfy_topic", "getmehired_alerts")).strip()
    
    if not target_topic:
        return {"success": False, "error": "No ntfy topic configured"}
        
    payload = {
        "topic": target_topic,
        "title": title,
        "message": message,
        "priority": priority,
        "tags": ["briefcase", "star"]
    }
    if url:
        payload["click"] = url

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post("https://ntfy.sh", json=payload)
            if resp.status_code == 200:
                return {
                    "success": True,
                    "channel": "ntfy.sh",
                    "topic": target_topic,
                    "message": f"Delivered to topic '{target_topic}'"
                }
            else:
                return {"success": False, "error": f"ntfy error {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_email_alert(subject: str, html_body: str) -> Dict[str, Any]:
    """Send email notification via configured SMTP server."""
    settings = load_settings()
    cfg = settings.get("notifications", {})
    
    if not cfg.get("email_enabled"):
        return {"success": False, "error": "Email notifications not enabled"}
        
    host = cfg.get("email_smtp_host")
    port = cfg.get("email_smtp_port", 587)
    user = cfg.get("email_user")
    pwd = cfg.get("email_pass")
    recipient = cfg.get("email_recipient") or user
    
    if not user or not pwd or not host:
        return {"success": False, "error": "Missing SMTP credentials"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = recipient
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(user, pwd)
            server.sendmail(user, recipient, msg.as_string())
            
        return {"success": True, "channel": "email"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_job_alert(job: Dict[str, Any], topic: Optional[str] = None) -> Dict[str, Any]:
    """Send unified notification across all enabled channels for a high-match job."""
    title = f"🎯 High Fit Job: {job.get('title')} at {job.get('company')}"
    body = f"Match Score: {job.get('match_score', 0)}%\nLocation: {job.get('location')}\nSalary: {job.get('salary')}\nApply & reach out to hiring leads!"
    job_url = job.get("job_url")
    
    results = {}
    settings = load_settings()
    cfg = settings.get("notifications", {})
    
    if cfg.get("ntfy_enabled", True):
        results["ntfy"] = send_iphone_ntfy(title, body, url=job_url, priority=4, topic=topic)
        
    if cfg.get("email_enabled", False):
        html = f"""<h3>{title}</h3>
        <p><strong>Match Score:</strong> {job.get('match_score')}%</p>
        <p><strong>Location:</strong> {job.get('location')}</p>
        <p><strong>Salary:</strong> {job.get('salary')}</p>
        <p><a href="{job_url}">View Job Posting</a></p>
        """
        results["email"] = send_email_alert(title, html)
        
    return results
