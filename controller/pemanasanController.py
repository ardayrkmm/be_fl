from flask import Blueprint, request, jsonify
from datetime import datetime
from models import db, Pemanasan, PemanasanVideo, generate_random_4_char

pemanasan_bp = Blueprint("pemanasan", __name__)


@pemanasan_bp.route("/pemanasan", methods=["POST"])
def create_pemanasan():
    data = request.get_json()

    if not data or not data.get("nama_pemanasan") or not data.get("id_bagian"):
        return jsonify({"message": "nama_pemanasan dan id_bagian wajib"}), 400

    try:
        pemanasan = Pemanasan(
            id_pemanasan=generate_random_4_char(),
            nama_pemanasan=data["nama_pemanasan"],
            id_bagian=data["id_bagian"],
            durasi_menit=data.get("durasi_menit"),
            created_at=datetime.utcnow()
        )

        for v in data.get("list_videos", []):
            video = PemanasanVideo(
                id_video=generate_random_4_char(),
                nama_gerakan=v.get("nama_gerakan"),
                video_url=v.get("video_url"),
                durasi_detik=v.get("durasi_detik"),
                urutan=v.get("urutan"),
                created_at=datetime.utcnow()
            )
            pemanasan.list_videos.append(video)

        db.session.add(pemanasan)
        db.session.commit()

        return jsonify({
            "message": "pemanasan berhasil dibuat",
            "id_pemanasan": pemanasan.id_pemanasan
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": "gagal membuat pemanasan",
            "error": str(e)
        }), 500


@pemanasan_bp.route("/pemanasan", methods=["GET"])
def get_all_pemanasan():
    data = Pemanasan.query.all()

    result = []
    for p in data:
        result.append({
            "id_pemanasan": p.id_pemanasan,
            "nama_pemanasan": p.nama_pemanasan,
            "id_bagian": p.id_bagian,
            "durasi_menit": p.durasi_menit
        })

    return jsonify({
        "total": len(result),
        "data": result
    })


@pemanasan_bp.route("/pemanasan/<id_pemanasan>", methods=["GET"])
def get_detail_pemanasan(id_pemanasan):
    pemanasan = Pemanasan.query.filter_by(
        id_pemanasan=id_pemanasan
    ).first()

    if not pemanasan:
        return jsonify({"message": "pemanasan tidak ditemukan"}), 404

    return jsonify({
        "id_pemanasan": pemanasan.id_pemanasan,
        "nama_pemanasan": pemanasan.nama_pemanasan,
        "id_bagian": pemanasan.id_bagian,
        "durasi_menit": pemanasan.durasi_menit,
        "list_videos": [
            {
                "id_video": v.id_video,
                "nama_gerakan": v.nama_gerakan,
                "video_url": v.video_url,
                "durasi_detik": v.durasi_detik,
                "urutan": v.urutan
            } for v in sorted(pemanasan.list_videos, key=lambda x: x.urutan)
        ]
    })


@pemanasan_bp.route("/pemanasan/<id_pemanasan>", methods=["PUT"])
def update_pemanasan(id_pemanasan):
    data = request.get_json()
    pemanasan = Pemanasan.query.get(id_pemanasan)

    if not pemanasan:
        return jsonify({"message": "pemanasan tidak ditemukan"}), 404

    try:
        pemanasan.nama_pemanasan = data.get(
            "nama_pemanasan", pemanasan.nama_pemanasan
        )
        pemanasan.durasi_menit = data.get(
            "durasi_menit", pemanasan.durasi_menit
        )

        db.session.commit()

        return jsonify({"message": "pemanasan berhasil diupdate"})

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": "gagal update",
            "error": str(e)
        }), 500


@pemanasan_bp.route("/pemanasan/<id_pemanasan>", methods=["DELETE"])
def delete_pemanasan(id_pemanasan):
    pemanasan = Pemanasan.query.get(id_pemanasan)

    if not pemanasan:
        return jsonify({"message": "pemanasan tidak ditemukan"}), 404

    try:
        db.session.delete(pemanasan)
        db.session.commit()

        return jsonify({"message": "pemanasan berhasil dihapus"})

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": "gagal menghapus",
            "error": str(e)
        }), 500
