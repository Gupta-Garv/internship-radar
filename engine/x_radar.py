import os
import re
import sys
import json
import time
import math
import asyncio
import hashlib
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "config", "x_radar_config.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

X_DATA_FILE = os.path.join(DATA_DIR, "x_radar.json")
SEEN_X_FILE = os.path.join(DATA_DIR, "seen_x_posts.json")
HACKATHONS_JSON = os.path.join(DATA_DIR, "hackathons.json")

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_NVIDIA_KEY = "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"
DEFAULT_NIM_MODEL = "mistralai/mistral-large-4-1t-a52b"

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

FORTUNE_500_MARQUEE = {
    "google", "microsoft", "amazon", "apple", "meta", "nvidia", "openai", "anthropic",
    "stripe", "uber", "airbnb", "netflix", "tesla", "databricks", "figma", "vercel",
    "linear", "notion", "ramp", "plaid", "cloudflare", "goldman sachs", "mckinsey",
    "bcg", "bain", "jpmorgan", "morgan stanley", "razorpay", "swiggy", "zomato", "cred",
    "zepto", "blinkit", "flipkart", "y combinator", "yc"
}

FOREIGN_LANG_HARD_BLOCK = re.compile(
    r'\b(fluent in|native|must speak|proficiency in|bilingual in)\s+(arabic|german|french|spanish|italian|dutch|japanese|mandarin|chinese|korean|portuguese|russian|swedish|turkish|polish|vietnamese|thai)\b',
    re.IGNORECASE
)

DEAL_KEYWORDS_AI = re.compile(
    r'\b(free|promo|discount|credit|credits|offer|student|off|deal|giveaway|trial|tier|beta|waitlist|open.?source|just launched|announced|dropped|code|claim|grant|pro plan|subscription|api key|limitless|unlimited)\b',
    re.IGNORECASE
)

FORTNITE_SIGNAL_KEYWORDS = re.compile(
    r'\b(free|skin|cosmetic|item shop|shop|quest|reward|cup|tournament|drop|twitch|vbuck|v-buck|bundle|code|leak|update|event|collab|unlock|claim)\b',
    re.IGNORECASE
)


def load_local_env():
    """Load key=value pairs from .env if present (without overriding existing env vars)."""
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def make_item_id(source, url, text):
    key = f"{source}|{url}|{text[:80]}".encode("utf-8", errors="ignore")
    return "xr_" + hashlib.md5(key).hexdigest()[:12]


def extract_urls(text):
    if not text:
        return []
    found = re.findall(r'https?://[^\s\)\]\>\"\'`]+', text)
    cleaned = []
    for u in found:
        u = u.rstrip(".,;:!?")
        if u not in cleaned:
            cleaned.append(u)
    return cleaned


def unshorten_url(url):
    """Resolve t.co or bit.ly redirects quickly so Garv gets the real destination link."""
    if not url:
        return ""
    if not any(d in url.lower() for d in ("t.co/", "bit.ly/", "tinyurl.com/", "buff.ly/")):
        return url
    try:
        r = requests.head(url, allow_redirects=True, timeout=2.5, headers={"User-Agent": USER_AGENT})
        if r.url and "t.co/" not in r.url:
            return r.url
    except Exception:
        pass
    return url


def parse_burner_accounts():
    """Load burner X cookie accounts from X_BURNER_ACCOUNTS (JSON) or X_AUTH_TOKEN + X_CT0."""
    accounts = []
    raw_json = os.environ.get("X_BURNER_ACCOUNTS", "").strip()
    if raw_json:
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, list):
                for idx, item in enumerate(parsed):
                    if isinstance(item, dict) and item.get("auth_token") and item.get("ct0"):
                        accounts.append({
                            "username": item.get("username", f"burner_{idx+1}"),
                            "auth_token": item["auth_token"].strip(),
                            "ct0": item["ct0"].strip(),
                        })
        except Exception:
            pass

    single_token = os.environ.get("X_AUTH_TOKEN", "").strip()
    single_ct0 = os.environ.get("X_CT0", "").strip()
    if single_token and single_ct0:
        if not any(a["auth_token"] == single_token for a in accounts):
            accounts.append({
                "username": os.environ.get("X_BURNER_USERNAME", "burner_primary").strip(),
                "auth_token": single_token,
                "ct0": single_ct0,
            })
    return accounts


