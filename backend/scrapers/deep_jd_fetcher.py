import logging
import re
import urllib.parse
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from curl_cffi import requests

logger = logging.getLogger("getmehired.deep_jd_fetcher")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

def is_generic_homepage(url: str) -> bool:
    """Check if the URL is just a generic company homepage rather than a specific job posting."""
    if not url:
        return True
    try:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.strip("/")
        if not path or path in ["home", "index", "index.html"]:
            return True
        if path.lower() in ["careers", "jobs", "about", "contact"]:
            return True
    except Exception:
        pass
    return False

def extract_linkedin_job_id(url: str) -> Optional[str]:
    """Extract numeric job ID from a LinkedIn job URL."""
    m = re.search(r"/jobs/view/(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"currentJobId=(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"-(\d+)(?:\?|$)", url)
    if m and len(m.group(1)) >= 8:
        return m.group(1)
    return None

def fetch_with_curl_cffi(url: str) -> Dict[str, Any]:
    """
    Tier 1 Fast Path: Fetch page content using curl_cffi Chrome 124 TLS fingerprinting.
    Takes < 1s, bypasses Cloudflare, and uses LinkedIn Guest Job API for LinkedIn URLs.
    """
    target_url = url
    is_linkedin = "linkedin.com" in url

    if is_linkedin:
        li_job_id = extract_linkedin_job_id(url)
        if li_job_id:
            target_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{li_job_id}"

    try:
        resp = requests.get(
            target_url,
            impersonate="chrome124",
            timeout=12,
            headers=HEADERS,
            allow_redirects=True
        )
        if resp.status_code != 200:
            return {"fetched": False, "status_code": resp.status_code}

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "svg"]):
            tag.decompose()

        jd_text = ""
        if is_linkedin:
            markup = soup.select_one(".show-more-less-html__markup, .description__text")
            if markup:
                jd_text = markup.get_text(separator=" ", strip=True)

        if not jd_text:
            jd_selectors = [
                ".job-description", "#job-description", ".description__text",
                ".show-more-less-html__markup", ".posting-requirements",
                ".content", "article", "main", ".job-details",
                ".job-detail", ".description", ".content-wrapper"
            ]
            for selector in jd_selectors:
                elem = soup.select_one(selector)
                if elem:
                    extracted = elem.get_text(separator=" ", strip=True)
                    if len(extracted) > 150:
                        jd_text = extracted
                        break

        if not jd_text:
            body = soup.find("body")
            if body:
                jd_text = body.get_text(separator=" ", strip=True)

        jd_text = re.sub(r"\s+", " ", jd_text).strip()
        h1 = soup.find("h1")
        extracted_title = h1.get_text(strip=True) if h1 else ""

        return {
            "fetched": bool(len(jd_text) >= 200),
            "final_url": url,
            "extracted_title": extracted_title,
            "full_description": jd_text[:6000] if jd_text else None,
            "html": resp.text
        }
    except Exception as e:
        logger.warning(f"Tier 1 curl_cffi fetch notice for {url}: {e}")
        return {"fetched": False, "error": str(e)}

def fetch_with_playwright_fallback(url: str) -> Dict[str, Any]:
    """
    Tier 2 Fallback: Spawns Playwright headless Chromium for dynamic SPA / client-side React pages.
    Executes JavaScript, waits for dynamic DOM hydration (like #khembedjobs), and extracts full rendered text.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(2000)

            title = page.title()

            # Try to click common expanders
            for expander in ["button:has-text('Read More')", "button:has-text('Show More')", "text=View Open Roles"]:
                try:
                    if page.is_visible(expander):
                        page.click(expander, timeout=2000)
                        page.wait_for_timeout(500)
                except Exception:
                    pass

            text = page.inner_text("body")
            text = re.sub(r"\s+", " ", text).strip()

            # Discover specific ATS job links inside the dynamic DOM
            discovered_job_links = []
            try:
                links = page.eval_on_selector_all("a", "elements => elements.map(e => ({ text: e.innerText, href: e.href }))")
                for l in links:
                    href = l.get("href", "")
                    if any(ats in href.lower() for ats in ["jobdetails", "/job/", "/jobs/", "keka.com", "lever.co", "greenhouse.io", "ashbyhq.com"]):
                        discovered_job_links.append(l)
            except Exception:
                pass

            browser.close()

            return {
                "fetched": bool(len(text) >= 200),
                "final_url": url,
                "extracted_title": title,
                "full_description": text[:6000] if text else None,
                "discovered_job_links": discovered_job_links,
                "used_playwright": True
            }
    except Exception as e:
        logger.warning(f"Tier 2 Playwright fallback notice for {url}: {e}")
        return {"fetched": False, "error": str(e), "used_playwright": True}

def fetch_deep_job_details(job_url: str) -> Dict[str, Any]:
    """
    Unified Hybrid Crawler:
    1. Tier 1: curl_cffi fast path (< 1s, lightweight, zero bot detection)
    2. Tier 2: Playwright headless browser fallback (only if Tier 1 gets < 250 chars or encounters dynamic SPA)
    """
    if not job_url:
        return {"is_generic_url": True, "fetched": False, "full_description": None}

    # Reject plain root homepages (e.g. https://zocket.com without path)
    if is_generic_homepage(job_url) and not ("/careers" in job_url or "/jobs" in job_url):
        return {
            "is_generic_url": True,
            "fetched": False,
            "full_description": None
        }

    # --- Tier 1: Fast Path ---
    tier1_res = fetch_with_curl_cffi(job_url)
    tier1_desc = tier1_res.get("full_description") or ""

    # Check if page hints at client-side loader (e.g. khembedjobs, React loading spinner)
    html = tier1_res.get("html", "")
    is_spa_loader = any(s in html.lower() for s in ["khembedjobs", "loading open positions", "loading positions", "open-positions"])

    # If Tier 1 retrieved rich JD text (>= 250 chars) and does NOT have a pending SPA loader, return immediately!
    if tier1_res.get("fetched") and len(tier1_desc) >= 250 and not is_spa_loader:
        return {
            "fetched": True,
            "final_url": job_url,
            "extracted_title": tier1_res.get("extracted_title", ""),
            "full_description": tier1_desc,
            "is_generic_url": False,
            "used_tier": 1
        }

    # --- Tier 2: Playwright Dynamic Fallback ---
    logger.info(f"[Deep JD] Tier 1 yielded only {len(tier1_desc)} chars (is_spa={is_spa_loader}). Engaging Playwright fallback for {job_url}...")
    tier2_res = fetch_with_playwright_fallback(job_url)
    tier2_desc = tier2_res.get("full_description") or ""

    if tier2_res.get("fetched") and len(tier2_desc) >= 200:
        return {
            "fetched": True,
            "final_url": job_url,
            "extracted_title": tier2_res.get("extracted_title", ""),
            "full_description": tier2_desc,
            "discovered_job_links": tier2_res.get("discovered_job_links", []),
            "is_generic_url": False,
            "used_tier": 2
        }

    # Fallback to whatever Tier 1 found if Tier 2 also returned minimal text
    return {
        "fetched": bool(len(tier1_desc) > 0),
        "final_url": job_url,
        "extracted_title": tier1_res.get("extracted_title", ""),
        "full_description": tier1_desc or None,
        "is_generic_url": False,
        "used_tier": 1
    }
