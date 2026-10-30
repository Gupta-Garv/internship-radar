import os
import json
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEN_JOBS_FILE = os.path.join(BASE_DIR, "data", "seen_jobs.json")
MATCHES_FILE = os.path.join(BASE_DIR, "data", "latest_matches.json")

def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_seen_jobs(seen_dict):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(seen_dict, f, indent=2)

def send_macos_notification(title, subtitle, message):
    try:
        script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
        subprocess.run(["osascript", "-e", script], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def process_alerts(scored_jobs):
    seen = load_seen_jobs()
    now_str = datetime.now().isoformat()
    new_alerts = []
    
    for job in scored_jobs:
        job_id = job["id"]
        score = job["match_score"]
        comp = job["company"]
        title = job["title"]
        loc = job["location"]
        
        if job_id not in seen:
            seen[job_id] = {
                "first_seen": now_str,
                "company": comp,
                "title": title,
                "score": score
            }
            job["is_new"] = True
            new_alerts.append(job)
        else:
            job["is_new"] = False
            
    # Save updated seen jobs
    save_seen_jobs(seen)
    
    # Save all active scored jobs sorted: NEW first, then latest published timestamp, then match score
    scored_jobs.sort(key=lambda x: (x.get("is_new", False), x.get("timestamp", 0), x.get("match_score", 0)), reverse=True)
    with open(MATCHES_FILE, "w") as f:
        json.dump(scored_jobs, f, indent=2)
        
    # Also write a JS bundle for direct double-click file:// support without web server
    js_bundle_path = os.path.join(BASE_DIR, "dashboard", "jobs_data.js")
    with open(js_bundle_path, "w") as f:
        f.write("window.RADAR_JOBS_DATA = " + json.dumps(scored_jobs) + ";\n")
    
    # Also copy to root for GitHub Pages hosting root
    root_js_path = os.path.join(BASE_DIR, "jobs_data.js")
    with open(root_js_path, "w") as f:
        f.write("window.RADAR_JOBS_DATA = " + json.dumps(scored_jobs) + ";\n")
        
    # Trigger notifications for high-priority new matches (top 3 in this sweep)
    high_tier_new = [j for j in new_alerts if j["match_score"] >= 88]
    for j in high_tier_new[:3]:
        send_macos_notification(
            title=f"🚀 Top Internship Alert ({j['match_score']}%)",
            subtitle=f"{j['company']} • {j['category']}",
            message=f"{j['title']} ({j['location']})"
        )
        
    return new_alerts
