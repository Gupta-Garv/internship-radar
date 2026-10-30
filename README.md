# 📡 Internship Radar • 24/7 Automated Discovery & Matcher

> **Autonomous ATS Harvester & Fit Scorer for Non-Technical Operators**  
> Direct Greenhouse, Lever, and Ashby queries with zero API keys. Eliminates 1,000+ applicant LinkedIn queues by catching fresh postings as soon as they go live.

---

## ⚡ Candidate Profile
- **Candidate:** Garv Gupta
- **Institution:** BBA in Digital & Business Entrepreneurship, **IIM Bangalore** (2024–2027)
- **Track Focus:** Product / APM, BizOps & Strategy, Growth & Product Marketing, UI/UX Design
- **Proven Moat:**
  - 🥈 **Baidu MeDo Global AI Hackathon (2nd Place & Community Choice):** $6,500 prize pool won solo among 8,424 global participants.
  - 📈 **Owner & Operations Lead at AnybodyCanBake:** Full P&L responsibility for a 10,000+ student brand with 5-7 team members.
  - ⚡ **Shipped SlotSaver MVP in < 48 Hours:** AI scheduling MVP using Claude API, Twilio, and WhatsApp Business API.
  - 🎨 **2x Global UI/UX Finalist:** Top 10 in Zo Computers build competition and Anything.com Remixathon.
- **Portfolio:** [garvgupta.app](https://garvgupta.app)

---

## 🌍 Global Hub Priority & Visa Sponsorship
- **Tier 1 Welcoming Hubs:** 🇨🇳 China & HK, 🇯🇵 Japan (Tokyo), 🇸🇬 Singapore, 🇦🇪 UAE (Dubai), 🇩🇪 Germany, 🇳🇱 Netherlands, 🇨🇭 Nordics & Switzerland, 🇦🇺 Australia & NZ, 🌐 Remote.
- **🛂 Visa Sponsorship Intelligence:** Identifies corporate visa assistance, round-trip flights, and corporate housing from scaleups like Coupang, Mercari, Databricks, Celonis, Adyen, and Stripe.
- **Strictly Deprioritized:** US, UK, and France flagged due to heavy visa hurdles and local authorization prerequisites.

---

## 🛠️ Architecture & 24/7 Cloud Sweeps

- **Harvester (`engine/harvester.py`):** Multi-threaded ATS scrapers hitting public boards directly in <15 seconds.
- **Scorer (`engine/scorer.py`):** Evaluates non-technical roles, immigrant-friendly hubs, and attaches 1-click recruiter outreach pitch notes.
- **Dashboard (`dashboard/index.html`):** Clean Modern Ledger UI with Dynamic Island top dock, Kanban pipeline tracker, and slide-over pitch drawer.
- **GitHub Actions (`.github/workflows/radar_sweep.yml`):** Runs every 5 hours in the cloud 24/7/365, keeping the portal fresh even when your laptop is powered off.

---

## 🚀 Running Locally

```bash
# 1. Install requirements
pip install -r requirements.txt

# 2. Trigger an immediate sweep
python radar_runner.py scan

# 3. Launch the visual dashboard
python radar_runner.py serve
```

