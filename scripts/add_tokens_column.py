import sys
from pathlib import Path
from sqlalchemy import text

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from server.db.session import engine

def migrate():
    print(f"Connecting to database via engine: {engine.url}")
    with engine.connect() as conn:
        try:
            # Check if column exists (this is a bit tricky across DBs, but we can try-catch the ADD COLUMN)
            # Or assume it doesn't exist.
            # A safer way for both SQLite and Postgres:
            
            print("Attempting to add total_tokens column...")
            conn.execute(text("ALTER TABLE agent_artifacts ADD COLUMN total_tokens INTEGER DEFAULT 0"))
            conn.commit()
            print("Migration successful: Added total_tokens column.")
        except Exception as e:
            # If column exists, it will likely fail with "duplicate column name"
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("Column total_tokens already exists.")
            else:
                print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
