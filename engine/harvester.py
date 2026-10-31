import re
import html
import hashlib
import requests
import concurrent.futures
from datetime import datetime

NEGATIVE_KEYWORDS = [
    'software engineer', 'software development', 'software developer',
    'backend', 'frontend', 'full stack', 'fullstack', 'firmware',
    'devops', 'infrastructure engineer', 'site reliability', 'sre',
    'ml engineer', 'machine learning engineer', 'deep learning',
    'nlp engineer', 'computer vision', 'robotics engineer',
    'clinical', 'nursing', 'veterinary', 'physician', 'biologist',
    'chemist', 'hardware engineer', 'silicon', 'embedded system',
    'security engineer', 'internal audit'
]

INTERN_PATTERN = re.compile(r'\b(intern|internship|co-op|coop|apm|fellow|fellowship|summer analyst)\b', re.IGNORECASE)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

def generate_job_id(company, title, location):
    raw = f"{company.strip().lower()}_{title.strip().lower()}_{str(location).strip().lower()}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def is_non_tech_internship(title):
    lower_title = title.lower()
    
    # Must match intern pattern
    if not INTERN_PATTERN.search(lower_title):
        return False
        
    # Must NOT contain hard technical/engineering/medical keywords
    for neg in NEGATIVE_KEYWORDS:
        if neg in lower_title:
            return False
            
    return True

def fetch_greenhouse_board(board_info):
    company = board_info["name"]
    token = board_info["token"]
    jobs = []
    
    # Use content=true to extract embedded salary/compensation text
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=6)
        if r.status_code == 200:
            data = r.json()
            for j in data.get("jobs", []):
                title = j.get("title", "")
                if is_non_tech_internship(title):
                    loc_name = j.get("location", {}).get("name", "Remote / Unspecified")
                    job_url = j.get("absolute_url", "")
                    job_id = generate_job_id(company, title, loc_name)
                    
                    # Parse timestamp
                    updated_raw = j.get("updated_at") or j.get("first_published")
                    ts = int(datetime.now().timestamp())
                    date_display = datetime.now().strftime("%b %d, %Y")
                    if updated_raw:
                        try:
                            clean_iso = updated_raw.replace("Z", "+00:00")
                            dt = datetime.fromisoformat(clean_iso)
                            ts = int(dt.timestamp())
                            date_display = dt.strftime("%b %d, %Y")
                        except Exception:
                            pass
                    
                    raw_content = html.unescape(j.get("content", ""))
                    
                    jobs.append({
                        "id": job_id,
                        "company": company,
                        "title": title,
                        "location": loc_name,
                        "url": job_url,
                        "source": "Greenhouse Direct ATS",
                        "timestamp": ts,
                        "date_posted": date_display,
                        "raw_department": j.get("departments", [{}])[0].get("name", "") if j.get("departments") else "",
                        "salary_raw": raw_content[:4000]
                    })
    except Exception:
        pass
    return jobs

def fetch_lever_board(board_info):
    company = board_info["name"]
    token = board_info["token"]
    jobs = []
    
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=6)
        if r.status_code == 200:
            postings = r.json()
            for p in postings:
                title = p.get("text", "")
                if is_non_tech_internship(title):
                    loc_name = p.get("categories", {}).get("location", "Remote / Unspecified")
                    job_url = p.get("hostedUrl", "")
                    job_id = generate_job_id(company, title, loc_name)
                    
                    # Parse Lever createdAt (ms)
                    created_at_ms = p.get("createdAt")
                    ts = int(datetime.now().timestamp())
                    date_display = datetime.now().strftime("%b %d, %Y")
                    if created_at_ms:
                        try:
                            ts = int(created_at_ms / 1000)
                            dt = datetime.fromtimestamp(ts)
                            date_display = dt.strftime("%b %d, %Y")
                        except Exception:
                            pass
                            
                    raw_desc = (p.get("descriptionPlain", "") + " " + p.get("additionalPlain", ""))
                    
                    jobs.append({
                        "id": job_id,
                        "company": company,
                        "title": title,
                        "location": loc_name,
                        "url": job_url,
                        "source": "Lever Direct ATS",
                        "timestamp": ts,
                        "date_posted": date_display,
                        "raw_department": p.get("categories", {}).get("department", ""),
                        "salary_raw": raw_desc[:4000]
                    })
    except Exception:
        pass
    return jobs

