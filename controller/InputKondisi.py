from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import KondisiUser, db, Question, QuestionOption, BagianTubuh
from datetime import datetime
import uuid

kondisi_bp = Blueprint("kondisi", __name__)

@kondisi_bp.route("/kondisi-user", methods=["POST"])
@jwt_required()
def create_kondisi_user():
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Payload kosong"}), 400

    id_bagian = data.get("id_bagian")
    lama_nyeri_hari = data.get("lama_nyeri_hari")
    tingkat_nyeri = data.get("tingkat_nyeri")
    jenis_keluhan = data.get("jenis_keluhan")



    # Handle answers list if present
    if "answers" in data and isinstance(data["answers"], list):
        for answer in data["answers"]:
            q_id = answer.get("question_id")
            opt_id = answer.get("option_id")
            
            if not q_id or not opt_id:
                continue

            question = Question.query.get(q_id)
            option = QuestionOption.query.get(opt_id)

            if question and option:
                target = question.target_field
                # print(f"DEBUG: Mapping {target} -> {option.label} (Value: {option.nilai})")
                if target == "id_bagian":
                    # Cari ID bagian berdasarkan nama (label)
                    bagian = BagianTubuh.query.filter(BagianTubuh.nama_bagian.ilike(option.label)).first()
                    if bagian:
                        id_bagian = bagian.id_bagian
                    else:
                        print(f"Warning: Bagian tubuh '{option.label}' tidak ditemukan di database.")
                        id_bagian = None # Atau handle error
                elif target == "lama_nyeri_hari":
                    lama_nyeri_hari = option.nilai
                elif target == "tingkat_nyeri":
                    tingkat_nyeri = option.nilai
                elif target == "jenis_keluhan":
                    jenis_keluhan = option.label



    try:
        kondisi = KondisiUser(
            id_form=str(uuid.uuid4())[:4],
            id_user=user_id,
            id_bagian=id_bagian,
            lama_nyeri_hari=lama_nyeri_hari,
            tingkat_nyeri=tingkat_nyeri,
            jenis_keluhan=jenis_keluhan,
            created_at=datetime.utcnow()
        )

        db.session.add(kondisi)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Kondisi user berhasil disimpan",
            "data": {
                "tingkat_nyeri": kondisi.tingkat_nyeri,
                "id_bagian": kondisi.id_bagian
            }
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"DEBUG: Error creating KondisiUser: {e}")
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