# =============================================================================
# TIER 1: LIVE X GRAPHQL SCRAPER (twscrape pool + direct cookie fallback)
# =============================================================================
async def _fetch_via_twscrape(queries_by_cat, accounts, max_per_query=12):
    from twscrape import API
    db_path = os.path.join(DATA_DIR, ".twscrape_pool.db")
    api = API(db_path)

    for acc in accounts:
        cookies_str = f"auth_token={acc['auth_token']}; ct0={acc['ct0']}"
        try:
            await api.pool.add_account(
                acc["username"],
                "placeholder_pass",
                f"{acc['username']}@placeholder.local",
                "placeholder_email_pass",
                cookies=cookies_str,
            )
        except Exception:
            pass

    results = []
    for cat, queries in queries_by_cat.items():
        for q in queries:
            try:
                count = 0
                async for tw in api.search(q, limit=max_per_query, kv={"product": "Latest"}):
                    text = getattr(tw, "rawContent", "") or ""
                    tw_id = str(getattr(tw, "id", ""))
                    user = getattr(tw, "user", None)
                    handle = getattr(user, "username", "unknown") if user else "unknown"
                    followers = getattr(user, "followersCount", 0) if user else 0
                    likes = getattr(tw, "likeCount", 0) or 0
                    retweets = getattr(tw, "retweetCount", 0) or 0
                    replies = getattr(tw, "replyCount", 0) or 0
                    dt = getattr(tw, "date", None)
                    ts = int(dt.timestamp()) if dt else int(time.time())
                    post_url = getattr(tw, "url", "") or f"https://x.com/{handle}/status/{tw_id}"

                    ext_urls = []
                    for link_obj in (getattr(tw, "links", None) or []):
                        u = getattr(link_obj, "url", "") or ""
                        if u and "x.com" not in u and "twitter.com" not in u:
                            ext_urls.append(u)
                    if not ext_urls:
                        for u in extract_urls(text):
                            if "x.com/" not in u and "twitter.com/" not in u:
                                ext_urls.append(u)

                    results.append({
                        "raw_id": tw_id,
                        "source_engine": "x_live",
                        "source_label": "𝕏 LIVE",
                        "category_hint": cat,
                        "author": f"@{handle}",
                        "author_followers": followers,
                        "text": text,
                        "title": text.split("\n")[0][:120],
                        "post_url": post_url,
                        "external_url": ext_urls[0] if ext_urls else "",
                        "likes": likes,
                        "retweets": retweets,
                        "replies": replies,
                        "timestamp": ts,
                    })
                    count += 1
                    if count >= max_per_query:
                        break
                await asyncio.sleep(2.5)
            except Exception as e:
                print(f"  [twscrape] query warning ({cat}): {str(e)[:120]}")
    return results


def fetch_x_live(queries_by_cat, accounts):
    """Run Tier 1 live X search using burner cookie pool."""
    if not accounts:
        return [], "not_configured"
    try:
        import twscrape  # noqa: F401
        items = asyncio.run(_fetch_via_twscrape(queries_by_cat, accounts))
        status = "active" if items else "cookie_expired_or_empty"
        return items, status
    except ImportError:
        return [], "twscrape_not_installed"
    except Exception as e:
        print(f"  [x_live] failed ({str(e)[:120]}), failing over to Exa + live feeds.")
        return [], f"error:{str(e)[:60]}"


# =============================================================================
# TIER 2: EXA.AI FREE TIER ($10/mo recurring, native category="tweet")
# =============================================================================
def fetch_exa_tweets(exa_queries_by_cat, hours_back=48):
    api_key = os.environ.get("EXA_API_KEY", "").strip()
    if not api_key:
        return [], "not_configured"

    start_iso = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }
    results = []
    errors = 0

    for cat, query in exa_queries_by_cat.items():
        try:
            payload = {
                "query": query,
                "type": "auto",
                "category": "tweet",
                "numResults": 8,
                "startPublishedDate": start_iso,
                "contents": {"text": {"maxCharacters": 900}},
            }
            r = requests.post("https://api.exa.ai/search", headers=headers, json=payload, timeout=12)
            if r.status_code == 200:
                data = r.json()
                for item in data.get("results", []):
                    url = item.get("url", "")
                    text = (item.get("text") or item.get("title") or "").strip()
                    if not text or not url:
                        continue
                    author = item.get("author") or ""
                    if not author and ("x.com/" in url or "twitter.com/" in url):
                        m = re.search(r'(?:x|twitter)\.com/([^/]+)/status', url)
                        if m:
                            author = f"@{m.group(1)}"
                    if author and not author.startswith("@") and ("x.com/" in url or "twitter.com/" in url):
                        author = f"@{author.lstrip('@')}"

                    pub = item.get("publishedDate", "")
                    ts = int(time.time())
                    if pub:
                        try:
                            ts = int(datetime.fromisoformat(pub.replace("Z", "+00:00")).timestamp())
                        except Exception:
                            pass

                    ext_urls = [u for u in extract_urls(text) if "x.com/" not in u and "twitter.com/" not in u]
                    results.append({
                        "raw_id": item.get("id", url),
                        "source_engine": "exa_x",
                        "source_label": "𝕏 EXA",
                        "category_hint": cat,
                        "author": author or "@x_post",
                        "author_followers": 0,
                        "text": text,
                        "title": (item.get("title") or text.split("\n")[0])[:120],
                        "post_url": url,
                        "external_url": ext_urls[0] if ext_urls else "",
                        "likes": 0,
                        "retweets": 0,
                        "replies": 0,
                        "timestamp": ts,
                    })
            else:
                errors += 1
                print(f"  [exa] HTTP {r.status_code} on {cat}: {r.text[:100]}")
            time.sleep(0.35)
        except Exception as e:
            errors += 1
            print(f"  [exa] error on {cat}: {str(e)[:100]}")

    status = "active" if results else ("error" if errors else "empty")
    return results, status


