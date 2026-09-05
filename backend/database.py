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


def _add_column_if_missing(connection, table: str, column: str, col_type: str):
    result = connection.execute(text(f"PRAGMA table_info({table});"))
    columns = [row[1] for row in result.fetchall()]
    if not columns:
        return
    if column not in columns:
        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};"))
        logger.info("Migrated table %s: added %s column", table, column)


def init_db():
    """Initialize database tables, run safe column migrations for SQLite, and verify connection."""
    try:
        from backend import models  # noqa
        Base.metadata.create_all(bind=engine)
        
        # Idempotent SQLite migration for columns
        if "sqlite" in settings.database_url:
            with engine.connect() as connection:
                # Accounts table migration
                _add_column_if_missing(connection, "accounts", "smtp_host", "VARCHAR(255)")
                _add_column_if_missing(connection, "accounts", "smtp_port", "INTEGER DEFAULT 587")
                _add_column_if_missing(connection, "accounts", "smtp_security", "VARCHAR(50) DEFAULT 'starttls'")
                _add_column_if_missing(connection, "accounts", "smtp_username", "VARCHAR(255)")

                # Campaigns table migration — pacing / delivery (desktop parity)
                _add_column_if_missing(connection, "campaigns", "tag", "VARCHAR(50) DEFAULT 'Marketing'")
                _add_column_if_missing(connection, "campaigns", "delay_seconds", "INTEGER DEFAULT 30")
                _add_column_if_missing(connection, "campaigns", "jitter_seconds", "INTEGER DEFAULT 2")
                _add_column_if_missing(connection, "campaigns", "max_retries", "INTEGER DEFAULT 3")
                _add_column_if_missing(connection, "campaigns", "rotation_mode", "VARCHAR(50) DEFAULT 'round_robin'")
                _add_column_if_missing(connection, "campaigns", "reply_to", "VARCHAR(255)")
                _add_column_if_missing(connection, "campaigns", "delivery_route", "VARCHAR(50) DEFAULT 'auto'")

                # Drafts table check & migration
                _add_column_if_missing(connection, "drafts", "from_name", "VARCHAR(255)")
                _add_column_if_missing(connection, "drafts", "attachments", "TEXT")

                # Leads table check & migration
                _add_column_if_missing(connection, "leads", "sender_name", "VARCHAR(100)")
                _add_column_if_missing(connection, "leads", "sender_full_name", "VARCHAR(100)")

                # Activity logs table check & migration
                _add_column_if_missing(connection, "activity_logs", "lead_email", "VARCHAR(255)")
                _add_column_if_missing(connection, "activity_logs", "account_name", "VARCHAR(100)")
                _add_column_if_missing(connection, "activity_logs", "status", "VARCHAR(50) DEFAULT 'SENT'")
                _add_column_if_missing(connection, "activity_logs", "provider_type", "VARCHAR(50)")
                _add_column_if_missing(connection, "activity_logs", "provider_message_id", "VARCHAR(255)")
                _add_column_if_missing(connection, "activity_logs", "error_code", "VARCHAR(50)")
                _add_column_if_missing(connection, "activity_logs", "campaign_id", "INTEGER")

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
