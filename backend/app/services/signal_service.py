import logging
import math
from typing import Optional
import yfinance as yf
from sqlalchemy.orm import Session
from ..repositories.signal_repo import SignalRepository
from ..repositories.market_repo import MarketRepository
from ..repositories.risk_repo import GTIRepository, CountryRiskRepository
from ..repositories.event_repo import EventRepository
from ..schemas.signal_schema import SignalCreate
from ..ai.chatbot.chat_engine import get_chat_engine
from ..config import settings

logger = logging.getLogger("geotrade.services.signal")

# ML predictor is imported lazily inside the try/except block at runtime
# to allow the service to start even if ML models are not trained yet.
try:
    from ..ml.inference.ml_predictor import ml_predictor as _ml_predictor
    _ML_AVAILABLE = True
except Exception:
    _ml_predictor = None  # type: ignore
    _ML_AVAILABLE = False



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
        1. PRIMARY: XGBoost ML Model if confidence >= settings.ML_CONFIDENCE_THRESHOLD (0.80)
        2. BACKUP: OpenAI reasoning with live GTI + country risk context.
        3. FALLBACK: Rule-based heuristic model if AI is unavailable.
        """
        # Gather all necessary context
        market = MarketRepository(db).get_by_id(market_id)
        if not market:
            return None

        # ── 1. Try ML XGBoost prediction first ──────────────────────────────
        ml_result = None
        if _ML_AVAILABLE and _ml_predictor is not None:
            try:
                ml_result = _ml_predictor.predict(db, market_id)
            except Exception as e:
                logger.warning("ML prediction failed for market %d: %s", market_id, e)


        # Get RAF and adjust threshold
        raf = self.get_raf(market.symbol)
        adjusted_threshold = round(settings.ML_CONFIDENCE_THRESHOLD * raf, 4)
        logger.info("[%s] Base Threshold: %.2f | RAF: %.2f | Adjusted Threshold: %.2f", 
                    market.symbol, settings.ML_CONFIDENCE_THRESHOLD, raf, adjusted_threshold)

        if ml_result and ml_result["confidence"] >= adjusted_threshold:
            logger.info("Using ML signal for market %s with confidence %.2f (threshold %.2f)", 
                        market.symbol, ml_result["confidence"], adjusted_threshold)
            
            # Calculate GARCH-regime aware signal strength
            garch_sigma = ml_result.get("garch_sigma_1d", 0.02)
            vix = ml_result.get("vix", 15.0)
            sig_strength = self.calculate_signal_strength(
                confidence=ml_result["confidence"],
                garch_sigma=garch_sigma,
                vix=vix,
                threshold=adjusted_threshold
            )
            
            # Map volatility label
            pred_vol = ml_result["predicted_volatility"]
            if pred_vol < 0.12:
                vol_label = "Low"
            elif pred_vol >= 0.25:
                vol_label = "High"
            else:
                vol_label = "Medium"

            # Derive target and stop loss from drift and volatility
            price = market.price or 100.0
            # Annualized expected drift: expected 5-day return = drift * 5 / 252
            fwd_return = ml_result["predicted_drift"] * 5 / 252
            
            # 5-day volatility = volatility * sqrt(5 / 252)
            vol_5d = pred_vol * math.sqrt(5 / 252)
            
            if ml_result["predicted_signal"] == "BUY":
                target_price = price * (1 + fwd_return)
                stop_loss = price * (1 - 1.5 * vol_5d)
                # Ensure logical ordering
                if target_price <= price:
                    target_price = price * (1 + 1.5 * vol_5d)
                if stop_loss >= price:
                    stop_loss = price * (1 - 1.5 * vol_5d)
            elif ml_result["predicted_signal"] == "SELL":
                target_price = price * (1 + fwd_return)
                stop_loss = price * (1 + 1.5 * vol_5d)
                # Ensure logical ordering
                if target_price >= price:
                    target_price = price * (1 - 1.5 * vol_5d)
                if stop_loss <= price:
                    stop_loss = price * (1 + 1.5 * vol_5d)
            else:  # HOLD
                target_price = price * 1.04
                stop_loss = price * 0.97

            # Ensure non-negative bounds
            stop_loss = max(stop_loss, 0.01)
            target_price = max(target_price, 0.01)

            # Risk reward ratio
            rr = round(abs(target_price - price) / abs(price - stop_loss), 2) if price != stop_loss else 1.0

            # Estimate strength from confidence
            if ml_result["predicted_signal"] == "BUY":
                bullish = ml_result["confidence"]
                bearish = round(1 - bullish, 2)
            elif ml_result["predicted_signal"] == "SELL":
                bearish = ml_result["confidence"]
                bullish = round(1 - bearish, 2)
            else:
                bullish = 0.5
                bearish = 0.5

            signal_in = SignalCreate(
                market_id=market_id,
                signal_type=ml_result["predicted_signal"],
                confidence=ml_result["confidence"],
                uncertainty=round(1 - ml_result["confidence"], 2),
                bullish_strength=bullish,
                bearish_strength=bearish,
                signal_strength=sig_strength,
                entry_price=price,
                stop_loss=round(stop_loss, 2),
                target_price=round(target_price, 2),
                risk_reward_ratio=rr,
                volatility_level=vol_label,
                reasoning=(
                    f"Signal generated by the Stage 2 XGBoost model ({ml_result['source']}) with "
                    f"{ml_result['confidence']:.1%} confidence. Annualized expected drift: {ml_result['predicted_drift']:.1%}, "
                    f"expected volatility: {ml_result['predicted_volatility']:.1%}. "
                    f"Fundamental RAF: {raf:.2f}. Volatility-adjusted signal strength: {sig_strength:.3f}."
                ),
                risk_factors=[
                    "XGBoost model projection error",
                    "Volatility levels exceeding simulation boundaries",
                    "Unexpected geopolitical shocks not captured by historical technicals"
                ],
                tags=["ml-generated", ml_result["source"]],
            )
            return SignalRepository(db).create(signal_in)

        # ── 2. LLM / Heuristic Fallbacks ───────────────────────────────────
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
        sig_strength = self.calculate_signal_strength(
            confidence=confidence,
            garch_sigma=0.02,   # conservative default for rule-based path
            vix=15.0,
            threshold=settings.ML_CONFIDENCE_THRESHOLD,
        )

        return SignalCreate(
            market_id=market.id,
            signal_type=signal_type,
            confidence=confidence,
            uncertainty=round(1 - confidence, 2),
            bullish_strength=bullish,
            bearish_strength=bearish,
            signal_strength=sig_strength,
            entry_price=price,
            stop_loss=stop,
            target_price=target,
            risk_reward_ratio=rr,
            volatility_level=volatility,
            reasoning=reasoning,
            risk_factors=risk_factors,
            tags=["rule-based-fallback"],
        )

    def get_raf(self, symbol: str) -> float:
        """
        Retrieves company fundamental metrics from yfinance and calculates
        the Fundamental Risk Adjustment Factor (RAF).
        Clamps return to [0.5, 1.5]. Defaults to 1.0 on failure/inapplicability.
        """
        try:
            # Map symbol to correct ticker mapping
            ticker_map = {
                "SPY": "SPY",
                "GC=F": "GC=F",
                "BZ=F": "BZ=F",
                "BTCUSD": "BTC-USD",
                "BTC-USD": "BTC-USD",
            }
            mapped_ticker = ticker_map.get(symbol, symbol)
            ticker = yf.Ticker(mapped_ticker)
            info = ticker.info
            
            # yfinance info returns None or empty dict if not found
            if not info or not isinstance(info, dict):
                return 1.0
                
            roe = info.get("returnOnEquity")
            de = info.get("debtToEquity")
            roa = info.get("returnOnAssets")
            
            if roe is None and de is None and roa is None:
                # Likely a commodity or crypto with no company balance sheet
                return 1.0
                
            roe = roe or 0.10
            de = (de or 100.0) / 100.0
            roa = roa or 0.05
            
            # Higher ROE/ROA and lower D/E = lower risk adjustment
            raf = 1.0 - (roe * 0.3) - (roa * 0.2) + (de * 0.1)
            return float(max(0.5, min(1.5, raf)))
        except Exception as e:
            logger.debug("Failed to calculate RAF for symbol %s: %s. Using default 1.0.", symbol, e)
            return 1.0

    def calculate_signal_strength(
        self, confidence: float, garch_sigma: float, vix: float, threshold: float
    ) -> float:
        """
        Calculates a continuous signal strength score (0.0 to 1.0)
        by combining model confidence, GARCH conditional volatility, and VIX regime.
        """
        vol_penalty = 1.0 / (1.0 + garch_sigma * 10.0)
        raw_strength = (confidence - threshold) / (1.0 - threshold + 1e-6)
        return float(round(max(0.0, min(1.0, raw_strength * vol_penalty)), 3))


signal_service = SignalService()
