"""
Database module for TCET Chatbot - PostgreSQL connection pool
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from src.config import settings
from src.models.opportunity import Base, OpportunityModel
import logging

logger = logging.getLogger(__name__)

# Create engine
engine = create_engine(
    settings.database_url,
    echo=settings.sqlalchemy_echo,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("✓ Database tables initialized")


def test_connection():
    """Test DB connection"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✓ PostgreSQL connected")
            return True
    except Exception as e:
        logger.error(f"✗ PostgreSQL failed: {e}")
        return False


def get_db():
    """FastAPI dependency - get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    if test_connection():
        print("✓ DB OK")
        init_db()
        print("✓ Tables created")
    else:
        print("✗ DB failed")