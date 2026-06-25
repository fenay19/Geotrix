import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.dependencies import get_db
from app.database.base import Base
from app.models.supply_chain_model import SupplyChainNode, SupplyChainDependency, SupplyChainSimulationRun
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
def seed_data(db_session):
    # Create CountryRisk record
    ukraine_risk = CountryRisk(
        id=1,
        country_code="UA",
        country_name="Ukraine",
        risk_score=90.0,
        color_code="Red",
        sector_exposure={"Agriculture": 70}
    )
    db_session.add(ukraine_risk)

    # Create Markets and History
    adm_market = Market(
        id=1,
        symbol="ADM",
        name="Archer-Daniels-Midland Co",
        price=60.0,
        category="Equity",
        asset_class="Stocks",
        is_global=True,
        country_id=ukraine_risk.id
    )
    db_session.add(adm_market)
    db_session.commit()

    adm_history = MarketHistory(
        market_id=adm_market.id,
        open=58.0,
        high=61.0,
        low=57.5,
        close=59.0,
        volume=12000.0
    )
    db_session.add(adm_history)

    # Create SupplyChainNodes
    agriculture = SupplyChainNode(
        id=10,
        name="Agriculture / Grain",
        location="Ukraine",
        type="resource"
    )
    energy = SupplyChainNode(
        id=7,
        name="Energy Sector",
        location="Global",
        type="industry"
    )
    db_session.add_all([agriculture, energy])
    db_session.commit()

    # Create SupplyChainDependency
    dep = SupplyChainDependency(
        id=1,
        source_node_id=10,
        target_node_id=7,
        dependency_type="minor_input",
        dependency_strength=0.3
    )
    db_session.add(dep)
    db_session.commit()

    return {
        "ukraine_risk": ukraine_risk,
        "adm_market": adm_market,
        "adm_history": adm_history,
        "agriculture": agriculture,
        "energy": energy,
        "dependency": dep
    }


def test_get_all_nodes(client, seed_data):
    resp = client.get("/api/v1/supply-chain/nodes")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    names = [node["name"] for node in data]
    assert "Agriculture / Grain" in names
    assert "Energy Sector" in names


