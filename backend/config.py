import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# Load .env if present
try:
    from dotenv import load_dotenv
    BASE_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
CONFIG_FILE = DATA_DIR / "settings.json"
DATABASE_FILE = DATA_DIR / "getmehired.db"

def _env_str(key: str, default: str) -> str:
    val = os.getenv(key)
    return val if val is not None else default

def _env_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is not None:
        try:
            return int(val)
        except ValueError:
            pass
    return default

def _env_float(key: str, default: float) -> float:
    val = os.getenv(key)
    if val is not None:
        try:
            return float(val)
        except ValueError:
            pass
    return default

def _env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is not None:
        return val.strip().lower() in ("true", "1", "yes", "on")
    return default

def _env_list(key: str, default: List[str]) -> List[str]:
    val = os.getenv(key)
    if val is not None:
        items = [x.strip() for x in val.split(",") if x.strip()]
        return items if items else default
    return default

# Read active profile ID from env or fallback
ACTIVE_PROFILE_ID = _env_str("ACTIVE_PROFILE_ID", "default")

# Default User Profile built from environment variables
DEFAULT_USER_PROFILE: Dict[str, Any] = {
    "id": ACTIVE_PROFILE_ID,
    "full_name": _env_str("USER_FULL_NAME", "AI Engineer"),
    "headline": _env_str("USER_HEADLINE", "Agentic AI & GenAI Systems Engineer | LangGraph • FastMCP • RAG • FastAPI"),
    "email": _env_str("USER_EMAIL", ""),
    "phone": _env_str("USER_PHONE", ""),
    "location": _env_str("USER_LOCATION", "Remote / India"),
    "education": _env_str("USER_EDUCATION", "B.Tech Computer Science (AIML)"),
    "linkedin_url": _env_str("USER_LINKEDIN_URL", ""),
    "linkedin_cookie_li_at": _env_str("USER_LINKEDIN_COOKIE", ""),
    "naukri_url": _env_str("USER_NAUKRI_URL", ""),
    "naukri_username": _env_str("USER_NAUKRI_USERNAME", ""),
    "wellfound_url": _env_str("USER_WELLFOUND_URL", ""),
    "github_url": _env_str("USER_GITHUB_URL", ""),
    "portfolio_url": _env_str("USER_PORTFOLIO_URL", ""),
    "ntfy_topic": _env_str("NTFY_TOPIC", "getmehired_alerts"),
    "summary": _env_str(
        "USER_SUMMARY",
        "AI/ML Engineer specializing in Agentic AI, Generative AI, and production-ready AI systems with hands-on experience building multi-agent workflows, tool integrations, and RAG pipelines."
    ),
    "skills": _env_list("USER_SKILLS", [
        "Python", "LangGraph", "Agentic AI", "Model Context Protocol (MCP)", "FastMCP",
        "Generative AI", "RAG", "Agentic RAG", "Multi-Agent Systems", "FastAPI",
        "Docker", "PyTorch", "TensorFlow", "PostgreSQL", "Prompt Engineering"
    ]),
    "experience_years": _env_int("USER_EXPERIENCE_YEARS", 1),
    "agent_directives": _env_str(
        "AGENT_DIRECTIVES",
        "Target fast-moving AI startups and product companies with 50-300 employees offering 7-10 LPA. Strictly avoid mass IT service firms. For small startups, identify Founders, CEOs, and CTOs directly since they hire via LinkedIn/Email. Highlight real-world project workflows and tool calling in all outreach."
    ),
    "resume_text": "",
    "cover_letter_template": ""
}

# Stage Banner configuration
DEFAULT_STAGE: Dict[str, Any] = {
    "title": _env_str("STAGE_BANNER_TITLE", ""),
    "description": _env_str("STAGE_BANNER_DESCRIPTION", ""),
    "subtitle": _env_str("STAGE_BANNER_SUBTITLE", ""),
    "badge_text": _env_str("STAGE_BANNER_BADGE_TEXT", _env_str("STAGE_BADGE_TEXT", "")),
    "button_text": _env_str("STAGE_BANNER_BUTTON_TEXT", "Start Live Startup & Job Hunt")
}

