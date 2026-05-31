from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE kondisi_users ADD COLUMN id_bagian VARCHAR(4);"))
        print("Added id_bagian")
    except Exception as e:
        print("Failed to add id_bagian:", e)
        
    try:
        db.session.execute(text("ALTER TABLE kondisi_users CHANGE bengkak_besar_cepat bengkak_cepat_besar BOOLEAN;"))
        print("Renamed bengkak_besar_cepat")
    except Exception as e:
        print("Failed to rename bengkak_besar_cepat:", e)

    db.session.commit()
    print("Done")
