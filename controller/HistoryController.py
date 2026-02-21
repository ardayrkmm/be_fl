from flask import Blueprint, request, jsonify
from models import db, HistoryAktifitas, JadwalLatihanUser, Latihan, JadwalLatihanDetail,generate_random_id
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
from sqlalchemy import desc

history_bp = Blueprint('history_bp', __name__)

@history_bp.route("/history", methods=["POST"])
@jwt_required()
def save_history():
    user_id = str(get_jwt_identity())
    data = request.get_json()

    # Validasi input dari MediaPipe/Mobile
    required = ["id_latihan", "set_tercapai", "repetisi_tercapai", "nilai_akurasi"]
    for field in required:
        if field not in data:
            return jsonify({"message": f"Field {field} wajib ada"}), 400

    try:
        # 1. Simpan ke History
        new_history = HistoryAktifitas(
            id_history_aktifitas=generate_random_id(4),
            id_user=user_id,
            id_latihan=data["id_latihan"],
            tanggal=datetime.utcnow(),
            set_tercapai=data["set_tercapai"],
            repetisi_tercapai=data["repetisi_tercapai"],
            durasi_aktual=data.get("durasi_aktual", 0.0),
            nilai_akurasi=data["nilai_akurasi"],
            jumlah_gerakan_benar=data.get("jumlah_gerakan_benar", 0),
            jumlah_gerakan_salah=data.get("jumlah_gerakan_salah", 0),
            nilai_latihan=data.get("nilai_latihan", "Cukup") # Bagus, Sangat Bagus, dll
        )

        # 2. Update Status di JadwalDetail (jika ada id_detail)
        id_detail = data.get("id_detail")
        if id_detail:
            detail = JadwalLatihanDetail.query.get(id_detail)
            if detail:
                detail.status_eksekusi = True

        db.session.add(new_history)
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": "Data latihan berhasil disimpan",
            "id_history": new_history.id_history_aktifitas
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@history_bp.route("/history/me", methods=["GET"])
@jwt_required()
def get_my_history():
    user_id = str(get_jwt_identity())
    
    # Ambil 10 riwayat terakhir
    histories = HistoryAktifitas.query.filter_by(id_user=user_id)\
                .order_by(HistoryAktifitas.tanggal.desc()).limit(10).all()

    result = []
    for h in histories:
        result.append({
            "tanggal": h.tanggal.strftime("%Y-%m-%d %H:%M"),
            "latihan": h.latihan.nama_latihan if h.latihan else "Unknown",
            "akurasi": h.nilai_akurasi,
            "benar": h.jumlah_gerakan_benar,
            "salah": h.jumlah_gerakan_salah,
            "nilai": h.nilai_latihan
        })

    return jsonify({"success": True, "data": result}), 200

@history_bp.route("/jadwal/selesai", methods=["POST"])
@jwt_required()
def selesai_jadwal():
    user_id = str(get_jwt_identity())
    data = request.get_json()

    id_jadwal = data.get("id_jadwal")

    if not id_jadwal:
        return jsonify({"message": "id_jadwal wajib diisi"}), 400

    try:
        # 1️⃣ Ambil jadwal user
        jadwal = JadwalLatihanUser.query.filter_by(
            id_jadwal=id_jadwal,
            id_user=user_id
        ).first()

        if not jadwal:
            return jsonify({"message": "Jadwal tidak ditemukan"}), 404

        # 2️⃣ Ambil semua detail
        details = JadwalLatihanDetail.query.filter_by(
            id_jadwal=id_jadwal
        ).all()

        if not details:
            return jsonify({"message": "Detail latihan kosong"}), 400

        # 3️⃣ Cek apakah semua sudah dieksekusi
        belum_selesai = [
            d for d in details if not d.status_eksekusi
        ]

        if belum_selesai:
            return jsonify({
                "success": False,
                "message": "Masih ada latihan yang belum selesai",
                "total_belum_selesai": len(belum_selesai)
            }), 400

        # 4️⃣ Update status jadwal
        jadwal.status = "Completed"
        jadwal.tanggal_selesai = datetime.utcnow()

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Jadwal latihan berhasil diselesaikan"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500