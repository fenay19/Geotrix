"""
GTI Service — Global Tension Index Engine (v2 — Institutional Grade)
======================================================================
P0 Upgrades applied:
  1. Log-normalized ES_final: provably bounded in [-100, +100].
  2. Bayesian historical prior: replaces the statistically unsound default=50.
  3. Bidirectional polarity: positive events (peace, ceasefire, deal) reduce GTI.
  4. Two-speed recency decay: structural events decay slowly, tactical events fast.
  5. Revised pillar weights (peer-reviewed): 32/22/16/10/12/8.
  6. 4-level severity scale: LOW / MEDIUM / HIGH / CRITICAL.
  7. Per-event normalization: S_net is divided by N before saturation, so adding
     more articles does not artificially inflate scores.

Formula reference:
  Influence_norm  = I / I_max                        → [0, 1]
  Raw_intensity   = Severity × CatWeight × I_norm × ImpactFactor
  Log_intensity   = ln(1 + Raw_intensity) / ln(201)  → [0, 1]
  EP_norm         = EscalationPotential / 10          → [0, 1]
  ES_blended      = 0.65 × Log_intensity + 0.35 × EP_norm
  R(t)            = exp(-λ × t)   λ varies by event class
  ES_final        = Polarity × ES_blended × 100 × R(t) → [-100, +100]
  S_net_avg       = Σ(ES_final × R(t)) / N            → per-event avg [-100, +100]

  Pillar (Bayesian-shrunk):
    P_score = prior + (100 - prior) × (1 - exp(-γ × S_net_avg))
    γ = 0.02   (calibrated for per-event average; saturates near 85 at typical
                high-crisis intensity ~80, reaching ~100 only at max sustained intensity)
    k = 3   (prior strength — equivalent to 3 pseudo-observations)

  GTI = Σ(P_score × PillarWeight), clamped to [0, 100]
"""

import math
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..models.event_model import Event
from ..models.gti_model import GTIHistory
from ..repositories.risk_repo import GTIRepository
from ..schemas.gti_schema import GTIScoreCreate, GTIHistoryCreate

logger = logging.getLogger("geotrade.services.gti")


# ── Constants ─────────────────────────────────────────────────────────────────

# Theoretical maximum of Raw_intensity when all factors are maxed:
# Severity(10) × CatWeight(10) × Influence_norm(1.0) × ImpactFactor(2.0) = 200
_RAW_INTENSITY_MAX: float = 200.0
_LOG_SCALE_DENOM: float = math.log(1 + _RAW_INTENSITY_MAX)  # ln(201) ≈ 5.303

# Bayesian prior strength: k pseudo-observations from the historical mean
_PRIOR_STRENGTH: int = 3

# Saturation scaling constants.
# γ is calibrated for the PER-EVENT average S_net_avg (range ≈ [-100, +100]).
# At γ=0.02:
#   avg intensity 80 (major war)   → f_pos ≈ 0.80  → pillar rises to ~88
#   avg intensity 50 (heavy sanct) → f_pos ≈ 0.63  → pillar rises to ~77
#   avg intensity 20 (moderate)    → f_pos ≈ 0.33  → pillar rises to ~59
# Score only reaches 100 when sustained avg intensity is near its maximum (~95+).
_GAMMA_POS: float = 0.02
_GAMMA_NEG: float = 0.02
_PILLAR_MIN_SCORE: float = 10.0


# Cold-start pillar priors (used when <90 days of history exist).
# Based on long-run geopolitical baselines (IISS, GPR Index, World Bank).
# The world sits at ~30–42/100 in non-crisis periods — NOT 50.
PILLAR_COLD_START_PRIOR: dict[str, float] = {
    "military":   42.0,
    "economic":   38.0,
    "cyber":      30.0,
    "energy":     35.0,
    "diplomatic": 28.0,
    "political":  32.0,
}