# =============================================================================
# TIER 3: ZERO-AUTH ALWAYS-ON LIVE FEEDS (GamerPower, Epic, Fortnite-API, HN)
# =============================================================================
def fetch_gamerpower_freebies(active_categories):
    """Fetch 100% free live PC games, Epic/Steam/GOG claims & beta drops (zero auth, HTTP 200)."""
    if "gaming_general" not in active_categories:
        return []
    results = []
    try:
        r = requests.get(
            "https://www.gamerpower.com/api/giveaways?platform=pc&sort-by=date",
            headers={"User-Agent": USER_AGENT},
            timeout=8,
        )
        if r.status_code != 200:
            return []
        for g in r.json()[:14]:
            title = (g.get("title") or "").strip()
            worth = (g.get("worth") or "Free").strip()
            platforms = (g.get("platforms") or "PC").strip()
            desc = (g.get("description") or "").strip()
            instructions = (g.get("instructions") or "").strip()
            open_url = (g.get("open_giveaway_url") or g.get("gamerpower_url") or "").strip()
            pub_str = g.get("published_date", "")
            ts = int(time.time())
            if pub_str:
                try:
                    ts = int(datetime.strptime(pub_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
                except Exception:
                    pass
            results.append({
                "raw_id": f"gp_{g.get('id', title[:20])}",
                "source_engine": "gamerpower_live",
                "source_label": "FREE GAME LIVE",
                "category_hint": "gaming_general",
                "author": f"GamerPower • {platforms[:28]}",
                "author_followers": 0,
                "text": f"{title} (Worth {worth}, Free on {platforms}). {desc[:300]} Steps: {instructions[:220]}",
                "title": f"{title} ({worth} -> FREE)",
                "post_url": open_url,
                "external_url": open_url,
                "likes": int(g.get("users") or 0),
                "retweets": 0,
                "replies": 0,
                "timestamp": ts,
            })
    except Exception as e:
        print(f"  [gamerpower] warning: {str(e)[:80]}")
    return results


def fetch_epic_free_games(active_categories):
    """Fetch official Epic Games Store free weekly titles localized for India (zero auth)."""
    if "gaming_general" not in active_categories:
        return []
    results = []
    try:
        r = requests.get(
            "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=IN&allowCountries=IN",
            headers={"User-Agent": USER_AGENT},
            timeout=8,
        )
        if r.status_code != 200:
            return []
        elements = r.json().get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
        for el in elements:
            promos = el.get("promotions") or {}
            active_offers = promos.get("promotionalOffers") or []
            upcoming_offers = promos.get("upcomingPromotionalOffers") or []
            if not active_offers and not upcoming_offers:
                continue
            title = (el.get("title") or "").strip()
            desc = (el.get("description") or "").strip()
            slug = el.get("productSlug") or (el.get("catalogNs", {}).get("mappings") or [{}])[0].get("pageSlug", "")
            url = f"https://store.epicgames.com/en-US/p/{slug}" if slug else "https://store.epicgames.com/en-US/free-games"
            is_live = bool(active_offers)
            end_str = ""
            if active_offers and active_offers[0].get("promotionalOffers"):
                end_str = active_offers[0]["promotionalOffers"][0].get("endDate", "")[:10]
            elif upcoming_offers and upcoming_offers[0].get("promotionalOffers"):
                end_str = "Starts " + upcoming_offers[0]["promotionalOffers"][0].get("startDate", "")[:10]

            results.append({
                "raw_id": f"epic_{el.get('id', title[:20])}",
                "source_engine": "epic_live",
                "source_label": "EPIC FREE LIVE" if is_live else "EPIC UPCOMING",
                "category_hint": "gaming_general",
                "author": "Epic Games Store (India)",
                "author_followers": 0,
                "text": f"Epic Games 100% Free Claim: {title}. {desc[:300]} Window: {end_str}",
                "title": f"Epic Free: {title}" + (" (Live Now)" if is_live else f" ({end_str})"),
                "post_url": url,
                "external_url": url,
                "likes": 500 if is_live else 200,
                "retweets": 0,
                "replies": 0,
                "timestamp": int(time.time()),
            })
    except Exception as e:
        print(f"  [epic] warning: {str(e)[:80]}")
    return results


def fetch_fortnite_live(active_categories):
    """Fetch live Fortnite Battle Royale news, free quests, events & item shop drops (zero auth)."""
    if "gaming_fortnite" not in active_categories:
        return []
    results = []
    try:
        r = requests.get("https://fortnite-api.com/v2/news/br", headers={"User-Agent": USER_AGENT}, timeout=8)
        if r.status_code == 200:
            data = r.json().get("data") or {}
            motds = data.get("motds") or []
            for m in motds[:8]:
                title = (m.get("title") or "").strip()
                body = (m.get("body") or "").strip()
                if not title:
                    continue
                results.append({
                    "raw_id": f"fn_{m.get('id', title[:20])}",
                    "source_engine": "fortnite_live",
                    "source_label": "FORTNITE LIVE",
                    "category_hint": "gaming_fortnite",
                    "author": "Fortnite Official Feed",
                    "author_followers": 0,
                    "text": f"Fortnite Live Drop / Event: {title}. {body}",
                    "title": f"Fortnite: {title}",
                    "post_url": "https://www.fortnite.com/news",
                    "external_url": "https://www.fortnite.com/item-shop",
                    "likes": 250,
                    "retweets": 0,
                    "replies": 0,
                    "timestamp": int(time.time()),
                })
    except Exception as e:
        print(f"  [fortnite] warning: {str(e)[:80]}")
    return results


def fetch_hn_live(active_categories):
    """Fetch fresh AI deals/launches, hackathons, grants & bounties from Hacker News Algolia (100% free)."""
    results = []
    now_ts = int(time.time())
    cutoff = now_ts - 7 * 86400
    hn_queries = []
    if "ai_alpha" in active_categories:
        hn_queries.append(("ai_alpha", "free AI credits OR free tier LLM OR open source AI"))
        hn_queries.append(("ai_alpha", "Show HN AI free"))
    if "x_hackathons" in active_categories:
        hn_queries.append(("x_hackathons", "hackathon"))
    if "vibe_bounties" in active_categories:
        hn_queries.append(("vibe_bounties", "bounty OR design challenge AI"))
    if "grants_credits" in active_categories:
        hn_queries.append(("grants_credits", "microgrant OR fellowship OR startup grant"))
    if "money_earning" in active_categories:
        hn_queries.append(("money_earning", "RLHF OR AI trainer OR Mercor OR Outlier"))
    if "money_internships" in active_categories:
        hn_queries.append(("money_internships", "hiring intern product OR growth OR founder"))

    for cat, q in hn_queries:
        try:
            url = (
                "https://hn.algolia.com/api/v1/search_by_date?"
                f"query={urllib.parse.quote(q)}&tags=story&numericFilters=created_at_i>{cutoff}&hitsPerPage=8"
            )
            r = requests.get(url, timeout=6)
            if r.status_code != 200:
                continue
            for h in r.json().get("hits", []):
                title = (h.get("title") or "").strip()
                if not title or len(title) < 12:
                    continue
                obj_id = h.get("objectID", "")
                hn_url = f"https://news.ycombinator.com/item?id={obj_id}"
                ext_url = h.get("url") or ""
                is_x_link = bool(ext_url and ("x.com/" in ext_url or "twitter.com/" in ext_url))
                results.append({
                    "raw_id": f"hn_{obj_id}",
                    "source_engine": "hn_live",
                    "source_label": "𝕏 VIA HN" if is_x_link else "HN LIVE",
                    "category_hint": cat,
                    "author": f"hn/{h.get('author', 'builder')}",
                    "author_followers": 0,
                    "text": f"{title} {h.get('story_text') or ''}"[:600].strip(),
                    "title": title[:140],
                    "post_url": ext_url if is_x_link else hn_url,
                    "external_url": ext_url,
                    "likes": int(h.get("points") or 0),
                    "retweets": 0,
                    "replies": int(h.get("num_comments") or 0),
                    "timestamp": int(h.get("created_at_i") or now_ts),
                })
        except Exception:
            pass
    return results


# =============================================================================
# LAYER 1: ZERO-COST PYTHON SPAM & GUARDRAIL FILTER
# =============================================================================
def prefilter_candidates(raw_items, spam_patterns, seen_ids):
    spam_regex = re.compile("|".join(spam_patterns), re.IGNORECASE) if spam_patterns else None
    deduped = []
    local_seen_urls = set()

    for item in raw_items:
        text = item.get("text", "")
        lower = text.lower()
        post_url = item.get("post_url", "")
        if not text or not post_url:
            continue
        if post_url in local_seen_urls:
            continue
        local_seen_urls.add(post_url)

        # Strip engagement-bait & crypto/scam spam
        if spam_regex and spam_regex.search(lower):
            continue

        # Enforce English & Hindi only (reject hard 3rd language requirements)
        if FOREIGN_LANG_HARD_BLOCK.search(lower):
            continue

        # Enforce internship guardrail: reject unpaid roles unless Fortune 500 / marquee
        if item.get("category_hint") == "money_internships":
            if re.search(r'\b(unpaid|no pay|volunteer|equity only|zero stipend)\b', lower):
                if not any(brand in lower for brand in FORTUNE_500_MARQUEE):
                    continue

        item_id = make_item_id(item["source_engine"], post_url, text)
        item["id"] = item_id
        item["is_new"] = item_id not in seen_ids

        # Unshorten external URL if needed (lightweight)
        if item.get("external_url"):
            item["external_url"] = unshorten_url(item["external_url"])

        deduped.append(item)

    return deduped


# =============================================================================
# LAYER 2: BATCHED NVIDIA NIM CLASSIFIER & EXTRACTOR (2-4 calls per sweep!)
# =============================================================================
BATCH_SYSTEM_PROMPT = """You are Garv Gupta's personal X & real-time opportunity intelligence analyst.
Garv's profile:
- Undergraduate at IIM Bangalore (BBA Digital & Business Entrepreneurship).
- High-agency AI builder, product/growth/BizOps operator, UI/UX designer, hackathon winner (2nd of 8,424 in Baidu Global AI Hackathon), and PC gamer (plays Fortnite).
- Location & Eligibility: Based in India; speaks English & Hindi only. Eligible for India-based, Global/Worldwide, Remote, or Visa-sponsored roles/opportunities.

Your job: Given a JSON list of raw posts, ruthlessly filter out noise/fluff/clickbait/scams/US-only-ineligible posts and keep ONLY genuinely useful, actionable, high-signal drops.

Valid categories (pick exactly one per kept item):
- "ai_alpha": Limited-time AI promos, free Pro tiers, massive price drops, student offers, free API credit drops, notable newly launched free AI tools/models, beta invites.
- "gaming_general": Limited-time 100% free games to claim/keep (Epic, Steam, GOG, Prime), free beta keys, major gaming giveaways/deals.
- "gaming_fortnite": Fortnite item shop updates/leaks, free skins/cosmetics/quests, Fortnite tournaments/cups, notable patch drops.
- "x_hackathons": Active hackathons or buildathons with real prizes (cash, MacBooks/gadgets, Claude/Cursor/API subscriptions, YC fast-tracks) open to India/Global builders.
- "money_earning": Legit, high-paying earning opportunities suited to a smart university builder (new AI training/RLHF platforms like Mercor/Outlier/Alignerr, high-paying user research studies, product bounties) available in India or globally. Reject generic spam or low-pay survey junk.
- "money_internships": Founders or startups hiring for Product, BizOps, Founder's Office, Growth, Marketing, Analytics, or UI/UX interns. MUST be paid (unless Fortune 500 / elite marquee brand like Google/OpenAI/YC) and open to India or Remote/Visa-sponsored. Reject pure SWE/C++/hardware and cold-calling sales.
- "vibe_bounties": Short-term (24h-7d) UI/UX design challenges, remixathons, or vibe-coding bounties (Figma, Framer, v0, Cursor, Lovable, Bolt, Replit) with cash or top-tier prizes.
- "grants_credits": Student micro-grants ($500-$10k non-dilutive like Emergent Ventures, 1517, Merge Club, Bagel Fund), fellowships, or free cloud/AI compute credit drops ($1k-$25k).

Return ONLY a valid JSON object with key "items" containing an array of objects for EVERY input index:
{
  "items": [
    {
      "idx": 0,
      "keep": true,
      "category": "ai_alpha",
      "headline": "Short punchy title (max 75 chars, no clickbait)",
      "summary": "Crisp 1-2 sentence explanation of what this is and why it matters right now. No em dashes.",
      "action_steps": ["Step 1", "Step 2"],
      "value_badge": "Short pill e.g. FREE Claim | $10k Pool | $50/hr Remote | Free Skin",
      "eligibility": "India & Global",
      "signal_score": 88,
      "is_urgent": true,
      "prize_usd_est": 0,
      "deadline_display": "Limited Time"
    }
  ]
}
If an item is low-quality, irrelevant, expired, spam, clickbait, or ineligible for India/Global, set "keep": false."""


def heuristic_evaluate(item):
    """Zero-API fallback classifier so sweeps never fail even if LLM times out."""
    cat = item.get("category_hint", "ai_alpha")
    title = item.get("title", "").strip()
    text = item.get("text", "").strip()
    lower = f"{title} {text}".lower()

    # Basic quality filter
    if len(title) < 12:
        return None
    if cat == "gaming_general" and not re.search(r'\b(free|100%|steam|epic|gog|itch|prime|beta|claim|giveaway)\b', lower):
        return None
    if cat == "ai_alpha" and not DEAL_KEYWORDS_AI.search(lower):
        return None
    if cat == "x_hackathons" and not re.search(r'\b(hackathon|buildathon|prize|register|submit|challenge)\b', lower):
        return None
    if cat == "money_internships" and not re.search(r'\b(intern|hiring|founder|product|growth|design|ops|stipend)\b', lower):
        return None

    # Estimate value badge
    money_m = re.search(r'(\$\s?[\d,]+(?:\.\d+)?\s?[kKmM]?|₹\s?[\d,]+(?:\.\d+)?\s?[kK]?)', text)
    if "100%" in lower or "free" in lower:
        badge = f"FREE • {money_m.group(1)}" if money_m else "FREE Claim"
    elif money_m:
        badge = money_m.group(1)
    else:
        badge = {
            "ai_alpha": "AI Alpha",
            "gaming_general": "Free Game",
            "gaming_fortnite": "Fortnite Drop",
            "x_hackathons": "Hackathon",
            "money_earning": "Paid Opportunity",
            "money_internships": "Paid Intern",
            "vibe_bounties": "Bounty",
            "grants_credits": "Grant / Credits",
        }.get(cat, "Live Signal")

    prize_usd = 0
    usd_m = re.search(r'\$\s?([\d,]+)\s*([kKmM])?', text)
    if usd_m:
        try:
            val = float(usd_m.group(1).replace(",", ""))
            mult = (usd_m.group(2) or "").lower()
            if mult == "k":
                val *= 1000
            elif mult == "m":
                val *= 1000000
            prize_usd = int(val)
        except Exception:
            pass

    age_hrs = max(0, (time.time() - item.get("timestamp", time.time())) / 3600.0)
    is_urgent = age_hrs <= 6 or any(w in lower for w in ("limited time", "24h", "48h", "expires", "free to keep", "claim now"))
    base_score = 78
    if item.get("source_engine") in ("x_live", "exa_x"):
        base_score += 8
    if item.get("likes", 0) >= 50:
        base_score += 6
    if is_urgent:
        base_score += 5

    snippet = re.sub(r'https?://\S+', '', text).strip()
    snippet = re.sub(r'\s+', ' ', snippet)[:210]

    return {
        **item,
        "category": cat,
        "headline": title[:85],
        "summary": snippet if len(snippet) > 30 else title,
        "action_steps": [
            "Open the direct post link to verify live status and latest replies",
            "Follow the claim or registration link before the window closes"
        ],
        "value_badge": badge,
        "eligibility": "India & Global",
        "signal_score": min(97, base_score),
        "is_urgent": is_urgent,
        "prize_usd_est": prize_usd,
        "deadline_display": "Time Sensitive" if is_urgent else "Active Now",
    }


def classify_batch_with_nim(batch_items):
    """Send 12-15 items in a single NVIDIA NIM call to stay far below the 40 RPM cap."""
    api_key = os.environ.get("NVIDIA_API_KEY", "").strip() or DEFAULT_NVIDIA_KEY
    model = os.environ.get("NVIDIA_X_MODEL", DEFAULT_NIM_MODEL).strip()

    compact_input = []
    for idx, it in enumerate(batch_items):
        compact_input.append({
            "idx": idx,
            "hint": it.get("category_hint"),
            "source": it.get("source_label"),
            "author": it.get("author"),
            "likes": it.get("likes", 0),
            "text": it.get("text", "")[:550],
            "url": it.get("external_url") or it.get("post_url"),
        })

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": BATCH_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(compact_input, ensure_ascii=False)},
        ],
        "temperature": 0.15,
        "max_tokens": 2200,
    }

    try:
        r = requests.post(
            NVIDIA_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=35,
        )
        if r.status_code != 200:
            print(f"  [nim] HTTP {r.status_code}, using heuristic fallback for batch.")
            return [x for x in (heuristic_evaluate(it) for it in batch_items) if x]

        content = r.json()["choices"][0]["message"]["content"].strip()
        # Strip markdown fences if present
        content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content, flags=re.MULTILINE).strip()
        m = re.search(r'\{[\s\S]*\}', content)
        if not m:
            return [x for x in (heuristic_evaluate(it) for it in batch_items) if x]

        parsed = json.loads(m.group(0))
        kept = []
        valid_cats = {
            "ai_alpha", "gaming_general", "gaming_fortnite", "x_hackathons",
            "money_earning", "money_internships", "vibe_bounties", "grants_credits"
        }

        for row in parsed.get("items", []):
            if not row.get("keep"):
                continue
            idx = row.get("idx")
            if not isinstance(idx, int) or idx < 0 or idx >= len(batch_items):
                continue
            base = batch_items[idx]
            cat = row.get("category") if row.get("category") in valid_cats else base.get("category_hint", "ai_alpha")
            score = int(row.get("signal_score") or 75)
            if score < 65:
                continue

            summary = str(row.get("summary") or base.get("title", "")).replace("—", ", ").replace("–", "-")
            headline = str(row.get("headline") or base.get("title", ""))[:95].replace("—", "-")
            steps = row.get("action_steps") or ["Open the source link and claim before expiry"]
            if isinstance(steps, str):
                steps = [steps]

            kept.append({
                **base,
                "category": cat,
                "headline": headline,
                "summary": summary,
                "action_steps": [str(s)[:140] for s in steps[:3]],
                "value_badge": str(row.get("value_badge") or "Live Drop")[:32],
                "eligibility": str(row.get("eligibility") or "India & Global")[:30],
                "signal_score": min(99, max(65, score)),
                "is_urgent": bool(row.get("is_urgent", False)),
                "prize_usd_est": int(row.get("prize_usd_est") or 0),
                "deadline_display": str(row.get("deadline_display") or "Active Now")[:28],
            })
        return kept
    except Exception as e:
        print(f"  [nim] batch error ({str(e)[:90]}), using heuristic fallback.")
        return [x for x in (heuristic_evaluate(it) for it in batch_items) if x]


