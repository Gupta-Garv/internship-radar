import re

def categorize_role(title, dept=""):
    t = title.lower() + " " + dept.lower()
    
    if any(k in t for k in ['product manager', 'product management', 'apm', 'product intern', 'product operations', 'product strategy']):
        return "Product / APM"
    if any(k in t for k in ['business operations', 'strategy', 'chief of staff', 'founder', 'business analyst', 'operations lead', 'program management', 'project management']):
        return "BizOps & Strategy"
    if any(k in t for k in ['marketing', 'growth', 'gtm', 'content', 'brand', 'seo', 'social media', 'communications']):
        return "Growth & Marketing"
    if any(k in t for k in ['design', 'ui', 'ux', 'product designer', 'experience designer']):
        return "Design & UX"
    if any(k in t for k in ['finance', 'investment', 'ventures', 'financial', 'audit']):
        return "Finance & Analytics"
        
    return "General Business"

def evaluate_location(loc_str, title_str=""):
    combined = (loc_str + " " + title_str).lower()
    
    # 1. India (Domestic base)
    if re.search(r'\b(india|bengaluru|bangalore|gurugram|gurgaon|hyderabad|mumbai|pune|delhi|noida)\b', combined):
        return {"region": "India", "score": 1.0, "visa_note": "Domestic (Zero visa friction)", "badge": "🇮🇳 India"}
        
    # 2. Remote / Worldwide
    if re.search(r'\b(remote|work from home|telecommute|anywhere)\b', combined) or re.search(r'\bworldwide\b', loc_str.lower()):
        return {"region": "Remote", "score": 1.0, "visa_note": "Global Remote (Work from anywhere in India / USD or EUR)", "badge": "🌐 Remote Global"}

    # 3. China & Greater China (High Growth, Safe, Major Tech Ecosystem)
    if re.search(r'\b(china|beijing|shanghai|shenzhen|hangzhou|hong kong|hk|taiwan|taipei|guangzhou)\b', combined):
        return {"region": "China / HK / TW", "score": 1.0, "visa_note": "High growth global tech hub • Baidu Hackathon alumni leverage", "badge": "🇨🇳 China / HK"}

    # 4. Japan (English-first global tracks, safe, corporate relocation)
    if re.search(r'\b(japan|tokyo|kyoto|osaka|yokohama)\b', combined):
        return {"region": "Japan", "score": 1.0, "visa_note": "English-first tracks, full relocation & corporate housing (Coupang, Mercari, Rakuten)", "badge": "🇯🇵 Japan"}

    # 5. Singapore (Premier APAC hub, highest safety index)
    if re.search(r'\b(singapore|sg)\b', combined):
        return {"region": "Singapore", "score": 1.0, "visa_note": "World #1 safety index, massive Indian expat community, top corporate stipends", "badge": "🇸🇬 Singapore"}

    # 6. UAE & Middle East (Extremely welcoming to Indians, 0% tax)
    if re.search(r'\b(dubai|abu dhabi|uae|united arab emirates|doha|qatar|riyadh|saudi)\b', combined):
        return {"region": "UAE / Middle East", "score": 1.0, "visa_note": "Very welcoming to Indians, 0% tax, rapid visa issuance", "badge": "🇦🇪 UAE (Dubai)"}

    # 7. Welcoming Continental Europe (Germany, Netherlands, Ireland, Switzerland, Nordics, Spain, Poland)
    is_us_location = bool(re.search(r'\b(oh|va|ohio|virginia|ca|ny|tx|ma|wa|nc|ga|fl|il|pa|co|nj|united states|usa|us|canada|calgary|toronto|vancouver|san francisco|new york|seattle|austin|boston|amelia)\b', loc_str.lower()))
    
    if not is_us_location:
        if re.search(r'\b(berlin|munich|germany|frankfurt|hamburg)\b', loc_str.lower()):
            return {"region": "Germany", "score": 0.98, "visa_note": "Opportunity Card & Student visas, English tech startups, welcoming climate", "badge": "🇩🇪 Germany"}
        if re.search(r'\b(amsterdam|netherlands|rotterdam)\b', loc_str.lower()):
            return {"region": "Netherlands", "score": 0.98, "visa_note": "95%+ English fluency, Zoekjaar orientation visa for global grads", "badge": "🇳🇱 Netherlands"}
        if re.search(r'\bireland\b', loc_str.lower()) or re.search(r'\bdublin\b', loc_str.lower()):
            return {"region": "Ireland", "score": 0.98, "visa_note": "European tech capital, large welcoming Indian tech community, Stamp 1G", "badge": "🇮🇪 Ireland"}
        if re.search(r'\b(switzerland|zurich|geneva|sweden|stockholm|denmark|copenhagen|norway|oslo|finland|helsinki)\b', loc_str.lower()):
            return {"region": "Nordics / Swiss", "score": 0.98, "visa_note": "Ultra safe, progressive, English widely spoken, top stipends", "badge": "🇨🇭 Nordics / Swiss"}
        if re.search(r'\b(spain|madrid|barcelona|portugal|lisbon|pt|poland|warsaw|krakow)\b', loc_str.lower()):
            return {"region": "Southern / Central Europe", "score": 0.96, "visa_note": "Welcoming international tech hub, vibrant culture", "badge": "🇪🇺 Europe Hub"}

    # 8. Australia & New Zealand (Multicultural, large diaspora)
    if re.search(r'\b(australia|sydney|melbourne|brisbane|new zealand|auckland)\b', combined):
        return {"region": "Australia / NZ", "score": 0.98, "visa_note": "Safe, multicultural, large Indian diaspora (Canva, Atlassian)", "badge": "🇦🇺 Australia / NZ"}

    # 9. Deprioritized / Restrictive Visa Regions (US, UK, France)
    if re.search(r'\b(france|paris)\b', loc_str.lower()):
        return {"region": "France", "score": 0.70, "visa_note": "Strict French language requirements & complex conventions de stage", "badge": "🇫🇷 France"}
    if re.search(r'\b(london|united kingdom|uk|manchester|edinburgh)\b', loc_str.lower()):
        return {"region": "UK", "score": 0.78, "visa_note": "Strict visa sponsorship thresholds (Temporary Work GAE required)", "badge": "🇬🇧 UK"}
    if is_us_location or re.search(r'\b(united states|us|usa|canada|toronto|san francisco|new york|seattle|austin|boston)\b', combined):
        return {"region": "US / Canada", "score": 0.72, "visa_note": "Requires J-1 sponsor or US/Canada work authorization", "badge": "🇺🇸 US / Canada"}
        
    return {"region": "International", "score": 0.88, "visa_note": "Open international location", "badge": "🌍 Global"}

