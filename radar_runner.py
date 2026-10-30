#!/usr/bin/env python3
import os
import sys
import json
import http.server
import socketserver
import webbrowser
from datetime import datetime

# Add engine to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from engine.harvester import run_harvest
from engine.scorer import score_job
from engine.notifier import process_alerts, send_macos_notification

CONFIG_FILE = os.path.join(BASE_DIR, "config", "companies.json")
PROFILE_FILE = os.path.join(BASE_DIR, "profile", "garv_gupta_profile.json")
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def run_scan():
    print("=" * 60)
    print("📡 GARV GUPTA • INTERNSHIP RADAR HARVESTER")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    config = load_json(CONFIG_FILE)
    profile = load_json(PROFILE_FILE)

    print("🔍 Harvesting live listings from Greenhouse, Lever, and Curated Repos...")
    raw_jobs = run_harvest(config)
    print(f"✓ Found {len(raw_jobs)} non-technical internship postings.")

    print("🧠 Scoring against Garv's Candidate DNA Profile...")
    scored_jobs = []
    for j in raw_jobs:
        score_data = score_job(j, profile)
        j.update(score_data)
        scored_jobs.append(j)

    print("🔔 Processing net-new alerts and desktop notifications...")
    new_alerts = process_alerts(scored_jobs)

    tier1_jobs = [j for j in scored_jobs if j["match_score"] >= 88]
    safe_hubs = ["China / HK / TW", "Japan", "Singapore", "UAE / Middle East", "Germany", "Netherlands", "Ireland", "Nordics / Swiss", "Australia / NZ", "Remote", "Southern / Central Europe"]
    intl_jobs = [j for j in scored_jobs if j["location_info"]["region"] in safe_hubs]

    print("\n" + "=" * 60)
    print("📊 SCAN SUMMARY")
    print("=" * 60)
    print(f"• Total Active Non-Tech Internships: {len(scored_jobs)}")
    print(f"• Tier 1 High Conversion Fits (>88%): {len(tier1_jobs)}")
    print(f"• Global / Welcoming Tech Hubs:       {len(intl_jobs)}")
    print(f"• Net-New Postings In This Sweep:    {len(new_alerts)}")

    print("\n🔥 TOP 7 HIGH CONVERSION MATCHES FOR GARV:")
    print("-" * 60)
    for i, j in enumerate(scored_jobs[:7], 1):
        badge = j["location_info"]["badge"]
        print(f"{i}. [{j['match_score']}% Match] {j['company']} — {j['title']}")
        print(f"   Category: {j['category']} | Location: {j['location']} ({badge})")
        print(f"   Apply:    {j['url']}")
        print(f"   Pitch:    \"{j['recruiter_pitch'][:90]}...\"\n")

    print("✅ Dashboard updated at: /Users/apple/.gemini/internship-radar/dashboard/index.html")
    print("👉 To open the visual dashboard: python3 radar_runner.py serve")

def start_server(port=8080):
    os.chdir(BASE_DIR)
    Handler = http.server.SimpleHTTPRequestHandler
    
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            url = f"http://localhost:{port}/dashboard/index.html"
            print("=" * 60)
            print(f"🚀 Internship Radar Dashboard is live at: {url}")
            print("=" * 60)
            print("Press Ctrl+C to stop the server.")
            try:
                webbrowser.open(url)
            except Exception:
                pass
            httpd.serve_forever()
    except OSError as e:
        if "Address already in use" in str(e):
            start_server(port + 1)
        else:
            raise e

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    
    if cmd == "scan":
        run_scan()
    elif cmd == "serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
        start_server(port)
    elif cmd == "test-alert":
        send_macos_notification("🚀 Test Notification", "Internship Radar", "Testing desktop notification for Garv Gupta")
        print("Sent test notification.")
    else:
        print("Usage: python3 radar_runner.py [scan|serve|test-alert]")

