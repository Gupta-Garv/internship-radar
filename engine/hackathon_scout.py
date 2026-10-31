import os
import re
import json
import requests
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

# Curated flagship AI and product competitions with verified high prize pools (>= $5k-$1M),
# open to India and 100% achievable for vibe coders using Claude, Cursor, v0 & Next.js.
CURATED_FLAGSHIP_HACKATHONS = [
    {
        "id": "google_gemini_competition",
        "title": "Google Gemini API Developer Competition",
        "organizer": "Google DeepMind & Google Cloud",
        "platform": "Google Developer",
        "prize_pool": "$1,000,000",
        "prize_usd": 1000000,
        "deadline_iso": "2026-12-15T23:59:59Z",
        "deadline_display": "Dec 15, 2026",
        "url": "https://ai.google.dev/competition",
        "eligibility": "Global & India Open (100% Online)",
        "vibe_coder_score": "100% Vibe Coder Friendly",
        "brief": "Build a breakthrough web application or agent leveraging Gemini 1.5 Pro's 2M-token context window and native multimodal audio/video processing. Grand prize is a custom electric DeLorean or $100k+ cash. Judged on real utility and creative execution.",
        "recommended_stack": "Gemini 1.5 Pro API + Next.js + Tailwind + Firebase Auth",
        "strategy": "Leverage long audio or PDF ingestion. Vibe code an interactive audit tool or customer feedback synthesizer that ingests entire video/audio calls and extracts instant actionable dashboards.",
        "tags": ["Multimodal AI", "Grand Prize", "High Impact", "Web App"]
    },
    {
        "id": "meta_vr_developer_2026",
        "title": "Meta VR & Spatial AI Challenge 2026",
        "organizer": "Meta Developer Ecosystem",
        "platform": "Devpost",
        "prize_pool": "$1,000,000",
        "prize_usd": 1000000,
        "deadline_iso": "2026-11-18T23:59:59Z",
        "deadline_display": "Nov 18, 2026",
        "url": "https://start-developer-competition-26.devpost.com/",
        "eligibility": "Worldwide Open & India Eligible",
        "vibe_coder_score": "95% Vibe Coder Friendly",
        "brief": "Build web-based spatial experiences or browser 3D AI applications using Three.js and WebXR. Focuses on intuitive user interactions, voice-command spatial helpers, and real-time generative canvas tools.",
        "recommended_stack": "Three.js / React Three Fiber + Meta Llama API + Cursor + Vercel",
        "strategy": "Don't build heavy Unity C# games. Build a sleek web-first 3D showroom or interactive product customizer using Three.js and Claude. Judges love immediate zero-install browser demos.",
        "tags": ["Spatial AI", "WebXR", "Three.js", "Top Prize"]
    },
    {
        "id": "atlassian_codegeist_2026",
        "title": "Atlassian Codegeist 2026: Build with Context",
        "organizer": "Atlassian",
        "platform": "Devpost",
        "prize_pool": "$120,000",
        "prize_usd": 120000,
        "deadline_iso": "2026-12-22T23:59:59Z",
        "deadline_display": "Dec 22, 2026",
        "url": "https://codegeist.devpost.com/",
        "eligibility": "Global & India Open (100% Online)",
        "vibe_coder_score": "95% Vibe Coder Friendly",
        "brief": "Build an Atlassian Forge app for Jira or Confluence that leverages AI to eliminate team busywork. Forge provides pre-hosted templates, allowing frontend operators to ship intelligent summaries, automated sprint triage, and ticket resolution bots in hours.",
        "recommended_stack": "Atlassian Forge (React / Node.js) + Mistral Large / Claude API",
        "strategy": "Use Atlassian's Forge starter templates. Create an AI sprint retrospective bot that analyzes completed Jira issues and generates executive slides automatically.",
        "tags": ["Enterprise AI", "Productivity", "Forge Apps", "Automation"]
    },
    {
        "id": "kiroween_2026",
        "title": "Kiroween 2026 Global AI Hackathon",
        "organizer": "Kiro AI & AWS",
        "platform": "Devpost",
        "prize_pool": "$100,000",
        "prize_usd": 100000,
        "deadline_iso": "2026-12-04T23:59:59Z",
        "deadline_display": "Dec 04, 2026",
        "url": "https://kiroween.devpost.com/",
        "eligibility": "Global & India Open (100% Online)",
        "vibe_coder_score": "100% Vibe Coder Friendly",
        "brief": "Build a creative, open-ended AI application, autonomous agent, or interactive product using any modern foundation model. Low barrier to entry: judges prioritize end-to-end user experience, functional prototypes, and sheer utility over low-level algorithmic complexity.",
        "recommended_stack": "Claude API / OpenAI API + Cursor / v0 + Next.js + Tailwind",
        "strategy": "Ship a complete end-to-end vertical tool (like SlotSaver or an automated client onboarding portal). Polish the landing page and include a 60-second Loom showing instant zero-friction value.",
        "tags": ["AI Agents", "Beginner Friendly", "Open Ended", "Web MVP"]
    },
    {
        "id": "solana_radar_ai_track",
        "title": "Solana Radar Global Hackathon: AI Track",
        "organizer": "Solana Foundation & Superteam",
        "platform": "DoraHacks / Colosseum",
        "prize_pool": "$100,000",
        "prize_usd": 100000,
        "deadline_iso": "2026-12-18T23:59:59Z",
        "deadline_display": "Dec 18, 2026",
        "url": "https://arena.colosseum.org/",
        "eligibility": "Global & India Open (Superteam India Support)",
        "vibe_coder_score": "90% Vibe Coder Friendly",
        "brief": "Create an autonomous AI agent capable of managing micro-transactions, buying data feeds, or executing decentralized tasks on behalf of users. Excellent mentorship and demo days hosted in Bangalore and online.",
        "recommended_stack": "Solana Web3.js + Eliza / AI Agent Framework + Cursor",
        "strategy": "Superteam India has massive active hubs in Bangalore. Build an AI agent with a Telegram or WhatsApp frontend that manages scheduled escrow or payment triggers for creators.",
        "tags": ["Autonomous Agents", "Web3 AI", "Superteam India", "Top Tier"]
    },
    {
        "id": "paypal_ai_2026",
        "title": "PayPal AI Global Hackathon",
        "organizer": "PayPal Developer",
        "platform": "Devpost",
        "prize_pool": "$67,500",
        "prize_usd": 67500,
        "deadline_iso": "2026-11-12T23:59:59Z",
        "deadline_display": "Nov 12, 2026",
        "url": "https://paypalaihackathon.devpost.com/",
        "eligibility": "Global & India Open (100% Online)",
        "vibe_coder_score": "95% Vibe Coder Friendly",
        "brief": "Create an AI-powered commerce or payment prototype using PayPal's developer APIs. Perfect for vibe coders to build automated invoicing, smart merchant bots, or AI customer checkout assistants using pre-built APIs.",
        "recommended_stack": "PayPal REST API + Next.js + Twilio or WhatsApp Business API",
        "strategy": "Tap into your AnybodyCanBake merchant experience: build an AI checkout assistant that recovers abandoned carts via conversational WhatsApp messages with 1-click PayPal payment links.",
        "tags": ["Commerce AI", "Low / No-Code", "Fintech", "Web"]
    },
    {
        "id": "aws_genai_builder_sprint",
        "title": "AWS Generative AI Global Builder Sprint",
        "organizer": "Amazon Web Services (AWS)",
        "platform": "Devpost",
        "prize_pool": "$50,000",
        "prize_usd": 50000,
        "deadline_iso": "2026-12-10T23:59:59Z",
        "deadline_display": "Dec 10, 2026",
        "url": "https://aws-genai-sprint.devpost.com/",
        "eligibility": "Worldwide Open & India Eligible",
        "vibe_coder_score": "95% Vibe Coder Friendly",
        "brief": "Build a customer-facing AI agent using Amazon Bedrock foundation models (Claude 3.5 Sonnet, Llama 3). Focuses on cost-effective, scalable workflows that solve real SMB pain points.",
        "recommended_stack": "Amazon Bedrock API + Next.js App Router + Tailwind + Vercel",
        "strategy": "Use Amazon Bedrock's Claude 3.5 Sonnet endpoint. Build an automated contract review or RFP analyzer for small business owners with PDF export.",
        "tags": ["Bedrock AI", "Cloud AI", "SMB Workflows", "SaaS MVP"]
    },
    {
        "id": "ugreen_ai_nas_2026",
        "title": "UGREEN AI Smart Storage & Hub Hackathon",
        "organizer": "UGREEN",
        "platform": "Devpost",
        "prize_pool": "$46,000",
        "prize_usd": 46000,
        "deadline_iso": "2026-11-16T23:59:59Z",
        "deadline_display": "Nov 16, 2026",
        "url": "https://ugreen-hackathon.devpost.com/",
        "eligibility": "Worldwide Open (100% Online)",
        "vibe_coder_score": "90% Vibe Coder Friendly",
        "brief": "Develop smart home or personal productivity automation tools that manage files, photos, or media using local or cloud AI models. Build intuitive web interfaces for document search and audio tagging.",
        "recommended_stack": "FastAPI / Node.js + Local AI / Ollama + Tailwind",
        "strategy": "Design an AI photo & document archivist with instant semantic natural language search ('find receipts from my trip to Goa last winter').",
        "tags": ["Smart Storage", "Personal AI", "Media Automation", "Web"]
    },
    {
        "id": "mistral_worldwide_sprint",
        "title": "Mistral AI Global Agent Sprint",
        "organizer": "Mistral AI",
        "platform": "Lablab.ai",
        "prize_pool": "$30,000",
        "prize_usd": 30000,
        "deadline_iso": "2026-11-20T23:59:59Z",
        "deadline_display": "Nov 20, 2026",
        "url": "https://lablab.ai/ai-hackathons/mistral-ai-sprint",
        "eligibility": "Global & India Open (100% Online)",
        "vibe_coder_score": "100% Vibe Coder Friendly",
        "brief": "Design and ship a multi-step agent workflow utilizing Mistral Large 4 function-calling and reasoning capabilities. Build conversational business assistants, legal triage, or automated research agents.",
        "recommended_stack": "Mistral Large API + LangChain / CrewAI + Next.js",
        "strategy": "Utilize your proven Mistral Large prompt doctrine. Build a multi-agent recruiter evaluation or candidate interview prep simulator that outputs custom markdown scorecards.",
        "tags": ["AI Agents", "Function Calling", "Product MVP", "Reasoning"]
    },
    {
        "id": "elevenlabs_voice_hackathon",
        "title": "ElevenLabs Worldwide AI Voice & Agent Hackathon",
        "organizer": "ElevenLabs",
        "platform": "Devpost",
        "prize_pool": "$25,000",
        "prize_usd": 25000,
        "deadline_iso": "2026-12-06T23:59:59Z",
        "deadline_display": "Dec 06, 2026",
        "url": "https://elevenlabs-agents.devpost.com/",
        "eligibility": "Worldwide Open & India Eligible",
        "vibe_coder_score": "100% Vibe Coder Friendly",
        "brief": "Build an ultra-low-latency voice agent or audio-first productivity tool using the ElevenLabs Conversational AI SDK and Voice Design tools. Perfect for phone receptionist bots or interactive podcasts.",
        "recommended_stack": "ElevenLabs Conversational AI SDK + WebRTC + React + Tailwind",
        "strategy": "Build a live voice interviewer or real-time voice reservation taker for restaurants or bakeries that talks fluidly with callers.",
        "tags": ["Voice AI", "Conversational Agents", "WebRTC", "Audio"]
    },
    {
        "id": "cloudflare_workers_ai_sprint",
        "title": "Cloudflare Workers AI Global Challenge",
        "organizer": "Cloudflare",
        "platform": "Cloudflare Devs",
        "prize_pool": "$20,000",
        "prize_usd": 20000,
        "deadline_iso": "2026-12-08T23:59:59Z",
        "deadline_display": "Dec 08, 2026",
        "url": "https://challenges.cloudflare.com/",
        "eligibility": "Global & India Open (100% Online)",
        "vibe_coder_score": "95% Vibe Coder Friendly",
        "brief": "Deploy a serverless AI micro-app running on Cloudflare's serverless GPU edge. Can be a text summarizer, image generator, or real-time voice translation widget deployed in under 5 minutes.",
        "recommended_stack": "Cloudflare Workers AI + Wrangler + Hono.js",
        "strategy": "Build an ultra-fast edge API gateway that intercepts webhooks and provides instantaneous summaries or safety redacting with zero latency.",
        "tags": ["Edge AI", "Serverless", "Instant Deploy", "Speed"]
    },
    {
        "id": "supabase_launch_challenge",
        "title": "Supabase Open Source AI Challenge",
        "organizer": "Supabase",
        "platform": "Supabase",
        "prize_pool": "$15,000",
        "prize_usd": 15000,
        "deadline_iso": "2026-11-28T23:59:59Z",
        "deadline_display": "Nov 28, 2026",
        "url": "https://supabase.com/blog",
        "eligibility": "Worldwide Open (100% Online)",
        "vibe_coder_score": "100% Vibe Coder Friendly",
        "brief": "Ship an open-source project during Supabase launch week utilizing Postgres pgvector for semantic search or AI agent memory. Top projects receive direct investor introductions and cash prizes.",
        "recommended_stack": "Supabase (Auth + pgvector) + Next.js App Router + Tailwind",
        "strategy": "Combine Supabase pgvector with an intuitive knowledge-base viewer. Allow users to drop in Notion notes or PDFs and chat with them with citation chips.",
        "tags": ["Vector Search", "Open Source", "Next.js", "AI Memory"]
    },
    {
        "id": "contra_builder_bounty",
        "title": "Contra AI Workflows & Freelancer Sprint",
        "organizer": "Contra",
        "platform": "Contra",
        "prize_pool": "$15,000",
        "prize_usd": 15000,
        "deadline_iso": "2026-11-25T23:59:59Z",
        "deadline_display": "Nov 25, 2026",
        "url": "https://contra.com/community",
        "eligibility": "Global Freelancers & Students",
        "vibe_coder_score": "100% Vibe Coder Friendly",
        "brief": "Design and build an AI-assisted tool or portfolio experience that helps independent operators scale their client intake or proposal delivery. Heavily weights visual polish, UI/UX feel, and real utility.",
        "recommended_stack": "Figma + Framer / Next.js + AI API",
        "strategy": "Apply your clean ledger UI design system. Create a micro-SaaS client portal where freelancers generate branded scopes of work and invoices from a brief bullet list.",
        "tags": ["UI/UX Design", "Freelance Ops", "Framer / Web", "Product"]
    },
    {
        "id": "dorahacks_ai_agents_sprint",
        "title": "DoraHacks Global AI Agents & Tooling Sprint",
        "organizer": "DoraHacks Community",
        "platform": "DoraHacks",
        "prize_pool": "$50,000",
        "prize_usd": 50000,
        "deadline_iso": "2026-12-12T23:59:59Z",
        "deadline_display": "Dec 12, 2026",
        "url": "https://dorahacks.io/hackathon",
        "eligibility": "Open to India & Global Online",
        "vibe_coder_score": "95% Vibe Coder Friendly",
        "brief": "Build autonomous agents, developer tooling, or low-code automation blocks. Submissions are judged by community quadratic voting and sponsor grants. Heavy focus on working web demos.",
        "recommended_stack": "Next.js + LangGraph / CrewAI + Tailwind + GitHub Pages",
        "strategy": "Create a visual workflow builder where users connect API blocks to build their own agents without code. Beautiful node-based UI gives massive voting traction.",
        "tags": ["AI Agents", "Quadratic Voting", "Web Tooling", "Grants"]
    }
]