def evaluate_visa_sponsorship(job, loc_eval):
    comp_lower = job.get("company", "").lower()
    title_lower = job.get("title", "").lower()
    loc_lower = job.get("location", "").lower()
    combined = f"{comp_lower} {title_lower} {loc_lower}"
    
    # 1. Known Verified Sponsoring & Relocation Scaleups
    sponsors_db = {
        'coupang': {
            'is_sponsored': True,
            'tier': 'Verified Full Sponsorship',
            'badge': '✈️ Full Visa & Relocation',
            'note': 'Provides employer visa sponsorship, round-trip international flights, and corporate housing in Tokyo/Seoul.',
            'boost': 5
        },
        'mercari': {
            'is_sponsored': True,
            'tier': 'Verified Full Sponsorship',
            'badge': '✈️ Full Visa & Relocation',
            'note': 'Actively recruits global interns with full visa sponsorship, international flights, and company housing in Tokyo.',
            'boost': 5
        },
        'databricks': {
            'is_sponsored': True,
            'tier': 'Verified Visa Assistance',
            'badge': '🛂 Visa Sponsored',
            'note': 'Provides work authorization and visa support for international interns in Amsterdam & Berlin.',
            'boost': 4
        },
        'celonis': {
            'is_sponsored': True,
            'tier': 'Verified Visa Assistance',
            'badge': '🛂 Visa Sponsored',
            'note': 'Actively sponsors and assists with intern work visas and relocation across German & Spanish hubs.',
            'boost': 4
        },
        'careem': {
            'is_sponsored': True,
            'tier': 'Verified UAE Sponsorship',
            'badge': '🇦🇪 UAE Visa & Relocation',
            'note': 'Provides employer-sponsored UAE entry visa, fast processing, and relocation assistance in Dubai.',
            'boost': 5
        },
        'adyen': {
            'is_sponsored': True,
            'tier': 'Verified Visa Assistance',
            'badge': '🛂 Visa Sponsored',
            'note': 'Offers visa sponsorship and relocation support for international candidates in Amsterdam & Singapore.',
            'boost': 4
        },
        'cloudflare': {
            'is_sponsored': True,
            'tier': 'Verified Visa Assistance',
            'badge': '🛂 Visa Assisted',
            'note': 'Structured international relocation and work authorization support for Lisbon and European offices.',
            'boost': 3
        },
        'stripe': {
            'is_sponsored': True,
            'tier': 'Verified Visa Assistance',
            'badge': '🛂 Visa Assisted',
            'note': 'Corporate relocation assistance and visa processing for Singapore and Dublin hubs.',
            'boost': 4
        },
        'grab': {
            'is_sponsored': True,
            'tier': 'Verified Visa Assistance',
            'badge': '🛂 Visa Assisted',
            'note': 'Facilitates Singapore Training Employment Pass (TEP) or Work Holiday Programme (WHP).',
            'boost': 4
        },
        'booking': {
            'is_sponsored': True,
            'tier': 'Verified Visa Assistance',
            'badge': '🛂 Visa Sponsored',
            'note': 'Full visa sponsorship and comprehensive relocation package for Amsterdam roles.',
            'boost': 4
        },
        'delivery hero': {
            'is_sponsored': True,
            'tier': 'Verified Visa Assistance',
            'badge': '🛂 Visa Assisted',
            'note': 'Assists with German work permits and relocation for Berlin scaleup teams.',
            'boost': 3
        },
        'spotify': {
            'is_sponsored': True,
            'tier': 'Verified Visa Assistance',
            'badge': '🛂 Visa Assisted',
            'note': 'Assists with Swedish work permit formalities for European operations.',
            'boost': 3
        },
        'canva': {
            'is_sponsored': True,
            'tier': 'Verified Visa Assistance',
            'badge': '🛂 Visa Assisted',
            'note': 'Provides international applicant visa documentation support for Sydney teams.',
            'boost': 3
        },
        'atlassian': {
            'is_sponsored': True,
            'tier': 'Verified Visa Assistance',
            'badge': '🛂 Visa Assisted',
            'note': 'Global visa processing support for international graduates and interns in Sydney and Amsterdam.',
            'boost': 3
        },
        'tencent': {
            'is_sponsored': True,
            'tier': 'International Program Support',
            'badge': '🤝 Visa Assisted',
            'note': 'Provides corporate invitation and visa support for international candidates.',
            'boost': 3
        },
        'baidu': {
            'is_sponsored': True,
            'tier': 'International Program Support',
            'badge': '🤝 Visa Assisted',
            'note': 'Corporate invitation documentation support for global hackathon and intern tracks.',
            'boost': 4
        },
        'alibaba': {
            'is_sponsored': True,
            'tier': 'International Program Support',
            'badge': '🤝 Visa Assisted',
            'note': 'Facilitates global intern visa documentation for cloud and AI divisions.',
            'boost': 3
        }
    }
    
    # Check matching sponsor from database
    for k, info in sponsors_db.items():
        if k in comp_lower:
            # If the job is located in the US/Canada, international undergrad sponsorship is legally restricted
            if loc_eval.get("region") == "US / Canada":
                return {
                    'is_sponsored': False,
                    'tier': 'US Work Auth Required',
                    'badge': '🇺🇸 Needs US Auth',
                    'note': f"{job.get('company')}'s US/Canada office requires existing local work authorization (CPT/OPT/Citizen) for undergraduate interns.",
                    'penalty': 10
                }
            return info
            
    # 2. Check Remote (No visa needed)
    if loc_eval.get("region") == "Remote":
        return {
            'is_sponsored': True,
            'tier': 'No Visa Needed (Remote)',
            'badge': '🌐 Remote (Zero Visa Friction)',
            'note': '100% remote worldwide. Work from India, get paid in USD or EUR with zero immigration requirements.',
            'boost': 4
        }
        
    # 3. Check Explicit Positive Text
    if re.search(r'\b(visa sponsorship|visa support|relocation assistance|relocation support|flight|housing provided|international applicants welcome|sponsorship available|sponsorship provided|open to international)\b', combined):
        return {
            'is_sponsored': True,
            'tier': 'Explicit Visa / Relocation Support',
            'badge': '🛂 Visa / Relo Assisted',
            'note': 'Listing explicitly mentions international visa support or relocation assistance.',
            'boost': 4
        }
        
    # 4. Check Explicit Negative Text
    if re.search(r'\b(no visa sponsorship|will not sponsor|must have existing authorization|without sponsorship|citizenship required|us citizen only|security clearance)\b', combined):
        return {
            'is_sponsored': False,
            'tier': 'Self-Authorized Only',
            'badge': '⚠️ No Sponsorship',
            'note': 'Company explicitly states they do not provide visa sponsorship for this position.',
            'penalty': 15
        }
        
    # 5. Default based on country friendliness
    region = loc_eval.get("region", "")
    if region in ["China / HK / TW", "Japan", "Singapore", "UAE / Middle East", "Germany", "Netherlands", "Nordics / Swiss", "Australia / NZ"]:
        return {
            'is_sponsored': True,
            'tier': 'Immigrant-Friendly Hub',
            'badge': '🤝 Visa Welcoming Hub',
            'note': f'Located in {region}: active bilateral intern/orientation visa schemes available for Indian students.',
            'boost': 2
        }
        
    return {
        'is_sponsored': False,
        'tier': 'Standard / Unspecified',
        'badge': '📍 Self-Check Visa',
        'note': 'Visa sponsorship policy not explicitly specified; check during initial recruiter phone screener.'
    }

