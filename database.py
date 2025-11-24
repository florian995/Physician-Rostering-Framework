from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import glob
import os

# --- Find the database file ---
db_files = glob.glob("database_*.db")
if not db_files:
    raise FileNotFoundError("No database file found matching pattern 'database_*.db'")

database_path = db_files[0]
clinic = os.path.basename(database_path).split("_")[2]

DATABASE_URI = f"sqlite:///{database_path}?timeout=60&check_same_thread=False"

# --- Create engine and sessionmaker ---
engine = create_engine(DATABASE_URI)
SessionLocal = sessionmaker(bind=engine)

def get_session():
    """Create a new SQLAlchemy session."""
    return SessionLocal()
