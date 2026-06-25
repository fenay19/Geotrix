"""
Zero-Shot Geopolitical Event Classifier
========================================
Uses a local DistilRoBERTa NLI model (via HuggingFace transformers pipeline)
to classify news text into one of 11 geopolitical categories.

Categories:
  war, conflict, sanctions, unrest, economic_policy, supply_chain,
  cyber_attack, energy_security, elections, trade_dispute, sovereignty

Falls back gracefully to keyword rules if the model is not available.
Runs entirely on CPU — no GPU required.
"""

import logging
from typing import Optional

logger = logging.getLogger("geotrade.nlp.zero_shot_classifier")

# ── 11 canonical geopolitical categories ──────────────────────────────────────
GEOPOLITICAL_CATEGORIES = [
    "war",
    "conflict",
    "sanctions",
    "unrest",
    "economic_policy",
    "supply_chain",
    "cyber_attack",
    "energy_security",
    "elections",
    "trade_dispute",
    "sovereignty",
]

# ── Human-readable label descriptions fed to the NLI model ───────────────────
_CATEGORY_HYPOTHESES = {
    "war":              "This is about armed warfare, military operations, or armed conflict between nations.",
    "conflict":         "This is about a regional conflict, skirmish, or military tensions between groups.",
    "sanctions":        "This is about economic sanctions, asset freezes, trade embargoes or export bans.",
    "unrest":           "This is about civil unrest, protests, riots, coups, or political instability.",
    "economic_policy":  "This is about monetary policy, central bank decisions, fiscal policy, or budget changes.",
    "supply_chain":     "This is about supply chain disruptions, logistics failures, or critical goods shortages.",
    "cyber_attack":     "This is about a cyberattack, ransomware, hacking, or digital infrastructure breach.",
    "energy_security":  "This is about oil, gas, energy supply, pipeline security, or energy market disruption.",
    "elections":        "This is about national elections, electoral fraud, political transitions, or referendums.",
    "trade_dispute":    "This is about trade disputes, tariffs, import/export restrictions, or trade wars.",
    "sovereignty":      "This is about diplomatic relations, peace talks, territorial disputes, summit negotiations, sovereignty, or annexation.",
}

# ── Keyword fallback rules ─────────────────────────────────────────────────────
# Note: 'sovereignty' is the proxy category for all diplomatic/peace/sovereignty
# events. It maps to event_type="diplomatic" in classify_to_event_type().
_KEYWORD_RULES = {
    "war":              ["war", "warfare", "military operation", "airstrike", "combat", "nuclear", "troops invade"],
    "conflict":         ["conflict", "clash", "skirmish", "battle", "troops", "armed group", "militia"],
    "sanctions":        ["sanction", "embargo", "asset freeze", "export ban", "export control", "blacklist"],
    "unrest":           ["protest", "riot", "uprising", "coup", "demonstration", "civil unrest", "rebellion"],
    "economic_policy":  ["interest rate", "inflation", "gdp", "central bank", "monetary policy", "recession", "fiscal"],
    "supply_chain":     ["supply chain", "semiconductor", "rare earth", "chip shortage", "logistics", "shortage"],
    "cyber_attack":     ["cyberattack", "ransomware", "hacking", "ddos", "malware", "data breach", "espionage"],
    "energy_security":  ["oil", "natural gas", "opec", "lng", "pipeline", "energy security", "petroleum", "diesel"],
    "elections":        ["election", "vote", "referendum", "ballot", "electoral"],
    "trade_dispute":    ["tariff", "trade war", "import duty", "trade restriction", "wto", "retaliatory"],
    # Expanded to capture all diplomatic/peace-negotiation signals
    "sovereignty":      [
        "territorial", "annexation", "separatist", "secession", "sovereignty", "disputed territory",
        "peace talks", "peace negotiations", "peace deal", "ceasefire talks",
        "diplomatic summit", "summit meeting", "bilateral talks", "multilateral talks",
        "normalization", "treaty", "diplomatic relations", "ambassador", "expulsion",
        "diplomatic", "diplomacy", "foreign minister", "secretary of state",
    ],
}


