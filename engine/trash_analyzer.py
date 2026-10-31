#!/usr/bin/env python3
"""
engine/trash_analyzer.py
========================
Analyzes manually trashed/disqualified jobs to learn negative patterns, 
extract low-level technical keywords, and permanently update the candidate profile
so future sweeps never suggest unaligned or overly technical postings.
"""

import os
import sys
import re
import json
from collections import Counter
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRASHED_FILE = os.path.join(BASE_DIR, "data", "trashed_jobs.json")
PROFILE_FILE = os.path.join(BASE_DIR, "profile", "garv_gupta_profile.json")

# Core technical stop words and indicators to flag as overly technical for non-tech operators
TECHNICAL_INDICATORS = [
    # Low-level systems & hardware
    "c++", "cpp", "cuda", "fpga", "verilog", "vhdl", "firmware", "kernel", "asic", 
    "microcontroller", "embedded", "pcb", "rtos", "arm", "dsp", "soc", "rfic",
    "hardware engineer", "silicon", "semiconductor", "device driver",
    
    # Deep engineering & systems
    "compiler", "distributed systems", "concurrency", "low-level", "systems software",
    "microservices", "kubernetes", "k8s", "docker container", "ci/cd pipeline",
    "infrastructure engineer", "site reliability", "sre", "devops",
    
    # Hard ML / AI / Vision research (not vibe coding / prompt engineering / product)
    "computer vision", "slam", "lidar", "deep learning research", "phd", "reinforcement learning",
    "pytorch internals", "tensorrt", "cuda kernels", "diffusion models research", "robotics engineer",
    "motion planning", "autonomous driving", "perception engineer",
    
    # Pure software engineering (Garv targets Product, APM, BizOps, Growth, Design)
    "software engineer intern", "software development intern", "full stack engineer intern",
    "backend engineer intern", "frontend engineer intern", "systems engineer intern"
]

