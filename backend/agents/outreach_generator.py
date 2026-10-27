import json
from typing import Dict, Any
from backend.ollama_client import ollama_client
from backend.config import load_settings

def _llm_draft_connection_note(user_name: str, company: str, job_title: str,
                                contact_role: str, key_skill: str) -> str:
    """MICRO LLM CALL 1: Connection note ONLY (<290 chars). Tiny & fast."""
    prompt = f"""Write a LinkedIn connection request note from {user_name} to {contact_role} at {company}.

Rules:
- UNDER 290 CHARACTERS (this is critical, LinkedIn limit)
- Mention {key_skill} and {company} product
- Warm, authentic tone, no buzzwords
- End with a hook to connect

JSON ONLY: {{"connection_note": "text under 290 chars"}}"""

    result = ollama_client.generate_json(prompt=prompt)
    if result and "connection_note" in result:
        note = str(result["connection_note"]).strip()
        return note[:289] if len(note) > 289 else note
    return ""

def _llm_draft_founder_pitch(user_name: str, company: str, job_title: str,
                              linkedin_url: str, github_url: str) -> str:
    """MICRO LLM CALL 2: Founder/CTO direct pitch DM. Short & punchy."""
    prompt = f"""Write a 80-100 word LinkedIn DM from {user_name} to a Founder/CTO at {company}.

Context: Candidate specializes in Agentic AI, LangGraph, FastMCP (MCP servers), RAG pipelines.
Production experience: PropVIVO (enterprise multi-agent workflows), TechSwarm (supervisor agents).
Ask: 10-min intro chat or demo call.
Links: LinkedIn={linkedin_url}, GitHub={github_url}

Make it punchy, real, zero fluff. Don't start with "Hi there" or "Hope you're well".

JSON ONLY: {{"pitch": "80-100 word DM text"}}"""

    result = ollama_client.generate_json(prompt=prompt)
    if result and "pitch" in result:
        return str(result["pitch"]).strip()
    return ""

def _llm_draft_cold_email(user_name: str, company: str, job_title: str,
                           contact_role: str, linkedin_url: str, phone: str) -> Dict[str, str]:
    """MICRO LLM CALL 3: Cold email subject + body."""
    prompt = f"""Write a cold email from {user_name} applying for {job_title} at {company} to {contact_role}.

Candidate: Agentic AI Engineer, LangGraph + FastMCP + RAG specialist. UPES B.Tech AIML 8.68 CGPA.
Internships: PropVIVO (agentic workflows), TechSwarm (supervisor agents), ONGC (RAG chatbot).

Write:
1. High open-rate subject line
2. 3-paragraph email body with: hook → value prop → CTA
3. Close with LinkedIn and phone

JSON ONLY: {{"subject": "line", "body": "3-para email"}}"""

    result = ollama_client.generate_json(prompt=prompt)
    if result and "subject" in result:
        return {"subject": str(result["subject"]).strip(), "body": str(result.get("body", "")).strip()}
    return {}

def _llm_draft_referral_ask(user_name: str, company: str, job_title: str,
                             job_url: str, linkedin_url: str) -> str:
    """MICRO LLM CALL 4: Referral request with copy-pasteable portal blurb."""
    prompt = f"""Write a referral request from {user_name} to a peer engineer at {company} for the {job_title} role.

Include a ready-made 2-sentence blurb they can paste into their internal referral portal.
{user_name}: Agentic AI engineer, LangGraph + FastMCP + RAG, UPES AIML 8.68 CGPA.
Job URL: {job_url or company + ' careers page'}
Profile: {linkedin_url}

Keep it under 150 words, polite, make the blurb easy to copy.

JSON ONLY: {{"referral_message": "full message with blurb clearly marked"}}"""

    result = ollama_client.generate_json(prompt=prompt)
    if result and "referral_message" in result:
        return str(result["referral_message"]).strip()
    return ""