def fetch_ashby_board(board_info):
    company = board_info["name"]
    token = board_info["token"]
    jobs = []
    
    url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=6)
        if r.status_code == 200:
            data = r.json()
            for j in data.get("jobs", []):
                title = j.get("title", "")
                if is_non_tech_internship(title):
                    loc_name = j.get("location") or "Remote / Unspecified"
                    job_url = j.get("jobUrl") or j.get("applyUrl") or ""
                    job_id = generate_job_id(company, title, loc_name)
                    
                    # Parse publishedAt timestamp
                    pub_raw = j.get("publishedAt")
                    ts = int(datetime.now().timestamp())
                    date_display = datetime.now().strftime("%b %d, %Y")
                    if pub_raw:
                        try:
                            clean_iso = pub_raw.replace("Z", "+00:00")
                            dt = datetime.fromisoformat(clean_iso)
                            ts = int(dt.timestamp())
                            date_display = dt.strftime("%b %d, %Y")
                        except Exception:
                            pass
                            
                    desc_plain = j.get("descriptionPlain", "")
                    
                    jobs.append({
                        "id": job_id,
                        "company": company,
                        "title": title,
                        "location": loc_name,
                        "url": job_url,
                        "source": "Ashby Direct ATS",
                        "timestamp": ts,
                        "date_posted": date_display,
                        "raw_department": j.get("department") or j.get("team") or "Product / Business",
                        "salary_raw": desc_plain[:4000]
                    })
    except Exception:
        pass
    return jobs

def fetch_linkedin_guest(query_info):
    keywords = query_info.get("keywords", "product intern")
    location = query_info.get("location", "Singapore")
    jobs = []
    
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {
        "keywords": keywords,
        "location": location,
        "f_TPR": "r86400",  # past 24 hours only
        "f_E": "1"          # internship level
    }
    
    try:
        r = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=7)
        if r.status_code == 200:
            # Parse card blocks using regex
            card_chunks = re.findall(r'<div[^>]*base-card[^>]*>([\s\S]*?)<\/li>', r.text)
            now = datetime.now()
            ts = int(now.timestamp())
            date_display = now.strftime("%b %d")
            
            for chunk in card_chunks:
                title_m = re.search(r'<h3[^>]*base-search-card__title[^>]*>([^<]+)<\/h3>', chunk)
                comp_m = re.search(r'<h4[^>]*base-search-card__subtitle[^>]*>[\s\S]*?<a[^>]*>([^<]+)<\/a>', chunk)
                if not comp_m:
                    comp_m = re.search(r'<h4[^>]*base-search-card__subtitle[^>]*>([^<]+)<\/h4>', chunk)
                loc_m = re.search(r'<span[^>]*job-search-card__location[^>]*>([^<]+)<\/span>', chunk)
                link_m = re.search(r'<a[^>]*base-card__full-link[^>]*href=\"([^\"]+)\"', chunk)
                salary_m = re.search(r'<span[^>]*job-search-card__salary-info[^>]*>([^<]+)<\/span>', chunk)
                
                if title_m and link_m:
                    title = title_m.group(1).strip()
                    company = comp_m.group(1).strip() if comp_m else "Global Firm"
                    loc_name = loc_m.group(1).strip() if loc_m else location
                    job_url = link_m.group(1).split("?")[0]  # clean tracking params
                    salary_raw = salary_m.group(1).strip() if salary_m else ""
                    
                    if is_non_tech_internship(title):
                        job_id = generate_job_id(company, title, loc_name)
                        jobs.append({
                            "id": job_id,
                            "company": company,
                            "title": title,
                            "location": loc_name,
                            "url": job_url,
                            "source": "LinkedIn (Past 24h)",
                            "timestamp": ts,
                            "date_posted": f"⚡ {date_display}",
                            "raw_department": "General Business",
                            "salary_raw": salary_raw
                        })
    except Exception:
        pass
    return jobs

