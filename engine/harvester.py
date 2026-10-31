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
    'research engineer', 'data scientist', 'deep learning engineer',
    'clinical', 'nursing', 'veterinary', 'physician', 'biologist',
    'chemist', 'hardware engineer', 'silicon', 'embedded system',
    'security engineer', 'internal audit', 'data engineer',
    'marketing engineer', 'reliability engineer', 'systems engineer',
    'packaging engineer', 'manufacturing engineer', 'civil engineer',
    'mechanical engineer', 'chemical engineer', 'product development engineering'
]

# Non-digital / Physical design roles to strictly disqualify
PHYSICAL_DESIGN_REGEX = re.compile(
    r'\b(landscape architecture|architectural|interior design|industrial design|cmf|cad designer|apparel|textile|fashion|garment|environmental designer)\b',
    re.IGNORECASE
)

# Degree & Enrollment restrictions (Garv is an Undergrad BBA student, NOT an MBA or PhD candidate)
DEGREE_RESTRICTION_REGEX = re.compile(
    r'\b(mba|phd|ph\.d\.|doctoral|postdoc|graduate student|graduated internship|graduate internship|master\'s only|masters only|ms only|postgraduate)\b',
    re.IGNORECASE
)

# Foreign languages to strictly disqualify (Garv Gupta is fluent in English and Hindi ONLY)
FOREIGN_LANGUAGES = [
    'arabic', 'german', 'deutsch', 'french', 'français', 'spanish', 'español',
    'italian', 'italiano', 'dutch', 'nederlands', 'japanese', 'mandarin',
    'chinese', 'cantonese', 'korean', 'swedish', 'danish', 'norwegian',
    'finnish', 'portuguese', 'português', 'russian', 'turkish', 'polish',
    'vietnamese', 'thai', 'bahasa', 'indonesian', 'malay', 'hebrew', 'greek',
    'czech', 'hungarian', 'tagalog', 'romanian'
]

# Foreign LinkedIn regional domains and terms
FOREIGN_DOMAINS_REGEX = re.compile(
    r'https?://(es|fr|de|it|nl|pt|br|pl|ru|jp)\.linkedin\.com',
    re.IGNORECASE
)

FOREIGN_MARKET_TERMS_REGEX = re.compile(
    r'\b(de coches|prácticas|practicas|becario|becaria|pasantía|pasantia|stagiaire|stage|alternance|contrat pro|praktikum|praktikant|werkstudent|abschlussarbeit|tirocinio|tirocinante|estágio|estagio)\b',
    re.IGNORECASE
)

# Citizenship, clearance, and local matriculation restrictions
CITIZENSHIP_RESTRICTION_REGEX = re.compile(
    r'\b(us citizen|citizenship required|security clearance|secret clearance|us government|government defense|uae nationals?|emiratis? only|saudi nationals?|singaporeans? only|nationals only|singaporeans/prs only|term-time internship|term time|front office|front desk|housekeeping|culinary|chef|barista|f&b|waiter|concierge)\b',
    re.IGNORECASE
)

# US Regional states that do not support international undergrad sponsorship for on-site roles
US_NON_SPONSOR_STATES = re.compile(
    r'\b(al|ak|az|ar|co|ct|de|fl|ga|hi|id|il|in|ia|ks|ky|la|me|md|ma|mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|nc|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wv|wi|wy|holland|roanoke|greensboro|terrell|fort mill|simpsonville|st\. paul|saint paul|buffalo|orlando|murrysville|fond du lac)\b',
    re.IGNORECASE
)

_LANG_OR_PATTERN = '|'.join(FOREIGN_LANGUAGES)

TITLE_LANG_REGEX = re.compile(
    rf'''(?x)
    (?:
        \b(?:{_LANG_OR_PATTERN})\s*[-–/]\s*(?:fluent|speaking|speaker|bilingual|required|native)\b
        |
        \bbilingual\s*[-–/]?\s*(?:{_LANG_OR_PATTERN})\b
        |
        \((?:{_LANG_OR_PATTERN})\s*/\s*english\)
        |
        \(\s*english\s*/\s*(?:{_LANG_OR_PATTERN})\)
        |
        \b(?:{_LANG_OR_PATTERN})\s+(?:speaking|speaker|fluent)\b
        |
        \bfluent\s+in\s+(?:{_LANG_OR_PATTERN})\b
    )
    ''',
    re.IGNORECASE
)

DESC_HARD_LANG_REGEX = re.compile(
    rf'''(?x)
    (?:
        # fluent in X / fluent in English and X / fluent in X and English
        \b(?:fluent|fluency|business\s+fluent|native|proficient|proficiency)\s+(?:in|of)?\s*(?:both\s+)?(?:english\s+(?:and|&)\s+)?(?:{_LANG_OR_PATTERN})\b
        |
        \b(?:english\s+(?:and|&)\s+({_LANG_OR_PATTERN}))\b
        |
        \b(?:({_LANG_OR_PATTERN})\s+(?:and|&)\s+english)\b
        |
        \b(?:{_LANG_OR_PATTERN})\s+(?:language\s+skills?\s+)?(?:is\s+)?(?:required|mandatory|essential|a\s+must)\b
        |
        \b(?:spoken\s+and\s+written|written\s+and\s+spoken)\s+(?:{_LANG_OR_PATTERN})\b
        |
        \b(?:{_LANG_OR_PATTERN})\s*\((?:written\s+and\s+spoken|spoken\s+and\s+written|verbal\s+and\s+written)\)
        |
        \b(?:jlpt\s*n[1-3]|hsk\s*[4-6]|(?:german|french|spanish|italian)\s+[bc][12])\b
        |
        \b(?:verhandlungssicher|fließend\s+deutsch|deutschkenntnisse|langue\s+maternelle|courant\s+en\s+français)\b
        |
        \b(?:must\s+speak|must\s+be\s+fluent\s+in)\s+(?:{_LANG_OR_PATTERN})\b
    )
    ''',
    re.IGNORECASE
)

