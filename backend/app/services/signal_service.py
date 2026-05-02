import logging
from typing import Optional
from sqlalchemy.orm import Session
from ..repositories.signal_repo import SignalRepository
from ..repositories.market_repo import MarketRepository
from ..repositories.risk_repo import GTIRepository, CountryRiskRepository
from ..repositories.event_repo import EventRepository
from ..schemas.signal_schema import SignalCreate
from ..ai.chatbot.chat_engine import get_chat_engine
from ..config import settings

logger = logging.getLogger("geotrade.services.signal")


class SignalService:

    def get_signals(self, db: Session, skip: int = 0, limit: int = 50):
        repo = SignalRepository(db)
        return repo.get_all(skip=skip, limit=limit)

    def get_signal(self, db: Session, signal_id: int):
        repo = SignalRepository(db)
        return repo.get_by_id(signal_id)

    def get_signals_by_market(self, db: Session, market_id: int):
        repo = SignalRepository(db)
        return repo.get_by_market(market_id)

    def get_latest_signal(self, db: Session, market_id: int):
        repo = SignalRepository(db)
        return repo.get_latest(market_id)

    def create_signal(self, db: Session, signal_in: SignalCreate):
        repo = SignalRepository(db)
        return repo.create(signal_in)

    # ── Hybrid AI Signal Generation ──────────────────────────────────────────

    def auto_generate_signal(self, db: Session, market_id: int):
        """
        Generates a trading signal using:
        1. PRIMARY: OpenAI reasoning with live GTI + country risk context.
        2. FALLBACK: Rule-based heuristic model if AI is unavailable.
        """
        # Gather all necessary context
        market = MarketRepository(db).get_by_id(market_id)
        if not market:
            return None

        gti = GTIRepository(db).get_latest()
        gti_score = gti.current_score if gti else 50.0

        country_risk = None
        top_events = []
        if market.country_id:
            country_risk = CountryRiskRepository(db).get_by_id(market.country_id)
            top_events = EventRepository(db).get_top_risks_by_country(market.country_id, limit=3)

        # Try AI first
        ai_result = self._openai_generate_signal(market, gti_score, country_risk, top_events)

        if ai_result:
            signal_in = SignalCreate(
                market_id=market_id,
                signal_type=ai_result["signal_type"],
                confidence=ai_result["confidence"],
                uncertainty=ai_result.get("uncertainty"),
                bullish_strength=ai_result.get("bullish_strength"),
                bearish_strength=ai_result.get("bearish_strength"),
                entry_price=market.price,
                stop_loss=ai_result.get("stop_loss"),
                target_price=ai_result.get("target_price"),
                risk_reward_ratio=ai_result.get("risk_reward_ratio"),
                volatility_level=ai_result.get("volatility_level"),
                reasoning=ai_result.get("reasoning"),
                risk_factors=ai_result.get("risk_factors", []),
                tags=["ai-generated"],
            )
        else:
            # Rule-based fallback
            signal_in = self._rule_based_signal(market, gti_score, country_risk)

        return SignalRepository(db).create(signal_in)

    def _openai_generate_signal(self, market, gti_score, country_risk, top_events) -> Optional[dict]:
        """Calls OpenAI to generate a structured trading signal. Returns None on failure."""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            return None

        country_name = country_risk.country_name if country_risk else "Global"
        country_score = country_risk.risk_score if country_risk else "N/A"
        event_lines = "\n".join(
            f"- {e.title} (Severity {e.severity}/10)" for e in top_events
        ) if top_events else "None"

        prompt = f"""You are a quantitative analyst specializing in geopolitical risk.

Analyze the following and generate a trading signal in JSON format.

Asset: {market.symbol} ({market.category})
Current Price: {market.price}
Global Tension Index (GTI): {gti_score}/100
Country (if applicable): {country_name} — Risk Score: {country_score}/100
Top Active Risks:
{event_lines}

Return ONLY a valid JSON object with these exact keys:
{{
  "signal_type": "BUY" | "SELL" | "HOLD",
  "confidence": <float 0-1>,
  "uncertainty": <float 0-1>,
  "bullish_strength": <float 0-1>,
  "bearish_strength": <float 0-1>,
  "stop_loss": <float>,
  "target_price": <float>,
  "risk_reward_ratio": <float>,
  "volatility_level": "Low" | "Medium" | "High",
  "reasoning": "<one paragraph explanation>",
  "risk_factors": ["<risk 1>", "<risk 2>", "<risk 3>"]
}}"""

        try:
            engine = get_chat_engine(api_key)
            result = engine.ask_json(
                prompt,
                temperature=0.4,
                max_tokens=600,
            )
            return result  # already parsed dict or None
        except Exception as e:
            logger.warning("AI signal generation failed, using fallback: %s", e)
            return None

    def _rule_based_signal(self, market, gti_score: float, country_risk) -> SignalCreate:
        """
        Fallback: generates a signal based on deterministic rules.
        - GTI > 70 → SELL (risk-off sentiment, buy safe havens like Gold)
        - GTI < 40 → BUY (calm markets, buy growth assets)
        - Otherwise → HOLD
        """
        price = market.price or 100.0
        country_score = country_risk.risk_score if country_risk else 50.0

        # Combined score
        combined = (gti_score * 0.6) + (country_score * 0.4)

        if combined > 65:
            signal_type = "SELL"
            confidence = round(min(0.9, combined / 100 + 0.1), 2)
            bullish = round(1 - confidence, 2)
            bearish = confidence
            target = round(price * 0.93, 2)  # 7% downside target
            stop = round(price * 1.04, 2)    # 4% stop above entry
            reasoning = (
                f"High geopolitical risk detected (Combined Score: {combined:.1f}). "
                "Risk-off sentiment favors exiting long positions."
            )
            risk_factors = ["Escalating geopolitical tensions", "High GTI reading", "Market uncertainty"]
            volatility = "High"
        elif combined < 38:
            signal_type = "BUY"
            confidence = round(min(0.85, (100 - combined) / 100 + 0.1), 2)
            bullish = confidence
            bearish = round(1 - confidence, 2)
            target = round(price * 1.08, 2)  # 8% upside target
            stop = round(price * 0.96, 2)    # 4% stop below entry
            reasoning = (
                f"Low geopolitical risk (Combined Score: {combined:.1f}). "
                "Risk-on environment supports long positions."
            )
            risk_factors = ["Monitor for sudden escalations", "Liquidity risk"]
            volatility = "Low"
        else:
            signal_type = "HOLD"
            confidence = 0.55
            bullish = 0.50
            bearish = 0.50
            target = round(price * 1.04, 2)
            stop = round(price * 0.97, 2)
            reasoning = (
                f"Geopolitical risk is moderate (Combined Score: {combined:.1f}). "
                "No clear directional bias — hold current positions."
            )
            risk_factors = ["Uncertain geopolitical trajectory", "Mixed market signals"]
            volatility = "Medium"

        rr = round(abs(target - price) / abs(price - stop), 2) if price != stop else 1.0

        return SignalCreate(
            market_id=market.id,
            signal_type=signal_type,
            confidence=confidence,
            uncertainty=round(1 - confidence, 2),
            bullish_strength=bullish,
            bearish_strength=bearish,
            entry_price=price,
            stop_loss=stop,
            target_price=target,
            risk_reward_ratio=rr,
            volatility_level=volatility,
            reasoning=reasoning,
            risk_factors=risk_factors,
            tags=["rule-based-fallback"],
        )


signal_service = SignalService()
