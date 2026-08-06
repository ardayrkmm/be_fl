from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt
from marshmallow import ValidationError
from datetime import datetime, timedelta
from email.message import EmailMessage
import os
import random
import re
import smtplib
import bcrypt
import jwt as pyjwt
from jwt import ExpiredSignatureError, InvalidTokenError


from models import User, db
from auth.schemas import LoginRequestSchema, RegisterRequestSchema
from middleware.jwt_middleware import generate_token, get_user_id_from_jwt

auth_bp = Blueprint("auth", __name__)


def error_response(message, status_code, error=None):
    payload = {"message": message}
    if error:
        payload["error"] = error
    return jsonify(payload), status_code


@auth_bp.errorhandler(ValidationError)
def handle_auth_validation_error(error):
    return error_response(
        "Validasi gagal. Periksa kembali data yang kamu isi.",
        422,
        "Validation error"
    )


def generate_verification_code():
    return f"{random.randint(0, 999999):06d}"


def generate_verification_token(user_id, email, code):
    secret_key = current_app.config.get("JWT_SECRET_KEY") or current_app.config.get("SECRET_KEY")
    payload = {
        "user_id": user_id,
        "email": email,
        "code": code,
        "type": "email_verification",
        "exp": datetime.utcnow() + timedelta(minutes=10)
    }

    return pyjwt.encode(payload, secret_key, algorithm="HS256")


def generate_reset_token(user, code):
    secret_key = current_app.config.get("JWT_SECRET_KEY") or current_app.config.get("SECRET_KEY")
    payload = {
        "id_user": user.id_user,
        "email": user.email,
        "reset_code": code,
        "purpose": "reset_password",
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }

    return pyjwt.encode(payload, secret_key, algorithm="HS256")


def decode_reset_token(reset_token):
    secret_key = current_app.config.get("JWT_SECRET_KEY") or current_app.config.get("SECRET_KEY")
    payload = pyjwt.decode(reset_token, secret_key, algorithms=["HS256"])
    if payload.get("purpose") != "reset_password":
        raise InvalidTokenError("Invalid reset token purpose")
    return payload


