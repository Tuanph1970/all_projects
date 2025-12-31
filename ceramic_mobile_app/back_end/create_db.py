#!/usr/bin/env python3
"""
Database initialization script for Ceramic Marketplace
Creates all tables with proper indexes and relationships
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.utils.database_init import create_tables

if __name__ == "__main__":
    print("Creating Ceramic Marketplace database tables...")
    create_tables()
    print("Database setup completed successfully!")