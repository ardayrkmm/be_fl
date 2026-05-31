from app import create_app
from models import db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    columns = inspector.get_columns('jadwal_latihan_users')
    for col in columns:
        print(f"Column: {col['name']}, Type: {col['type']}")
