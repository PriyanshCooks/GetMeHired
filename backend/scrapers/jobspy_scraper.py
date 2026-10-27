import logging
import re
import urllib.parse
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
import pandas as pd
from jobspy import scrape_jobs
from backend.config import load_settings

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def search_linkedin_dork(search_term: str, location: str = "Bengaluru", max_results: int = 8) -> List[Dict[str, Any]]:
    """
    Search LinkedIn jobs via public search index without encountering LinkedIn 429 rate limits.
    """
    jobs = []
    dork = f"site:linkedin.com/jobs/view \"{search_term}\" \"{location}\""
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(dork)}"
    try:
        with httpx.Client(headers=HEADERS, timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select(".result__body")
                for card in cards[:max_results]:
                    title_elem = card.select_one(".result__title a")
                    snippet_elem = card.select_one(".result__snippet")
                    if not title_elem:
                        continue
                    full_title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    if "uddg=" in href:
                        href = urllib.parse.unquote(href.split("uddg=")[-1].split("&")[0])
                    if "linkedin.com/jobs/view" not in href:
                        continue
                    
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    # Parse title and company (e.g. "Software Engineer hiring at Google")
                    company = "Hiring Tech Company"
                    title = full_title.replace(" | LinkedIn", "").replace(" - LinkedIn", "").strip()
                    if " hiring " in title.lower():
                        parts = re.split(r"\s+hiring\s+", title, flags=re.IGNORECASE)
                        company = parts[0].strip()
                        title = parts[1].split(" in ")[0].strip() if len(parts) > 1 else title
                    elif " at " in title:
                        parts = title.split(" at ")
                        title = parts[0].strip()
                        company = parts[1].split(" (")[0].strip()

                    job_id = f"li_dork_{abs(hash(title + company + href))}"
                    jobs.append({
                        "id": job_id,
                        "title": title,
                        "company": company,
                        "location": location,
                        "source": "LinkedIn",
                        "job_url": href,
                        "date_posted": "Active",
                        "description": f"{snippet} (Live LinkedIn opportunity for {title} at {company})",
                        "salary": "Competitive",
                        "status": "new"
                    })
    except Exception as e:
        logger.warning(f"LinkedIn dork search notice: {e}")
    return jobs

def scrape_with_jobspy(
    search_term: str,
    location: str = "Bengaluru",
    results_wanted: int = 10,
    country_exact: str = "India",
    is_remote: bool = False,
    sources: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Scrape jobs across LinkedIn, Indeed, Glassdoor, and ZipRecruiter with anti-block fallback.
    """
    settings = load_settings()
    excluded = [c.lower() for c in settings.get("excluded_companies", [])]
    
    if sources is None:
        sources = ["indeed", "glassdoor"] # default to indeed and glassdoor first to avoid linkedin 429
        
    site_names = [s.lower() for s in sources if s.lower() in ["indeed", "glassdoor", "zip_recruiter", "linkedin"]]
    jobs: List[Dict[str, Any]] = []

    try:
        country = "India"
        if "remote" in location.lower() or "us" in location.lower() or "united states" in location.lower():
            country = "USA"
        elif country_exact:
            country = country_exact

        jobs_df: pd.DataFrame = scrape_jobs(
            site_name=site_names,
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            country_indeed=country,
            is_remote=is_remote,
            hours_old=168
        )

        if jobs_df is not None and not jobs_df.empty:
            for _, row in jobs_df.iterrows():
                title = str(row.get("title") or "").strip()
                company = str(row.get("company") or "").strip()
                if not title or not company or company.lower() == "nan":
                    continue

                # Filter out excluded companies
                if any(ex in company.lower() for ex in excluded):
                    continue

                # Target 0-3 years roles: skip senior / lead / staff / principal titles
                is_senior_title = bool(re.search(r"\b(senior|sr\.?|lead|principal|staff|architect|director|head of|vp)\b", title.lower()))
                if is_senior_title:
                    continue

                job_url = str(row.get("job_url") or "")
                job_id = f"jobspy_{abs(hash(title + company + job_url))}"
                
                description = str(row.get("description") or "")
                if description.lower() == "nan":
                    description = f"Opportunity for {title} at {company} in {location}."
                    
                salary_min = row.get("min_amount")
                salary_max = row.get("max_amount")
                currency = row.get("currency") or ""
                salary_str = "Not disclosed"
                if pd.notna(salary_min) and pd.notna(salary_max):
                    salary_str = f"{currency} {int(salary_min):,} - {int(salary_max):,}"
                elif pd.notna(salary_min):
                    salary_str = f"{currency} {int(salary_min):,}+"

                loc = str(row.get("location") or location).strip()
                if loc.lower() == "nan":
                    loc = location

                site = str(row.get("site") or "Indeed").capitalize()

                jobs.append({
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": loc,
                    "source": site,
                    "job_url": job_url,
                    "date_posted": str(row.get("date_posted") or "")[:10],
                    "description": description[:3000],
                    "salary": salary_str,
                    "status": "new"
                })
    except Exception as e:
        logger.error(f"JobSpy scrape error: {e}")

    # Fallback to search LinkedIn via public dorking if LinkedIn was requested
    if "linkedin" in [s.lower() for s in (sources or [])]:
        li_jobs = search_linkedin_dork(search_term=search_term, location=location, max_results=results_wanted)
        for lj in li_jobs:
            if not any(ex in lj["company"].lower() for ex in excluded):
                jobs.append(lj)

    return jobs
