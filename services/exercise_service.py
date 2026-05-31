from models import Latihan, LatihanBagian, KondisiUser
from sqlalchemy.orm import load_only

class ExerciseService:
    @staticmethod
    def get_exercises_by_fase(fase, user_id):
        try:
            kondisi = KondisiUser.query.filter_by(id_user=user_id).order_by(KondisiUser.created_at.desc()).first()
            if not kondisi or not kondisi.id_bagian:
                return {"status": "error", "message": "bagian tubuh tidak ditemukan"}, 404
                
            latihans = (Latihan.query
                .join(LatihanBagian, LatihanBagian.id_latihan == Latihan.id_latihan)
                .options(
                    load_only(
                        Latihan.id_latihan, Latihan.nama_latihan, Latihan.target_set,
                        Latihan.target_repetisi, Latihan.hold_detik, Latihan.rest_set_detik,
                        Latihan.video_url
                    )
                )
                .filter(Latihan.fase == fase, LatihanBagian.id_bagian == kondisi.id_bagian)
                .all()
            )
            
            data = []
            for l in latihans:
                data.append({
                    "id_latihan": l.id_latihan,
                    "nama_latihan": l.nama_latihan,
                    "target_set": l.target_set,
                    "target_repetisi": l.target_repetisi,
                    "hold_detik": l.hold_detik,
                    "rest_set_detik": l.rest_set_detik,
                    "video_url": l.video_url
                })
                
            return {
                "status": "success",
                "fase": fase,
                "data": data
            }, 200
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
