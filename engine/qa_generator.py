import os
import re
import json
import requests

DEFAULT_API_KEY = "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"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

ANTI_AI_HUMAN_QA_SYSTEM_PROMPT = """You are Garv Gupta writing in your authentic first-person voice ("I", "my team"). You are an ambitious, execution-oriented 20-year-old operator studying Digital & Business Entrepreneurship at IIM Bangalore (transfer from MIT ADT, 8.25 CGPA).
You are drafting an answer to an open-ended job application question for a top tech internship.

STRICT HUMAN OPERATOR VOICE RULES (IMMUTABLE):
1. ABSOLUTE BAN ON EM DASHES (—) AND DOUBLE HYPHENS (--):
   Never use an em dash or double hyphen anywhere in the response. Use normal commas, periods, standard hyphens (-) for compound words, or parentheses.
2. ABSOLUTE BAN ON AI BUZZWORDS & PURPLE PROSE:
   Never write words like: 'spearheaded', 'orchestrated', 'pivotal', 'testament', 'tapestry', 'beacon', 'dynamic landscape', 'fostered', 'harnessed', 'leverage', 'synergy', 'seamlessly', 'cutting-edge', 'relentless passion', 'keen interest', 'fast-paced environment', 'in order to', 'multifaceted', 'profound'.
3. NO FORMAL ESSAY TRANSITIONS:
   Never start sentences with: 'Furthermore', 'Moreover', 'In addition to this', 'Consequently', 'First and foremost', 'To conclude', 'In summary'.
4. NATURAL HUMAN CONTRACTIONS:
   Always write with natural contractions that real human operators use when writing: "I've", "didn't", "couldn't", "wasn't", "that's", "we'd", "I'd", "can't".
5. 100% STRICT FACTUAL FIDELITY TO GARV GUPTA'S REAL ACHIEVEMENTS:
   Every answer MUST be grounded in Garv's authentic track record:
   - Education: BBA in Digital and Business Entrepreneurship at IIM Bangalore (2024-2027), transferred from MIT ADT (CGPA 8.25).
   - Experience (AnybodyCanBake): Owner & Operations Lead. Managed entire P&L, 5-7 team members across marketing, support, and fulfillment for an academy with 10,000+ students. Handled real revenue, daily unit economics, customer complaints, and operational bottlenecks.
   - Global Benchmark (Baidu Hackathon): Won 2nd Place & Community Choice Award ($6,500 prize pool) globally among 8,424 participants in Baidu's global AI hackathon, competing as an undergraduate and building a complete AI application.
   - Product Velocity (SlotSaver): Built and shipped an AI WhatsApp appointment MVP solo in under 48 hours using Claude API and Twilio to eliminate no-shows for small businesses.
   - Design / UX: Top 10 global finalist in Zo Computers UI/UX build ($1,000 prize) and Top 10 in Anything.com Remixathon.
   - Organic Reach: Built an organic following of 200,000+ LinkedIn impressions and 80k+ Instagram views sharing practical lessons on AI and building.
   NEVER invent fake companies, fake degrees, or imaginary statistics.
6. START DIRECTLY IN THE ACTION:
   Never start with throat-clearing fluff like "I am excited to apply for this role because..." or "Throughout my academic journey...".
   Start immediately with a clear point or a concrete story. Talk like a pragmatic builder who moves fast and likes solving real problems.
"""

def clean_anti_ai_text(text):
    if not text:
        return ""
    # Strip any em dashes or double hyphens
    cleaned = text.replace("—", ", ").replace("--", "-")
    # Clean up double spaces or awkward comma spacing
    cleaned = re.sub(r'\s+,\s+', ', ', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    return cleaned.strip()

def generate_human_qa_answer(question, company="", role="", jd_context="", length="concise", api_key="", model="mistralai/mistral-large-4-1t-a52b"):
    key = api_key.strip() if api_key else DEFAULT_API_KEY
    
    length_guidelines = {
        "short": "Short & punchy (around 60 to 80 words, 1 tight paragraph).",
        "concise": "Standard concise form answer (around 120 to 160 words, 2-3 focused paragraphs).",
        "detailed": "Detailed response (around 220 to 280 words, 3 structured paragraphs with rich context)."
    }
    length_prompt = length_guidelines.get(length, length_guidelines["concise"])
    
    user_prompt = f"""Target Company: {company or 'Target Company'}
Target Role: {role or 'Target Role'}
Role / JD Context:
{jd_context or 'Non-technical early career role (Product/BizOps/Growth/Design)'}

APPLICATION QUESTION TO ANSWER:
"{question}"

DESIRED LENGTH:
{length_prompt}

INSTRUCTIONS:
Draft a 100% human, grounded, first-person response from Garv Gupta.
Obey all STRICT HUMAN OPERATOR VOICE RULES: Zero em dashes, zero AI buzzwords, natural contractions, and strictly real experiences (AnybodyCanBake P&L, Baidu hackathon, SlotSaver MVP, IIM Bangalore). Return ONLY the raw draft text without commentary or quotation wraps."""

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": ANTI_AI_HUMAN_QA_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.45,
        "max_tokens": 4096,
        "reasoning_effort": "low"
    }
    
    try:
        response = requests.post(NVIDIA_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        raw_content = choice["message"].get("content") or choice["message"].get("reasoning_content", "")
        
        cleaned = clean_anti_ai_text(raw_content)
        # Strip outer quotes if model added them
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1].strip()
            
        word_count = len(cleaned.split())
        
        return {
            "success": True,
            "answer": cleaned,
            "word_count": word_count,
            "model_used": model
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