# =============================================================================
# DUAL-SYNC X HACKATHONS INTO MAIN HACKATHONS TAB
# =============================================================================
def sync_x_hackathons_to_main(x_items):
    """Inject X-discovered hackathons & bounties into hackathons.json & hackathons_data.js with distinct X styling."""
    existing = load_json(HACKATHONS_JSON, [])
    # Remove stale previously synced X items so fresh X items stay clean
    non_x = [h for h in existing if not h.get("is_from_x")]
    existing_urls = {h.get("url", "").lower().rstrip("/") for h in non_x}

    synced_x_hacks = []
    now_dt = datetime.now(timezone.utc)
    default_deadline = (now_dt + timedelta(days=10)).strftime("%Y-%m-%dT23:59:59Z")

    for item in x_items:
        if item.get("category") not in ("x_hackathons", "vibe_bounties"):
            continue
        target_url = (item.get("external_url") or item.get("post_url") or "").strip()
        if not target_url or target_url.lower().rstrip("/") in existing_urls:
            continue
        existing_urls.add(target_url.lower().rstrip("/"))

        prize_usd = int(item.get("prize_usd_est") or 0)
        badge = item.get("value_badge") or "X Live Prize"
        prize_type = "cash"
        lower_b = f"{badge} {item.get('summary', '')}".lower()
        if any(w in lower_b for w in ("macbook", "iphone", "quest", "gpu", "hardware", "ipad")):
            prize_type = "gadgets"
        elif any(w in lower_b for w in ("claude", "cursor", "credits", "pro", "api", "subscription")):
            prize_type = "ai_subs"
        elif any(w in lower_b for w in ("yc", "internship", "fast-track", "interview", "fellowship")):
            prize_type = "fast_track"

        synced_x_hacks.append({
            "id": f"xhack_{item['id']}",
            "title": item["headline"],
            "platform": "X (Twitter) Live",
            "organizer": item.get("author", "@x_scout"),
            "url": target_url,
            "x_post_url": item.get("post_url", target_url),
            "is_from_x": True,
            "source_label": item.get("source_label", "𝕏 LIVE"),
            "prize_usd": prize_usd,
            "prize_pool": f"${prize_usd:,}" if prize_usd >= 500 else badge,
            "prize_badge": badge,
            "prize_type": prize_type,
            "non_cash_perks": item.get("action_steps", [])[:3],
            "deadline_iso": default_deadline,
            "deadline_display": item.get("deadline_display", "Check X Post"),
            "brief": item.get("summary", ""),
            "recommended_stack": "Cursor + Claude / Gemini + Next.js",
            "vibe_coder_score": "𝕏 Early Discovery",
            "eligibility": item.get("eligibility", "India & Global"),
            "tags": ["X Exclusive", "Early Signal"] + (["Vibe Bounty"] if item.get("category") == "vibe_bounties" else ["Hackathon"]),
            "strategy": {
                "winning_angle": f"Spotted early via {item.get('source_label', 'X')}. Move fast while submission volume is still low.",
                "idea": item.get("summary", ""),
                "scaffold_prompt": f"Build a clean, demo-ready MVP for: {item['headline']}. Context: {item.get('summary', '')}"
            }
        })

    merged = synced_x_hacks + non_x
    save_json(HACKATHONS_JSON, merged)
    js_content = f"window.RADAR_HACKATHONS_DATA = {json.dumps(merged, indent=2)};\n"
    with open(os.path.join(DASHBOARD_DIR, "hackathons_data.js"), "w") as f:
        f.write(js_content)
    with open(os.path.join(BASE_DIR, "hackathons_data.js"), "w") as f:
        f.write(js_content)

    return len(synced_x_hacks)