def generate_recruiter_pitch(job, profile, category):
    comp = job["company"]
    title = job["title"]
    
    if category == "Product / APM":
        return f"Hi! I saw {comp}'s {title} opening. As an IIM Bangalore student who shipped a full AI MVP solo in 48 hours and placed 2nd globally among 8,400+ participants in Baidu's AI hackathon ($6.5k prize), I'd love to bring this execution speed to {comp}'s product team. My portfolio: garvgupta.app"
    elif category == "BizOps & Strategy":
        return f"Hi! I noticed the {title} opening at {comp}. I currently run operations & full P&L for a 10,000+ student education brand (AnybodyCanBake) with 5-7 team members alongside my degree at IIM Bangalore. Would love to bring proven execution and problem-solving to {comp}."
    elif category == "Growth & Marketing":
        return f"Hi! Excited by {comp}'s {title} role. Having built an organic audience of 200,000+ LinkedIn impressions and 80k+ IG views around AI and execution, I combine creative storytelling with quantitative funnel and SEO tracking to drive real GTM impact."
    elif category == "Design & UX":
        return f"Hi! Saw {comp}'s {title} post. Having placed Top 10 in two global UI/UX build competitions (Zo Computers & Anything.com), I bridge user empathy, rapid Figma prototyping, and AI product understanding. Portfolio: garvgupta.app"
    else:
        return f"Hi! I'm applying for the {title} position at {comp}. As an IIM Bangalore entrepreneurship student and operator running a 10,000-student brand, I'm passionate about high-impact execution at {comp}. Portfolio: garvgupta.app"

