import re
import json
import logging
from typing import Dict, Any, List
from backend.ollama_client import ollama_client
from backend.config import load_settings

logger = logging.getLogger("getmehired.matcher")

TECH_DICTIONARY = [
    # Core Agentic/GenAI Stack (Priyansh's primary strength)
    "python", "langgraph", "fastmcp", "mcp", "agentic ai", "generative ai", "rag",
    "agentic rag", "multi-agent", "langsmith", "langfuse", "pydantic ai", "langchain",
    "llm", "llms", "prompt engineering", "tool calling", "function calling",
    "vector database", "faiss", "chromadb", "weaviate", "pinecone", "qdrant",
    # Backend & Infrastructure
    "fastapi", "flask", "django", "rest api", "graphql", "websocket",
    "docker", "kubernetes", "azure", "aws", "gcp", "azure container apps",
    "azure functions", "azure blob", "cosmos db", "redis", "postgresql", "mongodb",
    "mssql", "mysql", "azure service bus", "kafka",
    # ML/DL
    "pytorch", "tensorflow", "keras", "scikit-learn", "opencv", "transformers",
    "hugging face", "fine-tuning", "embeddings", "semantic search",
    "machine learning", "deep learning", "nlp", "computer vision", "cnn",
    # Dev & Languages
    "git", "ci/cd", "pydantic", "pandas", "numpy", "sql", "javascript",
    "typescript", "react", "node.js", "html", "css", "linux", "bash",
    "c++", "java", "golang", "rust", "terraform",
]

def extract_tech_stack(text: str) -> List[str]:
    """Extract comprehensive technical tokens from text."""
    found = set()
    text_lower = text.lower()
    for tech in TECH_DICTIONARY:
        pattern = r"\b" + re.escape(tech) + r"\b"
        if re.search(pattern, text_lower):
            found.add(tech)
    return sorted(list(found))

def extract_experience_requirement(title: str, description: str) -> Dict[str, Any]:
    """
    Extract required years of experience from title and description.
    Target: strictly 0-3 years with highest weightage given to 0-1 years.
    Any senior role or >3 years experience (e.g. 3-6 years, 4+ years) is strictly disqualified.
    """
    full_text = f"{title} {description}".lower()
    
    # 1. Senior signals (Check BOTH title AND description)
    senior_title_pattern = r"\b(senior|sr\.?|lead|principal|staff|architect|director|head of|vp|manager)\b"
    senior_body_pattern = r"\b(looking for a senior|senior (?:ai|ml|software|engineer|developer|applied)|lead (?:ai|ml|engineer)|mentor other engineers|mentoring junior|mentoring other|3[\-–—]6 years|3 to 6 years|4[\-–—]7 years|5\+ years)\b"
    
    is_senior_title = bool(re.search(senior_title_pattern, title.lower()))
    is_senior_body = bool(re.search(senior_body_pattern, full_text))
    is_senior = is_senior_title or is_senior_body

    # 2. Fresher / Entry level signals
    is_fresher_title = bool(re.search(r"\b(fresher|freshers|entry[- ]level|intern|internship|associate|junior|jr\.?|trainee|graduate)\b", title.lower()))
    is_fresher_body = bool(re.search(r"\b(fresher|freshers can apply|fresh graduates|entry[- ]level|0 years|no experience required)\b", full_text))

    # 3. Numeric ranges supporting unicode dashes (-, –, —)
    range_match = re.search(r"(\d+)\s*(?:[\-–—]|to)\s*(\d+)\s*(?:years?|yrs?)", full_text)
    plus_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+exp", full_text)

    min_exp = None
    max_exp = None

    if range_match:
        min_exp = int(range_match.group(1))
        max_exp = int(range_match.group(2))
    elif plus_match:
        min_exp = int(plus_match.group(1))
        max_exp = min_exp + 2
    elif is_fresher_title or is_fresher_body:
        min_exp = 0
        max_exp = 1
    elif is_senior:
        min_exp = 5
        max_exp = 8

    # 4. Strict Categorization & Disqualification
    is_disqualified = False
    if is_senior:
        label = "Senior Role (Disqualified)"
        score_adj = -70
        tier = "Senior Role (Disqualified)"
        exp_reason = "Role requires senior level engineering / mentorship. Disqualified from 0-3 yrs target."
        is_disqualified = True
    elif min_exp is not None and min_exp >= 3 and (max_exp is not None and max_exp > 3):
        # e.g. 3-6 years, 3-5 years, 4-7 years
        label = f"{min_exp}-{max_exp} Years (Disqualified)"
        score_adj = -65
        tier = "Mid/Senior Stretch (Disqualified)"
        exp_reason = f"Role requires {min_exp}-{max_exp} years experience: exceeds candidate's 0-3 yrs target."
        is_disqualified = True
    elif min_exp is not None and min_exp >= 4:
        label = f"{min_exp}+ Years (Disqualified)"
        score_adj = -60
        tier = "Senior Role (Disqualified)"
        exp_reason = f"Role requires {min_exp}+ years: exceeds candidate's 0-3 yrs target."
        is_disqualified = True
    elif (min_exp is not None and min_exp <= 1 and (max_exp is None or max_exp <= 2)) or is_fresher_title or is_fresher_body:
        label = "0-1 Years (Prime Sweet Spot)"
        score_adj = 25
        tier = "Prime Target (0-1 Yrs)"
        exp_reason = "Role requires 0-1 years / Entry-Level: exact sweet spot for candidate (+25 priority boost)."
        is_disqualified = False
    elif (min_exp is not None and min_exp <= 3) and (max_exp is not None and max_exp <= 3):
        label = f"{min_exp}-{max_exp} Years (Target Match)"
        score_adj = 14
        tier = "Target Match (0-3 Yrs)"
        exp_reason = f"Role requires {min_exp}-{max_exp} years: within candidate's 0-3 years target range (+14 boost)."
        is_disqualified = False
    else:
        label = "0-3 Years (Open / Flexible)"
        score_adj = 10
        tier = "Flexible Match (0-3 Yrs)"
        exp_reason = "Flexible experience requirements: eligible for 0-3 yrs candidate (+10 bonus)."
        is_disqualified = False

    return {
        "min_exp": min_exp,
        "max_exp": max_exp,
        "label": label,
        "score_adjustment": score_adj,
        "tier": tier,
        "exp_reason": exp_reason,
        "is_sweet_spot": score_adj >= 20,
        "is_disqualified": is_disqualified
    }

