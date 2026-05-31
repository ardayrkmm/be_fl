from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.notification_service import NotificationService

notification_bp = Blueprint('notification_bp', __name__)

@notification_bp.route('/notification/create', methods=['POST'])
@jwt_required()
def create_notification():
    current_user = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON input"}), 400
        
    data['id_user'] = current_user
    result, status_code = NotificationService.create_notification(data)
    return jsonify(result), status_code

@notification_bp.route('/notification/<id_user>', methods=['GET'])
@jwt_required()
def get_notifications(id_user):
    current_user = get_jwt_identity()
    if str(current_user) != str(id_user):
        return jsonify({"status": "error", "message": "Akses Ditolak"}), 403
        
    result, status_code = NotificationService.get_user_notifications(id_user)
    return jsonify(result), status_code

@notification_bp.route('/notification/read/<id_notifikasi>', methods=['PATCH'])
@jwt_required()
def read_notification(id_notifikasi):
    current_user = get_jwt_identity()
    result, status_code = NotificationService.mark_as_read(id_notifikasi, current_user)
    return jsonify(result), status_code


@notification_bp.route('/notifications/fcm-token', methods=['POST'])
@jwt_required()
def save_fcm_token():
    current_user = get_jwt_identity()
    data = request.get_json() or {}
    fcm_token = data.get("fcm_token")

    if not fcm_token:
        return jsonify({
            "success": False,
            "message": "fcm_token wajib diisi"
        }), 400

    result, status_code = NotificationService.save_fcm_token(
        current_user,
        fcm_token
    )
    return jsonify(result), status_code


@notification_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_my_notifications():
    current_user = get_jwt_identity()
    result, status_code = NotificationService.get_user_notifications(current_user)
    return jsonify(result), status_code


@notification_bp.route('/notifications/<id_notifikasi>/read', methods=['PUT'])
@jwt_required()
def read_my_notification(id_notifikasi):
    current_user = get_jwt_identity()
    result, status_code = NotificationService.mark_as_read(
        id_notifikasi,
        current_user
    )
    return jsonify(result), status_code


@notification_bp.route('/notifications/read-all', methods=['PUT'])
@jwt_required()
def read_all_notifications():
    current_user = get_jwt_identity()
    result, status_code = NotificationService.mark_all_as_read(current_user)
    return jsonify(result), status_code


@notification_bp.route('/notifications/<id_notifikasi>', methods=['DELETE'])
@jwt_required()
def delete_my_notification(id_notifikasi):
    current_user = get_jwt_identity()
    result, status_code = NotificationService.delete_notification(
        id_notifikasi,
        current_user
    )
    return jsonify(result), status_code