def evaluate_compensation(job):
    raw = job.get("salary_raw", "")
    title = job.get("title", "")
    text = f"{title} {raw}"
    
    if not raw and not title:
        return {
            "pay_display": "Not mentioned",
            "pay_monthly_usd": 0,
            "is_disclosed": False,
            "note": "Compensation is not publicly disclosed in the posting."
        }
        
    # 1. Hourly rate: e.g. $40 - $60 / hr, $45/hour, $50/hr
    m_hour = re.search(r'(\$|€|£|₹|SGD|AED|CAD|AUD)?\s*(\d{2,3})(?:\s*(?:-|to)\s*(\$|€|£|₹|SGD|AED|CAD|AUD)?\s*(\d{2,3}))?\s*(?:/|\bper\b)?\s*(?:hour|hr)\b', text, re.I)
    if not m_hour:
        m_hour = re.search(r'(?:hourly\s+(?:rate|pay|compensation)\s+(?:of|is|:)?\s*)(\$|€|£|₹|SGD|AED|CAD|AUD)?\s*(\d{2,3})', text, re.I)
    if m_hour:
        curr = m_hour.group(1) or "$"
        min_v = int(m_hour.group(2))
        max_v = int(m_hour.group(4)) if (len(m_hour.groups()) >= 4 and m_hour.group(4)) else min_v
        avg_v = (min_v + max_v) / 2
        mult = 1.0
        if curr in ["£", "€"]: mult = 1.15
        elif curr == "SGD": mult = 0.75
        elif curr in ["AUD", "CAD"]: mult = 0.7
        elif curr == "₹": mult = 0.012
        monthly_usd = int(avg_v * 160 * mult)
        display = f"{curr}{min_v} - {curr}{max_v}/hr" if min_v != max_v else f"{curr}{min_v}/hr"
        return {
            "pay_display": display,
            "pay_monthly_usd": monthly_usd,
            "is_disclosed": True,
            "note": f"Disclosed hourly rate (~${monthly_usd:,}/mo full-time equivalent)."
        }

    # 2. Monthly rate / Stipend: "monthly ... $12,500" or "$12,500 / month" or "$12,500/mo"
    m_month = re.search(r'monthly\b[^\d$€£₹]{0,40}(\$|€|£|₹|SGD|AED)?\s*(\d{1,2}(?:,\d{3})+|\d{4,5})', text, re.I)
    if not m_month:
        m_month = re.search(r'(\$|€|£|₹|SGD|AED|CAD|AUD)?\s*(\d{1,2}(?:,\d{3})+|\d{4,5})\s*(?:USD|EUR|GBP|SGD|AED)?\s*(?:(?:/|\bper\b)\s*(?:month|mo)\b|\bmonthly\b)', text, re.I)
    if m_month:
        curr = m_month.group(1) or "$"
        val = int(m_month.group(2).replace(",", ""))
        if val >= 500:
            mult = 1.0
            if curr in ["£", "€"]: mult = 1.15
            elif curr == "SGD": mult = 0.75
            elif curr in ["AUD", "CAD"]: mult = 0.7
            elif curr == "₹": mult = 0.012
            monthly_usd = int(val * mult)
            return {
                "pay_display": f"{curr}{val:,}/mo",
                "pay_monthly_usd": monthly_usd,
                "is_disclosed": True,
                "note": f"Disclosed monthly stipend/salary (~${monthly_usd:,} USD/mo)."
            }

    # 3. Annual salary: e.g. $80,000 - $100,000 / year
    m_annual = re.search(r'(\$|€|£|₹|SGD|AED|CAD|AUD)?\s*(\d{2,3}(?:,\d{3})+)\s*(?:-|to)\s*(\$|€|£|₹)?\s*(\d{2,3}(?:,\d{3})+)\s*(?:/|\bper\b)?\s*(?:year|yr|annum)\b', text, re.I)
    if m_annual:
        curr = m_annual.group(1) or "$"
        min_v = int(m_annual.group(2).replace(",", ""))
        max_v = int(m_annual.group(4).replace(",", ""))
        avg_v = (min_v + max_v) / 2
        monthly_usd = int(avg_v / 12)
        return {
            "pay_display": f"{curr}{min_v//1000}k - {curr}{max_v//1000}k/yr",
            "pay_monthly_usd": monthly_usd,
            "is_disclosed": True,
            "note": f"Disclosed annual compensation rate (~${monthly_usd:,}/mo equivalent)."
        }

    return {
        "pay_display": "Not mentioned",
        "pay_monthly_usd": 0,
        "is_disclosed": False,
        "note": "Compensation is not publicly disclosed in the posting."
    }