def requires_foreign_language(title, text=""):
    """
    Checks if a job posting has a hard requirement for a 3rd language (non-English, non-Hindi).
    Returns True if disqualified, False otherwise.
    """
    if TITLE_LANG_REGEX.search(title):
        return True

    if text:
        clean_text = text.replace('\n', ' ').replace('\r', ' ')
        for m in DESC_HARD_LANG_REGEX.finditer(clean_text):
            matched_str = m.group(0).lower()
            # Guard against English verb 'polish'
            if 'polish' in matched_str and not ('polish language' in matched_str or 'fluent in polish' in matched_str):
                continue

            start, end = m.span()
            ctx_start = max(0, start - 60)
            ctx_end = min(len(clean_text), end + 60)
            surrounding = clean_text[ctx_start:ctx_end].lower()

            # Skip if explicitly optional/bonus/plus
            if any(opt in surrounding for opt in ['plus', 'bonus', 'nice to have', 'advantageous', 'not required', 'optional', 'preferred but not', 'not a must']):
                continue

            return True

    return False

INTERN_PATTERN = re.compile(r'\b(intern|internship|co-op|coop|apm|fellow|fellowship|summer analyst)\b', re.IGNORECASE)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

def generate_job_id(company, title, location):
    raw = f"{company.strip().lower()}_{title.strip().lower()}_{str(location).strip().lower()}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def is_non_tech_internship(title, text="", url="", location="", company=""):
    lower_title = title.lower()
    full_text = f"{title} {company} {location} {text}".lower()

    # 1. Must match intern pattern
    if not INTERN_PATTERN.search(lower_title):
        return False

    # 2. Reject MBA, PhD, and Graduate-only degree restrictions
    if DEGREE_RESTRICTION_REGEX.search(lower_title) or DEGREE_RESTRICTION_REGEX.search(text[:600]):
        return False

    # 3. Reject physical / non-digital / hardware design
    if PHYSICAL_DESIGN_REGEX.search(lower_title):
        return False

    # 4. Reject engineering / hardware / data engineering / reliability keywords
    for neg in NEGATIVE_KEYWORDS:
        if neg in lower_title:
            return False

    # 5. Reject foreign LinkedIn domains (es., fr., de., it., etc.)
    if url and FOREIGN_DOMAINS_REGEX.search(url):
        return False

    # 6. Reject foreign market terms
    if FOREIGN_MARKET_TERMS_REGEX.search(full_text):
        return False

    # 7. Check foreign language text density
    sp_cnt = len(re.findall(r'\b(para|con|por|como|del|las|los|requisitos|experiencia|renting)\b', full_text))
    fr_cnt = len(re.findall(r'\b(pour|dans|avec|les|des|missions|profil)\b', full_text))
    de_cnt = len(re.findall(r'\b(und|fuer|für|mit|wir|uns|aufgaben|bewerbung)\b', full_text))
    if sp_cnt >= 3 or fr_cnt >= 3 or de_cnt >= 3:
        return False

    # 8. Must NOT require a 3rd language (Garv only speaks English and Hindi)
    if requires_foreign_language(title, text):
        return False

    # 9. Reject Citizenship / Security clearance / local term-time restrictions
    if CITIZENSHIP_RESTRICTION_REGEX.search(full_text):
        return False

    # 10. Reject US Local On-Site at non-sponsoring regional firms (Requires US CPT/OPT work auth)
    is_us = bool(re.search(r'\b(united states|usa|us)\b', location.lower()) or US_NON_SPONSOR_STATES.search(location.lower()))
    is_onsite = bool(re.search(r'\b(on site|onsite|in-person|in person)\b', text.lower()) or 'on site' in text.lower())
    is_remote = bool(re.search(r'\b(remote|work from home|anywhere)\b', location.lower()))
    if is_us and is_onsite and not is_remote:
        # Require explicit visa sponsorship mention for US on-site roles
        if not re.search(r'\b(visa sponsorship|international applicants welcome|j-1)\b', text.lower()):
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
                raw_content = html.unescape(j.get("content", ""))
                loc_name = j.get("location", {}).get("name", "Remote / Unspecified")
                job_url = j.get("absolute_url", "")
                if is_non_tech_internship(title, raw_content, job_url, loc_name, company):
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
                raw_desc = (p.get("descriptionPlain", "") + " " + p.get("additionalPlain", ""))
                loc_name = p.get("categories", {}).get("location", "Remote / Unspecified")
                job_url = p.get("hostedUrl", "")
                if is_non_tech_internship(title, raw_desc, job_url, loc_name, company):
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
                desc_plain = j.get("descriptionPlain", "")
                loc_name = j.get("location") or "Remote / Unspecified"
                job_url = j.get("jobUrl") or j.get("applyUrl") or ""
                if is_non_tech_internship(title, desc_plain, job_url, loc_name, company):
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
                    
                    if is_non_tech_internship(title, f"{title} {chunk}", job_url, loc_name, company):
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
            last_company = ""
            for line in lines:
                if not line.startswith("|") or "---" in line or "Company" in line:
                    continue
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 4:
                    # Clean company name
                    raw_comp = parts[0]
                    comp_match = re.search(r'\[([^\]]+)\]', raw_comp)
                    company = comp_match.group(1) if comp_match else re.sub(r'[*_]', '', raw_comp)
                    if company in ['↳', '->', '»', ''] or not company.strip():
                        company = last_company
                    else:
                        last_company = company
                    
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
                        
                    if is_non_tech_internship(title, line, job_url, location, company):
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
