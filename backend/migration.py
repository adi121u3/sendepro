import logging
import sys
from sqlalchemy import text
from backend.database import engine, init_db

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("email_sender_pro.migration")

def run_migrations():
    logger.info("Starting database migration script to synchronize SQLite schema with SQLAlchemy models...")
    init_db()
    
    with engine.connect() as conn:
        # Check leads table columns
        leads_info = conn.execute(text("PRAGMA table_info(leads);")).fetchall()
        leads_cols = [row[1] for row in leads_info]
        
        if "sender_name" not in leads_cols:
            conn.execute(text("ALTER TABLE leads ADD COLUMN sender_name VARCHAR(100);"))
            logger.info("Added missing 'sender_name' column to leads table.")
        if "sender_full_name" not in leads_cols:
            conn.execute(text("ALTER TABLE leads ADD COLUMN sender_full_name VARCHAR(100);"))
            logger.info("Added missing 'sender_full_name' column to leads table.")
            
        # Check activity_logs table columns
        logs_info = conn.execute(text("PRAGMA table_info(activity_logs);")).fetchall()
        logs_cols = [row[1] for row in logs_info]
        
        for col_name, col_type in [
            ("lead_email", "VARCHAR(255)"),
            ("account_name", "VARCHAR(100)"),
            ("status", "VARCHAR(50) DEFAULT 'SENT'"),
            ("provider_type", "VARCHAR(50)"),
            ("provider_message_id", "VARCHAR(255)"),
            ("error_code", "VARCHAR(50)"),
            ("campaign_id", "INTEGER")
        ]:
            if col_name not in logs_cols:
                conn.execute(text(f"ALTER TABLE activity_logs ADD COLUMN {col_name} {col_type};"))
                logger.info(f"Added missing '{col_name}' column to activity_logs table.")
                
        conn.commit()
    logger.info("Database migration script completed successfully.")

if __name__ == "__main__":
    run_migrations()
