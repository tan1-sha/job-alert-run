import os
import re
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
    "interaction designer",
]

# Focus on US cities; "Remote" treated as US-based (most US boards default US remote)
LOCATIONS = ["San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX", "Remote"]

RESULTS_PER_QUERY = 25   # per jobspy source per term
HOURS_OLD         = 5    # only grab jobs posted in last 5h (run every 4h + buffer)

# ── Candidate profile (used for level + fit filtering) ───────────────────────
# Entry-level new grad, 4 internships, BFA Interaction Design @ CCA May 2026
# Strengths: fintech/platform UI, design systems, Figma, Framer, eng collaboration
# On F-1 OPT from June 15 2026 — needs W-2 USA jobs

# ── Priority companies → bonus STRONG signal ──────────────────────────────────
PRIORITY_COMPANIES = {
    "apple", "google", "notion", "figma", "slack", "clay", "airtable",
    "retool", "youtube", "linear", "loom", "mercury", "stripe", "vercel",
    "anthropic", "openai", "perplexity", "arc", "raycast",
    "superhuman", "pitch", "miro", "framer", "webflow",
    "github", "dropbox", "zoom", "asana", "intercom",
    "brex", "ramp", "rippling", "canva", "figma",
}

# ── ATS slugs to poll directly ────────────────────────────────────────────────
GREENHOUSE_SLUGS = [
    "notion", "figma", "airtable", "retool", "loom", "mercury", "brex",
    "rippling", "lattice", "intercom", "asana", "dropbox", "anthropic",
    "perplexity", "openai", "vercel", "linear",
]

LEVER_SLUGS = [
    "clay", "superhuman", "pitch", "raycast",
]

ASHBY_SLUGS = [
    "linear", "mercury", "arc",
]

# ── Hard-out description patterns → SKIP ─────────────────────────────────────
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

# ── Review description patterns → REVIEW bucket ───────────────────────────────
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

# ── Experience year gates (applied to full description text) ─────────────────
# Candidate has ~10 months internship experience (4 internships, new grad May 2026).

# If description explicitly targets new grads / entry level → bypass year gates
ENTRY_LEVEL_SIGNAL = re.compile(
    r"\b(entry[\s\-]level|new\s+grad(uate)?|recent\s+grad(uate)?|early\s+career"
    r"|0[\s\-]2\s*years?|0[\s\-]1\s*years?|1[\s\-]2\s*years?"
    r"|no\s+experience\s+required|internship\s+experience\s+(counts?|considered|welcome))\b",
    re.IGNORECASE,
)

# 3+ years explicitly required → too senior, SKIP
# (?<![\-–]) prevents matching "3" in "2-3 years" (word boundary fires on "3" after dash)
EXPERIENCE_SKIP = re.compile(
    # "3+ years of [design/ux/...] experience"  (not preceded by a dash → not end of 2-3 range)
    r"(?<![\-–\d])([3-9]|\d{2,})\+?\s*years?\s+(of\s+)?"
    r"(ux|ui|product|design|professional|work|relevant|full[\s\-]time|industry)?\s*"
    r"(design\s+)?experience\b"
    # "3–5 years of [product design] experience" (leading number must be 3+)
    r"|(?<![\-–\d])([3-9]|\d{2,})\s*[\-–]\s*\d+\s*years?\s*(of\s+)?"
    r"(ux|ui|product|design|professional|work|relevant)?\s*(design\s+)?experience\b"
    # "minimum/at least 3 years"
    r"|\b(minimum|at\s+least)\s+(of\s+)?([3-9]|\d{2,})\s*years?\b",
    re.IGNORECASE,
)