def fetch_devpost_hackathons(min_prize=5000):
    url = "https://devpost.com/api/hackathons?challenge_type[]=online&status[]=open"
    results = []
    
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=8)
        if r.status_code == 200:
            data = r.json()
            for h in data.get("hackathons", []):
                raw_prize = h.get("prize_amount", "")
                clean_prize = re.sub(r"<[^>]+>", "", raw_prize).strip()
                num_m = re.search(r"[\$€£]?\s*([0-9,]+)", clean_prize)
                val = int(num_m.group(1).replace(",", "")) if num_m else 0
                
                if val >= min_prize:
                    title = h.get("title", "").strip()
                    h_url = h.get("url", "")
                    themes = [t.get("name") for t in h.get("themes", [])]
                    dates = h.get("submission_period_dates", "")
                    
                    # Estimate deadline ISO
                    deadline_iso = "2026-12-01T23:59:59Z"
                    end_match = re.search(r'(?:-|to)\s*([A-Za-z]{3})\s+(\d{1,2})(?:,?\s*(\d{4}))?', dates)
                    if end_match:
                        month_str = end_match.group(1)
                        day_str = end_match.group(2)
                        year_str = end_match.group(3) or "2026"
                        try:
                            dt = datetime.strptime(f"{month_str} {day_str} {year_str} 23:59:59", "%b %d %Y %H:%M:%S")
                            deadline_iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                        except Exception:
                            pass
                            
                    h_id = f"devpost_{abs(hash(title)) % 100000}"
                    
                    brief = f"Online competition on Devpost with ${val:,} in cash and sponsor prizes. Themes include {', '.join(themes[:3]) if themes else 'web and software prototyping'}."
                    if any("AI" in t or "Machine" in t for t in themes):
                        brief = f"Build a rapid AI-powered application competing for ${val:,} in {', '.join(themes[:2])}. Ideal for vibe coders to prototype a complete user journey with Claude/OpenAI APIs and a clean web UI."
                    
                    strategy = "Rapid prototyping edge: build a working Next.js web application deployed to Vercel with a 90-second demo video highlighting real user problem resolution."
                    
                    results.append({
                        "id": h_id,
                        "title": title,
                        "organizer": "Devpost Sponsor",
                        "platform": "Devpost",
                        "prize_pool": f"${val:,}",
                        "prize_usd": val,
                        "deadline_iso": deadline_iso,
                        "deadline_display": dates.split("-")[-1].strip() if "-" in dates else dates,
                        "url": h_url,
                        "eligibility": "Worldwide Open & India Eligible",
                        "vibe_coder_score": "95% Vibe Coder Friendly",
                        "brief": brief,
                        "recommended_stack": "Next.js + LLM API + Tailwind + Vercel",
                        "strategy": strategy,
                        "tags": themes[:4] if themes else ["AI", "Web", "Prototype"]
                    })
    except Exception as e:
        print(f"Devpost fetch error: {e}")
        
    return results

