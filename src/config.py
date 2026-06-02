import os
from dotenv import load_dotenv

load_dotenv()

# ── Secrets ──────────────────────────────────────────────────────────────────
ADZUNA_APP_ID   = os.environ["ADZUNA_APP_ID"]
ADZUNA_APP_KEY  = os.environ["ADZUNA_APP_KEY"]
NOTION_TOKEN    = os.environ["NOTION_TOKEN"]
NOTION_DB_ID    = os.environ["NOTION_DB_ID"]
TELEGRAM_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT   = os.environ["TELEGRAM_CHAT_ID"]

# ── Search config ─────────────────────────────────────────────────────────────
SEARCH_TERMS = [
    "product designer",
    "ux designer",
    "ui designer",
    "experience designer",
]

LOCATIONS = ["San Francisco, CA", "New York, NY", "Seattle, WA", "Remote"]

RESULTS_PER_QUERY = 25   # per jobspy source per term
HOURS_OLD         = 5    # only grab jobs posted in last 5h (run every 4h + buffer)

# ── Priority companies (STRONG signal) ────────────────────────────────────────
PRIORITY_COMPANIES = {
    "apple", "google", "notion", "figma", "slack", "clay", "airtable",
    "retool", "youtube", "linear", "loom", "mercury", "stripe", "vercel",
    "anthropic", "openai", "perplexity", "arc", "raycast", "cron",
    "superhuman", "pitch", "craft", "miro", "framer", "webflow",
    "github", "gitlab", "dropbox", "zoom", "asana", "intercom",
    "brex", "ramp", "rippling", "lattice", "figma", "canva",
}

# ── ATS slugs to poll directly ────────────────────────────────────────────────
GREENHOUSE_SLUGS = [
    "notion", "figma", "airtable", "retool", "loom", "mercury", "brex",
    "rippling", "lattice", "intercom", "asana", "dropbox", "anthropic",
    "perplexity", "openai", "vercel", "linear",
]

LEVER_SLUGS = [
    "clay", "superhuman", "pitch", "craft", "raycast",
]

ASHBY_SLUGS = [
    "linear", "mercury", "arc", "cron",
]

# ── Hard-out patterns (SKIP) ──────────────────────────────────────────────────
import re

HARD_OUT_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"must\s+be\s+(a\s+)?us\s+citizen",
        r"us\s+citizen(ship)?\s+(only|required)",
        r"citizens?\s+only",
        r"security\s+clearance\s+required",
        r"secret\s+clearance",
        r"top\s+secret",
        r"\bITAR\b",
        r"\b1099\b",
        r"independent\s+contractor",
        r"contract.only",
        r"staffing\s+agenc(y|ies)",
        r"must\s+be\s+(a\s+)?citizen\s+or\s+permanent\s+resident",
        r"(citizen|permanent\s+resident)\s+required",
        r"no\s+visa\s+sponsorship.*permanent",
    ]
]

# ── Review patterns (REVIEW bucket) ───────────────────────────────────────────
REVIEW_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"without\s+sponsorship\s+now\s+or\s+in\s+the\s+future",
        r"permanent\s+work\s+authoriz",
        r"legally\s+authorized\s+to\s+work.*without\s+sponsorship",
        r"not\s+able\s+to\s+sponsor",
        r"unable\s+to\s+provide\s+sponsorship",
        r"not\s+eligible\s+for\s+visa\s+sponsorship",
    ]
]

# ── Title must contain at least one of these ──────────────────────────────────
TITLE_KEYWORDS = re.compile(
    r"\b(product|ux|ui|user\s+experience|experience|interaction|visual)\s+(designer?|design)\b"
    r"|\b(designer?)\b",
    re.IGNORECASE,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
SEEN_JOBS_PATH = "data/seen_jobs.json"
