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
    "design systems designer",
    "ux ui designer",
]

# US + Bengaluru searches
LOCATIONS = ["United States", "Remote", "Bengaluru, India"]

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
    # Original
    "notion", "figma", "airtable", "retool", "loom", "mercury", "brex",
    "rippling", "lattice", "intercom", "asana", "dropbox", "anthropic",
    "perplexity", "openai", "vercel", "linear",
    # Fintech / banking
    "stripe", "plaid", "robinhood", "coinbase", "chime", "wealthfront",
    "carta", "gusto", "deel", "remote", "ripple",
    # Consumer / social
    "airbnb", "doordash", "lyft", "duolingo", "reddit", "pinterest",
    "snap", "discord", "eventbrite", "meetup",
    # SaaS / productivity
    "hubspot", "zendesk", "amplitude", "mixpanel", "segment", "typeform",
    "miro", "coda", "hex", "descript", "runway", "framer", "webflow",
    "klaviyo", "iterable", "sendbird", "liveblocks",
    # AI / infrastructure
    "cohere", "scaleai", "replit", "modal", "langchain", "weights-biases",
    "huggingface", "together",
    # Enterprise / data
    "benchling", "palantir", "figma", "canva", "lucid",
    # Other design-strong companies
    "spotify", "netflix", "twitch", "roblox", "unity",
]

LEVER_SLUGS = [
    # Original
    "clay", "superhuman", "pitch", "raycast",
    # Additional
    "discord", "loom", "figma", "ramp", "watershed",
    "linear", "vercel", "dbt-labs", "prefect", "dagster",
    "gather", "mmhmm", "jam", "fathom",
]

