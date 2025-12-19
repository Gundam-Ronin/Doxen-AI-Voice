import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL")

_engine = None
_SessionLocal = None

def get_engine():
    """Lazy engine creation - only connects when first needed."""
    global _engine
    if _engine is None and DATABASE_URL:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine

def get_session_local():
    """Lazy session factory creation."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        if engine:
            _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal

class _LazySessionLocal:
    """Wrapper to allow SessionLocal to be used as if it were a class."""
    def __call__(self):
        session_local = get_session_local()
        if session_local:
            return session_local()
        return None
    
    def __bool__(self):
        return DATABASE_URL is not None

SessionLocal = _LazySessionLocal()

def init_db():
    """Initialize database tables."""
    engine = get_engine()
    if engine:
        from .models import Base
        Base.metadata.create_all(bind=engine)

def get_db():
    """Database session dependency for FastAPI."""
    session_local = get_session_local()
    if session_local is None:
        raise Exception("Database not configured")
    db = session_local()
    try:
        yield db
    finally:
        db.close()
