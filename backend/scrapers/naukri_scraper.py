import logging
import urllib.parse
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.naukri.com/"
}

def search_naukri(
    search_term: str,
    location: str = "Bengaluru",
    results_wanted: int = 15
) -> List[Dict[str, Any]]:
    """
    Search Naukri.com for Indian tech roles with multi-layer fallback.
    1. Naukri Direct Search
    2. DuckDuckGo / SearX / Google dork for site:naukri.com
    """
    jobs: List[Dict[str, Any]] = []
    slug_term = search_term.lower().replace(" ", "-")
    slug_loc = location.lower().replace(" ", "-")
    
    # Method 1: Direct Naukri Search Page
    url = f"https://www.naukri.com/{slug_term}-jobs-in-{slug_loc}"
    try:
        with httpx.Client(headers=HEADERS, timeout=12.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200 and "jobTuple" in resp.text:
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select("div.srp-jobtuple-wrapper, article.jobTuple")
                for card in cards[:results_wanted]:
                    title_elem = card.select_one("a.title, .title")
                    comp_elem = card.select_one("a.comp-name, .subTitle")
                    loc_elem = card.select_one("span.loc-wrap, .location")
                    exp_elem = card.select_one("span.exp-wrap, .experience")
                    sal_elem = card.select_one("span.sal-wrap, .salary")
                    desc_elem = card.select_one("span.job-desc, .job-description")
                    
                    if not title_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    company = comp_elem.get_text(strip=True) if comp_elem else "Hiring Company"
                    job_link = title_elem.get("href", "")
                    if job_link and not job_link.startswith("http"):
                        job_link = f"https://www.naukri.com{job_link}"
                        
                    loc = loc_elem.get_text(strip=True) if loc_elem else location
                    exp = exp_elem.get_text(strip=True) if exp_elem else ""
                    sal = sal_elem.get_text(strip=True) if sal_elem else "Not disclosed"
                    desc = desc_elem.get_text(strip=True) if desc_elem else f"Naukri opening for {title} at {company} ({exp})."
                    
                    # Target 0-3 years roles: skip senior / lead / staff titles
                    is_senior_title = bool(re.search(r"\b(senior|sr\.?|lead|principal|staff|architect|director|head of|vp)\b", title.lower()))
                    exp_m = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)", exp)
                    if is_senior_title or (exp_m and int(exp_m.group(1)) >= 4):
                        continue
                    
                    jobs.append({
                        "id": f"naukri_{abs(hash(title + company + job_link))}",
                        "title": title,
                        "company": company,
                        "location": loc,
                        "source": "Naukri",
                        "job_url": job_link or f"https://www.naukri.com/{slug_term}-jobs",
                        "date_posted": "Recent",
                        "description": f"{desc} | Experience: {exp} | Location: {loc}",
                        "salary": sal,
                        "status": "new"
                    })
    except Exception as e:
        logger.warning(f"Direct Naukri crawl notice: {e}")

    # Method 2: Public search engine index lookup (site:naukri.com)
    if len(jobs) < 3:
        try:
            dork = f"site:naukri.com/job-listings \"{search_term}\" \"{location}\""
            ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(dork)}"
            with httpx.Client(headers={"User-Agent": HEADERS["User-Agent"]}, timeout=10.0) as client:
                res = client.get(ddg_url)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.select(".result__body")
                    for item in links[:results_wanted]:
                        title_tag = item.select_one(".result__title a")
                        snippet_tag = item.select_one(".result__snippet")
                        if not title_tag:
                            continue
                        full_title = title_tag.get_text(strip=True)
                        href = title_tag.get("href", "")
                        # Parse actual target URL if duckduckgo redirect
                        if "uddg=" in href:
                            href = urllib.parse.unquote(href.split("uddg=")[-1].split("&")[0])
                        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                        
                        # Extract company and clean title
                        comp = "Naukri Employer"
                        if " - " in full_title:
                            parts = full_title.split(" - ")
                            clean_title = parts[0]
                            comp = parts[1].replace("Naukri.com", "").strip() or comp
                        else:
                            clean_title = full_title.replace(" | Naukri.com", "").strip()

                        jobs.append({
                            "id": f"naukri_{abs(hash(clean_title + comp + href))}",
                            "title": clean_title,
                            "company": comp,
                            "location": location,
                            "source": "Naukri",
                            "job_url": href,
                            "date_posted": "Active",
                            "description": snippet or f"{clean_title} job opportunity on Naukri India.",
                            "salary": "Competitive",
                            "status": "new"
                        })
        except Exception as e:
            logger.warning(f"Naukri dork lookup notice: {e}")

    return jobs
