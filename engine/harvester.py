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

    # 1. Must match target operator / intern pattern in title, or be early-career/entry level
    is_early_career = bool(
        INTERN_PATTERN.search(lower_title) or 
        re.search(r'\b(intern|internship|co-op|coop|apm|associate|fellow|fellowship|entry[- ]level|junior|trainee|apprentice|special projects)\b', lower_title)
    )
    if not is_early_career:
        return False

    # 2. Strict target track enforcement (APM, Founder\'s Office, BizOps, Growth, Marketing, Product Design)
    TARGET_ROLE_PATTERNS = re.compile(
        r'\b(product|apm|associate product manager|founder|chief of staff|bizops|business operations|operations|strategy|growth|marketing|gtm|go-to-market|brand|social media|content|ui\b|ux\b|design|designer|product analyst|business analyst|commercial|fellow|fellowship|special projects)\b',
        re.IGNORECASE
    )
    if not TARGET_ROLE_PATTERNS.search(lower_title):
        return False

    # 3. Reject MBA, PhD, and Graduate-only degree restrictions
    if DEGREE_RESTRICTION_REGEX.search(lower_title) or DEGREE_RESTRICTION_REGEX.search(text[:600]):
        return False

    # 4. Strict Experience Cap: Reject roles requiring 2+ years of full-time experience
    exp_match = re.search(r'\b([2-9]|\d{2})\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:full[- ]time\s+)?experience\b', full_text)
    if exp_match:
        if not re.search(r'\b(?:0\s*[-–to]\s*[12]|1\s*[-–to]\s*2|under\s*2|<=\s*2)\s*(?:years?|yrs?)\b', full_text):
            return False

    # 5. Reject physical / non-digital / hardware design
    if PHYSICAL_DESIGN_REGEX.search(lower_title):
        return False

    # 6. Reject engineering / hardware / data engineering / reliability keywords
    for neg in NEGATIVE_KEYWORDS:
        if neg in lower_title:
            return False

    # 7. Strict Coding & Technical Knowledge Gate (with AI Exception)
    # Reject coding languages, software development, medical, law
    HARD_CODING_PATTERNS = re.compile(
        r'\b(proficiency in (?:c\+\+|java|rust|golang|c#|swift|kotlin)|must know (?:c\+\+|java|rust|golang)|experience with (?:c\+\+|java|rust|golang|microservices|distributed systems|kernel|embedded c)|deep learning research|training llms from scratch|pytorch architecture|medical degree|license to practice law|bar admission|clinical trial)\b',
        re.IGNORECASE
    )
    if HARD_CODING_PATTERNS.search(full_text):
        return False

    # 8. Reject foreign LinkedIn domains and foreign market terms
    if url and FOREIGN_DOMAINS_REGEX.search(url):
        return False
    if FOREIGN_MARKET_TERMS_REGEX.search(full_text):
        return False

    # 9. Check foreign language text density
    sp_cnt = len(re.findall(r'\b(para|con|por|como|del|las|los|requisitos|experiencia|renting)\b', full_text))
    fr_cnt = len(re.findall(r'\b(pour|dans|avec|les|des|missions|profil)\b', full_text))
    de_cnt = len(re.findall(r'\b(und|fuer|für|mit|wir|uns|aufgaben|bewerbung)\b', full_text))
    if sp_cnt >= 3 or fr_cnt >= 3 or de_cnt >= 3:
        return False

    # 10. Must NOT require a 3rd language (Garv only speaks English and Hindi)
    if requires_foreign_language(title, text):
        return False

    # 11. Reject Citizenship / Security clearance / local term-time restrictions
    if CITIZENSHIP_RESTRICTION_REGEX.search(full_text):
        return False

    # 12. Strict Location & Overseas Visa Sponsorship Gate:
    # India: Allowed without visa sponsorship (Domestic).
    # Remote Global: Allowed without visa sponsorship (can work from India).
    # Onsite/Hybrid Abroad (outside India): MUST have explicit visa sponsorship!
    loc_lower = location.lower()
    is_india = bool(re.search(r'\b(india|bengaluru|bangalore|mumbai|delhi|gurgaon|gurugram|hyderabad|pune|noida|chennai|kolkata|ahmedabad|jaipur)\b', loc_lower))
    is_hybrid = bool(re.search(r'\b(hybrid|onsite & remote|in[- ]office)\b', full_text))
    is_pure_remote = (
        bool(re.search(r'\b(remote worldwide|worldwide remote|work from anywhere|anywhere in the world|global remote|remote - anywhere)\b', loc_lower)) or
        (bool(re.search(r'\b(remote|telecommute|work from home)\b', loc_lower)) and not is_hybrid and not re.search(r'\b(us only|u\.s\. only|united states only|uk only|europe only|canada only|must reside in|must be based in)\b', full_text))
    )

    if not is_india and not is_pure_remote:
        # Must have verified visa sponsorship!
        has_visa_sponsorship = bool(
            re.search(r'\b(visa sponsorship|will sponsor|sponsorship available|relocation package|relocation support|corporate housing|j-1 sponsor|international applicants welcome|work visa)\b', text.lower())
            or (company.lower() in ['coupang', 'mercari'] and re.search(r'\b(tokyo|seoul|japan)\b', loc_lower))
            or (company.lower() in ['databricks'] and re.search(r'\b(amsterdam|berlin)\b', loc_lower))
            or (company.lower() in ['careem'] and re.search(r'\b(dubai|uae)\b', loc_lower))
        )
        no_visa_keywords = bool(re.search(r'\b(no visa sponsorship|cannot sponsor|will not sponsor|without (?:company )?sponsorship|authorized to work in (?:the )?(?:us|uk|eu|canada|singapore|australia) without (?:need for )?sponsorship|must have (?:valid )?work authorization|no relocation)\b', text.lower()))
        if no_visa_keywords or not has_visa_sponsorship:
            return False

    # 13. Reject explicit unpaid or non-paid listings
    if re.search(r'\b(unpaid|non[- ]?paid|no stipend|zero stipend|voluntary)\b', full_text):
        return False

    # 14. Reject generic outbound tele-sales, BDA calling, and non-operator labor
    if re.search(r'\b(business development associate|bda|telecaller|telecalling|telesales|cold call|inside sales associate|lead generation executive|counter sales|door to door sales|school evaluation|preschool|mechanical design|cad engineer)\b', lower_title):
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
    f_tpr = query_info.get("f_tpr")
    if not f_tpr:
        loc_l = location.lower()
        f_tpr = "r604800" if ("india" in loc_l or "bengaluru" in loc_l or "gurgaon" in loc_l) else "r86400"
    jobs = []
    
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {
        "keywords": keywords,
        "location": location,
        "f_TPR": f_tpr,
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

def fetch_hackernews_hiring():
    jobs = []
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get('https://hacker-news.firebaseio.com/v0/user/whoishiring.json', headers=headers, timeout=5)
        if r.status_code != 200:
            return jobs
        submitted = r.json().get('submitted', [])
        target_item_id = None
        for item_id in submitted[:3]:
            item = requests.get(f'https://hacker-news.firebaseio.com/v0/item/{item_id}.json', headers=headers, timeout=5).json()
            if 'who is hiring' in item.get('title', '').lower():
                target_item_id = item_id
                break
        if not target_item_id:
            return jobs

        thread = requests.get(f'https://hacker-news.firebaseio.com/v0/item/{target_item_id}.json', headers=headers, timeout=5).json()
        kids = thread.get('kids', [])[:80]

        def fetch_comment(kid_id):
            try:
                c = requests.get(f'https://hacker-news.firebaseio.com/v0/item/{kid_id}.json', headers=headers, timeout=4).json()
                raw_text = c.get('text', '')
                if not raw_text:
                    return None
                clean_text = html.unescape(re.sub(r'<[^>]+>', ' ', raw_text))
                lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
                if not lines:
                    return None
                header = lines[0]
                parts = [p.strip() for p in header.split('|')]
                if len(parts) >= 2:
                    comp = parts[0]
                    role_or_loc = parts[1]
                    loc = parts[2] if len(parts) > 2 else "Remote / Unspecified"
                    title = role_or_loc
                    url = f"https://news.ycombinator.com/item?id={kid_id}"
                    links = re.findall(r'https?://[^\s<>"]+', clean_text)
                    if links:
                        url = links[0]

                    if is_non_tech_internship(title, clean_text, url, loc, comp):
                        job_id = generate_job_id(comp, title, loc)
                        now = datetime.now()
                        return {
                            "id": job_id,
                            "company": comp,
                            "title": title,
                            "location": loc,
                            "url": url,
                            "source": "YC Hacker News Who is Hiring",
                            "timestamp": int(now.timestamp()),
                            "date_posted": now.strftime("%b %d"),
                            "raw_department": "Founder / Operator",
                            "salary_raw": clean_text[:200]
                        }
            except Exception:
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            results = executor.map(fetch_comment, kids)
            for res in results:
                if res:
                    jobs.append(res)
    except Exception:
        pass
    return jobs

def fetch_remoteok():
    jobs = []
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get('https://remoteok.com/api', headers=headers, timeout=6)
        if r.status_code == 200:
            data = r.json()
            target_tags = {'marketing', 'growth', 'product', 'design', 'operations', 'bizops', 'intern', 'junior', 'entry level', 'community'}
            now = datetime.now()
            ts = int(now.timestamp())
            for item in data[1:]:
                tags = set([t.lower() for t in item.get('tags', [])])
                pos = item.get('position', '')
                lower_pos = pos.lower()
                desc = item.get('description', '')
                loc = item.get('location', 'Remote Worldwide')
                comp = item.get('company', '')
                url = item.get('url', '')

                # Filter out senior/management roles
                if any(k in lower_pos for k in ['director', 'vp', 'head of', 'senior', 'sr.', 'principal', 'staff', 'lead ']):
                    continue

                if tags.intersection(target_tags) or any(t in lower_pos for t in ['product', 'marketing', 'growth', 'design', 'operations', 'bizops', 'founder']):
                    if is_non_tech_internship(pos, desc, url, loc, comp):
                        job_id = generate_job_id(comp, pos, loc)
                        jobs.append({
                            "id": job_id,
                            "company": comp,
                            "title": pos,
                            "location": loc or "Remote Worldwide",
                            "url": url,
                            "source": "RemoteOK Verified Startups",
                            "timestamp": ts,
                            "date_posted": now.strftime("%b %d"),
                            "raw_department": "Remote Operator",
                            "salary_raw": desc[:200]
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

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
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

        # 6. Hacker News Who is Hiring
        futures.append(executor.submit(fetch_hackernews_hiring))
        # 7. RemoteOK
        futures.append(executor.submit(fetch_remoteok))

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
