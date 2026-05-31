# app/routes.py
from controller.authController import auth_bp
from controller.bagianController import bagian_bp
from controller.JadwalController import latihanuser_bp
from controller.questionController import question_bp
from controller.InputKondisi import kondisi_bp
from controller.HistoryController import history_bp
from controller.notification_controller import notification_bp

def register_routes(app):
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(bagian_bp, url_prefix="/api")
    app.register_blueprint(latihanuser_bp, url_prefix="/api/latihanuser")
    app.register_blueprint(question_bp, url_prefix="/api")
    app.register_blueprint(kondisi_bp, url_prefix="/api")
    app.register_blueprint(history_bp, url_prefix="/api")
    
    
    app.register_blueprint(notification_bp, url_prefix="/api")
