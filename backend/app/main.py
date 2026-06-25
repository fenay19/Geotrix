from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.logging import setup_logging
from sqlalchemy import text
from .database.base import Base
from .database.db import engine
from .api.router import api_router
from .ai.embeddings.vector_store import vector_store
from .config import settings

# ── Initialise structured logging before anything else ───────────────────────
logger = setup_logging()

# ── Create DB tables (idempotent) ────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── Upgrade DB tables (add columns dynamically if missing) ───────────────────
with engine.connect() as _conn:
    # 1. Upgrade events table
    try:
        _conn.execute(text("SELECT escalation_potential, impact_factor, casualties, economic_damage, infrastructure_destruction, displaced_population FROM events LIMIT 1"))
    except Exception:
        # Check and add escalation_potential / impact_factor if missing
        try:
            _conn.execute(text("SELECT escalation_potential, impact_factor FROM events LIMIT 1"))
        except Exception:
            try:
                logger.info("Adding escalation_potential and impact_factor to events...")
                _conn.execute(text("ALTER TABLE events ADD COLUMN escalation_potential INTEGER DEFAULT 3"))
                _conn.execute(text("ALTER TABLE events ADD COLUMN impact_factor FLOAT DEFAULT 1.0"))
                _conn.commit()
            except Exception as e:
                logger.error("Failed to add initial columns: %s", e)

        # Check and add casualties
        try:
            _conn.execute(text("SELECT casualties FROM events LIMIT 1"))
        except Exception:
            try:
                logger.info("Adding casualties to events table...")
                _conn.execute(text("ALTER TABLE events ADD COLUMN casualties INTEGER DEFAULT 0"))
                _conn.commit()
            except Exception as e:
                logger.error("Failed to add casualties: %s", e)

        # Check and add economic_damage
        try:
            _conn.execute(text("SELECT economic_damage FROM events LIMIT 1"))
        except Exception:
            try:
                logger.info("Adding economic_damage to events table...")
                _conn.execute(text("ALTER TABLE events ADD COLUMN economic_damage FLOAT DEFAULT 0.0"))
                _conn.commit()
            except Exception as e:
                logger.error("Failed to add economic_damage: %s", e)

        # Check and add infrastructure_destruction
        try:
            _conn.execute(text("SELECT infrastructure_destruction FROM events LIMIT 1"))
        except Exception:
            try:
                logger.info("Adding infrastructure_destruction to events table...")
                _conn.execute(text("ALTER TABLE events ADD COLUMN infrastructure_destruction VARCHAR DEFAULT 'Minimal'"))
                _conn.commit()
            except Exception as e:
                logger.error("Failed to add infrastructure_destruction: %s", e)

        # Check and add displaced_population
        try:
            _conn.execute(text("SELECT displaced_population FROM events LIMIT 1"))
        except Exception:
            try:
                logger.info("Adding displaced_population to events table...")
                _conn.execute(text("ALTER TABLE events ADD COLUMN displaced_population INTEGER DEFAULT 0"))
                _conn.commit()
            except Exception as e:
                logger.error("Failed to add displaced_population: %s", e)

    # 2. Upgrade gti_scores table
    try:
        _conn.execute(text("SELECT breakdown FROM gti_scores LIMIT 1"))
    except Exception:
        try:
            logger.info("Upgrading gti_scores table schema (adding breakdown)...")
            _conn.execute(text("ALTER TABLE gti_scores ADD COLUMN breakdown JSON"))
            _conn.commit()
            logger.info("gti_scores table schema upgrade complete.")
        except Exception as e:
            logger.error("Failed to dynamically upgrade gti_scores table: %s", e)

    # 3. Upgrade gti_history table
    try:
        _conn.execute(text("SELECT breakdown FROM gti_history LIMIT 1"))
    except Exception:
        try:
            logger.info("Upgrading gti_history table schema (adding breakdown)...")
            _conn.execute(text("ALTER TABLE gti_history ADD COLUMN breakdown JSON"))
            _conn.commit()
            logger.info("gti_history table schema upgrade complete.")
        except Exception as e:
            logger.error("Failed to dynamically upgrade gti_history table: %s", e)

    # 4. Upgrade markets table — add name, asset_class, geo_sensitivity
    for col, col_type, default in [
        ("name",            "VARCHAR",  "NULL"),
        ("asset_class",     "VARCHAR",  "NULL"),
        ("geo_sensitivity", "FLOAT",    "NULL"),
    ]:
        try:
            _conn.execute(text(f"SELECT {col} FROM markets LIMIT 1"))
        except Exception:
            try:
                logger.info("Adding column '%s' to markets table...", col)
                _conn.execute(text(f"ALTER TABLE markets ADD COLUMN {col} {col_type} DEFAULT {default}"))
                _conn.commit()
            except Exception as e:
                logger.error("Failed to add markets.%s: %s", col, e)

    # 5. Upgrade trading_signals table — add reliability metrics
    for col, col_type in [
        ("signal_accuracy",          "FLOAT"),
        ("win_rate",                 "FLOAT"),
        ("sharpe_ratio",             "FLOAT"),
        ("max_drawdown",             "FLOAT"),
        ("annual_reliability_score", "FLOAT"),
        ("triggering_event",         "VARCHAR"),
    ]:
        try:
            _conn.execute(text(f"SELECT {col} FROM trading_signals LIMIT 1"))
        except Exception:
            try:
                logger.info("Adding column '%s' to trading_signals table...", col)
                _conn.execute(text(f"ALTER TABLE trading_signals ADD COLUMN {col} {col_type}"))
                _conn.commit()
            except Exception as e:
                logger.error("Failed to add trading_signals.%s: %s", col, e)

    # 6. Ensure supply_chain_simulation_runs table exists (new BFS simulation engine)
    try:
        _conn.execute(text("SELECT id FROM supply_chain_simulation_runs LIMIT 1"))
    except Exception:
        try:
            logger.info("Creating supply_chain_simulation_runs table...")
            _conn.execute(text("""
                CREATE TABLE IF NOT EXISTS supply_chain_simulation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_node_id INTEGER REFERENCES supply_chain_nodes(id),
                    source_node_name VARCHAR NOT NULL,
                    severity FLOAT NOT NULL,
                    disruption_type VARCHAR DEFAULT 'Blockade',
                    apply_variability BOOLEAN DEFAULT 1,
                    affected_nodes_json JSON,
                    logs_json JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            _conn.commit()
            logger.info("supply_chain_simulation_runs table created.")
        except Exception as e:
            logger.error("Failed to create supply_chain_simulation_runs table: %s", e)

logger.info("Database tables created/verified.")



# ── Lifespan: replaces deprecated @app.on_event("startup") ───────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and (future) shutdown logic via the modern lifespan API."""
    import sys
    if "pytest" in sys.modules:
        logger.info("Lifespan: running in testing mode. Skipping database seeding and warm-up.")
        yield
        logger.info("Lifespan: testing mode shutdown.")
        return

    logger.info("GeoTrade Backend starting up...")

    # Clean up any leftover test placeholder market records (e.g., 'STRING')
    try:
        from .database.db import SessionLocal
        from .models.market_model import Market
        db_cleanup = SessionLocal()
        try:
            deleted_count = db_cleanup.query(Market).filter(Market.symbol.in_(["string", "STRING"])).delete(synchronize_session=False)
            if deleted_count > 0:
                db_cleanup.commit()
                logger.info("Lifespan: Cleaned up %d invalid market records from database.", deleted_count)
        except Exception as db_exc:
            logger.error("Lifespan: Failed to delete invalid market records: %s", db_exc)
        finally:
            db_cleanup.close()
    except Exception as cleanup_exc:
        logger.error("Lifespan: Database cleanup setup error: %s", cleanup_exc)

    # Seed markets with 35 assets if DB is sparse
    try:
        from .database.db import SessionLocal
        from .database.seed_markets import seed_markets
        db_seed = SessionLocal()
        try:
            n = seed_markets(db_seed)
            if n > 0:
                logger.info("Lifespan: Seeded %d new markets into database.", n)
        except Exception as seed_exc:
            logger.error("Lifespan: Market seeding failed: %s", seed_exc)
        finally:
            db_seed.close()
    except Exception as seed_setup_exc:
        logger.error("Lifespan: Market seed setup error: %s", seed_setup_exc)

    # Ensure guest analyst user exists and is a superuser (admin)
    try:
        from .database.db import SessionLocal
        from .models.user_model import User
        from .core.security import get_password_hash
        db_user_setup = SessionLocal()
        try:
            guest_email = settings.GUEST_ANALYST_EMAIL
            guest_pass = settings.GUEST_ANALYST_PASSWORD
            guest = db_user_setup.query(User).filter(User.email == guest_email).first()
            if guest:
                if not guest.is_superuser:
                    guest.is_superuser = True
                    db_user_setup.commit()
                    logger.info("Lifespan: Promoted existing guest analyst to superuser/admin.")
            else:
                hashed_password = get_password_hash(guest_pass)
                new_guest = User(
                    email=guest_email,
                    hashed_password=hashed_password,
                    is_active=True,
                    is_superuser=True
                )
                db_user_setup.add(new_guest)
                db_user_setup.commit()
                logger.info("Lifespan: Created guest analyst user as superuser/admin.")
        except Exception as db_exc:
            logger.error("Lifespan: Failed to setup guest analyst user: %s", db_exc)
        finally:
            db_user_setup.close()
    except Exception as setup_exc:
        logger.error("Lifespan: Guest analyst user setup error: %s", setup_exc)

    # Warm up the vector store (loads existing events into memory vector store)
    try:
        vector_store.warm_up()

        # Check for dimension mismatch against active embedding model
        from .ai.embeddings.embedding_model import embedding_model
        test_emb = embedding_model.get_embedding("test")
        if vector_store.dim is not None and vector_store.dim != len(test_emb):
            logger.warning(
                "VectorStore: Dimension mismatch detected (loaded %d, active model %d). "
                "Wiping legacy index and rebuilding from SQLite events...",
                vector_store.dim, len(test_emb)
            )
            vector_store.clear()

        # Always wipe the on-disk index and rebuild fresh from the current DB.
        # Keeping the old persisted index causes stale vectors from previous runs
        # to accumulate, which inflates the dedup index and blocks new events from
        # being ingested (every new article scores >0.88 against 100s of old vectors).
        vector_store.clear()
        logger.info("VectorStore: Cleared stale persisted index. Rebuilding from DB...")

        # Populate in-memory vector store with existing database events
        from .database.db import SessionLocal
        from .repositories.event_repo import EventRepository

        db = SessionLocal()
        try:
            event_repo = EventRepository(db)
            events = event_repo.get_all(limit=100)  # load up to 100 recent events
            if events:
                logger.info("Indexing %d existing database events into Vector Store...", len(events))
                for e in events:
                    text_to_embed = f"{e.title} {e.description[:400]}"
                    vec = embedding_model.get_embedding(text_to_embed)
                    vector_store.add_vector(
                        id=f"event_{e.id}",
                        vector=vec,
                        metadata={
                            "title":      e.title,
                            "summary":    e.description[:300],
                            "event_type": e.event_type,
                            "severity":   e.severity,
                            "country_id": e.country_id,
                        },
                    )
                logger.info("Vector Store indexing complete. Total vectors: %d", vector_store.count())
            else:
                logger.info("VectorStore: No existing events in DB. Starting fresh.")
        finally:
            db.close()

        logger.info("Vector Store warmed up successfully.")
    except Exception as e:
        logger.error("Vector Store warm-up failed: %s", e)

    # Warm up ML Models (Phase 4 startup optimization)
    try:
        logger.info("Loading ML models...")
        from .ml.inference.ml_predictor import ml_predictor
        ml_predictor.load_models()
        logger.info("ML models loaded successfully.")
    except Exception as e:
        logger.error("Failed to load ML models at startup: %s", e)

    # Log API key availability (values are never logged)
    logger.info("OpenAI API Key : %s", "Set" if settings.OPENAI_API_KEY else "MISSING")
    logger.info("Finnhub API Key: %s", "Set" if settings.FINNHUB_API_KEY else "MISSING")
    logger.info("News API Key   : %s", "Set" if settings.NEWS_API_KEY else "MISSING")

    # Start background scheduler task
    scheduler_task = None
    if settings.SCHEDULER_ENABLED:
        from .services.scheduler import background_sync_scheduler
        scheduler_task = asyncio.create_task(background_sync_scheduler())
        logger.info("Background sync scheduler task spawned.")

    yield  # ── Application runs here ────────────────────────────────────────

    # Shutdown logic
    settings.IS_SHUTTING_DOWN = True
    if scheduler_task:
        logger.info("Stopping background sync scheduler task...")
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            logger.info("Background sync scheduler task cancelled successfully.")
            
    logger.info("GeoTrade Backend shutting down.")



# ── Application instance ─────────────────────────────────────────────────────
app = FastAPI(
    title="GeoTrade AI — Geopolitical Trading Intelligence Platform",
    description=(
        "Combines global event monitoring, financial market analysis, "
        "AI-based reasoning, and interactive visualization."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# allow_origins must be explicit (not "*") when allow_credentials=True.
# See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#credentialed_requests
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://.*$",  # Allow all origins for local dev testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)  # reload trigger
