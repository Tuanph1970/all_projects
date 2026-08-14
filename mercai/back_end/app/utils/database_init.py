from app.core.database import engine, Base
from app.models import *

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

def drop_tables():
    """Drop all database tables"""
    Base.metadata.drop_all(bind=engine)
    print("Database tables dropped successfully")

if __name__ == "__main__":
    create_tables()