# import eventlet
# eventlet.monkey_patch()
# from flask import Flask, send_from_directory
# from routes import register_routes
# from models import db
# from flask_jwt_extended import JWTManager
# import os
# from dotenv import load_dotenv
# from extensions import socketio # Import extension

# load_dotenv()

# def create_app():
#     app = Flask(__name__)

#     app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "secret-key")
    
#     # Load DB config from .env
#     db_user = os.getenv("DB_USER", "root")
#     db_pass = os.getenv("DB_PASS", "") 
#     db_host = os.getenv("DB_HOST", "localhost")
#     db_name = os.getenv("DB_NAME", "fisio_app")
    
#     app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}"
#     app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

#     db.init_app(app)
#     JWTManager(app)
    
#     # Initialize SocketIO
#     socketio.init_app(app)

#     register_routes(app)
    
#     # Register WebSocket Events
#     with app.app_context():
#         import controller.poseController

#     # STATIC FILES SERVING (UPLOADS)
#     # Get absolute path to uploads folder
#     # Assuming uploads is in the same directory as app.py
#     basedir = os.path.abspath(os.path.dirname(__file__))
#     upload_folder = os.path.join(basedir, 'uploads')

#     @app.route('/uploads/<path:filename>')
#     def serve_uploads(filename):
#         return send_from_directory(upload_folder, filename)

#     return app


# # 👇 ENTRY POINT
# if __name__ == "__main__":
#     app = create_app()
#     print("🚀 Starting Flask-SocketIO Server...")
#     # ⚠️ FIX: Debug=False prevents reloader interference with Eventlet on Windows
#     # ⚠️ FIX: log_output=True helps see request status
#     socketio.run(
#         app,
#         host="0.0.0.0", 
#         port=5000, 
#         debug=True,
#         log_output=True
#     )

from flask import Flask, send_from_directory
from routes import register_routes
from models import db
from flask_jwt_extended import JWTManager
import os
from dotenv import load_dotenv
from extensions import socketio
import socket
from flask_migrate import Migrate
from marshmallow import ValidationError
load_dotenv()


def create_app():
    
    app = Flask(__name__)

    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "secret-key")

    db_user = os.getenv("DB_USER", "root")
    db_pass = os.getenv("DB_PASS", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_name = os.getenv("DB_NAME", "fisio_app")

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    migrate = Migrate(app, db)
    db.init_app(app)
    jwt = JWTManager(app)

    from flask import jsonify
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"status": "error", "message": "Token tidak valid"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"status": "error", "message": "Token tidak valid"}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"status": "error", "message": "Token tidak valid"}), 401

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify({
            "message": "Validasi gagal. Periksa kembali data yang kamu isi."
        }), 422

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            "message": "Data atau endpoint yang diminta tidak ditemukan."
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            "message": "Metode request tidak didukung."
        }), 405

    @app.errorhandler(500)
    def handle_internal_server_error(error):
        return jsonify({
            "message": "Sistem sedang mengalami gangguan. Silakan coba lagi nanti."
        }), 500

    socketio.init_app(app)

    register_routes(app)

    import controller.poseController

    basedir = os.path.abspath(os.path.dirname(__file__))
    upload_folder = os.path.join(basedir, 'uploads')

    @app.route('/uploads/<path:filename>')
    def serve_uploads(filename):
        return send_from_directory(upload_folder, filename)

    return app


if __name__ == "__main__":
    app = create_app()
    
    # Fungsi untuk mendapatkan IP lokal PC/Laptop di jaringan Wi-Fi
    def get_local_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Tidak benar-benar melakukan koneksi, hanya untuk memicu interface jaringan
            s.connect(('8.8.8.8', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    local_ip = get_local_ip()
    port = 5000

    print("\n" + "="*50)
    print(f"🚀 Flask-SocketIO Server Aktif!")
    print(f"🔗 Akses Lokal: http://localhost:{port}")
    print(f"📱 Akses dari HP: http://{local_ip}:{port}")
    print("="*50 + "\n")

    # Pastikan host tetap "0.0.0.0" agar bisa diakses dari perangkat luar
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=True
    )
