#!/usr/bin/env python3
import os
import sys
import json
import subprocess
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
from engine.cv_generator import generate_tailored_cv, export_html_to_pdf
from engine.qa_generator import generate_human_qa_answer
from engine.hackathon_scout import scout_all_hackathons

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
        if score_data is not None:
            j.update(score_data)
            scored_jobs.append(j)

    print("🔔 Processing net-new alerts and desktop notifications...")
    new_alerts = process_alerts(scored_jobs)

    print("🏆 Scouting active high-prize hackathons & developer challenges...")
    scouted_hacks = scout_all_hackathons()

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

class RadarHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/generate_cv":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                jd = data.get("jd", "")
                comp = data.get("company", "")
                role = data.get("role", "")
                key = data.get("api_key", "")
                model = data.get("model", "mistralai/mistral-large-4-1t-a52b")
                
                result = generate_tailored_cv(jd, company=comp, role=role, api_key=key, model=model)
                
                self.send_response(200 if result.get("success") else 500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
        elif self.path == "/api/generate_qa":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                q = data.get("question", "")
                comp = data.get("company", "")
                role = data.get("role", "")
                jd = data.get("jd_context", "")
                ans_len = data.get("length", "concise")
                key = data.get("api_key", "")
                model = data.get("model", "mistralai/mistral-large-4-1t-a52b")
                
                result = generate_human_qa_answer(q, company=comp, role=role, jd_context=jd, length=ans_len, api_key=key, model=model)
                
                self.send_response(200 if result.get("success") else 500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
        elif self.path == "/api/export_pdf":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                html = data.get("html", "")
                filename = data.get("filename", "Garv_Gupta_Resume.pdf")
                out_path = os.path.join(BASE_DIR, "data", filename)
                ok = export_html_to_pdf(html, out_path)
                
                self.send_response(200 if ok else 500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": ok, "file_path": out_path}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
        else:
            super().do_POST()

def start_server(port=8080):
    os.chdir(BASE_DIR)
    Handler = RadarHandler
    
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            url = f"http://localhost:{port}/dashboard/index.html"
            print("=" * 60)
            print(f"🚀 Internship Radar Dashboard & AI Studio is live at: {url}")
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

def run_cv_cli(company, role, jd_file_or_text):
    jd = jd_file_or_text
    if os.path.exists(jd_file_or_text):
        with open(jd_file_or_text, "r") as f:
            jd = f.read()
            
    print(f"🧠 Generating tailored human CV for {company} - {role} using Mistral Large...")
    res = generate_tailored_cv(jd, company=company, role=role)
    if res.get("success"):
        out_name = f"Garv_Gupta_Resume_{company.replace(' ', '_')}.pdf"
        out_path = os.path.join(BASE_DIR, "data", out_name)
        export_html_to_pdf(res["html"], out_path)
        print(f"✅ Success! PDF saved to: {out_path}")
        subprocess.run(["open", out_path])
    else:
        print(f"❌ Error: {res.get('error')}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    
    if cmd == "scan":
        run_scan()
    elif cmd == "serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
        start_server(port)
    elif cmd == "cv":
        comp = sys.argv[2] if len(sys.argv) > 2 else "Target Company"
        role = sys.argv[3] if len(sys.argv) > 3 else "Product Intern"
        jd = sys.argv[4] if len(sys.argv) > 4 else "Product management and execution role."
        run_cv_cli(comp, role, jd)
    elif cmd == "qa":
        comp = sys.argv[2] if len(sys.argv) > 2 else "Target Company"
        role = sys.argv[3] if len(sys.argv) > 3 else "Product Intern"
        q = sys.argv[4] if len(sys.argv) > 4 else "Why are you interested in this role?"
        res = generate_human_qa_answer(q, company=comp, role=role)
        if res.get("success"):
            print("\n" + "=" * 60)
            print(f"✍️ HUMAN OPERATOR ANSWER FOR {comp} ({res['word_count']} words):")
            print("=" * 60)
            print(res["answer"])
            print("=" * 60 + "\n")
        else:
            print("❌ Error:", res.get("error"))
    elif cmd in ["trash", "analyze-trash"]:
        from engine.trash_analyzer import analyze_trashed_patterns
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
            print(f"\nRecommended Negative Filters Added to Profile:\n  {', '.join(res['recommended_negatives'])}")
        print("=" * 60 + "\n")
    elif cmd == "test-alert":
        send_macos_notification("🚀 Test Notification", "Internship Radar", "Testing desktop notification for Garv Gupta")
        print("Sent test notification.")
    elif cmd == "hackathons":
        scout_all_hackathons()
    else:
        print("Usage: python3 radar_runner.py [scan|serve|cv|qa|hackathons|trash|test-alert]")