def _llm_score_fit(job_title: str, company: str, job_desc_snippet: str,
                   user_skills: str, resume_snippet: str,
                   directives: str, pre_matching: List[str], pre_missing: List[str],
                   exp_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    MICRO LLM CALL 1: Score the fit (score + tier + brief reasoning only).
    Small, focused prompt — best quality from a 4B model.
    """
    exp_label = (exp_info or {}).get("label", "0-3 Years")
    exp_reason = (exp_info or {}).get("exp_reason", "")
    prompt = f"""You are a recruiter scoring a candidate fit for a job.
Candidate is actively targeting 0-3 years experience, giving highest weightage to 0-1 years.

JOB: {job_title} at {company}
EXPERIENCE REQUIRED: {exp_label} ({exp_reason})
DESCRIPTION (first 500 chars): {job_desc_snippet[:500]}

CANDIDATE SKILLS: {user_skills[:250]}
RESUME EXCERPT: {resume_snippet[:400]}

KEYWORD OVERLAP: Matching={pre_matching[:6]}, Missing={pre_missing[:4]}

Rate fit (0-100, give highest points to 0-1 yrs roles) and give a 1-sentence reason.

JSON ONLY:
{{"match_score": 88, "fit_tier": "Target Priority", "reasoning": "one sentence why"}}"""

    result = ollama_client.generate_json(prompt=prompt)
    if result and "match_score" in result:
        score = max(20, min(99, int(result.get("match_score", 60))))
        return {
            "match_score": score,
            "fit_tier": str(result.get("fit_tier", "Evaluate")),
            "reasoning": str(result.get("reasoning", ""))
        }
    return {}

def _llm_generate_bullets(job_title: str, company: str, matching_skills: List[str],
                           resume_snippet: str) -> List[str]:
    """
    MICRO LLM CALL 2: Generate 2 tailored resume achievement bullets ONLY.
    Separate focused call for maximum quality on small model.
    """
    skills_str = ", ".join(matching_skills[:5]) if matching_skills else "Python, LangGraph, FastAPI"
    prompt = f"""Write 2 tailored resume bullet points for {job_title} at {company}.

Candidate's matching skills: {skills_str}
Resume context: {resume_snippet[:400]}

Make each bullet QUANTIFIED and specific to this role.

JSON ONLY:
{{"bullets": ["bullet 1 starting with action verb", "bullet 2 starting with action verb"]}}"""

    result = ollama_client.generate_json(prompt=prompt)
    if result and "bullets" in result:
        return [str(b) for b in result["bullets"][:2] if b]
    return []

def _llm_ats_gaps(job_desc_snippet: str, user_skills: str) -> List[str]:
    """
    MICRO LLM CALL 3: Identify top 3-5 ATS keyword gaps ONLY.
    Tiny focused call.
    """
    prompt = f"""Job requires: {job_desc_snippet[:500]}
Candidate has: {user_skills[:250]}

List 3-5 important ATS keywords from the job NOT in candidate's skills.

JSON ONLY:
{{"missing_ats_keywords": ["keyword1", "keyword2", "keyword3"]}}"""

    result = ollama_client.generate_json(prompt=prompt)
    if result and "missing_ats_keywords" in result:
        return [str(k) for k in result["missing_ats_keywords"][:5] if k]
    return []

def analyze_job_fit(job: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Multi-Dimensional Resume Fit Analyzer.
    Uses 3 SEPARATE small focused LLM calls for maximum quality from qwen3.5:4b:
      1. Score fit + reasoning (fast, laser-focused)
      2. Generate tailored resume bullets (creative, unconstrained)
      3. Identify ATS keyword gaps (analytical, precise)
    Falls back to deterministic heuristics if LLM times out.
    """
    resume_text = user_profile.get("resume_text", "")
    user_skills = user_profile.get("skills", [])
    if isinstance(user_skills, str):
        user_skills = [s.strip().lower() for s in user_skills.split(",") if s.strip()]
    elif isinstance(user_skills, list):
        user_skills = [s.lower() for s in user_skills]

    user_skills_set = set(user_skills + extract_tech_stack(resume_text))

    job_title = job.get("title", "Software Engineer")
    company = job.get("company", "Target Company")
    job_desc = job.get("description", "")
    job_location = job.get("location", "")

    job_skills = set(extract_tech_stack(f"{job_title} {job_desc}"))

    # Extract experience requirements (0-3 yrs focus, highest weightage to 0-1 yrs)
    exp_info = extract_experience_requirement(job_title, job_desc)

    # Pre-compute keyword overlap (deterministic, instant)
    matching_skills = sorted(list(job_skills.intersection(user_skills_set)))
    missing_skills = sorted(list(job_skills.difference(user_skills_set)))

    settings = load_settings()
    custom_directives = settings.get("agent_directives", "")
    user_skills_str = ", ".join(list(user_skills_set)[:20])
    resume_snippet = resume_text[:800]  # short snippet for LLM context

    # --- MICRO CALL 1: Score ---
    score_result = _llm_score_fit(
        job_title, company, job_desc,
        user_skills_str, resume_snippet,
        custom_directives, matching_skills, missing_skills,
        exp_info=exp_info
    )

    # --- MICRO CALL 2: Tailored Bullets ---
    bullets = _llm_generate_bullets(job_title, company, matching_skills, resume_snippet)

    # --- MICRO CALL 3: ATS Gaps (only if LLM didn't time out on call 1) ---
    llm_missing = []
    if score_result:
        llm_missing = _llm_ats_gaps(job_desc, user_skills_str)

    # Merge results with experience weightage
    is_disq = exp_info.get("is_disqualified", False)
    if score_result:
        raw_score = score_result["match_score"]
        if is_disq:
            # Strictly cap senior/disqualified roles so they never pollute matched opportunities
            final_score = min(25, max(10, raw_score - 65))
        else:
            final_score = max(20, min(99, raw_score + exp_info["score_adjustment"]))
        reasoning = score_result.get("reasoning", "")
        rationale = f"[{exp_info['label']}] {reasoning}" if reasoning else f"[{exp_info['label']}] {exp_info['exp_reason']} Strong overlap with {company}'s requirements."

        top_matching = ', '.join(matching_skills[:3] or list(user_skills_set)[:3] or ['modern software architectures'])
        secondary_matching = ', '.join(matching_skills[3:5] or list(user_skills_set)[3:5] or ['distributed systems', 'APIs'])

        return {
            "match_score": final_score,
            "is_disqualified": is_disq,
            "match_rationale": rationale,
            "matching_skills": matching_skills,
            "missing_skills": llm_missing or missing_skills[:6],
            "experience_required": exp_info["label"],
            "tailored_bullets": bullets or [
                f"Engineered scalable solutions leveraging {top_matching}, reducing process latency and directly addressing {company}'s technical requirements.",
                f"Architected and deployed high-reliability backend services and automated pipelines utilizing {secondary_matching}."
            ]
        }

    # Fallback: fast deterministic scoring if all LLM calls timed out
    base_score = 50
    if job_skills:
        overlap_ratio = len(matching_skills) / max(1, len(job_skills))
        base_score = int(35 + (overlap_ratio * 50))
    # Apply experience weight adjustment
    if is_disq:
        base_score = 20
    else:
        base_score = max(20, min(98, base_score + exp_info["score_adjustment"]))

    top_matching = ', '.join(matching_skills[:3] or list(user_skills_set)[:3] or ['modern software architectures'])
    secondary_matching = ', '.join(matching_skills[3:5] or list(user_skills_set)[3:5] or ['distributed systems', 'APIs'])

    return {
        "match_score": base_score,
        "is_disqualified": is_disq,
        "match_rationale": (
            f"[{exp_info['label']}] {exp_info['exp_reason']} "
            f"Keyword overlap: {', '.join(matching_skills[:4]) or 'agentic ai, python'}. "
            f"Gaps: {', '.join(missing_skills[:3]) or 'none identified'}."
        ),
        "matching_skills": matching_skills,
        "missing_skills": missing_skills[:6],
        "experience_required": exp_info["label"],
        "tailored_bullets": [
            f"Led end-to-end implementation and deployment of production systems using {top_matching}, delivering measurable operational efficiency.",
            f"Designed and deployed modular microservices and automated workflows utilizing {secondary_matching} aligned with {job_title} standards."
        ]
    }