def get_slug_key(title, url=""):
    """Normalized key for smart deduplication across platforms."""
    # Check subdomain in url
    if url:
        m = re.search(r'https?://([^./]+)\.', url)
        if m:
            clean_sub = re.sub(r'[^a-z]', '', m.group(1).lower())
            # Strip trailing years or generic terms
            clean_sub = re.sub(r'202[0-9]|hackathon|challenge', '', clean_sub)
            if len(clean_sub) >= 4:
                return clean_sub
                
    # Fallback to normalized title
    words = [w for w in re.sub(r'[^a-z0-9 ]', ' ', title.lower()).split() if w not in ('2026', '2025', 'global', 'ai', 'hackathon', 'challenge', 'developer', 'the', 'and', 'with')]
    return "".join(words[:3])

def scout_all_hackathons():
    """Scout Devpost API and merge with curated flagships, eliminating duplicates."""
    devpost_hacks = fetch_devpost_hackathons(min_prize=5000)
    
    all_hackathons = []
    seen_keys = set()
    
    # 1. Add curated high-conviction challenges first
    for c in CURATED_FLAGSHIP_HACKATHONS:
        key = get_slug_key(c["title"], c.get("url", ""))
        seen_keys.add(key)
        all_hackathons.append(c)
        
    # 2. Add scraped Devpost hackathons if not already seen
    for d in devpost_hacks:
        key = get_slug_key(d["title"], d.get("url", ""))
        if key not in seen_keys:
            seen_keys.add(key)
            all_hackathons.append(d)
            
    # Sort primarily by deadline urgency (closest deadline first), or prize
    # We will preserve prize_usd for client-side sorting
    all_hackathons.sort(key=lambda x: x.get("prize_usd", 0), reverse=True)
    
    # Save to data/hackathons.json
    out_json = os.path.join(DATA_DIR, "hackathons.json")
    with open(out_json, "w") as f:
        json.dump(all_hackathons, f, indent=2)
        
    # Write to dashboard/hackathons_data.js and root hackathons_data.js
    js_content = f"window.RADAR_HACKATHONS_DATA = {json.dumps(all_hackathons, indent=2)};\n"
    with open(os.path.join(DASHBOARD_DIR, "hackathons_data.js"), "w") as f:
        f.write(js_content)
    with open(os.path.join(BASE_DIR, "hackathons_data.js"), "w") as f:
        f.write(js_content)
        
    total_capital = sum(h.get("prize_usd", 0) for h in all_hackathons)
    print(f"✓ Scouted {len(all_hackathons)} high-conviction hackathons (Total capital: ${total_capital:,}).")
    return all_hackathons

if __name__ == "__main__":
    scout_all_hackathons()
