import os
import sys
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from engine.harvester import (
    CS_ENGINEERING_DEGREE_REGEX,
    HARD_CODING_PATTERNS,
    DEGREE_RESTRICTION_REGEX,
    requires_foreign_language
)

def audit_jobs(jobs):
    if not jobs:
        return 100.0, [], []

    verified_jobs = []
    disqualified = []

    for j in jobs:
        title = j.get("title", "")
        comp = j.get("company", "")
        loc = j.get("location", "")
        raw_text = j.get("salary_raw", "")
        full_text = f"{title} {comp} {loc} {raw_text}".lower()
        reasons = []

        # 1. Computer Science / Engineering degree check
        if CS_ENGINEERING_DEGREE_REGEX.search(full_text):
            m = CS_ENGINEERING_DEGREE_REGEX.search(full_text).group(0)
            reasons.append(f"Requires CS/Engineering degree: '{m}'")

        # 2. Hard coding / programming / SQL / Python check
        if HARD_CODING_PATTERNS.search(full_text):
            m = HARD_CODING_PATTERNS.search(full_text).group(0)
            reasons.append(f"Requires coding / SQL / Python: '{m}'")

        # 3. Graduate / MBA / PhD degree check
        if DEGREE_RESTRICTION_REGEX.search(full_text):
            m = DEGREE_RESTRICTION_REGEX.search(full_text).group(0)
            reasons.append(f"Requires MBA/PhD/Graduate: '{m}'")

        # 4. Experience cap check (>= 2 years full-time experience)
        exp_match = re.search(r'\b([2-9]|\d{2})\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:full[- ]time\s+)?experience\b', full_text)
        if exp_match:
            if not re.search(r'\b(?:0\s*[-–to]\s*[12]|1\s*[-–to]\s*2|under\s*2|<=\s*2)\s*(?:years?|yrs?)\b', full_text):
                reasons.append(f"Requires {exp_match.group(0)}")

        # 5. Foreign language check
        if requires_foreign_language(title, raw_text):
            reasons.append("Requires foreign language (non-English, non-Hindi)")

        # 6. Overseas Onsite / Hybrid Visa Sponsorship Check
        is_india = bool(re.search(r'\b(india|bengaluru|bangalore|mumbai|delhi|gurgaon|gurugram|hyderabad|pune|noida|chennai|kolkata|ahmedabad|jaipur)\b', loc.lower()))
        is_hybrid = bool(re.search(r'\b(hybrid|in[- ]office & remote|onsite & remote)\b', full_text))
        is_pure_remote = bool(
            re.search(r'\b(remote worldwide|worldwide remote|work from anywhere|anywhere in the world|global remote|remote - anywhere)\b', loc.lower()) or
            (re.search(r'\b(remote|work from home|telecommute)\b', loc.lower()) and not is_hybrid and not re.search(r'\b(us only|u\.s\. only|united states only|uk only|europe only|canada only|must reside in|must be based in)\b', full_text))
        )

        if not is_india and not is_pure_remote:
            has_visa = bool(
                re.search(r'\b(visa sponsorship|will sponsor visa|sponsorship available|visa & relocation|relocation support|corporate housing|j-1 visa sponsor|international applicants welcome|work authorization sponsorship)\b', full_text)
                or (comp.lower() in ['coupang', 'mercari'] and re.search(r'\b(tokyo|seoul|japan)\b', loc.lower()))
                or (comp.lower() in ['careem'] and re.search(r'\b(dubai|uae)\b', loc.lower()))
            )
            no_visa = bool(re.search(r'\b(no visa sponsorship|cannot sponsor|will not sponsor|without (?:company )?sponsorship|authorized to work in (?:the )?(?:us|uk|eu|canada|singapore|australia|germany|netherlands) without (?:need for )?sponsorship|must have (?:valid )?work authorization|no relocation assistance|existing right to work)\b', full_text))
            if no_visa or not has_visa:
                reasons.append("Abroad on-site without verified visa sponsorship")

        if reasons:
            disqualified.append({
                "job": j,
                "reasons": reasons
            })
        else:
            verified_jobs.append(j)

    total = len(jobs)
    passed = len(verified_jobs)
    accuracy_rate = (passed / total) * 100 if total > 0 else 100.0

    print("=" * 60)
    print("🛡️ RADAR QUALITY & CANDIDATE-FIT VERIFICATION REPORT")
    print("=" * 60)
    print(f"Total roles audited:  {total}")
    print(f"Passed verification:  {passed}")
    print(f"Disqualified pruned:  {len(disqualified)}")
    print(f"Clean accuracy rate:  {accuracy_rate:.1f}%")

    if disqualified:
        print("\nPruned Violations:")
        for item in disqualified:
            j = item["job"]
            print(f"  ❌ {j.get('company')} — {j.get('title')} ({j.get('location')})")
            for r in item["reasons"]:
                print(f"     • {r}")
    print("=" * 60)

    return accuracy_rate, verified_jobs, disqualified

def run_verification_loop():
    matches_file = os.path.join(BASE_DIR, "data", "latest_matches.json")
    if not os.path.exists(matches_file):
        print("No matches file found to verify.")
        return 100.0, []

    with open(matches_file, "r") as f:
        jobs = json.load(f)

    if not jobs:
        print("No jobs currently in feed to verify.")
        return 100.0, []

    accuracy_rate, verified_jobs, disqualified = audit_jobs(jobs)

    # Write cleaned verified list back to database
    with open(matches_file, "w") as f:
        json.dump(verified_jobs, f, indent=2)

    js_code = "window.RADAR_JOBS_DATA = " + json.dumps(verified_jobs) + ";\n"
    with open(os.path.join(BASE_DIR, "dashboard", "jobs_data.js"), "w") as f:
        f.write(js_code)
    with open(os.path.join(BASE_DIR, "jobs_data.js"), "w") as f:
        f.write(js_code)

    return accuracy_rate, verified_jobs

if __name__ == "__main__":
    run_verification_loop()
