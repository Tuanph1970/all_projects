#!/usr/bin/env python3
"""
Standalone script to initialize Ceramic Marketplace database tables.
This runs outside Docker to create tables in the host MySQL database.
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Initialize database tables for Ceramic Marketplace"""
    try:
        print("=" * 50)
        print("Ceramic Marketplace - Database Table Initialization")
        print("=" * 50)
        print()

        # Import after path is set
        from app.core.config import settings
        from app.utils.database_init import create_tables

        # Log connection details for debugging
        print(f"Database Configuration:")
        print(f"  Host: {settings.DB_HOST}")
        print(f"  Port: {settings.DB_PORT}")
        print(f"  Database: {settings.DB_NAME}")
        print(f"  User: {settings.DB_USER}")
        print(f"  Environment: {settings.ENVIRONMENT}")
        print()

        print("Creating database tables...")
        create_tables()
        print("✓ Database tables created successfully")
        print()

        # Optionally seed data if SEED_DATA environment variable is set
        seed_data = os.getenv('SEED_DATA', '').lower() in ('true', '1', 'yes')
        if seed_data:
            print("Seeding initial data...")
            try:
                from app.utils.seed_data import seed_database
                seed_database()
                print("✓ Database seeded successfully")
            except ImportError:
                print("Note: Seed data module not found, skipping...")
            except Exception as e:
                print(f"Note: Seed data error: {e}")
                print("Continuing without seed data...")
            print()

        print("=" * 50)
        print("Database initialization completed successfully!")
        print("=" * 50)
        return 0

    except Exception as e:
        print()
        print("✗ Error initializing database:")
        print(f"  {type(e).__name__}: {e}")
        print()

        # Import settings for diagnostic info
        try:
            from app.core.config import settings
            print("Current Configuration:")
            print(f"  DB_HOST: {settings.DB_HOST}")
            print(f"  DB_PORT: {settings.DB_PORT}")
            print(f"  DB_NAME: {settings.DB_NAME}")
            print(f"  DB_USER: {settings.DB_USER}")
            print(f"  Environment: {settings.ENVIRONMENT}")
            print()
        except:
            pass

        print("Please check:")
        print("  1. MySQL is running and accessible")
        print("  2. Database 'ceramic_marketplace' exists")
        print("  3. Database credentials in .env are correct")
        print("  4. Python dependencies are installed (pip install -r requirements.txt)")
        print("  5. If using 'localhost', ensure MySQL accepts local connections")
        print("  6. If using 'db', ensure you're running inside Docker network")
        print()

        # Connection test
        import socket
        try:
            from app.core.config import settings
            print(f"Testing DNS resolution for '{settings.DB_HOST}'...")
            ip = socket.gethostbyname(settings.DB_HOST)
            print(f"  ✓ Resolved to: {ip}")
        except socket.gaierror as dns_err:
            print(f"  ✗ DNS resolution failed: {dns_err}")
            print(f"  Hint: Hostname '{settings.DB_HOST}' cannot be resolved")
        except:
            pass
        print()

        return 1

if __name__ == "__main__":
    sys.exit(main())
