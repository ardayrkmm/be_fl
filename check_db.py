from app import create_app
from models import db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    columns = inspector.get_columns('users')
    column_names = [col['name'] for col in columns]
    print("Columns in users table in DB:", column_names)
