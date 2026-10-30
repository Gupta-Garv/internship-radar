import os
import sys
import json
import re
import subprocess
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESUME_FILE = os.path.join(BASE_DIR, "profile", "resume.md")
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

DEFAULT_API_KEY = "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"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

ANTI_AI_SYSTEM_PROMPT = """You are an elite executive career strategist who crafts crisp, credible, and 100% human-written resumes for top-tier candidates.
Your task is to write a tailored, single-page, ATS-compliant CV for Garv Gupta specifically aligned to the provided Job Description.

STRICT ANTI-AI & HUMAN TONE DOCTRINE:
1. ABSOLUTE BAN ON AI MARKER WORDS:
   Never use words like: 'spearheaded', 'orchestrated', 'pivotal', 'tapestry', 'delve', 'beacon', 'testament', 'dynamic', 'fostered', 'harnessed', 'leverage', 'seamless', 'cutting-edge', 'synergy', 'in order to', 'groundbreaking', 'robust', 'fostering', 'passionate', 'adept'.
2. PURE OPERATOR VOICE:
   Start every single bullet point with punchy, concrete active verbs: Built, Shipped, Won, Cut, Led, Managed, Designed, Coordinated, Ran, Scaled, Pitched, Automated, Analyzed.
3. 100% FACTUAL FIDELITY:
   Strictly preserve Garv Gupta's authentic credentials:
   - Education: Indian Institute of Management Bangalore (IIM Bangalore) - BBA in Digital & Business Entrepreneurship (2024-2027); MIT ADT transfer (CGPA 8.25).
   - Key Achievements: 2nd Place & Community Choice Award at Baidu MeDo Global AI Hackathon ($6,500 prize pool, 8,424 participants); Top 10 Global Finalist in Zo Computers UI/UX build ($1,000 prize); Top 10 in Anything.com Remixathon; 1st Place IIM Bangalore essay cited by Microsoft researcher; 200,000+ organic LinkedIn impressions.
   - Experience: AnybodyCanBake Owner & Operations Lead (10,000+ students, full legal & P&L responsibility, 5-7 team members); Digibility AI (Early team member); SocialBent (Content/SEO).
   - Projects: SlotSaver (AI WhatsApp MVP shipped solo in under 48 hours with Claude API and Twilio).
   NEVER invent fake companies, fake degrees, or imaginary statistics.
4. TARGETED EMPHASIS:
   Selectively order and frame bullets to highlight the exact skills and traits requested in the JD (e.g. scoping & product velocity for APM; P&L, team leadership & cross-functional execution for BizOps; SEO & distribution for Growth).
5. FORMAT:
   Return a complete, self-contained HTML document with standard single-page Harvard/IIM formatting. Use Times New Roman or serif fonts, clean section headers with bottom borders, flexbox for dates/locations, and bullet points with concise metrics.
"""

def get_base_resume():
    if os.path.exists(RESUME_FILE):
        with open(RESUME_FILE, "r") as f:
            return f.read()
    return ""

def generate_tailored_cv(jd_text, company="", role="", api_key="", model="mistralai/mistral-large-4-1t-a52b", tone="operator"):
    key = api_key.strip() if api_key else DEFAULT_API_KEY
    base_resume = get_base_resume()
    current_date = datetime.now().strftime("%B %Y")
    
    user_prompt = f"""
CANDIDATE BASE RESUME:
{base_resume}

TARGET COMPANY: {company or 'Target Company'}
TARGET ROLE: {role or 'Target Role'}
APPLICATION DATE: {current_date}

JOB DESCRIPTION & REQUIREMENTS:
{jd_text}

INSTRUCTIONS:
Craft a tailored, single-page, human-written CV for Garv Gupta that matches the above JD.
Follow the STRICT ANTI-AI rules. Return only clean HTML with standard embedded CSS for an ATS-compliant 1-page resume.
"""

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": ANTI_AI_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.4,
        "max_tokens": 4096,
        "reasoning_effort": "low"
    }
    
    try:
        response = requests.post(NVIDIA_URL, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        raw_content = choice["message"].get("content")
        
        # Fallback if reasoning consumed tokens
        if not raw_content:
            raw_content = choice["message"].get("reasoning_content", "")
            
        html = raw_content or ""
        if "```html" in html:
            html = html.split("```html")[1].split("```")[0].strip()
        elif "```" in html:
            html = html.split("```")[1].split("```")[0].strip()
            
        return {
            "success": True,
            "html": html,
            "model_used": model,
            "tokens": data.get("usage", {}).get("total_tokens", 0)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def export_html_to_pdf(html_content, output_pdf_path):
    temp_html = output_pdf_path.replace(".pdf", ".temp.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    if os.path.exists(CHROME_PATH):
        try:
            cmd = [
                CHROME_PATH,
                "--headless",
                "--disable-gpu",
                f"--print-to-pdf={output_pdf_path}",
                temp_html
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(temp_html):
                os.remove(temp_html)
            return True
        except Exception:
            pass
            
    if os.path.exists(temp_html):
        os.remove(temp_html)
    return False