DEFAULT_SETTINGS: Dict[str, Any] = {
    # Server & LLM Settings
    "ollama_base_url": _env_str("OLLAMA_BASE_URL", "http://localhost:11434"),
    "ollama_model": _env_str("OLLAMA_MODEL", "qwen3.5:4b"),
    "llm_temperature": _env_float("LLM_TEMPERATURE", 0.4),

    # Stage Banner
    "stage": DEFAULT_STAGE,

    # Search Preferences
    "target_roles": _env_list("TARGET_ROLES", [
        "Agentic AI Engineer",
        "Generative AI Engineer",
        "Junior AI Engineer",
        "Associate AIML Engineer",
        "AI Systems Engineer"
    ]),
    "target_locations": _env_list("TARGET_LOCATIONS", [
        "Gurugram",
        "Pune",
        "Surat",
        "Dehradun",
        "Remote"
    ]),
    "experience_level": _env_str("EXPERIENCE_LEVEL", "0-3 years"),
    "target_salary_min": _env_int("TARGET_SALARY_MIN", 700000),
    "target_salary_max": _env_int("TARGET_SALARY_MAX", 1000000),
    "target_salary_display": _env_str("TARGET_SALARY_DISPLAY", "₹7-10 LPA"),
    "company_size": _env_str("COMPANY_SIZE", "50-300 employees"),
    "remote_only": _env_bool("REMOTE_ONLY", False),
    "max_results_per_source": _env_int("MAX_RESULTS_PER_SOURCE", 15),

    # Scraper Source Toggles
    "sources": {
        "linkedin": _env_bool("SOURCE_LINKEDIN", True),
        "naukri": _env_bool("SOURCE_NAUKRI", True),
        "wellfound": _env_bool("SOURCE_WELLFOUND", True),
        "indeed": _env_bool("SOURCE_INDEED", True),
        "glassdoor": _env_bool("SOURCE_GLASSDOOR", True)
    },

    # Custom Agent Directives
    "agent_directives": _env_str(
        "AGENT_DIRECTIVES",
        "Target fast-moving AI startups and product companies with 50-300 employees offering 7-10 LPA. Strictly avoid mass IT service firms. For small startups, identify Founders, CEOs, and CTOs directly since they hire via LinkedIn/Email. Highlight real-world project workflows and tool calling in all outreach."
    ),

    # Excluded Companies / Blacklist
    "excluded_companies": _env_list("EXCLUDED_COMPANIES", [
        "TCS", "Infosys", "Wipro", "Cognizant", "Accenture", "Capgemini",
        "Tech Mahindra", "HCLTech", "LTIMindtree", "Mphasis", "Hexaware",
        "IBM", "DXC Technology", "Birlasoft", "Persistent Systems"
    ]),

    # Autonomous Multi-Agent Runner
    "scheduler": {
        "enabled": _env_bool("SCHEDULER_ENABLED", True),
        "interval_minutes": _env_int("SCHEDULER_INTERVAL_MINUTES", 30),
        "last_run": None,
        "next_run": None,
        "auto_eval_fit": _env_bool("AUTO_EVAL_FIT", True),
        "auto_find_contacts": _env_bool("AUTO_FIND_CONTACTS", True),
        "auto_draft_outreach": _env_bool("AUTO_DRAFT_OUTREACH", True),
        "auto_notify_threshold": _env_int("AUTO_NOTIFY_THRESHOLD", 75),
        "status": "idle"
    },

    # Notification Settings (iPhone, Email, Telegram)
    "notifications": {
        "ntfy_enabled": _env_bool("NTFY_ENABLED", True),
        "ntfy_topic": _env_str("NTFY_TOPIC", "getmehired_alerts"),
        "email_enabled": _env_bool("EMAIL_ENABLED", False),
        "email_smtp_host": _env_str("EMAIL_SMTP_HOST", "smtp.gmail.com"),
        "email_smtp_port": _env_int("EMAIL_SMTP_PORT", 587),
        "email_user": _env_str("EMAIL_USER", ""),
        "email_pass": _env_str("EMAIL_PASS", ""),
        "email_recipient": _env_str("EMAIL_RECIPIENT", ""),
        "telegram_enabled": _env_bool("TELEGRAM_ENABLED", False),
        "telegram_bot_token": _env_str("TELEGRAM_BOT_TOKEN", ""),
        "telegram_chat_id": _env_str("TELEGRAM_CHAT_ID", "")
    },

    # Active Profile & Multi-Profile Support
    "active_profile_id": ACTIVE_PROFILE_ID,
    "profiles": {
        ACTIVE_PROFILE_ID: DEFAULT_USER_PROFILE
    },
    "user_profile": DEFAULT_USER_PROFILE
}

