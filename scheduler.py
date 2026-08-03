import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, Notifikasi, User
from services.firebase_service import FirebaseService

def send_scheduled_notifications(app):
    with app.app_context():
        try:
            now = datetime.utcnow()
            # Find unsent notifications whose scheduled time has arrived or passed
            pending_notifications = Notifikasi.query.filter(
                Notifikasi.is_sent == False,
                Notifikasi.jadwal_kirim <= now
            ).all()

            if not pending_notifications:
                return

            print(f"[Scheduler] Found {len(pending_notifications)} pending notifications to send.")

            for notif in pending_notifications:
                user = User.query.get(notif.id_user)
                if user and user.fcm_token:
                    # Construct notification payload
                    data = {
                        "id_notifikasi": str(notif.id_notifikasi),
                        "id_jadwal": str(notif.id_jadwal or ""),
                        "tipe": str(notif.tipe or "reminder")
                    }
                    
                    res = FirebaseService.send_push(
                        token=user.fcm_token,
                        title=notif.judul or "Reminder Latihan",
                        body=notif.pesan or "Saatnya latihan",
                        data=data
                    )
                    
                    if res.get("success"):
                        notif.is_sent = True
                        db.session.commit()
                        print(f"[Scheduler] Sent notification {notif.id_notifikasi} to user {user.id_user}")
                    else:
                        print(f"[Scheduler] Failed to send notification {notif.id_notifikasi}: {res.get('message')}")
                else:
                    print(f"[Scheduler] Skipped notification {notif.id_notifikasi}: user or FCM token not found.")
        except Exception as e:
            print(f"[Scheduler] Error running notification job: {e}")

def init_scheduler(app):
    # Avoid running multiple scheduler threads in Flask reload/debug mode
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    scheduler = BackgroundScheduler()
    
    # Run every 15 minutes
    scheduler.add_job(
        func=send_scheduled_notifications,
        trigger="interval",
        seconds=15000,
        args=[app],
        id="scheduled_notifications_job"
    )
    
    scheduler.start()
    print("Background Scheduler started for pending notifications.")