def score_job(job, profile):
    title = job["title"]
    category = categorize_role(title, job.get("raw_department", ""))
    loc_eval = evaluate_location(job["location"], title)
    visa_eval = evaluate_visa_sponsorship(job, loc_eval)
    pay_eval = evaluate_compensation(job)
    
    # Base category weights based on Garv's strengths
    cat_weights = {
        "Product / APM": 96,
        "BizOps & Strategy": 93,
        "Growth & Marketing": 91,
        "Design & UX": 88,
        "Finance & Analytics": 82,
        "General Business": 78
    }
    base_score = cat_weights.get(category, 75)
    
    # Adjust by location viability
    final_score = int(base_score * loc_eval["score"])
    
    # Add bonus for tier 1 direct ATS postings
    if "Direct ATS" in job.get("source", ""):
        final_score = min(99, final_score + 2)

    # Visa sponsorship adjustment
    if visa_eval.get("is_sponsored"):
        final_score = min(99, final_score + visa_eval.get("boost", 3))
    if visa_eval.get("penalty"):
        final_score = max(40, final_score - visa_eval.get("penalty", 15))
        
    tier = "Tier 1 (High Conversion)" if final_score >= 88 else ("Tier 2 (Strong Fit)" if final_score >= 78 else "Tier 3 (Stretch)")
    pitch = generate_recruiter_pitch(job, profile, category)
    
    return {
        "category": category,
        "match_score": final_score,
        "tier": tier,
        "location_info": loc_eval,
        "visa_info": visa_eval,
        "pay_info": pay_eval,
        "recruiter_pitch": pitch
    }
