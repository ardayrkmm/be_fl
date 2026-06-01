from flask import Blueprint, request, jsonify
from models import Question, QuestionOption, db
import uuid

question_bp = Blueprint("question", __name__)


@question_bp.route("/questions", methods=["POST"])
def create_question():
    req = request.get_json()
    
    if not req:
        return jsonify({"error": "Payload tidak valid"}), 400

    try:
        new_id = str(uuid.uuid4())[:8]
        
        question = Question(
            id=new_id,
            title=req.get("title"),
            subtitle=req.get("subtitle"),
            multiSelect=req.get("multiSelect"),
          
            id_bagian=req.get("id_bagian"),
            urutan=req.get("urutan")
        )

        for opt in req.get("options", []):
            question.options.append(
                QuestionOption(
                    id=str(uuid.uuid4())[:8],
                    key=opt.get("key"),   # ✅ FIX TAMBAHAN
                    label=opt.get("label"),
                    nilai=opt.get("nilai")
                )
            )

        db.session.add(question)
        db.session.commit()

        req["id"] = new_id
        return jsonify(req), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

from sqlalchemy.orm import joinedload

@question_bp.route("/questions", methods=["GET"])
def get_questions():
    try:
        id_bagian = request.args.get("id_bagian")

        # =========================
        # QUERY BASE
        # =========================
        query = Question.query.options(
            joinedload(Question.options)
        )

        # =========================
        # FILTER LOGIC
        # =========================
        if id_bagian:
            query = query.filter(
                (Question.id_bagian == id_bagian) |
                (Question.id_bagian.is_(None))
            )
        else:
            # STEP AWAL: hanya question umum (bagian selection)
            query = query.filter(Question.id_bagian.is_(None))

        # =========================
        # ORDER
        # =========================
        questions = query.order_by(
            Question.urutan.is_(None),
            Question.urutan.asc()
        ).all()

        # =========================
        # FORMAT RESPONSE
        # =========================
        # Map category → target_field agar Flutter bisa routing per step
        CATEGORY_TARGET_MAP = {
            "TINGKAT_NYERI": "tingkat_nyeri",
            "DURASI_NYERI":  "durasi_nyeri_minggu",
            "REDFLAG":       "red_flag",
            "KONDISI":       "kondisi",
            None:            "id_bagian",  # pertanyaan pilih bagian tubuh
        }

        result = []

        for q in questions:
            target_field = CATEGORY_TARGET_MAP.get(q.category, "id_bagian")
            result.append({
                "id": q.id,
                "title": q.title,
                "subtitle": q.subtitle,
                "multiSelect": q.multiSelect,

                # penting untuk step logic Flutter
                "id_bagian": q.id_bagian,
                "target_field": target_field,  # 🔥 WAJIB untuk routing step Flutter

                "urutan": q.urutan,

                "options": [
                    {
                        "id": o.id,
                        "key": o.key,
                        "label": o.label,
                        "nilai": o.nilai
                    }
                    for o in q.options
                ]
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@question_bp.route("/questions/<id>", methods=["PUT"])
def update_question(id):
    question = Question.query.filter_by(id=id).first()
    
    if not question:
        return jsonify({"error": "Question tidak ditemukan"}), 404

    req = request.get_json()
    if not req:
        return jsonify({"error": "Payload tidak valid"}), 400

    try:
        question.title = req.get("title", question.title)
        question.subtitle = req.get("subtitle", question.subtitle)
        question.multiSelect = req.get("multiSelect", question.multiSelect)
        question.target_field = req.get("target_field", question.target_field)

        if "id_bagian" in req:
            question.id_bagian = req.get("id_bagian")
        if "urutan" in req:
            question.urutan = req.get("urutan")

        question.options.clear()

        for opt in req.get("options", []):
            question.options.append(
                QuestionOption(
                    id=str(uuid.uuid4())[:8],
                    key=opt.get("key"),   # ✅ FIX TAMBAHAN
                    label=opt.get("label"),
                    nilai=opt.get("nilai")
                )
            )

        db.session.commit()

        req["id"] = id
        return jsonify(req), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@question_bp.route("/questions/<id>", methods=["DELETE"])
def delete_question(id):
    try:
        question = Question.query.get(id)
        if not question:
            return jsonify({"error": "Question tidak ditemukan"}), 404
            
        # ORM-safe delete (otomatis menghapus options karena cascade delete-orphan)
        db.session.delete(question)
        db.session.commit()

        return jsonify({"message": "Question berhasil dihapus"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500