# =============================================================================
# FREE TELEGRAM PUSH ALERTS (For Time-Critical Urgent Drops)
# =============================================================================
def send_telegram_alerts(new_urgent_items):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id or not new_urgent_items:
        return 0

    sent = 0
    for item in new_urgent_items[:5]:
        cat_label = item.get("category", "").replace("_", " ").upper()
        msg = (
            f"⚡ [{cat_label}] {item['headline']}\n"
            f"🏷 {item.get('value_badge', 'Live')} | Score: {item.get('signal_score', 85)} | {item.get('source_label', 'X')}\n\n"
            f"{item.get('summary', '')}\n\n"
            f"🔗 Post: {item.get('post_url', '')}"
        )
        if item.get("external_url") and item["external_url"] != item.get("post_url"):
            msg += f"\n🚀 Direct Link: {item['external_url']}"
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "disable_web_page_preview": True},
                timeout=8,
            )
            if r.status_code == 200:
                sent += 1
        except Exception:
            pass
    return sent


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================
def run_x_radar(lane="full"):
    load_local_env()
    config = load_json(CONFIG_FILE, {})
    seen_map = load_json(SEEN_X_FILE, {})
    prev_items = load_json(X_DATA_FILE, [])

    fast_cats = config.get("lanes", {}).get("fast", [])
    std_cats = config.get("lanes", {}).get("standard", [])
    active_cats = fast_cats if lane == "fast" else (fast_cats + std_cats)

    print("=" * 60)
    print(f"𝕏 GARV'S FULL-HYBRID X INTELLIGENCE RADAR (Lane: {lane.upper()})")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    burner_accounts = parse_burner_accounts()
    x_queries = {k: v for k, v in config.get("x_queries", {}).items() if k in active_cats}
    exa_queries = {k: v for k, v in config.get("exa_queries", {}).items() if k in active_cats}

    raw_items = []

    # 1. Tier 1: Live X GraphQL (Burner Cookie Pool)
    x_live_items, x_live_status = fetch_x_live(x_queries, burner_accounts)
    print(f"• Tier 1 (𝕏 Live Burners): {len(x_live_items)} raw tweets [status: {x_live_status}]")
    raw_items.extend(x_live_items)

    # 2. Tier 2: Exa.ai Free Tier ($10/mo, category="tweet")
    # Run always if configured (booster + automatic failover if burner cookie expires!)
    exa_items, exa_status = fetch_exa_tweets(exa_queries, hours_back=48)
    print(f"• Tier 2 (Exa 𝕏 Free API): {len(exa_items)} raw tweets [status: {exa_status}]")
    raw_items.extend(exa_items)

    # 3. Tier 3: Zero-Auth Always-On Live Feeds (GamerPower, Epic India, Fortnite-API, HN Algolia)
    gp_items = fetch_gamerpower_freebies(active_cats)
    epic_items = fetch_epic_free_games(active_cats)
    fn_items = fetch_fortnite_live(active_cats)
    hn_items = fetch_hn_live(active_cats)
    print(f"• Tier 3 (Zero-Auth Live APIs): {len(gp_items)} Free Games + {len(epic_items)} Epic + {len(fn_items)} Fortnite + {len(hn_items)} HN")
    raw_items.extend(gp_items)
    raw_items.extend(epic_items)
    raw_items.extend(fn_items)
    raw_items.extend(hn_items)

    # Layer 1: Zero-cost Python spam killer & guardrails
    candidates = prefilter_candidates(raw_items, config.get("spam_patterns", []), seen_map)
    # Prioritize brand-new items for LLM classification, skip re-classifying already saved items
    existing_by_id = {it["id"]: it for it in prev_items if isinstance(it, dict) and it.get("id")}
    to_classify = []
    reused_items = []

    for c in candidates:
        if c["id"] in existing_by_id:
            reused = dict(existing_by_id[c["id"]])
            reused["is_new"] = False
            reused_items.append(reused)
        else:
            to_classify.append(c)

    print(f"• After Layer-1 Spam Filter: {len(candidates)} total ({len(to_classify)} net-new to classify)")

    # Layer 2: Batched NVIDIA NIM Scoring (14 items per call = tiny RPM usage)
    classified_new = []
    batch_size = 14
    api_calls = 0
    for i in range(0, len(to_classify), batch_size):
        batch = to_classify[i:i + batch_size]
        api_calls += 1
        kept = classify_batch_with_nim(batch)
        classified_new.extend(kept)
        if i + batch_size < len(to_classify):
            time.sleep(1.5)

    print(f"• Layer-2 Batched NIM Calls: {api_calls} calls -> kept {len(classified_new)} high-signal drops")

    # Merge newly classified + existing fresh items (keep rolling 7-day window, max 160 items)
    now_ts = int(time.time())
    merged_map = {}
    for it in prev_items:
        if isinstance(it, dict) and it.get("id"):
            if now_ts - int(it.get("timestamp", now_ts)) <= 7 * 86400:
                it["is_new"] = False
                merged_map[it["id"]] = it
    for it in reused_items:
        merged_map[it["id"]] = it
    for it in classified_new:
        it["is_new"] = True
        merged_map[it["id"]] = it
        seen_map[it["id"]] = {
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "category": it.get("category"),
            "headline": it.get("headline", "")[:80],
        }

    final_items = list(merged_map.values())
    # Sort: urgent & freshest first, then highest signal
    final_items.sort(key=lambda x: (x.get("timestamp", 0), x.get("signal_score", 0)), reverse=True)
    final_items = final_items[:160]

    # Sync X hackathons into main Hackathons tab
    synced_hacks = sync_x_hackathons_to_main(final_items)

    # Send optional Telegram push alerts for net-new high-urgency drops
    urgent_new = [it for it in classified_new if it.get("is_urgent") or it.get("signal_score", 0) >= 88]
    tg_sent = send_telegram_alerts(urgent_new)

    meta = {
        "last_sweep_iso": datetime.now(timezone.utc).isoformat(),
        "last_sweep_display": datetime.now().strftime("%b %d, %I:%M %p"),
        "lane": lane,
        "total_signals": len(final_items),
        "new_in_sweep": len(classified_new),
        "synced_x_hackathons": synced_hacks,
        "engines": {
            "x_live": x_live_status,
            "exa_x": exa_status,
            "community_live": "active",
            "telegram_alerts": "active" if (os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")) else "not_configured",
        }
    }

    save_json(X_DATA_FILE, final_items)
    save_json(SEEN_X_FILE, seen_map)

    js_payload = (
        f"window.RADAR_X_DATA = {json.dumps(final_items, indent=2)};\n"
        f"window.RADAR_X_META = {json.dumps(meta, indent=2)};\n"
    )
    with open(os.path.join(DASHBOARD_DIR, "x_radar_data.js"), "w") as f:
        f.write(js_payload)
    with open(os.path.join(BASE_DIR, "x_radar_data.js"), "w") as f:
        f.write(js_payload)

    print(f"✓ Saved {len(final_items)} active signals ({synced_hacks} X hackathons dual-synced, {tg_sent} Telegram alerts sent).")
    return final_items, meta


if __name__ == "__main__":
    lane_arg = "fast" if "--fast" in sys.argv else "full"
    run_x_radar(lane=lane_arg)