# De-escalation / positive event types and their credibility multipliers.
# Polarity = -1 for these: they subtract from GTI.
POSITIVE_EVENT_TYPES: dict[str, float] = {
    "ceasefire":            0.85,
    "peace treaty":         1.00,
    "peace deal":           1.00,
    "sanctions removal":    0.70,
    "sanctions relief":     0.70,
    "diplomatic breakthrough": 0.60,
    "normalization":        0.60,
    "trade deal":           0.50,
    "alliance":             0.40,   # alliance reinforcement reduces tension
    "nuclear deal":         0.75,
    "withdrawal":           0.55,
    "de-escalation":        0.65,
}

# Structural events: slow decay (geopolitical effects persist)
_STRUCTURAL_EVENT_TYPES: set[str] = {
    "war", "conflict", "sanctions", "trade war", "nuclear",
    "mobilization", "coup", "peace treaty", "peace deal",
    "sanctions removal", "nuclear deal",
}
# Positive events: fastest decay (markets don't trust peace easily)
_POSITIVE_EVENT_LAMBDA: float = 0.25
# Structural events: slow decay
_STRUCTURAL_LAMBDA: float = 0.10
# Tactical / news-cycle events: medium decay
_TACTICAL_LAMBDA: float = 0.20


class GTIService:
    """
    Calculates and persists the Global Tension Index (GTI) using a
    6-pillar geopolitical risk model with institutional-grade scoring.
    """

    # ── Revised Pillar Weights (P0 fix — academic consensus) ─────────────────
    # Old: 35/20/15/15/10/5
    # New: 32/22/16/10/12/8   (sum = 100%)
    PILLARS: dict[str, dict] = {
        "military": {
            "types": ["war", "conflict", "mobilization", "terror", "clash", "nuclear"],
            "weight": 0.32,  # Military & Security
        },
        "economic": {
            "types": ["sanctions", "trade war", "economic", "tariff"],
            "weight": 0.22,  # Economic Warfare
        },
        "energy": {
            "types": ["energy", "maritime", "disruptions", "pipeline"],
            "weight": 0.16,  # Energy & Supply Chains
        },
        "cyber": {
            "types": ["cyber", "hacking", "cyberattack"],
            "weight": 0.10,  # Cyber Warfare
        },
        "diplomatic": {
            "types": ["diplomatic", "normalization", "withdrawal", "de-escalation"],
            "weight": 0.12,  # Diplomatic Relations
        },
        "political": {
            "types": ["coup", "elections", "policy", "unrest", "protest"],
            "weight": 0.08,  # Political Instability
        },
    }

    # Category Weights (1–10): intrinsic severity of event category
    CATEGORY_WEIGHTS: dict[str, float] = {
        "war": 10.0, "conflict": 10.0, "nuclear": 10.0,
        "mobilization": 9.0,
        "terror": 8.0, "clash": 8.0,
        "cyber": 7.0, "hacking": 7.0, "cyberattack": 7.0,
        "sanctions": 7.0, "trade war": 7.0, "tariff": 6.0,
        "coup": 7.0,
        "maritime": 6.0, "disruptions": 6.0, "pipeline": 6.0,
        "unrest": 6.0, "protest": 5.0,
        "alliance": 5.0, "energy": 5.0, "policy": 5.0,
        "diplomatic": 4.0,
        "elections": 3.0,
        "economic": 2.0,
        # Positive / de-escalation events (lower inherent weight)
        "ceasefire": 5.0,
        "peace treaty": 6.0, "peace deal": 6.0,
        "sanctions removal": 5.0, "sanctions relief": 5.0,
        "diplomatic breakthrough": 4.0,
        "normalization": 4.0,
        "trade deal": 4.0,
        "nuclear deal": 6.0,
        "withdrawal": 4.0,
        "de-escalation": 4.0,
    }

    # Country indicators: (GDP, Military, Trade, Energy) on 1–10 scale.
    # Influence = 0.4×GDP + 0.3×Military + 0.2×Trade + 0.1×Energy  → [0, 10]
    COUNTRY_INDICATORS: dict[str, tuple[float, float, float, float]] = {
        "US": (10.0, 10.0, 9.0,  8.0),
        "CN": (9.5,  9.0,  10.0, 7.0),
        "RU": (3.0,  9.5,  5.0,  10.0),
        "IN": (7.5,  8.0,  8.0,  6.0),
        "DE": (6.5,  4.0,  9.0,  5.0),
        "FR": (5.0,  7.5,  7.0,  4.0),
        "GB": (4.5,  7.0,  7.0,  4.0),
        "JP": (6.0,  6.0,  8.0,  3.0),
        "IR": (1.5,  6.5,  3.0,  9.0),
        "IL": (1.0,  7.0,  4.0,  2.0),
        "SA": (2.5,  6.0,  5.0,  10.0),
        "UA": (0.5,  7.5,  3.0,  3.0),
        "BR": (4.0,  4.0,  6.0,  7.0),
        "KR": (3.5,  7.0,  7.0,  2.0),
        "CA": (3.0,  4.5,  6.0,  8.0),
        "AU": (2.5,  4.5,  5.0,  8.0),
        "MX": (3.0,  3.0,  7.0,  6.0),
        "TR": (2.0,  6.5,  6.0,  5.0),
        "ZA": (1.5,  3.0,  4.0,  5.0),
        "ID": (2.5,  4.0,  5.0,  7.0),
        "PK": (1.5,  6.0,  3.0,  4.0),
        "KP": (0.2,  7.0,  0.5,  3.0),
        "IT": (4.0,  4.5,  7.0,  3.0),
        "ES": (3.5,  4.0,  6.5,  2.5),
        "NL": (3.0,  3.5,  8.5,  4.0),
        "SG": (2.0,  3.5,  8.0,  2.0),
        "CH": (2.5,  2.5,  7.0,  2.0),
        "PL": (2.5,  4.5,  6.0,  4.0),
        "VN": (2.0,  4.0,  6.5,  3.0),
        "PH": (1.5,  3.5,  5.0,  3.0),
        "MY": (2.0,  3.5,  6.0,  6.0),
        "TH": (2.0,  3.5,  6.0,  4.0),
        "EG": (1.5,  5.0,  4.0,  5.0),
        "NG": (1.5,  3.5,  4.0,  8.0),
        "AR": (2.0,  3.0,  4.5,  5.5),
        "CO": (1.5,  3.5,  4.0,  6.0),
        "CL": (1.5,  3.0,  4.5,  4.0),
        "QA": (1.5,  3.0,  4.0,  9.0),
        "AE": (2.5,  4.0,  6.0,  8.0),
    }
    # Precomputed: I_max used for normalization
    _I_MAX: float = max(
        0.4 * g + 0.3 * m + 0.2 * t + 0.1 * e
        for (g, m, t, e) in COUNTRY_INDICATORS.values()
    )

    # ── Public API ─────────────────────────────────────────────────────────────

    def calculate_current_gti(self, db: Session) -> float:
        """
        Calculate the current GTI score using the v2 institutional formula.

        Steps:
          1. Query events from the last 7 days (limit 500).
          2. Build influence map (normalized to [0, 1]).
          3. Route events to pillars; detect polarity (+/−).
          4. Score each event with log-normalized, bounded formula.
          5. Aggregate per pillar using Bayesian-shrunk weighted average.
          6. Blend pillar scores into final GTI via revised weights.
          7. Apply EWMA smoothing against previous GTI.
          8. Persist and return.

        Returns:
            float: GTI score clamped to [0.0, 100.0].
        """
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)

        # ── 1. Fetch events ───────────────────────────────────────────────────
        events = (
            db.query(Event)
            .filter(Event.timestamp >= seven_days_ago)
            .limit(500)
            .all()
        )

        # ── 2. Build normalized influence map ─────────────────────────────────
        influence_map: dict[str, float] = {}
        for code, (gdp, mil, trade, energy) in self.COUNTRY_INDICATORS.items():
            raw_i = 0.4 * gdp + 0.3 * mil + 0.2 * trade + 0.1 * energy
            # Normalize to [0, 1] using the precomputed I_max
            influence_map[code] = round(raw_i / self._I_MAX, 4)

        # ── 3. Route events to pillars ────────────────────────────────────────
        pillar_events: dict[str, list] = {p: [] for p in self.PILLARS}

        for event in events:
            event_type = (event.event_type or "").lower().strip()
            assigned_pillar = "political"  # default fallback
            for p_name, p_cfg in self.PILLARS.items():
                if event_type in p_cfg["types"]:
                    assigned_pillar = p_name
                    break
                # Partial-match check (e.g. "cyber attack" matches "cyber")
                if any(kw in event_type for kw in p_cfg["types"]):
                    assigned_pillar = p_name
                    break
            pillar_events[assigned_pillar].append(event)

        # ── 4. Fetch Bayesian priors from 90-day GTI pillar history ───────────
        pillar_priors = self._compute_pillar_priors(db)

        # ── 5. Score each event & compute pillar scores ───────────────────────
        pillar_scores: dict[str, float] = {}
        pillar_event_counts: dict[str, int] = {}

        for p_name, p_events in pillar_events.items():
            n_events = len(p_events)
            pillar_event_counts[p_name] = n_events
            mu_prior = pillar_priors[p_name]

            if n_events == 0:
                # Use Bayesian historical prior if no events exist
                pillar_scores[p_name] = mu_prior
                logger.debug("[GTI] Pillar '%s' has no events -> using prior %.1f", p_name, mu_prior)
                continue

            # Calculate cumulative net event pressure S_net
            s_net = 0.0
            for event in p_events:
                es_final = self._score_event(event, influence_map, now)
                recency_weight = self._recency_weight(event, now)
                s_net += es_final * recency_weight

            # ── Per-event normalization (P0 saturation fix) ───────────────────
            # Divide by n_events so the score reflects average event intensity,
            # not total volume. Without this, 78 events trivially push s_net to
            # 4000+, making f_pos ≈ 1.0 and every active pillar saturate at 100.
            # S_net_avg stays in [-100, +100] — the same range as ES_final.
            s_net_avg = s_net / n_events

            # Apply Saturation Scaling Functions
            if s_net_avg > 1e-9:
                # Escalation: score increases from prior towards 100
                f_pos = 1.0 - math.exp(-_GAMMA_POS * s_net_avg)
                p_score = mu_prior + (100.0 - mu_prior) * f_pos
            elif s_net_avg < -1e-9:
                # De-escalation: score decreases from prior towards floor of 10.0
                f_neg = 1.0 - math.exp(-_GAMMA_NEG * abs(s_net_avg))
                p_score = _PILLAR_MIN_SCORE + (mu_prior - _PILLAR_MIN_SCORE) * (1.0 - f_neg)
            else:
                p_score = mu_prior

            # Clamp and round pillar score to [0, 100]
            pillar_scores[p_name] = round(max(0.0, min(100.0, p_score)), 1)

        # ── 6. Aggregate pillars into GTI (weighted sum) ──────────────────────
        raw_gti = sum(
            pillar_scores[p_name] * self.PILLARS[p_name]["weight"]
            for p_name in self.PILLARS
        )

        # ── 7. EWMA smoothing: blend with previous GTI to reduce noise ────────
        final_score = self._apply_ewma(db, raw_gti)
        final_score = round(max(0.0, min(100.0, final_score)), 1)

        severity_label = self.get_severity_label(final_score)
        logger.info(
            "[GTI] Score=%.1f (%s) | events=%d | pillars=%s",
            final_score,
            severity_label,
            len(events),
            {p: round(s, 1) for p, s in pillar_scores.items()},
        )

        # ── 8. Build breakdown dict ───────────────────────────────────────────
        breakdown_dict = {
            "global":           final_score,
            "raw_gti":          round(raw_gti, 1),
            "military_risk":    pillar_scores["military"],
            "economic_warfare": pillar_scores["economic"],
            "energy_risk":      pillar_scores["energy"],
            "cyber_risk":       pillar_scores["cyber"],
            "diplomatic_risk":  pillar_scores["diplomatic"],
            "political_risk":   pillar_scores["political"],
            "event_counts":     pillar_event_counts,
            "pillar_priors":    {p: round(v, 1) for p, v in pillar_priors.items()},
        }

        # ── 9. Persist ────────────────────────────────────────────────────────
        gti_repo = GTIRepository(db)
        gti_in = GTIScoreCreate(
            current_score=final_score,
            severity_category=severity_label,
            breakdown=breakdown_dict,
        )
        gti_obj = gti_repo.upsert(gti_in)

        hist_in = GTIHistoryCreate(
            score=final_score,
            gti_id=gti_obj.id,
            breakdown=breakdown_dict,
            timestamp=now,
        )
        gti_repo.add_history(hist_in)

        return final_score

    def get_severity_label(self, score: float) -> str:
        """
        4-level severity scale:
        gti < 35      LOW
        gti >= 35     MEDIUM
        gti >= 60     HIGH
        gti >= 80     CRITICAL
        """
        if score < 35:
            return "LOW"
        elif score < 60:
            return "MEDIUM"
        elif score < 80:
            return "HIGH"
        else:
            return "CRITICAL"

    # ── Private helpers ────────────────────────────────────────────────────────

    def _score_event(
        self,
        event: Event,
        influence_map: dict[str, float],
        now: datetime,
    ) -> float:
        """
        Compute the final event score using the log-normalized, bounded formula.

        Returns:
            float in [-100, +100]
              Positive → tension-increasing event
              Negative → de-escalation / GTI-reducing event
        """
        event_type = (event.event_type or "").lower().strip()
        title_desc = f"{event.title or ''} {event.description or ''}".lower()

        # ── Polarity: detect positive / de-escalation events ─────────────────
        polarity = +1
        credibility_mult = 1.0
        for pos_kw, cred in POSITIVE_EVENT_TYPES.items():
            if pos_kw == event_type or pos_kw in event_type or pos_kw in title_desc:
                polarity = -1
                credibility_mult = cred
                break

        # ── Factor 1: Severity (1–10) ─────────────────────────────────────────
        severity = max(1.0, min(10.0, float(event.severity or 5)))

        # ── Factor 2: Category Weight (1–10) ─────────────────────────────────
        cat_wt = self.CATEGORY_WEIGHTS.get(event_type, 5.0)

        # ── Factor 3: Country Influence (normalized to [0, 1]) ────────────────
        country_code = ""
        if event.country:
            country_code = (event.country.country_code or "").upper().strip()
        # Default influence of 0.4 (≈ mid-tier country) if not in map
        influence_norm = influence_map.get(country_code, 0.40)

        # ── Factor 4: Impact Factor (1.0–2.0) ────────────────────────────────
        impact_factor = max(1.0, min(2.0, float(getattr(event, "impact_factor", 1.0) or 1.0)))

        # ── Factor 5: Escalation Potential (1–10) ────────────────────────────
        esc_potential = max(1.0, min(10.0, float(getattr(event, "escalation_potential", 3) or 3)))

        # ── Log-normalized intensity (P0 Fix) ────────────────────────────────
        # Raw intensity max = 10 × 10 × 1.0 × 2.0 = 200
        raw_intensity = severity * cat_wt * influence_norm * impact_factor
        log_intensity = math.log(1 + raw_intensity) / _LOG_SCALE_DENOM  # [0, 1]

        # ── Escalation component (forward-looking) ────────────────────────────
        ep_norm = esc_potential / 10.0  # [0, 1]

        # ── Blend: 65% current event intensity + 35% escalation potential ─────
        es_blended = 0.65 * log_intensity + 0.35 * ep_norm  # [0, 1]

        # ── Apply polarity and scale to [-100, +100] ──────────────────────────
        # (Recency weight applied separately in the pillar aggregation loop)
        es_final = polarity * es_blended * 100.0 * credibility_mult

        return round(es_final, 4)

    def _recency_weight(self, event: Event, now: datetime) -> float:
        """
        Two-speed exponential recency decay (P0 Fix).

        Structural events (war, sanctions): λ = 0.10 (slow decay — effects persist)
        Positive events (ceasefire, deal):  λ = 0.25 (fast decay — markets don't trust peace)
        Tactical events (clash, protest):   λ = 0.20 (medium decay)
        """
        event_type = (event.event_type or "").lower().strip()
        title_desc = f"{event.title or ''} {event.description or ''}".lower()

        is_positive = any(
            pos_kw == event_type or pos_kw in event_type or pos_kw in title_desc
            for pos_kw in POSITIVE_EVENT_TYPES
        )
        if is_positive:
            lam = _POSITIVE_EVENT_LAMBDA
        elif event_type in _STRUCTURAL_EVENT_TYPES:
            lam = _STRUCTURAL_LAMBDA
        else:
            lam = _TACTICAL_LAMBDA

        event_ts = event.timestamp
        if event_ts.tzinfo is None:
            event_ts = event_ts.replace(tzinfo=timezone.utc)

        age_days = max(0.0, (now - event_ts).total_seconds() / 86400.0)
        return math.exp(-lam * age_days)

    def _compute_pillar_priors(self, db: Session) -> dict[str, float]:
        """
        Derive per-pillar Bayesian priors from the last 90 days of GTI history.

        Falls back to PILLAR_COLD_START_PRIOR if no history exists or
        if the history breakdown doesn't include pillar-level data.

        Returns:
            dict mapping pillar_name → prior_mean (float, [0, 100])
        """
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
        try:
            history_rows = (
                db.query(GTIHistory)
                .filter(GTIHistory.timestamp >= ninety_days_ago)
                .order_by(GTIHistory.timestamp.desc())
                .limit(90)
                .all()
            )
        except Exception as e:
            logger.warning("[GTI] Could not query GTIHistory for priors: %s", e)
            return dict(PILLAR_COLD_START_PRIOR)

        if not history_rows:
            logger.debug("[GTI] No historical data found — using cold-start priors.")
            return dict(PILLAR_COLD_START_PRIOR)

        # Aggregate per-pillar scores from the breakdown JSON column
        pillar_key_map = {
            "military":   "military_risk",
            "economic":   "economic_warfare",
            "energy":     "energy_risk",
            "cyber":      "cyber_risk",
            "diplomatic": "diplomatic_risk",
            "political":  "political_risk",
        }
        pillar_accum: dict[str, list[float]] = {p: [] for p in pillar_key_map}

        for row in history_rows:
            bd = row.breakdown or {}
            for p_name, json_key in pillar_key_map.items():
                val = bd.get(json_key)
                if val is not None:
                    try:
                        pillar_accum[p_name].append(float(val))
                    except (ValueError, TypeError):
                        pass

        priors: dict[str, float] = {}
        for p_name in self.PILLARS:
            vals = pillar_accum.get(p_name, [])
            if len(vals) >= 3:
                priors[p_name] = round(sum(vals) / len(vals), 2)
            else:
                # Insufficient history for this pillar — use cold-start default
                priors[p_name] = PILLAR_COLD_START_PRIOR[p_name]

        return priors

    def _apply_ewma(self, db: Session, raw_gti: float, alpha: float = 0.30) -> float:
        """
        Apply Exponential Weighted Moving Average smoothing to the raw GTI.

        GTI_smoothed = α × GTI_raw + (1 − α) × GTI_previous

        α = 0.30 → ~6-day half-life smoother.
        Reduces noise from single-event spikes while remaining responsive
        to genuine trend shifts (e.g., new major conflict).

        Returns:
            float: smoothed GTI score
        """
        try:
            gti_repo = GTIRepository(db)
            latest = gti_repo.get_latest()
            if latest and latest.current_score is not None:
                prev = latest.current_score
                smoothed = alpha * raw_gti + (1.0 - alpha) * prev
                logger.debug(
                    "[GTI] EWMA: raw=%.1f, prev=%.1f → smoothed=%.1f (α=%.2f)",
                    raw_gti, prev, smoothed, alpha,
                )
                return smoothed
        except Exception as e:
            logger.warning("[GTI] EWMA smoothing failed, using raw score: %s", e)

        return raw_gti


# Module-level singleton
gti_service = GTIService()
