from models import db
from models import KondisiUser, Latihan, JadwalLatihanUser, JadwalLatihanDetail
from sqlalchemy.orm import load_only
from datetime import datetime
import uuid

class ScheduleService:
    @staticmethod
    def generate_schedule(data):
        id_user = data.get('id_user')
        id_form = data.get('id_form')
        
        try:
            db.session.begin() # Start transaction
            
            if not id_form:
                # Auto-fetch the latest condition if id_form is missing (Backward compatibility)
                kondisi = KondisiUser.query.filter_by(id_user=id_user).order_by(KondisiUser.created_at.desc()).first()
                if not kondisi:
                    db.session.rollback()
                    return {"status": "error", "message": "Isi form kondisi terlebih dahulu"}, 404
                id_form = kondisi.id_form
            else:
                # Ambil kondisi user berdasarkan assessment sebelumnya
                kondisi = KondisiUser.query.filter_by(id_form=id_form).first()
                if not kondisi:
                    db.session.rollback()
                    return {"status": "error", "message": "Data assessment (kondisi) tidak ditemukan"}, 404
                    
                if kondisi.id_user != id_user:
                    db.session.rollback()
                    return {"status": "error", "message": "Akses Ditolak"}, 403
                
            # Ambil fase berdasarkan lama_nyeri (disimpan pada waktu_kejadian)
            lama_nyeri_hari = kondisi.waktu_kejadian or 0
            if lama_nyeri_hari < 3:
                fase = 'F1'
            elif 3 <= lama_nyeri_hari <= 20:
                fase = 'F2'
            else:
                fase = 'F3'
                
            # Ambil latihan, gunakan load_only untuk efisiensi jika memungkinkan (di sini cukup id_latihan)
            latihans = Latihan.query.options(load_only(Latihan.id_latihan)).filter_by(fase=fase).all()
            if not latihans:
                db.session.rollback()
                return {"status": "error", "message": f"Tidak ada latihan yang tersedia untuk fase {fase}"}, 404
                
            id_jadwal = str(uuid.uuid4())[:8].upper()
            
            jadwal = JadwalLatihanUser(
                id_jadwal=id_jadwal,
                id_user=id_user,
                id_form=id_form,
                fase=fase,
                fase_label=fase,
                nama_jadwal=fase,
                tanggal=datetime.utcnow(),
                status="Pending"
            )
            
            db.session.add(jadwal)
            db.session.flush() 
            
            urutan = 1
            for l in latihans:
                id_detail = str(uuid.uuid4())[:8].upper()
                detail = JadwalLatihanDetail(
                    id_detail=id_detail,
                    id_jadwal=id_jadwal,
                    id_latihan=l.id_latihan,
                    urutan=urutan,
                    status_eksekusi=False
                )
                db.session.add(detail)
                urutan += 1
                
            db.session.commit()
            
            return {
                "status": "success",
                "id_jadwal": id_jadwal,
                "fase": fase,
                "jumlah_latihan": len(latihans)
            }, 200
            
        except Exception as e:
            db.session.rollback()
            import traceback
            error_details = traceback.format_exc()
            print("ERROR IN GENERATE SCHEDULE:", error_details)
            return {"status": "error", "message": "Internal Server Error", "detail": str(e), "traceback": error_details}, 500
