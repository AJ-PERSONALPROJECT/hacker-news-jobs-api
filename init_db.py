"""
Database initialization script.
Run this to create the database tables.
"""
from app import app, db

def init_database():
    """Initialize the database with all tables"""
    with app.app_context():
        db.create_all()
        print("Database initialized successfully!")
        print(f"Database location: {app.config['SQLALCHEMY_DATABASE_URI']}")

if __name__ == "__main__":
    init_database()