def test_get_node_by_id(client, seed_data):
    resp = client.get("/api/v1/supply-chain/nodes/10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Agriculture / Grain"
    assert data["location"] == "Ukraine"

    # Test 404
    resp = client.get("/api/v1/supply-chain/nodes/999")
    assert resp.status_code == 404


def test_create_node(client):
    node_payload = {
        "name": "New Resource Node",
        "location": "Taiwan",
        "type": "resource"
    }
    resp = client.post("/api/v1/supply-chain/nodes", json=node_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New Resource Node"
    assert "id" in data


def test_create_dependency(client, seed_data):
    dep_payload = {
        "source_node_id": 7,
        "target_node_id": 10,
        "dependency_type": "major_input",
        "dependency_strength": 0.5
    }
    resp = client.post("/api/v1/supply-chain/dependencies", json=dep_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_node_id"] == 7
    assert data["target_node_id"] == 10
    assert data["dependency_strength"] == 0.5


def test_get_node_dependencies_and_dependents(client, seed_data):
    # Dependencies of node 10 (outgoing dependency to 7)
    resp = client.get("/api/v1/supply-chain/nodes/10/dependencies")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["target_node_id"] == 7

    # Dependents of node 7 (incoming dependency from 10)
    resp = client.get("/api/v1/supply-chain/nodes/7/dependents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["source_node_id"] == 10


def test_get_graph_and_critical_nodes(client, seed_data):
    resp = client.get("/api/v1/supply-chain/graph")
    assert resp.status_code == 200
    graph = resp.json()
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1

    resp = client.get("/api/v1/supply-chain/critical-nodes?min_score=0.2")
    assert resp.status_code == 200
    critical = resp.json()
    assert len(critical) == 1
    assert critical[0]["id"] == 10  # 10 is supplier of 7 (outgoing dependency)
    assert critical[0]["chokepoint_score"] == 0.3


def test_simulate_disruption_success(client, seed_data):
    simulate_payload = {
        "node_id": 10,
        "severity": 90.0,
        "disruption_type": "Strike",
        "apply_variability": False
    }
    resp = client.post("/api/v1/supply-chain/simulate", json=simulate_payload)
    assert resp.status_code == 201
    data = resp.json()
    
    # Check response structure
    assert data["source_node_id"] == 10
    assert data["source_node_name"] == "Agriculture / Grain"
    assert data["severity"] == 90.0
    assert data["disruption_type"] == "Strike"
    
    # Check affected nodes (BFS cascade)
    # severity 90.0 * strength 0.3 = 27.0
    assert len(data["affected_nodes"]) == 1
    affected = data["affected_nodes"][0]
    assert affected["node_id"] == 7
    assert affected["name"] == "Energy Sector"
    assert affected["impact"] == 27.0
    assert affected["depth"] == 1
    
    # Check simulation logs
    assert len(data["logs"]) > 0
    # The logs should contain mentions of the disruption event, the live events/markets context, and BFS execution
    log_texts = [l["text"] for l in data["logs"]]
    assert any("DISRUPTION EVENT DECLARED" in t for t in log_texts)
    assert any("Agriculture / Grain" in t for t in log_texts)
    assert any("Ukraine" in t for t in log_texts)
    assert any("STRIKE" in t for t in log_texts)
    # Check if market snapshot is included for Agriculture / Grain ADM stock
    assert any("ADM" in t for t in log_texts)
    
    # Verify it is persisted in simulation history
    resp_history = client.get("/api/v1/supply-chain/simulations")
    assert resp_history.status_code == 200
    history_data = resp_history.json()
    assert len(history_data) >= 1
    assert history_data[0]["source_node_id"] == 10
    assert history_data[0]["severity"] == 90.0


def test_get_node_intelligence_success(client, seed_data):
    resp = client.get("/api/v1/supply-chain/nodes/10/intelligence")
    assert resp.status_code == 200
    data = resp.json()
    
    # 1. Overview
    assert data["overview"]["id"] == 10
    assert data["overview"]["name"] == "Agriculture / Grain"
    
    # 2. Dependency Tree
    tree = data["dependency_tree"]
    assert tree["id"] == 10
    assert len(tree["children"]) == 1
    assert tree["children"][0]["id"] == 7
    assert tree["children"][0]["strength"] == 0.3
    
    # 3. Live Context
    context = data["live_context"]
    assert context["country_risk"]["country_code"] == "UA"
    assert len(context["markets"]) == 1
    assert context["markets"][0]["symbol"] == "ADM"
    
    # 4. Impact Preview
    preview = data["impact_preview"]
    assert "25" in preview
    assert "50" in preview
    assert "75" in preview
    assert "100" in preview
    # 25% * 0.3 = 7.5% impact on Energy Sector (id 7)
    assert len(preview["25"]) == 1
    assert preview["25"][0]["node_id"] == 7
    assert preview["25"][0]["impact"] == 7.5
    
    # 5. Chokepoint Analysis
    analysis = data["chokepoint_analysis"]
    assert analysis["chokepoint_score"] == 0.3
    assert analysis["rank"] == 1  # only one supplier has a score > 0
    
    # 6. Propagation Paths
    paths = data["propagation_paths"]
    assert len(paths) == 1
    assert paths[0]["target"] == "Energy Sector"
    assert paths[0]["path"] == ["Agriculture / Grain", "Energy Sector"]
    assert paths[0]["strength"] == 0.3


def test_get_node_intelligence_404(client, seed_data):
    resp = client.get("/api/v1/supply-chain/nodes/999/intelligence")
    assert resp.status_code == 404

