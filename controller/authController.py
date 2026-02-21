from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy.exc import NoResultFound


from models import User, db
from auth.schemas import LoginRequestSchema, RegisterRequestSchema
from middleware.jwt_middleware import generate_token, get_user_id_from_jwt

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = LoginRequestSchema().load(request.json)

    email = data["email"].lower().strip()

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(data["password"]):
        return jsonify({
            "error": "Authentication failed",
            "message": "Invalid email or password"
        }), 401

    token = generate_token(user.id_user, user.email, user.nama)

    return jsonify({
        "message": "Login successful",
        "user": user.to_public_user(),
        "token": token
    }), 200


@auth_bp.route("/register", methods=["POST"])
def register():
    data = RegisterRequestSchema().load(request.json)

    email = data["email"].lower().strip()

    if User.query.filter_by(email=email).first():
        return jsonify({
            "error": "Email already registered",
            "message": "An account with this email already exists"
        }), 409

    user = User(
        nama=data["nama"].strip(),
        email=email,
        password=data["password"],
        no_telepon=data["no_telepon"],
        role="user",
        verifikasi_status=0
    )

    db.session.add(user)
    db.session.commit()

    token = generate_token(user.id_user, user.email, user.nama)

    return jsonify({
        "message": "Registrasi berhasil",
        "user": user.to_public_user(),
        "token": token
    }), 201


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = get_user_id_from_jwt()

    user = User.query.get(user_id)
    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

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
        return jsonify({"error": "User not found"}), 404

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
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update profile", "details": str(e)}), 500
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


@auth_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "API is running"
    }), 200
