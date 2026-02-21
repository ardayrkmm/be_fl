from flask import Blueprint, request, jsonify
from models import BagianTubuh, db
from services import id_generator

bagian_bp = Blueprint("bagian", __name__)


@bagian_bp.route("/bagian-tubuh", methods=["POST"])
def create_bagian():
    data = request.json
    if not data.get("nama_bagian"):
        return jsonify({"error": "nama_bagian wajib diisi"}), 400

    bagian = BagianTubuh(
        id_bagian=id_generator(),
        nama_bagian=data["nama_bagian"]
    )

    db.session.add(bagian)
    db.session.commit()

    return jsonify({
        "message": "bagian tubuh berhasil dibuat",
        "data": bagian
    }), 201