class ZeroShotClassifier:
    """
    Classifies news text into one of 11 geopolitical event categories.

    Primary: HuggingFace zero-shot NLI pipeline (DistilRoBERTa / BART-MNLI).
    Fallback: Fast keyword rule matching.

    Usage:
        classifier = ZeroShotClassifier()
        result = classifier.classify("Russia launched missiles at Kyiv overnight.")
        # → {"category": "war", "confidence": 0.94, "source": "zero-shot-nli"}
    """

    _pipeline = None
    _model_loaded = False
    _model_failed = False

    # Model name: lightweight cross-encoder NLI model (~260MB, CPU-friendly)
    MODEL_NAME = "cross-encoder/nli-distilroberta-base"

    def __init__(self):
        pass

    def _load_model(self):
        """Lazy-loads the NLI pipeline on first call."""
        if self._model_loaded or self._model_failed:
            return
        try:
            from transformers import pipeline
            logger.info("Loading zero-shot NLI model: %s (CPU)...", self.MODEL_NAME)
            ZeroShotClassifier._pipeline = pipeline(
                "zero-shot-classification",
                model=self.MODEL_NAME,
                device=-1,          # -1 = CPU
                multi_label=False,
            )
            ZeroShotClassifier._model_loaded = True
            logger.info("Zero-shot NLI model loaded successfully.")
        except Exception as exc:
            logger.warning(
                "Failed to load zero-shot NLI model (%s): %s. "
                "Falling back to keyword rules.",
                self.MODEL_NAME, exc
            )
            ZeroShotClassifier._model_failed = True

    def classify(self, text: str) -> dict:
        """
        Classifies text into one of 11 geopolitical event categories.

        Pre-classification step: if 2+ high-signal diplomatic/sovereignty
        keywords are matched, return 'sovereignty' immediately without
        running the NLI. This prevents the NLI from overriding unambiguous
        diplomatic texts with spurious 'economic_policy' or 'conflict' labels.

        Returns:
            {
                "category":   str,    # one of GEOPOLITICAL_CATEGORIES
                "confidence": float,  # 0.0 – 1.0
                "source":     str,    # "zero-shot-nli" | "keyword-rules" | "keyword-precheck"
                "all_scores": dict,   # category → score (only from NLI)
            }
        """
        if not text or not text.strip():
            return self._keyword_classify(text or "")

        # ── Pre-classification: catch high-confidence diplomatic texts ──────
        # These are unambiguous diplomatic signals that NLI often mis-labels.
        _DIPLOMATIC_PRECHECK = [
            "peace talks", "peace negotiations", "peace deal",
            "diplomatic summit", "summit meeting", "bilateral talks",
            "ceasefire talks", "normalization talks", "diplomatic relations",
            "sovereignty talks", "territorial talks", "diplomatic talks",
            "foreign ministers met", "secretary of state met",
        ]
        lower_text = text.lower()
        diplomatic_hits = sum(1 for kw in _DIPLOMATIC_PRECHECK if kw in lower_text)
        if diplomatic_hits >= 1:
            # One strong multi-word phrase is sufficient to override NLI
            logger.debug("[ZSC] Diplomatic pre-check matched (%d hits) — returning sovereignty", diplomatic_hits)
            return {
                "category":   "sovereignty",
                "confidence": min(0.50 + 0.10 * diplomatic_hits, 0.90),
                "source":     "keyword-precheck",
                "all_scores": {},
            }

        self._load_model()

        if self._model_loaded and self._pipeline is not None:
            return self._nli_classify(text)

        return self._keyword_classify(text)

    def _nli_classify(self, text: str) -> dict:
        """Runs the HuggingFace zero-shot NLI pipeline."""
        try:
            hypotheses = [_CATEGORY_HYPOTHESES[cat] for cat in GEOPOLITICAL_CATEGORIES]
            result = self._pipeline(
                text[:512],         # truncate to model max length
                candidate_labels=hypotheses,
                hypothesis_template="{}",
            )
            # Map hypotheses back to category keys
            hyp_to_cat = {v: k for k, v in _CATEGORY_HYPOTHESES.items()}
            scores = {
                hyp_to_cat[label]: round(score, 4)
                for label, score in zip(result["labels"], result["scores"])
                if label in hyp_to_cat
            }
            best_hyp   = result["labels"][0]
            best_cat   = hyp_to_cat.get(best_hyp, "conflict")
            confidence = round(result["scores"][0], 4)
            return {
                "category":   best_cat,
                "confidence": confidence,
                "source":     "zero-shot-nli",
                "all_scores": scores,
            }
        except Exception as exc:
            logger.warning("NLI classification failed: %s. Using keyword fallback.", exc)
            return self._keyword_classify(text)

    def _keyword_classify(self, text: str) -> dict:
        """Keyword-based fallback classifier."""
        lower = text.lower()
        scores = {}
        for cat, keywords in _KEYWORD_RULES.items():
            scores[cat] = sum(1 for kw in keywords if kw in lower)

        best_cat = max(scores, key=scores.get)
        best_score = scores[best_cat]

        if best_score == 0:
            return {
                "category":   "conflict",
                "confidence": 0.30,
                "source":     "keyword-rules",
                "all_scores": scores,
            }

        total = sum(scores.values()) or 1
        confidence = round(best_score / total, 4)
        return {
            "category":   best_cat,
            "confidence": confidence,
            "source":     "keyword-rules",
            "all_scores": scores,
        }

    def classify_to_event_type(self, text: str) -> str:
        """
        Maps the 11 internal NLI categories to the 9 event_type values used
        in the DB schema and GTI pillar routing:
          war, conflict, sanctions, economic, cyber, energy, diplomatic, policy, unrest

        Mapping rationale:
          - cyber_attack    → "cyber"      (GTI cyber pillar)
          - energy_security → "energy"     (GTI energy pillar)
          - sovereignty     → "diplomatic" (GTI diplomatic pillar)
          - supply_chain    → "economic"   (supply chain disruptions = economic impact)
          - trade_dispute   → "economic"   (trade disputes = economic warfare)
          - economic_policy → "economic"
          - elections       → "policy"     (GTI political pillar)
        """
        result  = self.classify(text)
        cat     = result["category"]
        mapping = {
            "war":              "war",
            "conflict":         "conflict",
            "sanctions":        "sanctions",
            "unrest":           "unrest",
            "economic_policy":  "economic",
            "supply_chain":     "economic",
            "cyber_attack":     "cyber",        # FIX: was "conflict" — now routes to GTI cyber pillar
            "energy_security":  "energy",       # FIX: was "economic" — now routes to GTI energy pillar
            "elections":        "policy",
            "trade_dispute":    "economic",
            "sovereignty":      "diplomatic",   # FIX: was "conflict" — now routes to GTI diplomatic pillar
        }
        return mapping.get(cat, "policy")


# Singleton instance
zero_shot_classifier = ZeroShotClassifier()
