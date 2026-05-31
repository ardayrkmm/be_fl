import json
import os


class FirebaseService:
    _initialized = False

    @classmethod
    def _initialize(cls):
        if cls._initialized:
            return True

        try:
            import firebase_admin
            from firebase_admin import credentials

            if firebase_admin._apps:
                cls._initialized = True
                return True

            credentials_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
            credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

            if credentials_json:
                cred = credentials.Certificate(json.loads(credentials_json))
            elif credentials_path:
                cred = credentials.Certificate(credentials_path)
            else:
                print("[FCM] Firebase credentials belum dikonfigurasi")
                return False

            firebase_admin.initialize_app(cred)
            cls._initialized = True
            return True

        except Exception as e:
            print(f"[FCM] Gagal inisialisasi Firebase: {e}")
            return False

    @classmethod
    def send_push(cls, token, title, body, data=None):
        if not token:
            return {
                "success": False,
                "message": "FCM token kosong"
            }

        if not cls._initialize():
            return {
                "success": False,
                "message": "Firebase belum siap"
            }

        try:
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data={
                    key: "" if value is None else str(value)
                    for key, value in (data or {}).items()
                },
                token=token,
            )

            response = messaging.send(message)
            return {
                "success": True,
                "message": "Push notification berhasil dikirim",
                "response": response
            }

        except Exception as e:
            print(f"[FCM] Gagal kirim push: {e}")
            return {
                "success": False,
                "message": "Gagal kirim push notification",
                "error": str(e)
            }