def load_trashed_jobs():
    """Load trashed jobs from data/trashed_jobs.json if exists."""
    if not os.path.exists(TRASHED_FILE):
        return []
    try:
        with open(TRASHED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("jobs", []) or list(data.values())
    except Exception as e:
        print(f"⚠️ Error reading trashed jobs file: {e}")
    return []

def save_trashed_jobs(jobs):
    """Save trashed jobs to data/trashed_jobs.json."""
    os.makedirs(os.path.dirname(TRASHED_FILE), exist_ok=True)
    with open(TRASHED_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)

def analyze_trashed_patterns(trashed_jobs=None, update_profile=True):
    """
    Extract frequency patterns, technical keywords, and unaligned categories 
    from all trashed jobs, and update garv_gupta_profile.json.
    """
    if trashed_jobs is None:
        trashed_jobs = load_trashed_jobs()
        
    if not trashed_jobs:
        return {
            "status": "empty",
            "message": "No trashed jobs found in data/trashed_jobs.json.",
            "trashed_count": 0,
            "detected_keywords": [],
            "top_categories": [],
            "recommendations": []
        }
        
    print(f"📊 Analyzing {len(trashed_jobs)} manually trashed jobs for negative patterns...")
    
    # Collect titles, companies, categories, and descriptions
    titles = [j.get("title", "") for j in trashed_jobs]
    categories = [j.get("category", "") for j in trashed_jobs]
    companies = [j.get("company", "") for j in trashed_jobs]
    texts = [f"{j.get('title', '')} {j.get('salary_raw', '')} {j.get('category', '')}" for j in trashed_jobs]
    
    # 1. Match against known technical indicators
    matched_tech_keywords = Counter()
    for full_text in texts:
        t_lower = full_text.lower()
        for kw in TECHNICAL_INDICATORS:
            # Match word boundary for short acronyms like c++, rtos
            if kw in ["c++", "cpp"]:
                if re.search(r'\b(c\+\+|cpp)\b', t_lower):
                    matched_tech_keywords[kw] += 1
            elif kw in ["asic", "dsp", "soc", "arm", "slam", "k8s"]:
                if re.search(rf'\b{kw}\b', t_lower):
                    matched_tech_keywords[kw] += 1
            else:
                if kw in t_lower:
                    matched_tech_keywords[kw] += 1
                    
    # 2. Extract high-frequency technical bigrams/unigrams from titles
    title_words = []
    stop_words = {"intern", "internship", "summer", "fall", "spring", "at", "and", "or", "the", "in", "for", "with", "&", "-"}
    for t in titles:
        cleaned = re.sub(r'[^a-zA-Z0-9\s\+]', ' ', t.lower())
        tokens = [w for w in cleaned.split() if len(w) > 2 and w not in stop_words]
        title_words.extend(tokens)
        
    word_freq = Counter(title_words)
    
    # 3. Category distribution
    cat_dist = Counter([c for c in categories if c])
    comp_dist = Counter([c for c in companies if c])
    
    # 4. Generate recommendations for negative filter
    recommended_negatives = []
    for kw, count in matched_tech_keywords.most_common(15):
        if count >= 1 and kw not in recommended_negatives:
            recommended_negatives.append(kw)
            
    # Also suggest any repeated non-operator words from titles
    technical_role_words = ["engineer", "engineering", "developer", "hardware", "firmware", "embedded", "scientist", "compiler"]
    for w, count in word_freq.most_common(20):
        if w in technical_role_words and w not in recommended_negatives:
            recommended_negatives.append(w)
            
    # 5. Optionally update profile
    profile_updated = False
    if update_profile and os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                profile = json.load(f)
                
            current_negatives = set(profile.get("negative_keywords", []))
            current_disqualified_tech = set(profile.get("disqualified_technical_keywords", []))
            
            new_negatives = []
            for kw in recommended_negatives:
                if kw not in current_negatives and kw not in current_disqualified_tech:
                    new_negatives.append(kw)
                    
            if new_negatives or "disqualified_technical_keywords" not in profile:
                profile.setdefault("disqualified_technical_keywords", TECHNICAL_INDICATORS)
                profile["negative_keywords"] = sorted(list(current_negatives.union(new_negatives)))
                profile["trashed_analysis_last_run"] = datetime.now().isoformat()
                profile["trashed_sample_count"] = len(trashed_jobs)
                
                with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                    json.dump(profile, f, indent=2)
                profile_updated = True
                print(f"✅ Updated {PROFILE_FILE} with {len(new_negatives)} newly discovered negative filters!")
        except Exception as e:
            print(f"⚠️ Error updating candidate profile: {e}")

    summary = {
        "status": "success",
        "trashed_count": len(trashed_jobs),
        "profile_updated": profile_updated,
        "top_technical_flags": matched_tech_keywords.most_common(10),
        "frequent_title_tokens": word_freq.most_common(10),
        "category_distribution": cat_dist.most_common(5),
        "company_distribution": comp_dist.most_common(5),
        "recommended_negatives": recommended_negatives
    }
    
    return summary

def is_job_disqualified_by_trash_patterns(job, profile=None):
    """
    Check if a candidate job should be disqualified based on learned negative 
    technical patterns and trashed records.
    """
    title = (job.get("title", "") or "").lower()
    raw = (job.get("salary_raw", "") or "").lower()
    dept = (job.get("raw_department", "") or "").lower()
    combined = f"{title} {dept} {raw}"
    
    # 1. Check known trashed IDs
    trashed_jobs = load_trashed_jobs()
    trashed_ids = {j.get("id") for j in trashed_jobs if j.get("id")}
    if job.get("id") in trashed_ids:
        return True, "Job ID is in manual Trash compartment"
        
    # 2. Check profile disqualified technical keywords
    if profile:
        disqualified_tech = profile.get("disqualified_technical_keywords", TECHNICAL_INDICATORS)
        for kw in disqualified_tech:
            if kw in ["c++", "cpp"]:
                if re.search(r'\b(c\+\+|cpp)\b', combined):
                    return True, f"Contains disqualified technical term: {kw}"
            elif kw in ["asic", "dsp", "soc", "arm", "slam", "k8s", "rfic", "pcb"]:
                if re.search(rf'\b{kw}\b', combined):
                    return True, f"Contains disqualified technical term: {kw}"
            elif kw in combined:
                return True, f"Contains disqualified technical term: {kw}"
                
    return False, ""

if __name__ == "__main__":
    res = analyze_trashed_patterns(update_profile=True)
    print("\n" + "=" * 60)
    print("🧠 TRASH COMPARTMENT ANALYSIS REPORT")
    print("=" * 60)
    print(f"Total Trashed Jobs Analyzed: {res.get('trashed_count', 0)}")
    if res.get("top_technical_flags"):
        print("\nTop Technical Red Flags Detected:")
        for kw, cnt in res["top_technical_flags"]:
            print(f"  • {kw}: {cnt} occurrence(s)")
    if res.get("recommended_negatives"):
        print(f"\nRecommended Negative Filters: {', '.join(res['recommended_negatives'])}")
    print("=" * 60 + "\n")

