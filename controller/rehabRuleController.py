from flask import Blueprint, request, jsonify
from models import db, RehabRuleBagian, BagianTubuh

rehab_rule_bp = Blueprint("rehabRule", __name__)

@rehab_rule_bp.route("/rehab-rule", methods=["POST"])
def create_rule():
    data = request.get_json()
    id_bagian = data.get("id_bagian")

    if not id_bagian:
        return jsonify({
            "success": False,
            "message": "id_bagian wajib diisi",
            "data": None
        }), 400

    try:
        # Cek duplikat
        existing_rule = RehabRuleBagian.query.filter_by(id_bagian=id_bagian).first()
        if existing_rule:
            return jsonify({
                "success": False,
                "message": f"Rule untuk bagian tubuh {id_bagian} sudah ada",
                "data": None
            }), 409

        # Cek validitas id_bagian (harus ada di tabel BagianTubuh)
        bagian = BagianTubuh.query.filter_by(id_bagian=id_bagian).first()
        if not bagian:
            return jsonify({
                "success": False,
                "message": f"Bagian tubuh dengan ID {id_bagian} tidak ditemukan",
                "data": None
            }), 404

        new_rule = RehabRuleBagian(
            id_bagian=id_bagian,
            max_latihan_per_hari=data.get("max_latihan_per_hari", 6),
            max_durasi_minggu_home=data.get("max_durasi_minggu_home", 3)
        )

        db.session.add(new_rule)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Rule berhasil dibuat",
            "data": {
                "id": new_rule.id,
                "id_bagian": new_rule.id_bagian,
                "max_latihan_per_hari": new_rule.max_latihan_per_hari,
                "max_durasi_minggu_home": new_rule.max_durasi_minggu_home
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Gagal membuat rule",
            "data": str(e)
        }), 500


@rehab_rule_bp.route("/rehab-rule", methods=["GET"])
def get_all_rules():
    try:
        # Join ke BagianTubuh untuk get nama_bagian
        rules = db.session.query(RehabRuleBagian, BagianTubuh.nama_bagian)\
            .join(BagianTubuh, RehabRuleBagian.id_bagian == BagianTubuh.id_bagian)\
            .all()

        result = []
        for rule, nama_bagian in rules:
            result.append({
                "id": rule.id,
                "id_bagian": rule.id_bagian,
                "nama_bagian": nama_bagian,
                "max_latihan_per_hari": rule.max_latihan_per_hari,
                "max_durasi_minggu_home": rule.max_durasi_minggu_home
            })

        return jsonify({
            "success": True,
            "message": "Berhasil mengambil data rule",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Gagal mengambil data rule",
            "data": str(e)
        }), 500


@rehab_rule_bp.route("/rehab-rule/<id_bagian>", methods=["GET"])
def get_rule_by_id_bagian(id_bagian):
    try:
        rule_data = db.session.query(RehabRuleBagian, BagianTubuh.nama_bagian)\
            .join(BagianTubuh, RehabRuleBagian.id_bagian == BagianTubuh.id_bagian)\
            .filter(RehabRuleBagian.id_bagian == id_bagian)\
            .first()

        if not rule_data:
            return jsonify({
                "success": False,
                "message": "Rule tidak ditemukan",
                "data": None
            }), 404

        rule, nama_bagian = rule_data

        return jsonify({
            "success": True,
            "message": "Detail rule ditemukan",
            "data": {
                "id": rule.id,
                "id_bagian": rule.id_bagian,
                "nama_bagian": nama_bagian,
                "max_latihan_per_hari": rule.max_latihan_per_hari,
                "max_durasi_minggu_home": rule.max_durasi_minggu_home
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Gagal mengambil detail rule",
            "data": str(e)
        }), 500


@rehab_rule_bp.route("/rehab-rule/<id_bagian>", methods=["PUT"])
def update_rule(id_bagian):
    data = request.get_json()

    try:
        rule = RehabRuleBagian.query.filter_by(id_bagian=id_bagian).first()

        if not rule:
            return jsonify({
                "success": False,
                "message": "Rule tidak ditemukan",
                "data": None
            }), 404

        # Partial update
        if "max_latihan_per_hari" in data:
            rule.max_latihan_per_hari = data["max_latihan_per_hari"]
            
        if "max_durasi_minggu_home" in data:
            rule.max_durasi_minggu_home = data["max_durasi_minggu_home"]

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Rule berhasil diperbarui",
            "data": {
                "id": rule.id,
                "id_bagian": rule.id_bagian,
                "max_latihan_per_hari": rule.max_latihan_per_hari,
                "max_durasi_minggu_home": rule.max_durasi_minggu_home
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Gagal memperbarui rule",
            "data": str(e)
        }), 500


@rehab_rule_bp.route("/rehab-rule/<id_bagian>", methods=["DELETE"])
def delete_rule(id_bagian):
    try:
        rule = RehabRuleBagian.query.filter_by(id_bagian=id_bagian).first()

        if not rule:
            return jsonify({
                "success": False,
                "message": "Rule tidak ditemukan",
                "data": None
            }), 404

        db.session.delete(rule)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Rule berhasil dihapus",
            "data": None
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Gagal menghapus rule",
            "data": str(e)
        }), 500
