from app import create_app
from models import db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    for table_name in ['jadwal_latihan_details', 'history_aktifitas']:
        columns = inspector.get_columns(table_name)
        print(f"\n--- {table_name} ---")
        for col in columns:
            if 'jadwal' in col['name'] or 'id' in col['name']:
                print(f"Column: {col['name']}, Type: {col['type']}")
