import os
import sys

# Configure Python path to find app directory relative to this script
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import engine

def test_db_connection():
    print("Attempting to connect to PostgreSQL database...")
    print(f"Target URL: {settings.DATABASE_URL.split('@')[-1]}") # Print host/database, masking password
    
    session = None
    try:
        # Open session using the production-safe engine
        session = Session(engine)
        
        # Execute query using SQLAlchemy 2.0 text() wrapper
        result = session.execute(text("SELECT version();"))
        version = result.scalar()
        
        print("\nConnected Successfully")
        print(f"PostgreSQL Version: {version}")
        
    except Exception as e:
        print("\nConnection Failed!")
        print(f"Readable Error Message: Could not connect to the database. Verify that the PostgreSQL service is active on the configured host/port and that credentials are valid.")
        
        # If debugging is enabled, print the full traceback message
        if os.environ.get("DEVMIND_DEBUG") == "True" or os.environ.get("DEBUG") == "True":
            print("\n--- DEBUG TRACEBACK ---")
            import traceback
            traceback.print_exc()
        else:
            print(f"Error summary: {str(e)}")
            
        sys.exit(1)
    finally:
        if session:
            session.close()

if __name__ == "__main__":
    test_db_connection()
