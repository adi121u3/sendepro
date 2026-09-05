"""Backup or restore the local SQLite database.

Examples:
  python scripts/database_backup.py backup
  python scripts/database_backup.py restore backups/email_sender_pro_YYYYMMDD_HHMMSS.db
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "email_sender_pro.db"
BACKUP_DIR = PROJECT_ROOT / "backups"


def backup() -> None:
    if not DATABASE_PATH.exists():
        raise SystemExit(f"Database not found: {DATABASE_PATH}")
    BACKUP_DIR.mkdir(exist_ok=True)
    destination = BACKUP_DIR / f"email_sender_pro_{datetime.now():%Y%m%d_%H%M%S}.db"
    shutil.copy2(DATABASE_PATH, destination)
    print(f"Backup created: {destination}")


def restore(source: str) -> None:
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        raise SystemExit(f"Backup not found: {source_path}")
    if source_path == DATABASE_PATH.resolve():
        raise SystemExit("The backup and live database must be different files.")
    confirmation = input(f"Restore {source_path.name} over the live database? Type RESTORE to continue: ")
    if confirmation != "RESTORE":
        raise SystemExit("Restore cancelled.")
    shutil.copy2(source_path, DATABASE_PATH)
    print(f"Database restored from: {source_path}")


parser = argparse.ArgumentParser(description="Protect and restore Email Sender Pro SQLite data.")
subparsers = parser.add_subparsers(dest="command", required=True)
subparsers.add_parser("backup")
restore_parser = subparsers.add_parser("restore")
restore_parser.add_argument("backup_file")
args = parser.parse_args()

if args.command == "backup":
    backup()
else:
    restore(args.backup_file)
