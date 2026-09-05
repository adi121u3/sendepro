import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import settings

logger = logging.getLogger("email_sender_pro.database")

# SQLite connection
# check_same_thread=False is required for SQLite when accessed by multiple threads in FastAPI
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """Initialize database tables, run safe column migrations for SQLite, and verify connection."""
    try:
        from backend import models  # noqa
        Base.metadata.create_all(bind=engine)
        
        # Idempotent SQLite migration for columns
        if "sqlite" in settings.database_url:
            with engine.connect() as connection:
                # Accounts table migration
                result = connection.execute(text("PRAGMA table_info(accounts);"))
                columns = [row[1] for row in result.fetchall()]
                
                if "smtp_host" not in columns:
                    connection.execute(text("ALTER TABLE accounts ADD COLUMN smtp_host VARCHAR(255);"))
                    logger.info("Migrated table accounts: added smtp_host column")
                if "smtp_port" not in columns:
                    connection.execute(text("ALTER TABLE accounts ADD COLUMN smtp_port INTEGER DEFAULT 587;"))
                    logger.info("Migrated table accounts: added smtp_port column")
                if "smtp_security" not in columns:
                    connection.execute(text("ALTER TABLE accounts ADD COLUMN smtp_security VARCHAR(50) DEFAULT 'starttls';"))
                    logger.info("Migrated table accounts: added smtp_security column")
                if "smtp_username" not in columns:
                    connection.execute(text("ALTER TABLE accounts ADD COLUMN smtp_username VARCHAR(255);"))
                    logger.info("Migrated table accounts: added smtp_username column")

                # Campaigns table migration
                campaigns_res = connection.execute(text("PRAGMA table_info(campaigns);"))
                campaigns_cols = [row[1] for row in campaigns_res.fetchall()]
                if campaigns_cols and "tag" not in campaigns_cols:
                    connection.execute(text("ALTER TABLE campaigns ADD COLUMN tag VARCHAR(50) DEFAULT 'Marketing';"))
                    logger.info("Migrated table campaigns: added tag column")

                # Drafts table check & migration
                drafts_res = connection.execute(text("PRAGMA table_info(drafts);"))
                drafts_cols = [row[1] for row in drafts_res.fetchall()]
                if drafts_cols:
                    if "from_name" not in drafts_cols:
                        connection.execute(text("ALTER TABLE drafts ADD COLUMN from_name VARCHAR(255);"))
                        logger.info("Migrated table drafts: added from_name column")
                    if "attachments" not in drafts_cols:
                        connection.execute(text("ALTER TABLE drafts ADD COLUMN attachments TEXT;"))
                        logger.info("Migrated table drafts: added attachments column")

                # Leads table check & migration
                leads_res = connection.execute(text("PRAGMA table_info(leads);"))
                leads_cols = [row[1] for row in leads_res.fetchall()]
                if leads_cols:
                    if "sender_name" not in leads_cols:
                        connection.execute(text("ALTER TABLE leads ADD COLUMN sender_name VARCHAR(100);"))
                        logger.info("Migrated table leads: added sender_name column")
                    if "sender_full_name" not in leads_cols:
                        connection.execute(text("ALTER TABLE leads ADD COLUMN sender_full_name VARCHAR(100);"))
                        logger.info("Migrated table leads: added sender_full_name column")

                # Activity logs table check & migration
                logs_res = connection.execute(text("PRAGMA table_info(activity_logs);"))
                logs_cols = [row[1] for row in logs_res.fetchall()]
                if logs_cols:
                    if "lead_email" not in logs_cols:
                        connection.execute(text("ALTER TABLE activity_logs ADD COLUMN lead_email VARCHAR(255);"))
                    if "account_name" not in logs_cols:
                        connection.execute(text("ALTER TABLE activity_logs ADD COLUMN account_name VARCHAR(100);"))
                    if "status" not in logs_cols:
                        connection.execute(text("ALTER TABLE activity_logs ADD COLUMN status VARCHAR(50) DEFAULT 'SENT';"))
                    if "provider_type" not in logs_cols:
                        connection.execute(text("ALTER TABLE activity_logs ADD COLUMN provider_type VARCHAR(50);"))
                    if "provider_message_id" not in logs_cols:
                        connection.execute(text("ALTER TABLE activity_logs ADD COLUMN provider_message_id VARCHAR(255);"))
                    if "error_code" not in logs_cols:
                        connection.execute(text("ALTER TABLE activity_logs ADD COLUMN error_code VARCHAR(50);"))
                    if "campaign_id" not in logs_cols:
                        connection.execute(text("ALTER TABLE activity_logs ADD COLUMN campaign_id INTEGER;"))
                        logger.info("Migrated table activity_logs: added extended logging columns")

                connection.commit()

        logger.info("Database initialized successfully at %s", settings.database_url)
    except Exception as e:
        logger.error("Failed to initialize database: %s", str(e))
        raise

def get_db():
    """Dependency for obtaining database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
