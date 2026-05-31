

from models import db, Notifikasi, User, generate_random_id
from datetime import datetime
from services.firebase_service import FirebaseService

class NotificationService:

    @staticmethod
    def _format_notification(n):
        return {
            "id_notifikasi": n.id_notifikasi,
            "judul": n.judul,
            "pesan": n.pesan,
            "tipe": n.tipe,
            "status_baca": n.status_baca,
            "is_sent": n.is_sent,
            "jadwal_kirim": n.jadwal_kirim.strftime("%Y-%m-%d %H:%M") if n.jadwal_kirim else None,
            "id_jadwal": n.id_jadwal,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else None
        }

    @staticmethod
    def save_fcm_token(id_user, fcm_token):
        user = User.query.get(id_user)

        if not user:
            return {"success": False, "message": "User tidak ditemukan"}, 404

        user.fcm_token = fcm_token
        db.session.commit()

        return {"success": True, "message": "FCM token berhasil disimpan"}, 200

    @staticmethod
    def create_notification(data):
        try:
            notif = Notifikasi(
                id_notifikasi=generate_random_id(4),
                id_user=data["id_user"],
                judul=data.get("judul"),
                pesan=data.get("pesan"),
                tipe=data.get("tipe", "general"),
                jadwal_kirim=data.get("jadwal_kirim"),
                id_jadwal=data.get("id_jadwal"),
                is_sent=False
            )

            db.session.add(notif)
            db.session.commit()

            return {
                "success": True,
                "message": "Notifikasi berhasil dibuat",
                "data": NotificationService._format_notification(notif)
            }, 201

        except Exception as e:
            db.session.rollback()
            return {
                "success": False,
                "message": "Gagal membuat notifikasi",
                "error": str(e)
            }, 500

    @staticmethod
    def create_notification_and_push(data):
        try:
            notif = Notifikasi(
                id_notifikasi=generate_random_id(4),
                id_user=data["id_user"],
                judul=data.get("judul"),
                pesan=data.get("pesan"),
                tipe=data.get("tipe", "general"),
                jadwal_kirim=data.get("jadwal_kirim"),
                id_jadwal=data.get("id_jadwal"),
                is_sent=False
            )

            db.session.add(notif)
            db.session.commit()

            push_result = {
                "success": False,
                "message": "User tidak memiliki FCM token"
            }

            user = User.query.get(data["id_user"])
            if user and user.fcm_token:
                push_result = FirebaseService.send_push(
                    token=user.fcm_token,
                    title=notif.judul or "Notifikasi",
                    body=notif.pesan or "",
                    data={
                        "id_notifikasi": notif.id_notifikasi,
                        "id_jadwal": notif.id_jadwal,
                        "tipe": notif.tipe,
                    }
                )

                if push_result.get("success"):
                    notif.is_sent = True
                    db.session.commit()

            return {
                "success": True,
                "message": "Notifikasi berhasil dibuat",
                "data": NotificationService._format_notification(notif),
                "push": push_result
            }, 201

        except Exception as e:
            db.session.rollback()
            return {
                "success": False,
                "message": "Gagal membuat notifikasi",
                "error": str(e)
            }, 500

    @staticmethod
    def get_user_notifications(id_user):
        notifs = Notifikasi.query.filter_by(id_user=id_user)\
            .order_by(Notifikasi.created_at.desc()).all()

        result = []
        for n in notifs:
            result.append(NotificationService._format_notification(n))

        return {"success": True, "data": result}, 200

    @staticmethod
    def mark_as_read(id_notifikasi, user_id):
        notif = Notifikasi.query.filter_by(
            id_notifikasi=id_notifikasi,
            id_user=user_id
        ).first()

        if not notif:
            return {"success": False, "message": "Notifikasi tidak ditemukan"}, 404

        notif.status_baca = True
        db.session.commit()

        return {"success": True, "message": "Notifikasi dibaca"}, 200

    @staticmethod
    def mark_all_as_read(id_user):
        Notifikasi.query.filter_by(id_user=id_user, status_baca=False).update({
            "status_baca": True
        })
        db.session.commit()

        return {"success": True, "message": "Semua notifikasi dibaca"}, 200

    @staticmethod
    def delete_notification(id_notifikasi, id_user):
        notif = Notifikasi.query.filter_by(
            id_notifikasi=id_notifikasi,
            id_user=id_user
        ).first()

        if not notif:
            return {"success": False, "message": "Notifikasi tidak ditemukan"}, 404

        db.session.delete(notif)
        db.session.commit()

        return {"success": True, "message": "Notifikasi berhasil dihapus"}, 200
