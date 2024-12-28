from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
from config.settings import get_settings
from core.logger import logger
import time

settings = get_settings()

# Create the SQLAlchemy base class
Base = declarative_base()

def create_db_engine():
    """Create database engine with connection pooling"""
    return create_engine(
        settings.NEON_DB_URL,
        pool_pre_ping=True,  # Enable connection health checks
        pool_recycle=3600,   # Recycle connections after 1 hour
        pool_size=5,         # Maximum number of connections
        max_overflow=10      # Maximum number of connections that can be created beyond pool_size
    )

# Create engine instance
engine = create_db_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Database session generator with retry logic"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        db = None
        try:
            db = SessionLocal()
            # Test the connection with proper text() wrapper
            db.execute(text("SELECT 1"))
            yield db
        except OperationalError as e:
            logger.error(f"Database connection error (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if db:
                try:
                    db.rollback()
                except:
                    pass
                finally:
                    db.close()
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            raise
        except Exception as e:
            logger.error(f"Unexpected database error: {str(e)}")
            if db:
                try:
                    db.rollback()
                except:
                    pass
                finally:
                    db.close()
            raise
        finally:
            if db:
                db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine) 