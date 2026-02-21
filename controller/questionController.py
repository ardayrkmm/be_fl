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
            target_field=req.get("target_field")
        )

        for opt in req.get("options", []):
            question.options.append(
                QuestionOption(
                    id=str(uuid.uuid4())[:8],
                    label=opt.get("label"),
                    nilai=opt.get("nilai")
                )
            )

        db.session.add(question)
        db.session.commit()

        # Di Flask, kita perlu mengembalikan data secara manual karena SQLAlchemy 
        # tidak otomatis men-serialize objek seperti GORM.
        req["id"] = new_id
        return jsonify(req), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


from sqlalchemy.orm import joinedload

@question_bp.route("/questions", methods=["GET"])
def get_questions():
    try:
        # Sama seperti Preload("Options") di GORM
        questions = Question.query.options(joinedload(Question.options)).all()
        
        result = []
        for q in questions:
            result.append({
                "id": q.id,
                "title": q.title,
                "subtitle": q.subtitle,
                "multiSelect": q.multiSelect,
                "target_field": q.target_field,
                "options": [
                    {
                        "id": o.id, 
                        "question_id": o.question_id, 
                        "label": o.label, 
                        "nilai": o.nilai
                    } for o in q.options
                ]
            })
            
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@question_bp.route("/questions/<id>", methods=["PUT"])
def update_question(id):
    question = Question.query.filter_by(id=id).first()
    
    if not question:
        return jsonify({"error": "Question tidak ditemukan"}), 404

    req = request.get_json()
    if not req:
        return jsonify({"error": "Payload tidak valid"}), 400

    try:
        # Update field utama
        question.title = req.get("title", question.title)
        question.subtitle = req.get("subtitle", question.subtitle)
        question.multiSelect = req.get("multiSelect", question.multiSelect)
        question.target_field = req.get("target_field", question.target_field)

        # Sama persis dengan GORM: Hapus opsi lama
        QuestionOption.query.filter_by(question_id=id).delete()

        # Masukkan opsi baru
        for opt in req.get("options", []):
            new_opt = QuestionOption(
                id=str(uuid.uuid4())[:8],
                question_id=id,
                label=opt.get("label"),
                nilai=opt.get("nilai")
            )
            db.session.add(new_opt)

        db.session.commit()

        req["id"] = id
        return jsonify(req), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@question_bp.route("/questions/<id>", methods=["DELETE"])
def delete_question(id):
    try:
        # Hapus options terlebih dahulu (menghindari constraint error)
        QuestionOption.query.filter_by(question_id=id).delete()
        
        # Hapus question
        Question.query.filter_by(id=id).delete()
        
        db.session.commit()

        return jsonify({"message": "Question berhasil dihapus"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500