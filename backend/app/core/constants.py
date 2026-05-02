# Application-wide constants — single source of truth
API_VERSION = "1.0.0"
DEFAULT_PAGE_SIZE = 20

# ── Event Types ───────────────────────────────────────────────────────────────
EVENT_TYPES = ["war", "conflict", "sanctions", "unrest", "policy", "economic"]

# ── Risk Thresholds ───────────────────────────────────────────────────────────
HIGH_RISK_THRESHOLD = 65.0
LOW_RISK_THRESHOLD = 35.0

# ── Color Classification ──────────────────────────────────────────────────────
COLOR_RED = "Red"
COLOR_YELLOW = "Yellow"
COLOR_GREEN = "Green"

# ── GTI Labels & Score Ranges ─────────────────────────────────────────────────
GTI_LABELS = {
    "LOW":      (0, 30),
    "MODERATE": (30, 60),
    "HIGH":     (60, 80),
    "CRITICAL": (80, 100),
}
GTI_EVENT_TYPE_WEIGHTS = {
    "war":       1.5,
    "conflict":  1.4,
    "sanctions": 1.2,
    "unrest":    1.1,
    "policy":    1.0,
    "economic":  0.8,
}
GTI_LOOKBACK_DAYS = 7
GTI_BASELINE_SCORE = 50.0

# ── Signal Types ──────────────────────────────────────────────────────────────
SIGNAL_BUY  = "BUY"
SIGNAL_SELL = "SELL"
SIGNAL_HOLD = "HOLD"

# ── Impact Labels ─────────────────────────────────────────────────────────────
IMPACT_CRITICAL  = "CRITICAL"
IMPACT_HIGH      = "HIGH"
IMPACT_ELEVATED  = "ELEVATED"

# ── OpenAI / AI Config ────────────────────────────────────────────────────────
DEFAULT_AI_MODEL      = "gpt-4o-mini"
OPENAI_API_URL        = "https://api.openai.com/v1/chat/completions"
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
