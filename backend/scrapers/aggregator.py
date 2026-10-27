import logging
from typing import List, Dict, Any
from backend.config import load_settings
from backend.scrapers.jobspy_scraper import scrape_with_jobspy
from backend.scrapers.naukri_scraper import search_naukri
from backend.scrapers.wellfound_scraper import search_wellfound
from backend.scrapers.startup_finder import discover_ai_startups
from backend.database import save_job

logger = logging.getLogger(__name__)

def run_job_search(
    roles: List[str] = None,
    locations: List[str] = None,
    max_results: int = 5,
    max_total_jobs: int = 20
) -> List[Dict[str, Any]]:
    """
    Execute unified multi-source job search across enabled platforms.
    Caps batch at max_total_jobs (default 20) so local LLM can finish enrichment within 45 mins.
    """
    settings = load_settings()
    sources_cfg = settings.get("sources", {})
    
    if not roles:
        roles = settings.get("target_roles", ["Software Engineer"])
    if not locations:
        locations = settings.get("target_locations", ["Bengaluru", "Remote"])
        
    all_jobs: List[Dict[str, Any]] = []
    seen_keys = set()
    
    # Track 1: Curated & Live AI Startups (High priority leads for small companies)
    try:
        startups = discover_ai_startups(locations=locations)
        for s in startups:
            key = f"{s['company'].lower().strip()}_{s['title'].lower().strip()}"
            if key not in seen_keys:
                seen_keys.add(key)
                save_job(s)
                all_jobs.append(s)
                if len(all_jobs) >= max_total_jobs:
                    logger.info(f"Reached batch limit of {max_total_jobs} jobs.")
                    return all_jobs
    except Exception as e:
        logger.error(f"Startup discovery error: {e}")
    
    # 2. Scrape with JobSpy (LinkedIn, Indeed, Glassdoor)
    jobspy_sources = []
    if sources_cfg.get("linkedin", True):
        jobspy_sources.append("linkedin")
    if sources_cfg.get("indeed", True):
        jobspy_sources.append("indeed")
    if sources_cfg.get("glassdoor", True):
        jobspy_sources.append("glassdoor")

    sample_roles = roles[:2] if len(roles) > 2 else roles
    sample_locs = locations[:2] if len(locations) > 2 else locations

    for role in sample_roles:
        if len(all_jobs) >= max_total_jobs:
            break
        for loc in sample_locs:
            if len(all_jobs) >= max_total_jobs:
                break
            # JobSpy search (LinkedIn, Indeed, Glassdoor)
            if jobspy_sources:
                try:
                    js_jobs = scrape_with_jobspy(
                        search_term=role,
                        location=loc,
                        results_wanted=max_results,
                        sources=jobspy_sources
                    )
                    for j in js_jobs:
                        key = f"{j['company'].lower().strip()}_{j['title'].lower().strip()}"
                        if key not in seen_keys:
                            seen_keys.add(key)
                            save_job(j)
                            all_jobs.append(j)
                except Exception as e:
                    logger.error(f"JobSpy scrape failed for {role} in {loc}: {e}")

            # Naukri search (for Indian & Remote tech roles)
            if sources_cfg.get("naukri", True):
                try:
                    nk_jobs = search_naukri(
                        search_term=role,
                        location=loc,
                        results_wanted=max_results
                    )
                    for j in nk_jobs:
                        key = f"{j['company'].lower().strip()}_{j['title'].lower().strip()}"
                        if key not in seen_keys:
                            seen_keys.add(key)
                            save_job(j)
                            all_jobs.append(j)
                except Exception as e:
                    logger.error(f"Naukri scrape failed for {role} in {loc}: {e}")

            # Wellfound (AngelList Talent) startup jobs
            if sources_cfg.get("wellfound", True):
                try:
                    wf_jobs = search_wellfound(
                        search_term=role,
                        location=loc,
                        results_wanted=max_results
                    )
                    for j in wf_jobs:
                        key = f"{j['company'].lower().strip()}_{j['title'].lower().strip()}"
                        if key not in seen_keys:
                            seen_keys.add(key)
                            all_jobs.append(j)
                            if len(all_jobs) >= max_total_jobs:
                                return all_jobs[:max_total_jobs]
                except Exception as e:
                    logger.error(f"Wellfound scrape failed for {role} in {loc}: {e}")

    return all_jobs[:max_total_jobs]
