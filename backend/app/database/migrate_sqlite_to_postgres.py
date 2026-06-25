import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("geotrade.migration")

# Add backend directory to Python path to import app modules
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(backend_dir)

from app.database.base import Base
from app.models.user_model import User
from app.models.country_risk_model import CountryRisk
from app.models.event_model import Event
from app.models.gti_model import GTIScore, GTIHistory
from app.models.market_model import Market, MarketHistory
from app.models.trading_signal_model import TradingSignal
from app.models.supply_chain_model import SupplyChainNode, SupplyChainDependency
from app.models.chat_model import ChatSession, ChatMessage
from app.models.simulation_model import SimulationRun

# Load URLs from .env file
dotenv_path = os.path.join(backend_dir, ".env")
sqlite_url = "sqlite:///e:/Geo_mapping/geotrade-ai-platform/backend/app_sql.db"
pg_url = None

if os.path.exists(dotenv_path):
    with open(dotenv_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                # Check for commented-out PG url if we need it, or uncommented PG url
                if "DATABASE_URL" in line and "postgresql" in line:
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        pg_url = parts[1].strip().strip('"').strip("'")
            elif line.startswith("DATABASE_URL"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    val = parts[1].strip().strip('"').strip("'")
                    if "postgresql" in val:
                        pg_url = val
                    elif "sqlite" in val:
                        sqlite_url = val

# Hardcoded fallback for Supabase PG url if not found in .env
if not pg_url:
    pg_url = "postgresql://postgres:Devang123%23%40@db.xftrygnqdubstvdomfcf.supabase.co:5432/postgres"

logger.info("SQLite Source URL: %s", sqlite_url)
logger.info("PostgreSQL Target URL: %s", pg_url)

# Create engines and sessions
sqlite_engine = create_engine(sqlite_url)
pg_engine = create_engine(pg_url)

SqliteSession = sessionmaker(bind=sqlite_engine)
PgSession = sessionmaker(bind=pg_engine)

sqlite_db = SqliteSession()
pg_db = PgSession()

# Order of migration (topological order to respect foreign keys)
MIGRATION_ORDER = [
    (User, "users"),
    (CountryRisk, "country_risks"),
    (Event, "events"),
    (GTIScore, "gti_scores"),
    (GTIHistory, "gti_history"),
    (Market, "markets"),
    (MarketHistory, "market_history"),
    (TradingSignal, "trading_signals"),
    (SupplyChainNode, "supply_chain_nodes"),
    (SupplyChainDependency, "supply_chain_dependencies"),
    (ChatSession, "chat_sessions"),
    (ChatMessage, "chat_messages"),
    (SimulationRun, "simulation_runs")
]

def migrate():
    try:
        # Create all tables in target PostgreSQL database if they do not exist
        logger.info("Creating tables in PostgreSQL target database...")
        Base.metadata.create_all(bind=pg_engine)
        logger.info("Tables checked/created.")

        for model_cls, table_name in MIGRATION_ORDER:
            logger.info("Migrating table '%s'...", table_name)
            
            # Query SQLite records
            sqlite_records = sqlite_db.query(model_cls).all()
            if not sqlite_records:
                logger.info("No records found in SQLite for '%s'. Skipping.", table_name)
                continue
            
            logger.info("Found %d records in SQLite. Inserting into PostgreSQL...", len(sqlite_records))
            
            # Column list
            col_names = [c.name for c in model_cls.__table__.columns]
            
            # Query existing IDs in PG
            existing_ids = {row[0] for row in pg_db.query(model_cls.id).all()}
            
            records_to_insert = []
            added_count = 0
            updated_count = 0
            
            for rec in sqlite_records:
                # Build dict of column values
                data = {name: getattr(rec, name) for name in col_names}
                
                if rec.id in existing_ids:
                    # Update instead
                    exists = pg_db.query(model_cls).filter(model_cls.id == rec.id).first()
                    if exists:
                        for name in col_names:
                            setattr(exists, name, data[name])
                        updated_count += 1
                else:
                    pg_rec = model_cls(**data)
                    records_to_insert.append(pg_rec)
                    added_count += 1
            
            if records_to_insert:
                pg_db.bulk_save_objects(records_to_insert)
            
            pg_db.commit()
            logger.info("Successfully migrated '%s' (inserted: %d, updated: %d).", table_name, added_count, updated_count)
            
            # Reset sequence in PostgreSQL to max(id) to prevent constraint errors in future inserts
            try:
                # Check if the sequence exists
                seq_query = text(f"SELECT pg_get_serial_sequence('{table_name}', 'id')")
                seq_name = pg_db.execute(seq_query).scalar()
                if seq_name:
                    logger.info("Resetting sequence '%s' for table '%s'...", seq_name, table_name)
                    reset_query = text(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table_name}), 1), EXISTS(SELECT 1 FROM {table_name}))")
                    pg_db.execute(reset_query)
                    pg_db.commit()
            except Exception as seq_exc:
                pg_db.rollback()
                logger.warning("Could not reset sequence for table '%s': %s", table_name, seq_exc)

        logger.info("Database migration completed successfully!")

    except Exception as e:
        pg_db.rollback()
        logger.error("Migration failed: %s", e, exc_info=True)
    finally:
        sqlite_db.close()
        pg_db.close()

if __name__ == "__main__":
    migrate()
