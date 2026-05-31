from models import db
from models import HistoryAktifitas, HistoryAktifitasDetail, JadwalLatihanUser, Notifikasi, generate_random_id
import uuid

class ActivityService:
    @staticmethod
    def submit_activity(data):
        id_user = data.get('id_user')
        id_jadwal = data.get('id_jadwal')
        vas_sebelum = data.get('vas_sebelum', 0)
        vas_sesudah = data.get('vas_sesudah', 0)
        durasi_total = data.get('durasi_total', 0)
        akurasi_total = data.get('akurasi_total', 0)
        details = data.get('details', [])

        if not id_jadwal:
            return {"status": "error", "message": "id_jadwal harus diisi"}, 400

        try:
            db.session.begin() # Start transaction
            
            # Validasi Jadwal User
            jadwal = JadwalLatihanUser.query.filter_by(id_jadwal=id_jadwal).first()
            if not jadwal:
                db.session.rollback()
                return {"status": "error", "message": "Jadwal tidak ditemukan"}, 404
                
            if jadwal.id_user != id_user:
                db.session.rollback()
                return {"status": "error", "message": "Akses Ditolak"}, 403

            delta_vas = vas_sesudah - vas_sebelum

            # --- Rule-Based Re-Assessment Pasca Latihan ---
            # status: 'stop' → nyeri kritis, 'warning' → nyeri naik, 'done' → normal
            status_sesi = "done"
            rekomendasi = None

            if vas_sesudah >= 7 or delta_vas > 3:
                status_sesi = "stop"
                rekomendasi = "Disarankan konsultasi ke dokter"
                jadwal.status = "Stopped"

                id_notif = generate_random_id(4)
                notif = Notifikasi(
                    id_notifikasi=id_notif,
                    id_user=id_user,
                    judul="Peringatan Kritis Peningkatan Nyeri",
                    pesan=f"Nyeri Anda meningkat drastis usai latihan. Segera hentikan program latihan Anda. {rekomendasi}.",
                    tipe="warning"
                )
                db.session.add(notif)

            elif delta_vas > 2:
                status_sesi = "warning"

                id_notif = generate_random_id(4)
                notif = Notifikasi(
                    id_notifikasi=id_notif,
                    id_user=id_user,
                    judul="Peringatan Nyeri",
                    pesan=f"Nyeri Anda meningkat ({vas_sebelum} ke {vas_sesudah}) usai latihan. Istirahatkan sendi jika perlu.",
                    tipe="warning"
                )
                db.session.add(notif)

            id_history = str(uuid.uuid4())[:8].upper()
            history = HistoryAktifitas(
                id_history=id_history,
                id_user=id_user,
                id_jadwal=id_jadwal,
                durasi_total=durasi_total,
                akurasi_total=akurasi_total,
                status=status_sesi,
                vas_sebelum=vas_sebelum,
                vas_sesudah=vas_sesudah,
                delta_vas=delta_vas,
                rekomendasi=rekomendasi
            )

            db.session.add(history)

            for d in details:
                id_history_detail = str(uuid.uuid4())[:8].upper()
                detail = HistoryAktifitasDetail(
                    id_history_detail=id_history_detail,
                    id_history=id_history,
                    id_latihan=d.get('id_latihan'),
                    sisi=d.get('sisi'),
                    set_tercapai=d.get('set_tercapai', 0),
                    repetisi_tercapai=d.get('repetisi_tercapai', 0),
                    durasi_latihan=d.get('durasi_latihan', 0),
                    jumlah_gerakan_benar=d.get('jumlah_gerakan_benar', 0),
                    jumlah_gerakan_salah=d.get('jumlah_gerakan_salah', 0),
                    akurasi_latihan=d.get('akurasi_latihan', 0)
                )
                db.session.add(detail)

            # Tandai jadwal selesai jika tidak distop
            if status_sesi != "stop":
                jadwal.status = "Completed"

            db.session.commit()

            return {
                "status": "success",
                "delta_vas": delta_vas,
                "status_sesi": status_sesi,       # 'done' | 'warning' | 'stop'
                "warning": status_sesi == "warning",
                "stop_program": status_sesi == "stop",
                "rekomendasi": rekomendasi,
                "message": "Aktivitas berhasil disimpan"
            }, 200

        except Exception as e:
            db.session.rollback()
            return {"status": "error", "message": "Internal Server Error", "error_detail": str(e)}, 500

    @staticmethod
    def get_history(id_user):
        try:
            histories = db.session.query(HistoryAktifitas, JadwalLatihanUser).join(
                JadwalLatihanUser, HistoryAktifitas.id_jadwal == JadwalLatihanUser.id_jadwal
            ).filter(HistoryAktifitas.id_user == id_user).order_by(HistoryAktifitas.tanggal.desc()).all()

            data = []
            for h, j in histories:
                data.append({
                    "tanggal": h.tanggal.strftime("%Y-%m-%d"),
                    "fase": j.fase,
                    "vas_sebelum": h.vas_sebelum or 0,
                    "vas_sesudah": h.vas_sesudah or 0,
                    "delta_vas": h.delta_vas or 0,
                    "status_sesi": h.status,               # 'done' | 'warning' | 'stop'
                    "warning": h.status == "warning",
                    "stop_program": h.status == "stop",
                    "rekomendasi": h.rekomendasi,
                    "akurasi_total": h.akurasi_total
                })

            return {"status": "success", "data": data}, 200

        except Exception as e:
            return {"status": "error", "message": "Internal Server Error"}, 500
