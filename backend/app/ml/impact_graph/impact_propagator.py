"""
Impact Graph Propagator
=======================
Propagates a geopolitical event's impact across all tracked asset categories
using the sector-sensitivity matrix, scaled by NLP-extracted severity.

The propagation algorithm:
  1. Start with the triggering event (event_type, severity, country)
  2. Look up sensitivity coefficients for all asset categories
  3. Scale by severity_norm (0-1) and escalation_potential modifier
  4. Apply a country-risk amplifier (risk_score / 50.0)
  5. Return a sorted list of ImpactNode objects

Each ImpactNode represents one asset's predicted impact:
  - impact_score:  signed float [-1, +1]  (direction + magnitude)
  - signal_bias:   "BUY" | "SELL" | "NEUTRAL"  (trade direction)
  - confidence:    float [0, 1]  (how certain we are)

Design: static coefficients scaled by NLP severity (approved approach).
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from .sector_sensitivity import (
    get_all_sensitivities,
    get_sensitivity,
    SENSITIVITY_MATRIX,
)

logger = logging.getLogger("geotrade.ml.impact_graph.propagator")

# Minimum |impact_score| to include in output (filter near-zero noise)
MIN_IMPACT_THRESHOLD = 0.05


@dataclass
class ImpactNode:
    """Represents an asset's predicted price impact from a geopolitical event."""
    asset_category:  str
    impact_score:    float   # signed [-1, +1]: positive = price expected up
    signal_bias:     str     # "BUY" | "SELL" | "NEUTRAL"
    confidence:      float   # 0-1
    sensitivity:     float   # raw sensitivity coefficient
    severity_norm:   float   # normalized severity used


class ImpactPropagator:
    """
    Propagates geopolitical event impacts across all asset categories.

    Usage:
        propagator = ImpactPropagator()
        nodes = propagator.propagate(
            event_type="war",
            severity=8.0,
            escalation_potential=4.0,
            country_risk_score=75.0,
            nlp_confidence=0.92,
        )
        for node in nodes:
            print(node.asset_category, node.impact_score, node.signal_bias)
    """

    def propagate(
        self,
        event_type:           str,
        severity:             float,
        escalation_potential: float   = 3.0,
        country_risk_score:   float   = 50.0,
        nlp_confidence:       float   = 0.8,
        min_threshold:        float   = MIN_IMPACT_THRESHOLD,
    ) -> List[ImpactNode]:
        """
        Computes ImpactNode for all asset categories.

        Args:
            event_type:            One of: war, conflict, sanctions, unrest, economic, policy
            severity:              Event severity 1-10
            escalation_potential:  1-5 escalation score
            country_risk_score:    Affected country's risk score 0-100
            nlp_confidence:        NLI classification confidence 0-1
            min_threshold:         Minimum |impact| to include in output

        Returns:
            List of ImpactNode sorted by |impact_score| descending.
        """
        severity_norm  = float(min(max(severity / 10.0, 0.0), 1.0))
        esc_multiplier = float(1.0 + (escalation_potential - 1.0) * 0.15)  # 1.0 - 1.6x
        risk_amplifier = float(country_risk_score / 50.0)                   # 0.0 - 2.0x
        # Clamp amplifier so low-risk countries don't zero out everything
        risk_amplifier = min(max(risk_amplifier, 0.4), 2.0)

        sensitivities = get_all_sensitivities(event_type)

        nodes = []
        for asset_cat, sens in sensitivities.items():
            # Core impact formula
            raw_impact = sens * severity_norm * esc_multiplier * risk_amplifier

            # Confidence-weight: low NLP confidence → attenuate impact
            impact_score = raw_impact * nlp_confidence

            # Clamp to [-1, +1]
            impact_score = float(min(max(impact_score, -1.0), 1.0))

            if abs(impact_score) < min_threshold:
                continue  # too weak to signal

            # Derive signal bias
            if impact_score > 0.15:
                signal_bias = "BUY"
            elif impact_score < -0.15:
                signal_bias = "SELL"
            else:
                signal_bias = "NEUTRAL"

            # Confidence = NLP confidence × |sensitivity| (high-sens assets → more confident)
            confidence = float(min(nlp_confidence * abs(sens), 1.0))

            nodes.append(ImpactNode(
                asset_category = asset_cat,
                impact_score   = round(impact_score, 4),
                signal_bias    = signal_bias,
                confidence     = round(confidence, 4),
                sensitivity    = round(sens, 4),
                severity_norm  = round(severity_norm, 4),
            ))

        # Sort: highest |impact| first
        nodes.sort(key=lambda n: abs(n.impact_score), reverse=True)

        logger.debug(
            "Impact propagation: event=%s severity=%.1f -> %d asset nodes",
            event_type, severity, len(nodes),
        )
        return nodes

    def get_asset_impact(
        self,
        event_type:         str,
        severity:           float,
        asset_category:     str,
        escalation_potential: float = 3.0,
        country_risk_score:   float = 50.0,
        nlp_confidence:       float = 0.8,
    ) -> Optional[ImpactNode]:
        """
        Returns the ImpactNode for a single specific asset category.
        Returns None if the impact is below the minimum threshold.
        """
        nodes = self.propagate(
            event_type           = event_type,
            severity             = severity,
            escalation_potential = escalation_potential,
            country_risk_score   = country_risk_score,
            nlp_confidence       = nlp_confidence,
            min_threshold        = 0.0,  # include all for single-asset lookup
        )
        for node in nodes:
            if node.asset_category == asset_category:
                return node
        return None

    def to_signal_bias_map(
        self,
        event_type:           str,
        severity:             float,
        escalation_potential: float = 3.0,
        country_risk_score:   float = 50.0,
        nlp_confidence:       float = 0.8,
    ) -> dict:
        """
        Returns a dict mapping asset_category → signal_bias string.
        Convenient for downstream signal routing.
        """
        nodes = self.propagate(
            event_type           = event_type,
            severity             = severity,
            escalation_potential = escalation_potential,
            country_risk_score   = country_risk_score,
            nlp_confidence       = nlp_confidence,
        )
        return {n.asset_category: n.signal_bias for n in nodes}


# Singleton instance
impact_propagator = ImpactPropagator()
