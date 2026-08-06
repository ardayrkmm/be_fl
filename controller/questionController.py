from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Question, QuestionOption, db, KlinisThresholdBagian, JadwalLatihanUser, RehabRuleBagian
from sqlalchemy.orm import joinedload
import uuid

question_bp = Blueprint("question", __name__)

@question_bp.route("/update-durasi-db", methods=["GET"])
def update_durasi_db():
    try:
        # 1. Update max_durasi_minggu_home and batas_durasi_kronis
        rules = RehabRuleBagian.query.all()
        for rule in rules:
            rule.max_durasi_minggu_home = 4
            
        thresholds = KlinisThresholdBagian.query.all()
        for t in thresholds:
            t.batas_durasi_kronis = 5
            
        # 2. Update Opsi Pertanyaan Durasi Nyeri
        qs = Question.query.filter(Question.category == 'DURASI_NYERI').all()
        for q in qs:
            # Hapus option lama
            for opt in q.options:
                db.session.delete(opt)
            
            # Buat option baru (3 opsi sesuai permintaan)
            opt1 = QuestionOption(id=str(uuid.uuid4())[:8], key="<2", label="Kurang dari 2 minggu", nilai=1, question_id=q.id)
            opt2 = QuestionOption(id=str(uuid.uuid4())[:8], key="2-4", label="2 - 4 minggu", nilai=4, question_id=q.id)
            opt3 = QuestionOption(id=str(uuid.uuid4())[:8], key=">4", label="Lebih dari 4 minggu", nilai=7, question_id=q.id)
            
            db.session.add_all([opt1, opt2, opt3])
            
        db.session.commit()
        return jsonify({"success": True, "message": "Database berhasil diupdate untuk durasi nyeri!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

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
                "category": q.category,

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


@question_bp.route("/session-assessment/questions", methods=["GET"])
@jwt_required()
def get_session_assessment_questions():
    try:
        id_bagian = request.args.get("id_bagian")

        # Query KONDISI questions
        query = Question.query.options(joinedload(Question.options)).filter(
            Question.category == "KONDISI"
        )

        if id_bagian:
            query = query.filter(
                (Question.id_bagian == id_bagian) | (Question.id_bagian.is_(None))
            )
        else:
            query = query.filter(Question.id_bagian.is_(None))

        questions = query.order_by(
            Question.urutan.is_(None),
            Question.urutan.asc()
        ).all()

        kondisi_questions = []
        for q in questions:
            kondisi_questions.append({
                "id": q.id,
                "title": q.title,
                "subtitle": q.subtitle,
                "multiSelect": q.multiSelect,
                "category": q.category or "KONDISI",
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

        # Ambil threshold batas_nyeri_mandiri dari database berdasarkan id_bagian
        batas_nyeri_mandiri = 4
        if id_bagian:
            threshold = KlinisThresholdBagian.query.filter_by(id_bagian=id_bagian).first()
            if threshold and threshold.batas_nyeri_mandiri is not None:
                batas_nyeri_mandiri = threshold.batas_nyeri_mandiri

        # Default pain scale metadata
        pain_metadata = {
            "min": 0,
            "max": 10,
            "title": "Berapa tingkat nyeri Anda saat ini?",
            "subtitle": "Gunakan skala 0 sampai 10",
            "batas_nyeri_mandiri": batas_nyeri_mandiri
        }

        return jsonify({
            "success": True,
            "data": {
                "kondisi_questions": kondisi_questions,
                "pain": pain_metadata
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@question_bp.route("/session-assessment/submit", methods=["POST"])
@jwt_required()
def submit_session_assessment():
    user_id = str(get_jwt_identity())
    data = request.get_json() or {}

    id_jadwal = data.get("id_jadwal")
    id_bagian = data.get("id_bagian")
    tingkat_nyeri = data.get("tingkat_nyeri")
    answers = data.get("answers", [])

    if not id_jadwal:
        return jsonify({"success": False, "message": "id_jadwal wajib diisi"}), 400
    if not id_bagian:
        return jsonify({"success": False, "message": "id_bagian wajib diisi"}), 400
    if tingkat_nyeri is None:
        return jsonify({"success": False, "message": "tingkat_nyeri wajib diisi"}), 400

    try:
        tingkat_nyeri = float(tingkat_nyeri)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "tingkat_nyeri harus berupa angka"}), 400

    try:
        # Load Jadwal
        jadwal = JadwalLatihanUser.query.filter_by(id_jadwal=id_jadwal, id_user=user_id).first()
        if not jadwal:
            return jsonify({"success": False, "message": "Jadwal tidak ditemukan"}), 404

        # Load Threshold
        threshold = KlinisThresholdBagian.query.filter_by(id_bagian=id_bagian).first()
        batas_nyeri_ekstrem = threshold.batas_nyeri_ekstrem if threshold and threshold.batas_nyeri_ekstrem is not None else 8
        batas_nyeri_mandiri = threshold.batas_nyeri_mandiri if threshold and threshold.batas_nyeri_mandiri is not None else 4

        # Evaluate Pain Level
        # Jika tingkat_nyeri >= batas_nyeri_ekstrem atau tingkat_nyeri > batas_nyeri_mandiri, ditunda
        is_pain_unsafe = (tingkat_nyeri >= batas_nyeri_ekstrem) or (tingkat_nyeri > batas_nyeri_mandiri)

        # Evaluate KONDISI answers
        # Jika ada jawaban KONDISI yang nilai != 0 atau key berupa sakit/sensitif/kaku, ditunda
        is_kondisi_unsafe = False
        for answer in answers:
            opt_id = answer.get("option_id")
            if opt_id:
                option = QuestionOption.query.get(opt_id)
                if option and option.question and option.question.category == "KONDISI":
                    if int(option.nilai or 0) != 0 or (option.key in ["sakit", "sensitif", "kaku"]):
                        is_kondisi_unsafe = True
                        break

        is_safe = (not is_pain_unsafe) and (not is_kondisi_unsafe)

        if is_safe:
            jadwal.status = "Unlocked"
            db.session.commit()
            return jsonify({
                "success": True,
                "status": "allowed",
                "message": "Assessment aman. Latihan dapat dilanjutkan."
            }), 200
        else:
            jadwal.status = "Postponed"
            db.session.commit()
            return jsonify({
                "success": True,
                "status": "postponed",
                "message": "Silakan ke dokter atau fisioterapi terdekat. (Saran tambahan: Arummy Fisioterapi)"
            }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@question_bp.route("/final-program-assessment/questions", methods=["GET"])
@jwt_required()
def get_final_program_assessment_questions():
    try:
        id_bagian = request.args.get("id_bagian")

        # Query KONDISI questions
        query = Question.query.options(joinedload(Question.options)).filter(
            Question.category == "KONDISI"
        )

        if id_bagian:
            query = query.filter(
                (Question.id_bagian == id_bagian) | (Question.id_bagian.is_(None))
            )
        else:
            query = query.filter(Question.id_bagian.is_(None))

        questions = query.order_by(
            Question.urutan.is_(None),
            Question.urutan.asc()
        ).all()

        kondisi_questions = []
        for q in questions:
            kondisi_questions.append({
                "id": q.id,
                "title": q.title,
                "subtitle": q.subtitle,
                "multiSelect": q.multiSelect,
                "category": q.category or "KONDISI",
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

        # Ambil threshold batas_nyeri_mandiri dari database berdasarkan id_bagian
        batas_nyeri_mandiri = 4
        if id_bagian:
            threshold = KlinisThresholdBagian.query.filter_by(id_bagian=id_bagian).first()
            if threshold and threshold.batas_nyeri_mandiri is not None:
                batas_nyeri_mandiri = threshold.batas_nyeri_mandiri

        # Default pain scale metadata
        pain_metadata = {
            "min": 0,
            "max": 10,
            "title": "Berapa tingkat nyeri Anda saat ini?",
            "subtitle": "Gunakan skala 0 sampai 10",
            "batas_nyeri_mandiri": batas_nyeri_mandiri
        }

        return jsonify({
            "success": True,
            "data": {
                "kondisi_questions": kondisi_questions,
                "pain": pain_metadata
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@question_bp.route("/final-program-assessment/submit", methods=["POST"])
@jwt_required()
def submit_final_program_assessment():
    user_id = str(get_jwt_identity())
    data = request.get_json() or {}

    id_jadwal = data.get("id_jadwal")
    id_bagian = data.get("id_bagian")
    tingkat_nyeri = data.get("tingkat_nyeri")
    answers = data.get("answers", [])

    if not id_jadwal:
        return jsonify({"success": False, "message": "id_jadwal wajib diisi"}), 400
    if not id_bagian:
        return jsonify({"success": False, "message": "id_bagian wajib diisi"}), 400
    if tingkat_nyeri is None:
        return jsonify({"success": False, "message": "tingkat_nyeri wajib diisi"}), 400

    try:
        tingkat_nyeri = float(tingkat_nyeri)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "tingkat_nyeri harus berupa angka"}), 400

    try:
        # Load Jadwal
        jadwal = JadwalLatihanUser.query.filter_by(id_jadwal=id_jadwal, id_user=user_id).first()
        if not jadwal:
            return jsonify({"success": False, "message": "Jadwal tidak ditemukan"}), 404

        # Load Threshold
        threshold = KlinisThresholdBagian.query.filter_by(id_bagian=id_bagian).first()
        batas_nyeri_ekstrem = threshold.batas_nyeri_ekstrem if threshold and threshold.batas_nyeri_ekstrem is not None else 8
        batas_nyeri_mandiri = threshold.batas_nyeri_mandiri if threshold and threshold.batas_nyeri_mandiri is not None else 4

        # Evaluate Pain Level
        is_pain_unsafe = (tingkat_nyeri >= batas_nyeri_ekstrem) or (tingkat_nyeri > batas_nyeri_mandiri)

        # Evaluate KONDISI answers
        is_kondisi_unsafe = False
        for answer in answers:
            opt_id = answer.get("option_id")
            if opt_id:
                option = QuestionOption.query.get(opt_id)
                if option and option.question and option.question.category == "KONDISI":
                    if int(option.nilai or 0) != 0 or (option.key in ["sakit", "sensitif", "kaku"]):
                        is_kondisi_unsafe = True
                        break

        is_safe = (not is_pain_unsafe) and (not is_kondisi_unsafe)

        # Get all active schedules for this program (id_form)
        schedules = JadwalLatihanUser.query.filter_by(
            id_user=user_id,
            id_form=jadwal.id_form
        ).all()

        if is_safe:
            # Update all schedules of this id_form to Resolved
            for s in schedules:
                if s.status not in ["Closed", "Switched", "Resolved"]:
                    s.status = "Resolved"

            db.session.commit()

            status_code = "completed_no_pain" if tingkat_nyeri == 0 else "completed_safe"
            message = "Nyeri sudah hilang. Program latihan pada area ini telah selesai." if tingkat_nyeri == 0 else "Program latihan pada area ini telah selesai dan kondisi berada dalam batas aman."

            return jsonify({
                "success": True,
                "status": status_code,
                "message": message,
                "can_choose_other_area": True
            }), 200
        else:
            # Update all schedules of this id_form to Closed (meaning finished but needs expert)
            for s in schedules:
                if s.status not in ["Closed", "Switched", "Resolved"]:
                    s.status = "Closed"

            db.session.commit()

            return jsonify({
                "success": True,
                "status": "refer_to_expert",
                "message": "Program latihan mandiri telah mencapai batas maksimal durasi. Karena tingkat nyeri atau kondisi masih belum aman, pengguna disarankan berkonsultasi dengan fisioterapis atau dokter. (Saran tambahan: Arummy Fisioterapi)",
                "can_choose_other_area": False
            }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
@question_bp.route('/debug-questions', methods=['GET'])
def debug_questions():
    qs = Question.query.all()
    res = []
    for q in qs:
        res.append({'id': q.id, 'title': q.title, 'category': q.category, 'id_bagian': q.id_bagian})
    return jsonify(res)

