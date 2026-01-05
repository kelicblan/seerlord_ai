import sys
from pathlib import Path
import logging

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from server.db.session import engine, SessionLocal
from server.db.models import Base as AppBase
from server.core.database import Base as CoreBase
# Import User to ensure it's registered to CoreBase
from server.models.user import User
from server.core.security import get_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """
    Initialize the database:
    1. Create all tables (from both AppBase and CoreBase).
    2. Create default admin user.
    """
    logger.info("Creating database tables...")
    
    # Create tables for AppBase (Skills, Tenants, etc.)
    # ensure tables are created using the sync engine
    AppBase.metadata.create_all(bind=engine)
    
    # Create tables for CoreBase (Users, etc.)
    CoreBase.metadata.create_all(bind=engine)
    
    logger.info("Tables created successfully.")
    
    # Initialize Admin User
    init_admin_user()

def init_admin_user():
    """
    Create default admin user if not exists.
    Username: seerlord
    Password: <hashed 12345678>
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "seerlord").first()
        if not user:
            logger.info("Creating admin user 'seerlord'...")
            admin_user = User(
                username="seerlord",
                hashed_password=get_password_hash("12345678"),
                is_active=True,
                is_superuser=True
            )
            db.add(admin_user)
            db.commit()
            logger.info("Admin user created successfully.")
        else:
            logger.info("Admin user already exists.")
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
