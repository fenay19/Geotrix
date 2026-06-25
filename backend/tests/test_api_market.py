import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.dependencies import get_db
from app.database.base import Base
from app.models.market_model import Market, MarketHistory
from app.models.country_risk_model import CountryRisk

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
def seeded_data(db_session):
    # Seed India CountryRisk
    india = CountryRisk(
        id=1,
        country_code="IN",
        country_name="India",
        risk_score=45.0,
        color_code="Yellow",
        sector_exposure={"Energy": 15}
    )
    db_session.add(india)
    
    # Seed fallback assets
    spy = Market(id=1, symbol="SPY", name="S&P 500", price=500.0, category="Index", is_global=True)
    gold = Market(id=2, symbol="GC=F", name="Gold", price=2000.0, category="Commodity", is_global=True)
    oil = Market(id=3, symbol="CL=F", name="Oil", price=80.0, category="Commodity", is_global=True)
    
    db_session.add_all([spy, gold, oil])
    db_session.commit()
    
    # Seed Gold history
    history = MarketHistory(
        market_id=gold.id,
        open=1990.0,
        high=2010.0,
        low=1980.0,
        close=2000.0,
        volume=5000.0
    )
    db_session.add(history)
    db_session.commit()
    
    return {"india": india, "spy": spy, "gold": gold, "oil": oil, "history": history}


def test_local_assets_defaults_to_us_without_params(client, seeded_data):
    # Query with no country code and unknown id
    resp = client.get("/api/v1/market/local/999")
    assert resp.status_code == 200
    data = resp.json()
    
    fallback_assets = data["fallback_assets"]
    # SPY (price=500.0, rate=1.0, premium=1.0)
    spy_asset = next(a for a in fallback_assets if a["symbol"] == "SPY")
    assert spy_asset["price"] == 500.0
    assert spy_asset["currency"] == "USD"
    assert spy_asset["currency_symbol"] == "$"


def test_local_assets_resolves_db_country(client, seeded_data):
    # Query India (id=1)
    resp = client.get("/api/v1/market/local/1")
    assert resp.status_code == 200
    data = resp.json()
    
    fallback_assets = data["fallback_assets"]
    # Gold (price=2000.0, rate=83.5, premium=1.12)
    # Expected INR price: 2000 * 83.5 * 1.12 = 187,040.0
    gold_asset = next(a for a in fallback_assets if a["symbol"] == "GC=F")
    assert gold_asset["price"] == 187040.0
    assert gold_asset["currency"] == "INR"
    assert gold_asset["currency_symbol"] == "₹"


def test_local_assets_untracked_country_explicit_query_param(client, seeded_data):
    # Query Antarctica (AQ)
    resp = client.get("/api/v1/market/local/999?country_code=AQ")
    assert resp.status_code == 200
    data = resp.json()
    
    fallback_assets = data["fallback_assets"]
    gold_asset = next(a for a in fallback_assets if a["symbol"] == "GC=F")
    
    # Gold (price=2000.0) -> Antarctica (AQ) should have pseudo-currency AQCur, AQ$
    assert gold_asset["currency"] == "AQCur"
    assert gold_asset["currency_symbol"] == "AQ$"
    # Price should be 2000 * AQ_rate * AQ_premium
    # Let's verify rate and premium are deterministically calculated and not USD default
    assert gold_asset["price"] != 2000.0
    assert gold_asset["price"] > 0.0


def test_read_market_detail_with_country_conversion(client, seeded_data):
    # Query detail of Gold with India (IN) country_code
    resp = client.get("/api/v1/market/GC=F?country_code=IN")
    assert resp.status_code == 200
    data = resp.json()
    
    # Expected INR price: 2000 * 83.5 * 1.12 = 187040
    assert data["price"] == 187040.0
    assert data["currency"] == "INR"
    assert data["currency_symbol"] == "₹"
    
    # History open/high/low/close should also be converted
    history = data["history"]
    assert len(history) == 1
    # Raw open was 1990.0. Expected converted open: 1990.0 * 83.5 * 1.12 = 186104.8
    assert history[0]["open"] == 186104.8
    assert history[0]["close"] == 187040.0