def generate_outreach_messages(
    job: Dict[str, Any],
    contact: Dict[str, Any],
    user_profile: Dict[str, Any],
    tone: str = "direct"
) -> Dict[str, str]:
    """
    Generate all 5 outreach formats using SEPARATE focused micro LLM calls.
    Each call is small + laser-focused → maximizes qwen3.5:4b quality.
    Falls back to proven high-converting templates if LLM times out.
    """
    settings = load_settings()
    company = job.get("company", "Company")
    job_title = job.get("title", "AI / ML Engineer")
    job_url = job.get("job_url", "")
    is_hidden = job.get("is_hidden_startup", False)

    contact_role = contact.get("role", "Founder / Engineering Leader")
    contact_type = contact.get("contact_type", "Founder / CEO")

    user_name = user_profile.get("full_name") or "Candidate"
    headline = user_profile.get("headline") or "AI / Software Engineer"
    education = user_profile.get("education", "")
    user_skills = user_profile.get("skills", ["AI Systems", "Python", "FastAPI"])
    key_skill = user_skills[1] if len(user_skills) > 1 else (user_skills[0] if user_skills else "AI Systems")
    skills_preview = ", ".join(user_skills[:3]) if user_skills else "modern software architectures"

    linkedin_url = user_profile.get("linkedin_url", "")
    github_url = user_profile.get("github_url", "")
    phone = user_profile.get("phone", "")

    is_founder = any(k in contact_type.lower() or k in contact_role.lower()
                     for k in ["founder", "ceo", "cto", "co-founder"])

    # --- Run micro LLM calls sequentially (small model, don't overload) ---
    connection_note = _llm_draft_connection_note(user_name, company, job_title, contact_role, key_skill)
    inmail_dm = ""
    if is_founder:
        inmail_dm = _llm_draft_founder_pitch(user_name, company, job_title, linkedin_url, github_url)
    referral_msg = _llm_draft_referral_ask(user_name, company, job_title, job_url, linkedin_url)
    email_data = _llm_draft_cold_email(user_name, company, job_title, contact_role, linkedin_url, phone)

    # Always use proven static 3-day follow-up (LLM not needed here)
    contact_footer = " | ".join([x for x in [linkedin_url, phone] if x])
    follow_up = (
        f"Hi, just following up on my note from a few days ago about the {job_title} role at {company}. "
        f"I'm genuinely excited about what your team is building. Would love to share a quick 2-min demo "
        f"of the {key_skill} systems I've built — do you have 5 minutes this week?\n\n"
        f"Best,\n{user_name}\n{contact_footer}"
    )

    # Fallback templates (used when LLM times out)
    if not connection_note:
        if is_founder:
            connection_note = f"Hi! Following {company}'s roadmap closely. I build systems with {skills_preview}. Would love to connect!"
        else:
            connection_note = f"Hi! Closely tracking {company}'s engineering work. Applied for the {job_title} role — experience in {skills_preview}. Would love to connect!"
        if len(connection_note) > 289:
            connection_note = connection_note[:286] + "..."

    if not inmail_dm:
        inmail_dm = (
            f"I build production {headline} systems with hands-on experience in {skills_preview}.\n\n"
            f"I see {company} is moving fast in this space — I'd love to contribute. "
            f"Open to a 10-min chat or I can share a quick demo?\n\n{user_name} | {linkedin_url}"
        )

    if not referral_msg:
        edu_blurb = f", with a background from {education}" if education else ""
        referral_msg = (
            f"Hi, saw you're at {company} — I recently applied for the {job_title} role and would really appreciate a referral.\n\n"
            f"Here's a blurb for the portal:\n"
            f'"{user_name} is a {headline} specializing in {skills_preview}{edu_blurb}."\n\n'
            f"Resume & Profile: {linkedin_url}\nJob: {job_url or company + ' careers'}\n\nThanks so much!"
        )

    cold_email_subject = email_data.get("subject") or f"{job_title} Application — {user_name} ({key_skill})"
    footer_links = " | ".join([x for x in [f"LinkedIn: {linkedin_url}" if linkedin_url else "", f"GitHub: {github_url}" if github_url else "", f"Phone: {phone}" if phone else ""] if x])
    cold_email_body = email_data.get("body") or (
        f"Hi,\n\nI'm writing to express my strong interest in the {job_title} role at {company}.\n\n"
        f"I specialize in {headline} with hands-on experience in {skills_preview}.\n\n"
        f"Could we schedule a 10-minute call this week?\n\n"
        f"{footer_links}\n\nBest regards,\n{user_name}"
    )

    return {
        "connection_note": connection_note,
        "inmail_dm": inmail_dm,
        "referral_request": referral_msg,
        "cold_email_subject": cold_email_subject,
        "cold_email_body": cold_email_body,
        "follow_up_note": follow_up
    }