def _resolve_stage_text(stage: Dict[str, Any], profile: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to dynamically format template strings in stage settings."""
    resolved = dict(stage)
    name = profile.get("full_name") or "Candidate"
    salary = settings.get("target_salary_display") or "7-10 LPA"
    roles = settings.get("target_roles", ["AI / Software Engineer"])
    role = roles[0] if roles else "AI Engineer"
    locations = ", ".join(settings.get("target_locations", ["Remote"]))

    def _fmt(val: str, default_str: str) -> str:
        if not val:
            return default_str
        return val.replace("{name}", name).replace("{salary}", salary).replace("{role}", role).replace("{locations}", locations)

    resolved["title"] = _fmt(resolved.get("title", ""), f"Stage Ready for {name} ({salary} {role})")
    resolved["description"] = _fmt(
        resolved.get("description", ""),
        f"Your profile, skills, and target criteria are pre-loaded. Click below to launch the hunt across {locations}."
    )
    resolved["subtitle"] = _fmt(
        resolved.get("subtitle", ""),
        f"{' • '.join(roles[:3])} • {locations} ($0 Spend)"
    )
    resolved["badge_text"] = _fmt(
        resolved.get("badge_text", ""),
        f"{name.upper()} • {salary}"
    )
    resolved["button_text"] = resolved.get("button_text") or "Start Live Startup & Job Hunt"
    return resolved

def load_settings() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = DEFAULT_SETTINGS.copy()
            for k, v in data.items():
                if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                    merged[k] = merged[k].copy()
                    merged[k].update(v)
                else:
                    merged[k] = v

            # Clean any legacy un-tracked profiles (like Diksha)
            if "profiles" in merged and isinstance(merged["profiles"], dict):
                merged["profiles"].pop("diksha", None)
                if not merged["profiles"]:
                    merged["profiles"] = {ACTIVE_PROFILE_ID: DEFAULT_USER_PROFILE.copy()}
            else:
                merged["profiles"] = {ACTIVE_PROFILE_ID: DEFAULT_USER_PROFILE.copy()}

            active_id = merged.get("active_profile_id", ACTIVE_PROFILE_ID)
            if active_id not in merged["profiles"]:
                active_id = list(merged["profiles"].keys())[0]
                merged["active_profile_id"] = active_id

            # Sync active profile into user_profile
            merged["user_profile"] = merged["profiles"][active_id]

            # Resolve stage text dynamically
            merged["stage"] = _resolve_stage_text(
                merged.get("stage", DEFAULT_STAGE),
                merged["user_profile"],
                merged
            )

            return merged
    except Exception as e:
        print(f"Error loading settings, using defaults: {e}")
        return DEFAULT_SETTINGS.copy()

def save_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Never persist diksha if present
        if "profiles" in settings and isinstance(settings["profiles"], dict):
            settings["profiles"].pop("diksha", None)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        return settings
    except Exception as e:
        print(f"Error saving settings: {e}")
        return settings

def get_profiles() -> Dict[str, Any]:
    settings = load_settings()
    return settings.get("profiles", {ACTIVE_PROFILE_ID: DEFAULT_USER_PROFILE})

def get_active_profile_id() -> str:
    settings = load_settings()
    return settings.get("active_profile_id", ACTIVE_PROFILE_ID)

def set_active_profile_id(profile_id: str) -> str:
    settings = load_settings()
    profiles = settings.get("profiles", {})
    if profile_id in profiles:
        settings["active_profile_id"] = profile_id
        settings["user_profile"] = profiles[profile_id]
        save_settings(settings)
    return settings.get("active_profile_id", ACTIVE_PROFILE_ID)

def get_profile_by_id(profile_id: str) -> Dict[str, Any]:
    profiles = get_profiles()
    active_id = get_active_profile_id()
    return profiles.get(profile_id, profiles.get(active_id, DEFAULT_USER_PROFILE))