def fetch_github_markdown_table(source_info):
    name = source_info["name"]
    url = source_info["url"]
    default_cat = source_info["category"]
    jobs = []
    
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=6)
        if r.status_code == 200:
            lines = r.text.split("\n")
            for line in lines:
                if not line.startswith("|") or "---" in line or "Company" in line:
                    continue
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 4:
                    # Clean company name
                    raw_comp = parts[0]
                    comp_match = re.search(r'\[([^\]]+)\]', raw_comp)
                    company = comp_match.group(1) if comp_match else re.sub(r'[*_]', '', raw_comp)
                    
                    # Clean title & link
                    raw_title = parts[1]
                    title_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', raw_title)
                    if title_match:
                        title = title_match.group(1)
                        job_url = title_match.group(2)
                    else:
                        title = re.sub(r'[*_]', '', raw_title)
                        # Check if link is in another column
                        link_match = re.search(r'https?://[^\s|)]+', line)
                        job_url = link_match.group(0) if link_match else ""
                        
                    location = parts[2] if len(parts) > 2 else "Remote / Unspecified"
                    date_posted = parts[4] if len(parts) > 4 else parts[3]
                    date_str = re.sub(r'<[^>]+>', '', date_posted).strip()
                    
                    if not job_url or not title or not company:
                        continue
                        
                    if is_non_tech_internship(title):
                        job_id = generate_job_id(company, title, location)
                        
                        # Parse date string like 'Oct 30'
                        now = datetime.now()
                        ts = int(now.timestamp())
                        date_display = date_str if date_str else now.strftime("%b %d")
                        try:
                            m = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})', date_str, re.IGNORECASE)
                            if m:
                                dt = datetime.strptime(f"{m.group(1).capitalize()} {m.group(2)} {now.year}", "%b %d %Y")
                                if dt > now:
                                    dt = dt.replace(year=now.year - 1)
                                ts = int(dt.timestamp())
                                date_display = dt.strftime("%b %d")
                        except Exception:
                            pass
                            
                        jobs.append({
                            "id": job_id,
                            "company": company,
                            "title": title,
                            "location": location,
                            "url": job_url,
                            "source": name,
                            "timestamp": ts,
                            "date_posted": date_display,
                            "raw_department": default_cat,
                            "salary_raw": line
                        })
    except Exception:
        pass
    return jobs

def run_harvest(config):
    all_jobs = []
    
    # 1. Greenhouse
    gh_boards = config.get("greenhouse_boards", [])
    # 2. Lever
    lever_boards = config.get("lever_boards", [])
    # 3. Ashby
    ashby_boards = config.get("ashby_boards", [])
    # 4. LinkedIn Guest
    linkedin_queries = config.get("linkedin_guest_queries", [])
    # 5. Curated GitHub
    github_sources = config.get("curated_github_sources", [])
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=14) as executor:
        futures = []
        for b in gh_boards:
            futures.append(executor.submit(fetch_greenhouse_board, b))
        for b in lever_boards:
            futures.append(executor.submit(fetch_lever_board, b))
        for a in ashby_boards:
            futures.append(executor.submit(fetch_ashby_board, a))
        for l in linkedin_queries:
            futures.append(executor.submit(fetch_linkedin_guest, l))
        for g in github_sources:
            futures.append(executor.submit(fetch_github_markdown_table, g))
            
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                all_jobs.extend(res)
                
    # Deduplicate by ID
    unique_jobs = {}
    for j in all_jobs:
        if j["id"] not in unique_jobs:
            unique_jobs[j["id"]] = j
            
    return list(unique_jobs.values())
