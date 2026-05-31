from flask import Blueprint, request, jsonify
from models import BagianTubuh, db
from services.id_generator import generate_random_4_digit

bagian_bp = Blueprint("bagian", __name__)


@bagian_bp.route("/bagian-tubuh", methods=["POST"])
def create_bagian():
    data = request.json
    if not data.get("nama_bagian"):
        return jsonify({"error": "nama_bagian wajib diisi"}), 400

    bagian = BagianTubuh(
        id_bagian=generate_random_4_digit(),
        nama_bagian=data["nama_bagian"]
    )

    db.session.add(bagian)
    db.session.commit()

    return jsonify({
        "message": "bagian tubuh berhasil dibuat",
        "data": {
            "id_bagian": bagian.id_bagian,
            "nama_bagian": bagian.nama_bagian
        }
    }), 201


@bagian_bp.route("/bagian-tubuh", methods=["GET"])
def get_bagian_tubuh():
    bagian_list = (
        BagianTubuh.query
        .order_by(BagianTubuh.nama_bagian.asc())
        .all()
    )

    return jsonify({
        "success": True,
        "message": "Data bagian tubuh berhasil diambil",
        "data": [
            {
                "id_bagian": bagian.id_bagian,
                "nama_bagian": bagian.nama_bagian,
            }
            for bagian in bagian_list
        ],
    }), 200
