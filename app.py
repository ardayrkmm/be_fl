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

    db.init_app(app)
    JWTManager(app)

    socketio.init_app(app)

    register_routes(app)

    with app.app_context():
        import controller.poseController

    basedir = os.path.abspath(os.path.dirname(__file__))
    upload_folder = os.path.join(basedir, 'uploads')

    @app.route('/uploads/<path:filename>')
    def serve_uploads(filename):
        return send_from_directory(upload_folder, filename)

    return app


if __name__ == "__main__":
    app = create_app()
    print("🚀 Starting Flask-SocketIO Server (Threading Mode)...")

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True
    )
