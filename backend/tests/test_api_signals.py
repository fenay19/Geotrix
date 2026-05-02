"""
Integration tests for the /api/v1/signals routes using FastAPI TestClient.
Uses in-memory SQLite + seeded test data; no external APIs are called.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_db
from app.database.base import Base
from app.models.market_model import Market
from app.models.trading_signal_model import TradingSignal

# ── Test DB setup ─────────────────────────────────────────────────────────────
# StaticPool ensures all operations share ONE connection → same in-memory DB
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_market(db_session):
    """Seeds a market and a signal into the test DB."""
    market = Market(symbol="SPY", price=450.0, category="Index")
    db_session.add(market)
    db_session.commit()
    db_session.refresh(market)
    return market


@pytest.fixture
def seeded_signal(db_session, seeded_market):
    signal = TradingSignal(
        market_id=seeded_market.id,
        signal_type="BUY",
        confidence=0.80,
        reasoning="Test",
        tags=["test"],
        risk_factors=["none"],
    )
    db_session.add(signal)
    db_session.commit()
    db_session.refresh(signal)
    return signal


# ── GET /api/v1/signals/ ──────────────────────────────────────────────────────

class TestGetSignals:
    def test_returns_empty_list_when_no_signals(self, client):
        resp = client.get("/api/v1/signals/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_signals_after_seed(self, client, seeded_signal):
        resp = client.get("/api/v1/signals/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["signal_type"] == "BUY"
        assert data[0]["confidence"] == 0.80

    def test_pagination_skip_returns_empty(self, client, seeded_signal):
        resp = client.get("/api/v1/signals/?skip=100")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_pagination_limit(self, client, db_session, seeded_market):
        # Add 3 signals
        for i in range(3):
            db_session.add(TradingSignal(
                market_id=seeded_market.id,
                signal_type="HOLD",
                confidence=0.5,
                reasoning=f"Signal {i}",
            ))
        db_session.commit()
        resp = client.get("/api/v1/signals/?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ── GET /api/v1/signals/{signal_id} ──────────────────────────────────────────

class TestGetSignalById:
    def test_returns_signal_by_id(self, client, seeded_signal):
        resp = client.get(f"/api/v1/signals/{seeded_signal.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == seeded_signal.id

    def test_returns_404_for_nonexistent_id(self, client):
        resp = client.get("/api/v1/signals/99999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ── GET /api/v1/signals/market/{market_id} ───────────────────────────────────

class TestGetSignalsByMarket:
    def test_returns_signals_for_market(self, client, seeded_signal, seeded_market):
        resp = client.get(f"/api/v1/signals/market/{seeded_market.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["market_id"] == seeded_market.id

    def test_returns_empty_for_market_with_no_signals(self, client, db_session):
        market2 = Market(symbol="GOLD", price=2000.0, category="Commodity")
        db_session.add(market2)
        db_session.commit()
        db_session.refresh(market2)
        resp = client.get(f"/api/v1/signals/market/{market2.id}")
        assert resp.status_code == 200
        assert resp.json() == []


# ── GET /api/v1/signals/market/{market_id}/latest ────────────────────────────

class TestGetLatestSignal:
    def test_returns_latest_signal(self, client, seeded_signal, seeded_market):
        resp = client.get(f"/api/v1/signals/market/{seeded_market.id}/latest")
        assert resp.status_code == 200
        assert resp.json()["id"] == seeded_signal.id

    def test_returns_404_when_no_signals(self, client, db_session):
        market2 = Market(symbol="BTC", price=60000.0, category="Crypto")
        db_session.add(market2)
        db_session.commit()
        db_session.refresh(market2)
        resp = client.get(f"/api/v1/signals/market/{market2.id}/latest")
        assert resp.status_code == 404


# ── POST /api/v1/signals/ ─────────────────────────────────────────────────────

class TestCreateSignal:
    def test_creates_signal_successfully(self, client, seeded_market):
        payload = {
            "market_id": seeded_market.id,
            "signal_type": "SELL",
            "confidence": 0.72,
            "uncertainty": 0.28,
            "reasoning": "Geopolitical risk is elevated.",
        }
        resp = client.post("/api/v1/signals/", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["signal_type"] == "SELL"
        assert data["confidence"] == 0.72
        assert "id" in data

    def test_rejects_invalid_signal_type(self, client, seeded_market):
        payload = {
            "market_id": seeded_market.id,
            "signal_type": "STRONG_BUY",  # invalid
            "confidence": 0.9,
        }
        resp = client.post("/api/v1/signals/", json=payload)
        assert resp.status_code == 422

    def test_rejects_confidence_out_of_range(self, client, seeded_market):
        payload = {
            "market_id": seeded_market.id,
            "signal_type": "BUY",
            "confidence": 1.5,  # > 1.0
        }
        resp = client.post("/api/v1/signals/", json=payload)
        assert resp.status_code == 422


# ── POST /api/v1/signals/generate/{market_id} ───────────────────────────────

class TestGenerateSignal:
    def test_generate_signal_unauthenticated(self, client, seeded_market):
        resp = client.post(f"/api/v1/signals/generate/{seeded_market.id}")
        assert resp.status_code == 401
        assert "not authenticated" in resp.json()["detail"].lower()

    def test_generate_signal_authenticated(self, client, seeded_market, db_session):
        # Override get_current_user to simulate authenticated user
        from app.dependencies import get_current_user
        from app.models.user_model import User
        
        mock_user = User(id=1, email="test@example.com", is_active=True, is_superuser=False)
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            resp = client.post(f"/api/v1/signals/generate/{seeded_market.id}")
            assert resp.status_code == 201
            data = resp.json()
            assert data["market_id"] == seeded_market.id
            assert "signal_type" in data
            assert data["signal_strength"] is not None
        finally:
            # Make sure we clean up overrides cleanly, restore client db override if any
            if get_current_user in app.dependency_overrides:
                del app.dependency_overrides[get_current_user]
