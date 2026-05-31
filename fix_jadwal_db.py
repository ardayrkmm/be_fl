from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
        db.session.execute(text("ALTER TABLE jadwal_latihan_users MODIFY id_jadwal VARCHAR(8);"))
        db.session.execute(text("SET FOREIGN_KEY_CHECKS=1;"))
        db.session.commit()
        print("Successfully updated id_jadwal length to 8 characters.")
    except Exception as e:
        print("Failed to alter table:", str(e))
