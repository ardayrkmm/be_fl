from app import create_app
from models import db, JadwalLatihanUser
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("UPDATE jadwal_latihan_users SET status='Pending' WHERE status='Unlocked';"))
        db.session.commit()
        print("Successfully updated old schedules to Pending.")
    except Exception as e:
        print("Failed to update table:", str(e))