ASHBY_SLUGS = [
    # Original
    "linear", "mercury", "arc",
    # Additional
    "luma", "loops", "resend", "cal", "dub", "plain",
    "campsite", "superlist", "craft", "supabase", "neon",
    "turso", "trigger", "inngest", "basehub",
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
        r"\d+[\s\-]month\s+contract",
        r"\d+[\s\-]month\s+(project|engagement|assignment)\b",
        r"project[\s\-]based\s+(position|role)\b",
        r"\b(contract(ual)?\s+(basis|role|position|only|work)|contract\s+to\s+hire)\b",
        r"\bhiring\s+for\s+(one\s+of\s+)?our\s+client",
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

# 2+ years minimum required → too senior for entry-level new grad, SKIP
# (?<![\-–\d]) prevents matching "3" in "1-3 years" (word-boundary fires on trailing digit)
# Qualifier-word-agnostic on purpose — real JDs phrase this as "4 years of interaction
# design experience", "5+ years of overall software development experience", or just a bare
# "7 - 10 Years" header with no "experience" word at all. Matching on the year count alone
# (lower bound ≥ 2) catches all of these; false positives (vesting/degree/tenure mentions)
# are excluded via the negative lookahead instead of trying to whitelist every qualifier.
# "Founded 10 years ago", "in business for 15 years" etc. mention company age, not a
# requirement — stripped out of the description copy before EXPERIENCE_SKIP runs (see filter.py).
COMPANY_AGE_MENTION = re.compile(
    r"\b(founded|established|in\s+business(\s+for)?)\b[^.]{0,40}?\d+\+?\s*years?\b",
    re.IGNORECASE,
)

_NOT_EXPERIENCE = r"(?!\s*(?:ago|old|of\s+age|later|degree|vesting|cliff|warranty|in\s+business|history))"

EXPERIENCE_SKIP = re.compile(
    # Bare/explicit year count ≥ 2, with or without "+", with or without a range upper bound,
    # with or without a trailing "experience" word — "7 - 10 Years", "5+ years", "4 years of
    # interaction design experience" all match on the leading number alone.
    r"(?<![\-–\d])([2-9]|\d{2,})\s*\+?\s*(?:[\-–]\s*\d{1,2}\s*)?\+?\s*years?\b" + _NOT_EXPERIENCE +
    # "minimum/at least 2 years" or more
    r"|\b(minimum|at\s+least)\s+(of\s+)?([2-9]|\d{2,})\s*years?\b"
    # Spelled-out numbers ≥ two — including "or more" variant e.g. "three or more years"
    r"|\b(two|three|four|five|six|seven|eight|nine|ten)(\s+or\s+more)?\s*years?\b" + _NOT_EXPERIENCE,
    re.IGNORECASE,
)

# No REVIEW bucket for experience anymore — 2+ is SKIP, <2 is fine
EXPERIENCE_REVIEW = re.compile(r"(?!)", re.IGNORECASE)  # never matches

# Qualitative seniority signals in description — no year count, but implies mid/senior level.
# If found WITHOUT entry-level signal → REVIEW (not SKIP, in case it's aspirational language).
DESCRIPTION_SENIORITY_SIGNALS = re.compile(
    r"\b(proven|extensive|deep|substantial|significant|demonstrated|considerable)\s+"
    r"(track\s+record|experience|expertise|background)\b"
    r"|\bproven\s+track\s+record\b"
    r"|\bseasoned\s+(designer|professional|practitioner)\b"
    r"|\b(expert[\s\-]level|expert\s+knowledge)\b"
    r"|\bseveral\s+years\s+(of\s+)?(experience|design)\b"
    # "seeking a Senior/experienced/seasoned designer" in description body
    r"|\bseeking\s+a\s+(senior|experienced|seasoned|skilled|strong)\b"
    r"|\b(senior|staff|principal)\s+(ux|ui|product|interaction|experience)\s+designer\b",
    re.IGNORECASE,
)

# ── Staffing / contract agency company blocklist → SKIP ──────────────────────
# These post contract roles on behalf of clients — not direct employer jobs.
STAFFING_AGENCY_BLOCK = re.compile(
    r"\b(kforce|cella|aquent|apex\s+group|24\s+seven|leappoint|"
    r"fetchjobs|agile\s*grid|kpg99|synergy\s+business|leadstack|"
    r"teksystems|insight\s+global|robert\s+half|randstad|"
    r"hays|modis|creative\s+circle|onward\s+search|"
    r"jobs\s+via\s+dice|jobs\s+via\s+linkedin|staffmark|"
    r"aerotek|cybercoders|manpower|adecco)\b",
    re.IGNORECASE,
)

# ── Title: must match a digital/product design role ───────────────────────────
# Requires explicit qualifier — plain "designer" alone is too broad.
# "visual" removed — visual designer roles are not relevant to candidate's target.
TITLE_REQUIRED = re.compile(
    r"\b(product|ux|ui|user[\s\-]?experience|interaction|experience|growth|ai|associate)\s+designers?\b"
    r"|\b(ux|ui|product|experience|interaction)\s+design\b"
    r"|\bdesign\s+systems?\s+designers?\b",
    re.IGNORECASE,
)

# ── Title: seniority hard-out → too senior for entry-level candidate ──────────
# Anchored to title start so "Staff UX Content Designer" and "Senior Product Designer"
# both match regardless of what comes between the seniority word and "designer".
# Does NOT block plain "Product Designer" (no modifier = open level, often entry-OK).
TITLE_SENIORITY_BLOCK = re.compile(
    # Seniority modifier anywhere in title — not anchored to start, since real postings
    # often prefix titles with work-mode/location tags (e.g. "(Hybrid) Senior UX Designer",
    # "Senior UX/UI Designer | Remote") which break a leading-anchor match.
    r"\b(senior|sr\.?|staff|principal|lead)\b(?=[\s.,/\-]|$)"
    # "Senior Associate", "Senior Specialist" etc. anywhere in title (e.g. "Experience Design Senior Associate")
    r"|\bsenior\s+(associate|specialist|consultant|advisor|strategist)\b"
    # VP — both abbreviated and spelled out
    r"|\b(vice\s+president|vp)[,\s]*(of\s+)?(product\s+|ux\s+|ui\s+|experience\s+)?design\b"
    r"|\b(vice\s+president|vp)\b.*design"
    # Management / leadership roles
    r"|\b(head\s+of[\w\s]*design|director[\w\s]*design|design\s+director|design\s+manager|design\s+lead)\b"
    r"|\b(ux|product|ui|experience)\s+(design\s+)?(director|manager|lead|head)\b"
    # Manager/director/VP anywhere in title
    r"|\b(manager|director|vice\s+president)\b"
    # Mid-level explicitly stated — not entry-level
    r"|\bmid[\s\-]level\b"
    # "Sr"/"Sr." anywhere in title, not just leading (e.g. "Product Designer, Sr.")
    r"|\bsr\.?\b",
    re.IGNORECASE,
)

# ── Title: wrong role type hard-out ───────────────────────────────────────────
TITLE_ROLE_BLOCK = re.compile(
    # "visual [anything] designer" — visual designer, visual UX designer, visual product designer etc.
    r"\bvisual\s+(\w+\s+)?designer\b"
    r"|\b(motion|graphic|brand|industrial|fashion|textile|apparel|packaging|interior|"
    r"landscape|game|jewelry|accessory|accessories|photonics|technical|freelance|presentation|"
    r"powerpoint|instructional|curriculum|web\s+graphic|performance\s+creative|slide|"
    r"automotive|vehicle|furniture|hardware|floral|lighting|material|surface)\s+designer\b"
    r"|\bdesigner\s*([-–]\s*)?(handbag|apparel|sleep|knit|bottom|dress|outerwear|baby|kids\s+bedding|accessory|accessories|automotive|vehicle|furniture)\b"
    r"|\bcontent\s+(experience\s+|product\s+|ux\s+|ui\s+|design\s+)?designer\b"
    r"|\bdesigner\s+advocate\b"
    r"|\bdesign\s+advocate\b"
    # Academic / teaching roles
    r"|\b(professor|assistant\s+professor|associate\s+professor|adjunct|lecturer|instructor)\b"
    r"|\b(teaching|faculty|academic)\b"
    # Freelance / contract / gig work — anywhere in title, not just adjacent to "designer"
    r"|\bfreelance(r)?\b"
    r"|\bcontract(or)?\b"
    r"|\bcontract\s+to\s+hire\b"
    r"|\b(part[\s\-]time|gig|project[\s\-]based)\b"
    # Internship / student roles
    r"|\bintern(ship)?\b"
    r"|\b(student\s+placement|co[\s\-]?op|apprentice(ship)?)\b"
    # "Design Specialist" / generic specialist titles — not a product design role
    r"|\b(design\s+)?specialist\b",
    re.IGNORECASE,
)

# ── Title: founding designer → REVIEW (often wants 5+ yrs despite startup framing)
TITLE_FOUNDING = re.compile(r"\bfounding\s+(product\s+|ux\s+|ui\s+)?designer\b", re.IGNORECASE)

# ── Tier-1 companies with Bengaluru presence → allowed for India jobs ─────────
INDIA_TIER1_COMPANIES = {
    # Global tech with strong Bengaluru offices
    "google", "microsoft", "amazon", "apple", "meta", "samsung", "intel",
    "cisco", "oracle", "sap", "adobe", "linkedin", "paypal", "walmart",
    "atlassian", "servicenow", "salesforce", "workday", "vmware", "ibm",
    "accenture", "thoughtworks",
    # Indian unicorns / top product-design companies
    "flipkart", "swiggy", "zomato", "meesho", "cred", "phonepe", "razorpay",
    "freshworks", "zoho", "browserstack", "postman", "chargebee", "groww",
    "zepto", "bigbasket", "navi", "jupiter", "slice", "dunzo", "unacademy",
    "makemytrip", "cleartrip", "ola", "rapido", "licious", "cult.fit",
    "wakefit", "udaan", "mmt", "namma yatri",
}

# ── Location: India/Bengaluru presence check ──────────────────────────────────
INDIA_LOCATION = re.compile(
    r"\b(india|bengaluru|bangalore|karnataka)\b",
    re.IGNORECASE,
)

# ── Location: US presence check ───────────────────────────────────────────────
USA_LOCATION = re.compile(
    r"\b(united\s+states|usa|\bus\b|u\.s\.a?\.?|remote|anywhere\s+in\s+the\s+us|"
    r"san\s+francisco|new\s+york|seattle|austin|chicago|boston|los\s+angeles|"
    r"denver|atlanta|miami|portland|nashville|dallas|washington\s+dc|"
    r"minneapolis|philadelphia|phoenix|san\s+diego|las\s+vegas|detroit|"
    r"pittsburgh|charlotte|raleigh|salt\s+lake|indianapolis|columbus|"
    r"SF|NYC|LA|DC|"
    r"california|new\s+york\s+state|texas|washington\s+state|illinois|"
    # All 50 US state abbreviations
    r"\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|"
    r"MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|"
    r"SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b)\b",
    re.IGNORECASE,
)

# Non-US country/city signals — checked in location field AND description
# Catches jobs posted as "Remote" by non-US companies
NON_US_LOCATION = re.compile(
    r"\b(singapore|peru|lima|bogot[aá]|colombia|mexico\s+city|guadalajara|monterrey"
    r"|london|united\s+kingdom|\buk\b|england|scotland|ireland|dublin"
    r"|canada|toronto|vancouver|montreal|ottawa"
    r"|australia|sydney|melbourne|brisbane"
    r"|india|bangalore|bengaluru|mumbai|delhi|hyderabad|pune|chennai"
    r"|germany|berlin|munich|frankfurt|hamburg"
    r"|france|paris|lyon|toulouse"
    r"|netherlands|amsterdam|rotterdam"
    r"|spain|madrid|barcelona"
    r"|brazil|s[aã]o\s+paulo|rio\s+de\s+janeiro|brasilia"
    r"|argentina|buenos\s+aires"
    r"|chile|santiago"
    r"|philippines|manila|cebu"
    r"|indonesia|jakarta|bali"
    r"|malaysia|kuala\s+lumpur"
    r"|vietnam|ho\s+chi\s+minh|hanoi"
    r"|thailand|bangkok"
    r"|japan|tokyo|osaka"
    r"|south\s+korea|seoul"
    r"|china|beijing|shanghai|shenzhen"
    r"|taiwan|taipei"
    r"|israel|tel\s+aviv"
    r"|sweden|stockholm|gothenburg"
    r"|norway|oslo"
    r"|denmark|copenhagen"
    r"|finland|helsinki"
    r"|switzerland|zurich|geneva"
    r"|austria|vienna"
    r"|poland|warsaw|krakow"
    r"|czech|prague"
    r"|new\s+zealand|auckland|wellington"
    r"|south\s+africa|cape\s+town|johannesburg"
    r"|kenya|nairobi"
    r"|nigeria|lagos"
    r"|egypt|cairo"
    r"|uae|dubai|abu\s+dhabi"
    r"|saudi\s+arabia|riyadh"
    r"|malta|cyprus|greece|athens|lisbon|portugal|romania|bucharest"
    r"|estonia|latvia|lithuania|belarus|moldova"
    r"|hungary|budapest|bulgaria|sofia|serbia|belgrade|croatia|zagreb"
    r"|slovakia|bratislava|slovenia|ljubljana|bosnia|albania|kosovo|montenegro|macedonia"
    r"|belgium|brussels|luxembourg|iceland|reykjavik"
    r"|russia|moscow|saint\s+petersburg|kazakhstan|tbilisi|armenia|azerbaijan|baku"
    r"|turkey|istanbul|ankara|ukraine|kyiv|kiev"
    r"|pakistan|karachi|lahore|islamabad|bangladesh|dhaka|sri\s+lanka|colombo|nepal|kathmandu"
    r"|hong\s+kong|macau|mongolia|cambodia|phnom\s+penh|laos|myanmar|brunei"
    r"|qatar|doha|kuwait|bahrain|oman|muscat|amman|lebanon|beirut"
    r"|morocco|casablanca|tunisia|algeria|ghana|accra|uganda|ethiopia|addis\s+ababa"
    r"|costa\s+rica|panama|ecuador|quito|venezuela|caracas|uruguay|paraguay|bolivia"
    r"|europe|european)\b",
    re.IGNORECASE,
)

# Non-US timezone abbreviations in description — signals non-US employer on "Remote" listings
NON_US_TIMEZONE = re.compile(
    r"\b(AEST|AEDT|NZST|NZDT|CET|CEST|BST|IST|SGT|HKT|JST|KST|MYT|PHT|WIB|GMT[+-][1-9])\b",
    re.IGNORECASE,
)

# Non-USD currency signals in description — flags non-US employers
NON_USD_CURRENCY = re.compile(
    r"\b(AUD|CAD|GBP|EUR|SGD|NZD|INR)\b"
    r"|[£€₹]"
    r"|\bA\$|\bC\$|\bNZ\$",
)

# Non-Latin script chars — CJK, Hangul, Cyrillic, Arabic, Devanagari, Thai, Greek.
# Description written mostly in another language is a strong non-US/non-India signal
# (English-language regex checks above can't catch what they can't read).
NON_LATIN_SCRIPT = re.compile(
    r"[一-鿿぀-ヿ가-힣"   # CJK, Hiragana/Katakana, Hangul
    r"Ѐ-ӿ"                                # Cyrillic
    r"؀-ۿ"                                # Arabic
    r"ऀ-ॿ"                                # Devanagari
    r"฀-๿"                                # Thai
    r"Ͱ-Ͽ]"                               # Greek
)

# If non-US location, check if they offer visa support → REVIEW instead of SKIP
VISA_OFFER = re.compile(
    # "relocation package" deliberately excluded — standard intl-hiring perk, says nothing
    # about US visa/OPT sponsorship specifically, and was flooding REVIEW (→ Telegram) with
    # plain UK/EU jobs that happened to mention relocation assistance for local hires.
    r"\b(visa\s+sponsorship|will\s+sponsor|sponsoring\s+visa|OPT|CPT|f[\s\-]?1\s+visa|"
    r"h[\s\-]?1[\s\-]?b\s+sponsor|work\s+visa\s+provided|us\s+relocation)\b",
    re.IGNORECASE,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
SEEN_JOBS_PATH = "data/seen_jobs.json"
