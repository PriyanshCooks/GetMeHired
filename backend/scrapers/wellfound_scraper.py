import logging
import urllib.parse
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://wellfound.com/"
}

def search_wellfound(
    search_term: str,
    location: str = "Remote",
    results_wanted: int = 10
) -> List[Dict[str, Any]]:
    """
    Search Wellfound (formerly AngelList Talent) for tech and startup jobs.
    100% free with $0 API fees using public search dorking and direct parsing.
    """
    jobs: List[Dict[str, Any]] = []
    
    # Query Wellfound listings via public search index
    dork = f"site:wellfound.com/jobs \"{search_term}\" \"{location}\""
    ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(dork)}"
    
    try:
        with httpx.Client(headers=HEADERS, timeout=12.0, follow_redirects=True) as client:
            resp = client.get(ddg_url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results = soup.select(".result__body")
                for item in results[:results_wanted]:
                    title_elem = item.select_one(".result__title a")
                    snippet_elem = item.select_one(".result__snippet")
                    if not title_elem:
                        continue
                        
                    raw_title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    if "uddg=" in href:
                        href = urllib.parse.unquote(href.split("uddg=")[-1].split("&")[0])
                        
                    # Filter for actual wellfound job links
                    if "wellfound.com" not in href or "/jobs" not in href:
                        continue
                        
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    # Extract company and role
                    company = "Startup"
                    role_title = raw_title.replace(" | Wellfound", "").replace(" - Wellfound", "").strip()
                    
                    if " at " in role_title:
                        parts = role_title.split(" at ")
                        role_title = parts[0].strip()
                        company = parts[1].split(" | ")[0].split(" - ")[0].strip()
                    elif " - " in role_title:
                        parts = role_title.split(" - ")
                        role_title = parts[0].strip()
                        company = parts[1].strip()

                    job_id = f"wellfound_{abs(hash(role_title + company + href))}"
                    
                    jobs.append({
                        "id": job_id,
                        "title": role_title,
                        "company": company,
                        "location": location,
                        "source": "Wellfound",
                        "job_url": href,
                        "date_posted": "Active",
                        "description": f"{snippet} (Wellfound Startup Role: {role_title} at {company})",
                        "salary": "Equity + Competitive",
                        "status": "new"
                    })
    except Exception as e:
        logger.warning(f"Wellfound search notice: {e}")

    return jobs