# 2+ years required → borderline, REVIEW (4 internships might qualify)
EXPERIENCE_REVIEW = re.compile(
    # "2+ years of [design/...] experience"  (explicit + sign required to distinguish from "2 years ago")
    r"(?<![\-–\d])2\+\s*years?\s+(of\s+)?"
    r"(ux|ui|product|design|professional|work|relevant|full[\s\-]time|industry)?\s*"
    r"(design\s+)?experience\b"
    # "2–3 years" / "2–4 years" etc.
    r"|(?<![\-–\d])2\s*[\-–]\s*[3-9]\s*years?\s*(of\s+)?"
    r"(ux|ui|product|design|professional|work)?\s*experience\b"
    # "minimum/at least 2 years"
    r"|\b(minimum|at\s+least)\s+(of\s+)?2\s*years?\b",
    re.IGNORECASE,
)

# ── Title: must match a digital/product design role ───────────────────────────
# Requires explicit qualifier — plain "designer" alone is too broad
TITLE_REQUIRED = re.compile(
    r"\b(product|ux|ui|user[\s\-]?experience|interaction|experience|visual|content|growth|ai|associate)\s+designer\b"
    r"|\b(ux|ui|product|experience|interaction)\s+design\b",
    re.IGNORECASE,
)

# ── Title: seniority hard-out → too senior for entry-level candidate ──────────
# Anchored to title start so "Staff UX Content Designer" and "Senior Product Designer"
# both match regardless of what comes between the seniority word and "designer".
# Does NOT block plain "Product Designer" (no modifier = open level, often entry-OK).
TITLE_SENIORITY_BLOCK = re.compile(
    # Title begins with seniority modifier (covers "Senior X Designer", "Staff UX Y Designer", etc.)
    r"^\s*(senior|sr\.?|staff|principal|lead|manager)\b"
    # Management / leadership roles
    r"|\b(head\s+of[\w\s]*design|director[\w\s]*design|design\s+director|design\s+manager|design\s+lead)\b"
    r"|\b(ux|product|ui|experience)\s+(design\s+)?(director|manager|lead|head)\b"
    r"|\bvp[,\s]+(of\s+)?(product\s+)?design\b",
    re.IGNORECASE,
)

# ── Title: wrong role type hard-out ───────────────────────────────────────────
TITLE_ROLE_BLOCK = re.compile(
    r"\b(motion|graphic|brand|industrial|fashion|textile|apparel|packaging|interior|"
    r"landscape|game|jewelry|photonics|technical|freelance|presentation|powerpoint|"
    r"instructional|curriculum|web\s+graphic|performance\s+creative|slide)\s+designer\b"
    r"|\bdesigner\s*([-–]\s*)?(handbag|apparel|sleep|knit|bottom|dress|outerwear|baby|kids\s+bedding)\b"
    r"|\bdesigner\s+advocate\b"
    r"|\bdesign\s+advocate\b",
    re.IGNORECASE,
)

# ── Title: founding designer → REVIEW (often wants 5+ yrs despite startup framing)
TITLE_FOUNDING = re.compile(r"\bfounding\s+(product\s+|ux\s+|ui\s+)?designer\b", re.IGNORECASE)

# ── Location: US presence check ───────────────────────────────────────────────
USA_LOCATION = re.compile(
    r"\b(united\s+states|usa|u\.s\.a?\.?|remote|"
    r"san\s+francisco|new\s+york|seattle|austin|chicago|boston|los\s+angeles|"
    r"denver|atlanta|miami|portland|nashville|dallas|washington\s+dc|"
    r"SF|NYC|LA|DC|"
    r"california|new\s+york\s+state|texas|washington\s+state|illinois|"
    r"\b(CA|NY|TX|WA|IL|MA|CO|GA|FL|OR|NC|VA|PA|OH|MI|MN|AZ|TN|MD|DC)\b)\b",
    re.IGNORECASE,
)

# If non-US location, check if they offer visa support → REVIEW instead of SKIP
VISA_OFFER = re.compile(
    r"\b(visa\s+sponsorship|will\s+sponsor|sponsoring\s+visa|OPT|CPT|f[\s\-]?1\s+visa|"
    r"h[\s\-]?1[\s\-]?b\s+sponsor|work\s+visa\s+provided|relocation\s+package)\b",
    re.IGNORECASE,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
SEEN_JOBS_PATH = "data/seen_jobs.json"