def build_email_template(title, description, code, expiry_text, note_text):
    logo_url = os.getenv("APP_LOGO_URL")
    if logo_url:
        logo_html = f'<img src="{logo_url}" alt="PhysioMove" class="logo-img" style="max-height: 50px; width: auto; vertical-align: middle;">'
    else:
        logo_html = '<div class="logo-text" style="color: #FFFFFF; font-size: 28px; font-weight: 800; letter-spacing: 1px; margin: 0; font-family: \'Outfit\', \'Inter\', \'Segoe UI\', sans-serif;">PhysioMove</div>'

    current_year = datetime.now().year
    
    html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #F5F6FD;
            color: #2B2B2C;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: #FFFFFF;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
            border: 1px solid #e2e8f0;
        }}
        .header {{
            background: linear-gradient(135deg, #2C3BC1 0%, #5D54FF 100%);
            padding: 35px 30px;
            text-align: center;
        }}
        .logo-text {{
            color: #FFFFFF;
            font-size: 28px;
            font-weight: 800;
            letter-spacing: 1px;
            margin: 0;
            font-family: 'Outfit', 'Inter', 'Segoe UI', sans-serif;
        }}
        .logo-img {{
            max-height: 50px;
            width: auto;
            vertical-align: middle;
        }}
        .content {{
            padding: 40px 30px;
            text-align: center;
        }}
        .content h1 {{
            color: #2B2B2C;
            font-size: 22px;
            font-weight: 700;
            margin-top: 0;
            margin-bottom: 16px;
        }}
        .content p {{
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 24px;
            color: #626262;
        }}
        .code-container {{
            background-color: #F5F6FD;
            border: 2px dashed #5D54FF;
            border-radius: 12px;
            padding: 20px;
            margin: 30px auto;
            max-width: 280px;
        }}
        .code-text {{
            font-size: 36px;
            font-weight: 800;
            letter-spacing: 6px;
            color: #2C3BC1;
            margin: 0;
            font-family: 'Courier New', Courier, monospace;
        }}
        .expiry {{
            font-size: 14px;
            color: #626262;
            font-weight: 500;
            margin-top: 10px;
        }}
        .footer {{
            background-color: #F5F6FD;
            padding: 24px 30px;
            text-align: center;
            font-size: 12px;
            color: #626262;
            border-top: 1px solid #e2e8f0;
        }}
        .footer p {{
            margin: 4px 0;
            font-size: 12px;
            color: #626262;
        }}
        .disclaimer {{
            margin-top: 16px;
            font-style: italic;
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #F5F6FD; color: #2B2B2C; -webkit-font-smoothing: antialiased;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #F5F6FD; padding: 20px 0;">
        <tr>
            <td align="center">
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #FFFFFF; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                    <!-- Header -->
                    <tr>
                        <td align="center" style="background: linear-gradient(135deg, #2C3BC1 0%, #5D54FF 100%); padding: 35px 30px;">
                            {logo_html}
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td align="center" style="padding: 40px 30px;">
                            <h1 style="color: #2B2B2C; font-size: 22px; font-weight: 700; margin-top: 0; margin-bottom: 16px; font-family: 'Segoe UI', sans-serif;">{title}</h1>
                            <p style="font-size: 16px; line-height: 1.6; margin-bottom: 24px; color: #626262; font-family: 'Segoe UI', sans-serif;">{description}</p>
                            
                            <!-- OTP Box -->
                            <table border="0" cellpadding="0" cellspacing="0" style="margin: 30px auto; max-width: 280px; width: 100%;">
                                <tr>
                                    <td align="center" style="background-color: #F5F6FD; border: 2px dashed #5D54FF; border-radius: 12px; padding: 20px;">
                                        <span style="font-size: 36px; font-weight: 800; letter-spacing: 6px; color: #2C3BC1; font-family: 'Courier New', Courier, monospace;">{code}</span>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="font-size: 14px; color: #626262; font-weight: 500; margin-top: 10px; font-family: 'Segoe UI', sans-serif;">Kode ini berlaku selama <strong>{expiry_text}</strong>.</p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td align="center" style="background-color: #F5F6FD; padding: 24px 30px; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 4px 0; font-size: 12px; color: #626262; font-family: 'Segoe UI', sans-serif;">&copy; {current_year} PhysioMove. All rights reserved.</p>
                            <p style="margin: 16px 0 4px 0; font-size: 12px; color: #626262; font-family: 'Segoe UI', sans-serif; font-style: italic;">{note_text}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    return html_content


def send_reset_password_email(to_email, code):
    mail_server = os.getenv("MAIL_SERVER")
    mail_port = os.getenv("MAIL_PORT")
    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")

    if not mail_server or not mail_port or not mail_username or not mail_password:
        current_app.logger.warning("Konfigurasi email belum lengkap untuk kirim kode reset password")
        return False

    msg = EmailMessage()
    msg["Subject"] = "Kode Reset Password PhysioMove"
    msg["From"] = mail_username
    msg["To"] = to_email
    
    # Fallback plain text
    plain_text = (
        f"Kode reset password PhysioMove Anda adalah: {code}\n\n"
        "Kode ini berlaku selama 15 menit.\n\n"
        "Jika kamu tidak meminta reset password, abaikan email ini."
    )
    msg.set_content(plain_text)
    
    # HTML version
    title = "Reset Password Akun"
    description = "Masukkan kode berikut di aplikasi PhysioMove untuk melanjutkan proses reset password."
    expiry_text = "15 menit"
    note_text = "Jika kamu tidak meminta reset password, abaikan email ini."
    
    html_body = build_email_template(title, description, code, expiry_text, note_text)
    msg.add_alternative(html_body, subtype="html")

    port = int(mail_port)

    if port == 465:
        with smtplib.SMTP_SSL(mail_server, port) as server:
            server.login(mail_username, mail_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(mail_server, port) as server:
            server.starttls()
            server.login(mail_username, mail_password)
            server.send_message(msg)
    return True


def send_verification_email(to_email, code):
    mail_server = os.getenv("MAIL_SERVER")
    mail_port = os.getenv("MAIL_PORT")
    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")

    if not mail_server or not mail_port or not mail_username or not mail_password:
        raise ValueError("Konfigurasi email belum lengkap")

    msg = EmailMessage()
    msg["Subject"] = "Kode Verifikasi Email PhysioMove"
    msg["From"] = mail_username
    msg["To"] = to_email
    
    # Fallback plain text
    plain_text = (
        f"Kode verifikasi email PhysioMove Anda adalah: {code}\n\n"
        "Kode ini berlaku selama 10 menit.\n\n"
        "Jika kamu tidak merasa membuat akun PhysioMove, abaikan email ini."
    )
    msg.set_content(plain_text)
    
    # HTML version
    title = "Verifikasi Email Akun"
    description = "Masukkan kode berikut di aplikasi PhysioMove untuk menyelesaikan proses verifikasi email."
    expiry_text = "10 menit"
    note_text = "Jika kamu tidak merasa membuat akun PhysioMove, abaikan email ini."
    
    html_body = build_email_template(title, description, code, expiry_text, note_text)
    msg.add_alternative(html_body, subtype="html")

    port = int(mail_port)

    if port == 465:
        with smtplib.SMTP_SSL(mail_server, port) as server:
            server.login(mail_username, mail_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(mail_server, port) as server:
            server.starttls()
            server.login(mail_username, mail_password)
            server.send_message(msg)



@auth_bp.route("/login", methods=["POST"])
def login():
    if not request.is_json or not request.json:
        return error_response("Email dan password wajib diisi.", 400, "Invalid payload")

    data = LoginRequestSchema().load(request.json)

    email = data["email"].lower().strip()

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(data["password"]):
        return error_response(
            "Email atau password yang kamu masukkan belum sesuai.",
            401,
            "Authentication failed"
        )

    if user.verifikasi_status != 1:
        return error_response(
            "Akun belum diverifikasi. Silakan cek kode verifikasi email kamu.",
            403,
            "Account not verified"
        )

    token = generate_token(user.id_user, user.email, user.nama)

    return jsonify({
        "message": "Login successful",
        "user": user.to_public_user(),
        "token": token
    }), 200


@auth_bp.route("/register", methods=["POST"])
def register():
    if not request.is_json or not request.json:
        return error_response("Data registrasi wajib diisi.", 400, "Invalid payload")

    data = RegisterRequestSchema().load(request.json)

    email = data["email"].lower().strip()

    if User.query.filter_by(email=email).first():
        return error_response(
            "Email sudah terdaftar. Silakan gunakan email lain atau login.",
            409,
            "Email already registered"
        )

    user = User(
        nama=data["nama"].strip(),
        email=email,
        password=data["password"],
        no_telepon=data["no_telepon"],
        role="user",
        verifikasi_status=0,
        img_url='uploads/pl.jpg'
    )

    db.session.add(user)
    db.session.flush()

    token = generate_token(user.id_user, user.email, user.nama)
    verification_code = generate_verification_code()
    verification_token = generate_verification_token(
        user.id_user,
        user.email,
        verification_code
    )

    try:
        send_verification_email(user.email, verification_code)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return error_response(
            "Sistem sedang mengalami gangguan. Silakan coba lagi nanti.",
            500,
            "Failed to send verification email"
        )

    return jsonify({
        "message": "Registrasi berhasil",
        "user": user.to_public_user(),
        "token": token,
        "verification_token": verification_token
    }), 201


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    try:
        if not request.is_json or not request.json:
            return jsonify({"message": "Email wajib diisi."}), 400

        email_raw = request.json.get("email")
        if not email_raw:
            return jsonify({"message": "Email wajib diisi."}), 400

        email = email_raw.lower().strip()
        user = User.query.filter_by(email=email).first()

        if not user:
            return jsonify({
                "message": "Email belum terdaftar. Silakan buat akun terlebih dahulu."
            }), 404

        reset_code = generate_verification_code()
        
        # Development check
        is_development = (
            current_app.config.get("ENV") == "development"
            or current_app.debug
            or current_app.testing
            or current_app.config.get("TESTING")
            or os.getenv("FLASK_ENV") == "development"
            or os.getenv("FLASK_DEBUG") in ["1", "true", "True"]
        )

        if is_development:
            print(f"RESET PASSWORD CODE for {email}: {reset_code}")

        reset_token = generate_reset_token(user, reset_code)

        email_sent = False
        try:
            email_sent = send_reset_password_email(user.email, reset_code)
        except Exception as e:
            current_app.logger.error(f"Failed to send reset password email: {e}")

        if is_development:
            return jsonify({
                "message": "Kode reset password telah dibuat.",
                "reset_token": reset_token,
                "debug_code": reset_code
            }), 200
        else:
            if email_sent:
                return jsonify({
                    "message": "Kode reset password telah dikirim ke email kamu.",
                    "reset_token": reset_token
                }), 200
            else:
                current_app.logger.error("Email service not available or sending failed in production.")
                return jsonify({
                    "message": "Sistem pengiriman email tidak tersedia. Silakan hubungi admin."
                }), 500
    except Exception as e:
        current_app.logger.error(f"Error in forgot-password: {e}")
        return jsonify({
            "message": "Sistem sedang mengalami gangguan. Silakan coba lagi nanti."
        }), 500


@auth_bp.route("/verify-reset-code", methods=["POST"])
def verify_reset_code():
    try:
        if not request.is_json or not request.json:
            return jsonify({"message": "Token verifikasi tidak valid."}), 400

        email_raw = request.json.get("email")
        reset_token = request.json.get("reset_token")
        code = request.json.get("code")

        if not email_raw:
            return jsonify({"message": "Email wajib diisi."}), 400

        if not reset_token:
            return jsonify({"message": "Token verifikasi tidak valid."}), 400

        if not code:
            return jsonify({"message": "Kode verifikasi wajib diisi."}), 400

        email = email_raw.lower().strip()
        code = str(code).strip()

        try:
            payload = decode_reset_token(reset_token)
        except pyjwt.ExpiredSignatureError:
            return jsonify({"message": "Token reset password sudah kedaluwarsa."}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({"message": "Token reset password tidak valid."}), 401

        # Verify email matches payload
        if payload.get("email") != email:
            return jsonify({"message": "Token reset password tidak valid."}), 401

        # Verify code matches payload
        if str(payload.get("reset_code")) != code:
            return jsonify({"message": "Kode verifikasi tidak valid. Periksa kembali kode yang kamu masukkan."}), 400

        return jsonify({
            "message": "Kode verifikasi berhasil divalidasi.",
            "reset_token": reset_token
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error in verify-reset-code: {e}")
        return jsonify({
            "message": "Sistem sedang mengalami gangguan. Silakan coba lagi nanti."
        }), 500


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    try:
        if not request.is_json or not request.json:
            return jsonify({"message": "Token reset password tidak valid."}), 400

        reset_token = request.json.get("reset_token")
        code = request.json.get("code")
        new_password = request.json.get("new_password")

        if not reset_token:
            return jsonify({"message": "Token reset password tidak valid."}), 400

        if not code:
            return jsonify({"message": "Kode verifikasi wajib diisi."}), 400

        if not new_password:
            return jsonify({"message": "Password baru wajib diisi."}), 400

        new_password = str(new_password).strip()
        if len(new_password) < 6:
            return jsonify({"message": "Password baru belum memenuhi ketentuan."}), 400

        code = str(code).strip()

        try:
            payload = decode_reset_token(reset_token)
        except pyjwt.ExpiredSignatureError:
            return jsonify({"message": "Token reset password sudah kedaluwarsa."}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({"message": "Token reset password tidak valid."}), 401

        # Verify code matches payload
        if str(payload.get("reset_code")) != code:
            return jsonify({"message": "Kode verifikasi tidak valid. Periksa kembali kode yang kamu masukkan."}), 400

        id_user = payload.get("id_user")
        email = payload.get("email")

        user = User.query.filter_by(id_user=id_user).first()
        if not user or user.email != email:
            return jsonify({"message": "Akun tidak ditemukan."}), 404

        user.password = bcrypt.hashpw(
            new_password.encode(),
            bcrypt.gensalt()
        ).decode()
        db.session.commit()

        return jsonify({
            "message": "Password berhasil diubah. Silakan login kembali."
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error in reset-password: {e}")
        return jsonify({
            "message": "Sistem sedang mengalami gangguan. Silakan coba lagi nanti."
        }), 500



@auth_bp.route("/verify-email", methods=["POST"])
@jwt_required()
def verify_email():
    user_id = get_user_id_from_jwt()
    data = request.json

    if not data:
        return error_response("Data verifikasi wajib diisi.", 400, "Invalid payload")

    code = str(data.get("code", "")).strip()
    verification_token = data.get("verification_token")

    if not code:
        return error_response(
            "Kode verifikasi wajib diisi.",
            400,
            "Validation error"
        )

    if not verification_token:
        return error_response(
            "Token verifikasi tidak valid.",
            400,
            "Validation error"
        )

    secret_key = current_app.config.get("JWT_SECRET_KEY") or current_app.config.get("SECRET_KEY")

    try:
        payload = pyjwt.decode(
            verification_token,
            secret_key,
            algorithms=["HS256"]
        )
    except ExpiredSignatureError:
        return error_response(
            "Kode verifikasi sudah kedaluwarsa. Silakan minta kode baru.",
            400,
            "Token expired"
        )
    except InvalidTokenError:
        return error_response(
            "Token verifikasi tidak valid.",
            400,
            "Invalid token"
        )

    if payload.get("type") != "email_verification":
        return error_response(
            "Token verifikasi tidak valid.",
            400,
            "Invalid token type"
        )

    if str(payload.get("user_id")) != str(user_id):
        return error_response(
            "Akses ditolak. Token verifikasi tidak sesuai dengan akun kamu.",
            403,
            "Invalid user"
        )

    if str(payload.get("code")) != code:
        return error_response(
            "Kode verifikasi tidak valid. Periksa kembali kode yang kamu masukkan.",
            400,
            "Invalid code"
        )

    user = User.query.get(user_id)
    if not user:
        return error_response("Data pengguna tidak ditemukan.", 404, "User not found")

    if user.verifikasi_status == 1:
        return error_response(
            "Akun sudah diverifikasi. Silakan login.",
            400,
            "Account already verified"
        )

    user.verifikasi_status = 1
    db.session.commit()

    return jsonify({
        "message": "Email berhasil diverifikasi",
        "user": user.to_public_user()
    }), 200


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = get_user_id_from_jwt()

    user = User.query.get(user_id)
    if not user:
        return error_response("Data pengguna tidak ditemukan.", 404, "User not found")

    return jsonify({
        "message": "Profile fetched successfully",
        "user": user.to_public_user()
    }), 200


@auth_bp.route("/update-profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = get_user_id_from_jwt()
    user = User.query.get(user_id)

    if not user:
        return error_response("Data pengguna tidak ditemukan.", 404, "User not found")

    data = request.json
    
    # Update fields if provided
    if "nama" in data:
        user.nama = data["nama"].strip()
    if "no_telepon" in data:
        user.no_telepon = data["no_telepon"].strip()
    
    # Commit changes
    try:
        db.session.commit()
        return jsonify({
            "message": "Profile updated successfully",
            "user": user.to_public_user()
        }), 200
    except Exception:
        db.session.rollback()
        return error_response(
            "Sistem sedang mengalami gangguan. Silakan coba lagi nanti.",
            500,
            "Failed to update profile"
        )
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required()
def refresh_token():
    claims = get_jwt()
    user_id = get_user_id_from_jwt()

    token = generate_token(
        user_id,
        claims.get("email"),
        claims.get("name")
    )

    return jsonify({
        "message": "Token refreshed successfully",
        "token": token
    }), 200

import os
from werkzeug.utils import secure_filename

@auth_bp.route("/update-profile-photo", methods=["POST"])
@jwt_required()
def update_profile_photo():
    user_id = get_user_id_from_jwt()
    user = User.query.get(user_id)

    if not user:
        return error_response("Data pengguna tidak ditemukan.", 404, "User not found")

    if 'image' not in request.files:
        return error_response("File gambar tidak ditemukan.", 400, "No image part")
        
    file = request.files['image']
    
    if file.filename == '':
        return error_response("File gambar tidak dipilih.", 400, "No selected file")

    if file:
        filename = secure_filename(file.filename)
        import time
        unique_filename = f"user_{user_id}_{int(time.time())}_{filename}"
        
        basedir = os.path.abspath(os.path.dirname(__file__))
        project_dir = os.path.dirname(basedir)
        upload_folder = os.path.join(project_dir, 'uploads')
        
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        user.img_url = f"uploads/{unique_filename}"
        
        try:
            db.session.commit()
            return jsonify({
                "message": "Profile photo updated successfully",
                "user": user.to_public_user()
            }), 200
        except Exception:
            db.session.rollback()
            return error_response(
                "Sistem sedang mengalami gangguan. Silakan coba lagi nanti.",
                500,
                "Failed to update profile photo"
            )


@auth_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "API is running"
    }), 200
