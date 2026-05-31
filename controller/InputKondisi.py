from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import KondisiUser, db, Question, QuestionOption, BagianTubuh, KlinisThresholdBagian
from datetime import datetime
import uuid

kondisi_bp = Blueprint("kondisi", __name__)


def generate_unique_id_form():
    for _ in range(20):
        candidate = uuid.uuid4().hex[:4].upper()
        if not KondisiUser.query.get(candidate):
            return candidate
    raise ValueError("Gagal membuat id_form unik")

# @kondisi_bp.route("/kondisi-user", methods=["POST"])
# @jwt_required()
# def create_kondisi_user():
#     user_id = get_jwt_identity()
#     data = request.get_json()

#     if not data:
#         return jsonify({"success": False, "message": "Payload kosong"}), 400

#     id_bagian = data.get("id_bagian")
#     lama_nyeri_hari = data.get("lama_nyeri_hari")
#     tingkat_nyeri = data.get("tingkat_nyeri")
#     jenis_keluhan = data.get("jenis_keluhan")



#     # Handle answers list if present
#     if "answers" in data and isinstance(data["answers"], list):
#         for answer in data["answers"]:
#             q_id = answer.get("question_id")
#             opt_id = answer.get("option_id")

#             if not q_id or not opt_id:
#                 continue

#             question = Question.query.get(q_id)
#             option = QuestionOption.query.get(opt_id)

#             if question and option:
#                 target = question.target_field
#                 # print(f"DEBUG: Mapping {target} -> {option.label} (Value: {option.nilai})")
#                 if target == "id_bagian":
#                     # Cari ID bagian berdasarkan nama (label)
#                     bagian = BagianTubuh.query.filter(BagianTubuh.nama_bagian.ilike(option.label)).first()
#                     if bagian:
#                         id_bagian = bagian.id_bagian
#                     else:
#                         print(f"Warning: Bagian tubuh '{option.label}' tidak ditemukan di database.")
#                         id_bagian = None # Atau handle error
#                 elif target == "lama_nyeri_hari":
#                     lama_nyeri_hari = option.nilai
#                 elif target == "tingkat_nyeri":
#                     tingkat_nyeri = option.nilai
#                 elif target == "jenis_keluhan":
#                     jenis_keluhan = option.label



#     try:
#         kondisi = KondisiUser(
#             id_form=str(uuid.uuid4())[:4],
#             id_user=user_id,
#             id_bagian=id_bagian,
#             lama_nyeri_hari=lama_nyeri_hari,
#             tingkat_nyeri=tingkat_nyeri,
#             jenis_keluhan=jenis_keluhan,
#             created_at=datetime.utcnow()
#         )

#         db.session.add(kondisi)
#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "message": "Kondisi user berhasil disimpan",
#             "data": {
#                 "tingkat_nyeri": kondisi.tingkat_nyeri,
#                 "id_bagian": kondisi.id_bagian
#             }
#         }), 201

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         print(f"DEBUG: Error creating KondisiUser: {e}")
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "error": str(e)
#         }), 500


# @kondisi_bp.route("/kondisi-user", methods=["POST"])
# @jwt_required()
# def create_kondisi_user():
#     user_id = get_jwt_identity()
#     data = request.get_json()

#     if not data:
#         return jsonify({"success": False, "message": "Payload kosong"}), 400

#     # 1. Ambil field utama
#     id_bagian = data.get("id_bagian")
#     tingkat_nyeri = data.get("tingkat_nyeri")
#     durasi_nyeri_minggu = data.get("durasi_nyeri_minggu")

#     # 2. Proses jawaban kuesioner (jika dikirim dalam format answers list)
#     if "answers" in data and isinstance(data["answers"], list):
#         for answer in data["answers"]:
#             q_id = answer.get("question_id")
#             opt_id = answer.get("option_id")
#             if not q_id or not opt_id:
#                 continue
#             question = Question.query.get(q_id)
#             option = QuestionOption.query.get(opt_id)
#             if question and option:
#                 target = question.target_field
#                 if target == "id_bagian":
#                     bagian = BagianTubuh.query.filter(BagianTubuh.nama_bagian.ilike(option.label)).first()
#                     id_bagian = bagian.id_bagian if bagian else None
#                 elif target == "tingkat_nyeri":
#                     tingkat_nyeri = option.nilai
#                 elif target == "durasi_nyeri_minggu":
#                     durasi_nyeri_minggu = option.nilai

#     # 3. Red Flag Detection (universal â€” berbasis JSON, tidak ada kolom boolean per gejala)
#     # Kunci red flag umum musculoskeletal; frontend boleh kirim salah satu / beberapa
#     red_flag_keys = [
#         'tidak_bisa_menapak', 'trauma_langsung', 'bengkak_cepat_besar',
#         'demam_kemerahan', 'nyeri_malam', 'lutut_locking', 'instabilitas'
#     ]
#     red_flag_detail = {k: True for k in red_flag_keys if data.get(k, False)}

#     # -- SAFETY CONVERSION FIX --
#     # Mencegah runtime crash (TypeError/ValueError) jika input adalah None atau String
#     try:
#         tingkat_nyeri = int(tingkat_nyeri) if tingkat_nyeri is not None else 0
#     except (TypeError, ValueError):
#         tingkat_nyeri = 0

#     try:
#         durasi_nyeri_minggu = int(durasi_nyeri_minggu) if durasi_nyeri_minggu is not None else 0
#     except (TypeError, ValueError):
#         durasi_nyeri_minggu = 0

#     # Auto red flag jika nyeri ekstrem atau durasi sangat lama
#     if tingkat_nyeri >= 8:
#         red_flag_detail['nyeri_ekstrem'] = True
#     if durasi_nyeri_minggu >= 12:
#         red_flag_detail['durasi_kronis'] = True

#     has_red_flag = bool(red_flag_detail)

#     # 4. Rule-Based Decision
#     # IF has_red_flag == True     â†’ rujuk
#     # ELSE IF tingkat_nyeri 1â€“4  â†’ latihan mandiri
#     # ELSE (>4)                  â†’ rujuk
#     if has_red_flag:
#         rekomendasi = "rujuk"
#         fase = None
#     elif 1 <= tingkat_nyeri <= 4:
#         rekomendasi = "latihan_mandiri"
#         if durasi_nyeri_minggu <= 1:
#             fase = 'F1'
#         elif durasi_nyeri_minggu <= 3:
#             fase = 'F2'
#         else:
#             fase = 'F3'
#     else:
#         rekomendasi = "rujuk"
#         fase = None

#     perlu_evaluasi = bool(durasi_nyeri_minggu > 3)

#     try:
#         kondisi = KondisiUser(
#             id_form=str(uuid.uuid4())[:4],
#             id_user=user_id,
#             id_bagian=id_bagian,
#             tingkat_nyeri=tingkat_nyeri,
#             durasi_nyeri_minggu=durasi_nyeri_minggu,
#             has_red_flag=has_red_flag,
#             red_flag_detail=red_flag_detail if red_flag_detail else None,
#         )

#         db.session.add(kondisi)
#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "message": "Kondisi user berhasil disimpan",
#             "data": {
#                 "id_form": kondisi.id_form,
#                 "id_bagian": kondisi.id_bagian,
#                 "tingkat_nyeri": kondisi.tingkat_nyeri,
#                 "durasi_nyeri_minggu": kondisi.durasi_nyeri_minggu,
#                 "has_red_flag": has_red_flag,
#                 "red_flag_detail": red_flag_detail or None,
#                 "rekomendasi": rekomendasi,
#                 "fase": fase,
#                 "perlu_evaluasi": perlu_evaluasi
#             }
#         }), 201

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         print(f"DEBUG: Error creating KondisiUser: {e}")
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "error": str(e)
#         }), 500



# @kondisi_bp.route("/kondisi-user", methods=["POST"])
# @jwt_required()
# def create_kondisi_user():
#     user_id = get_jwt_identity()
#     data = request.get_json()

#     if not data:
#         return jsonify({"success": False, "message": "Payload kosong"}), 400

#     try:
#         # ===============================
#         # 1ï¸âƒ£ Ambil Field Dasar
#         # ===============================
#         id_bagian = data.get("id_bagian")
#         tingkat_nyeri = data.get("tingkat_nyeri")
#         durasi_nyeri = data.get("durasi_nyeri_minggu")

#         # Safe int conversion
#         try:
#             tingkat_nyeri = int(tingkat_nyeri)
#         except:
#             tingkat_nyeri = 0

#         try:
#             durasi_nyeri = int(durasi_nyeri)
#         except:
#             durasi_nyeri = 0

#         # ===============================
#         # 2ï¸âƒ£ Mapping dari answers (jika ada)
#         # ===============================
#         if "answers" in data and isinstance(data["answers"], list):
#             for answer in data["answers"]:
#                 q_id = answer.get("question_id")
#                 opt_id = answer.get("option_id")

#                 question = Question.query.get(q_id)
#                 option = QuestionOption.query.get(opt_id)

#                 if not question or not option:
#                     continue

#                 if question.target_field == "id_bagian":
#                     bagian = BagianTubuh.query.filter(
#                         BagianTubuh.nama_bagian.ilike(option.label)
#                     ).first()
#                     id_bagian = bagian.id_bagian if bagian else None

#                 elif question.target_field == "tingkat_nyeri":
#                     try:
#                         tingkat_nyeri = int(option.nilai)
#                     except:
#                         tingkat_nyeri = 0

#                 elif question.target_field == "durasi_nyeri_minggu":
#                     try:
#                         durasi_nyeri = int(option.nilai)
#                     except:
#                         durasi_nyeri = 0

#         if not id_bagian:
#             return jsonify({
#                 "success": False,
#                 "message": "Bagian tubuh tidak ditemukan"
#             }), 400

#         # ===============================
#         # 3ï¸âƒ£ Ambil Threshold Per Bagian
#         # ===============================
#         threshold = KlinisThresholdBagian.query.filter_by(
#             id_bagian=id_bagian
#         ).first()

#         if not threshold:
#             return jsonify({
#                 "success": False,
#                 "message": "Threshold klinis belum dikonfigurasi untuk bagian ini"
#             }), 400

#         # ===============================
#         # 4ï¸âƒ£ Red Flag Detection (Fully Dynamic)
#         # Frontend cukup kirim key diawali 'rf_'
#         # ===============================
#         red_flag_detail = {
#             key: True
#             for key, value in data.items()
#             if key.startswith("rf_") and value is True
#         }

#         # Auto red flag berdasarkan threshold
#         if tingkat_nyeri >= threshold.batas_nyeri_ekstrem:
#             red_flag_detail["rf_nyeri_ekstrem"] = True

#         if durasi_nyeri >= threshold.batas_durasi_kronis:
#             red_flag_detail["rf_durasi_kronis"] = True

#         has_red_flag = bool(red_flag_detail)

#         # ===============================
#         # 5ï¸âƒ£ Rule Engine (Dynamic Threshold)
#         # ===============================
#         if has_red_flag:
#             rekomendasi = "rujuk"
#             fase = None
#         elif 1 <= tingkat_nyeri <= threshold.batas_nyeri_mandiri:

#             if durasi_nyeri <= threshold.batas_fase1_minggu:
#                 rekomendasi = "latihan_mandiri"
#                 fase = "F1"

#             elif durasi_nyeri <= threshold.batas_fase2_minggu:
#                 rekomendasi = "latihan_mandiri"
#                 fase = "F2"

#             else:
#                 rekomendasi = "latihan_mandiri"
#                 fase = "F3"
#         else:
#             rekomendasi = "rujuk"
#             fase = None

#         perlu_evaluasi = durasi_nyeri > threshold.batas_fase2_minggu

#         # ===============================
#         # 6ï¸âƒ£ Simpan ke DB
#         # ===============================
#         kondisi = KondisiUser(
#             id_form=str(uuid.uuid4())[:4],
#             id_user=user_id,
#             id_bagian=id_bagian,
#             tingkat_nyeri=tingkat_nyeri,
#             durasi_nyeri_minggu=durasi_nyeri,
#             has_red_flag=has_red_flag,
#             red_flag_detail=red_flag_detail or None
#         )

#         db.session.add(kondisi)
#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "message": "Kondisi user berhasil disimpan",
#             "data": {
#                 "id_form": kondisi.id_form,
#                 "id_bagian": id_bagian,
#                 "tingkat_nyeri": tingkat_nyeri,
#                 "durasi_nyeri_minggu": durasi_nyeri,
#                 "has_red_flag": has_red_flag,
#                 "red_flag_detail": red_flag_detail or None,
#                 "rekomendasi": rekomendasi,
#                 "fase": fase,
#                 "perlu_evaluasi": perlu_evaluasi
#             }
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "error": str(e)
#         }), 500


# @kondisi_bp.route("/kondisi-user", methods=["POST"])
# @jwt_required()
# def create_kondisi_user():
#     user_id = get_jwt_identity()
#     data = request.get_json()

#     if not data:
#         return jsonify({
#             "success": False,
#             "message": "Payload kosong"
#         }), 400

#     try:
#         # ===============================
#         # 1ï¸âƒ£ Ambil Field Dasar
#         # ===============================
#         id_bagian = data.get("id_bagian")
#         tingkat_nyeri = data.get("tingkat_nyeri")
#         durasi_nyeri = data.get("durasi_nyeri_minggu")

#         # Safe conversion
#         try:
#             tingkat_nyeri = int(tingkat_nyeri)
#         except (TypeError, ValueError):
#             tingkat_nyeri = 0

#         try:
#             durasi_nyeri = int(durasi_nyeri)
#         except (TypeError, ValueError):
#             durasi_nyeri = 0

#         # ===============================
#         # 2ï¸âƒ£ Mapping dari answers (opsional)
#         # ===============================
#         if isinstance(data.get("answers"), list):
#             for answer in data["answers"]:
#                 q_id = answer.get("question_id")
#                 opt_id = answer.get("option_id")

#                 if not q_id or not opt_id:
#                     continue

#                 question = Question.query.get(q_id)
#                 option = QuestionOption.query.get(opt_id)

#                 if not question or not option:
#                     continue

#                 if question.target_field == "id_bagian":
#                     bagian = BagianTubuh.query.filter(
#                         BagianTubuh.nama_bagian.ilike(option.label)
#                     ).first()
#                     id_bagian = bagian.id_bagian if bagian else None

#                 elif question.target_field == "tingkat_nyeri":
#                     try:
#                         tingkat_nyeri = int(option.nilai)
#                     except:
#                         tingkat_nyeri = 0

#                 elif question.target_field == "durasi_nyeri_minggu":
#                     try:
#                         durasi_nyeri = int(option.nilai)
#                     except:
#                         durasi_nyeri = 0

#         # ===============================
#         # 3ï¸âƒ£ Validasi Bagian Tubuh
#         # ===============================
#         if not id_bagian:
#             return jsonify({
#                 "success": False,
#                 "message": "Bagian tubuh tidak ditemukan"
#             }), 400

#         bagian_exist = BagianTubuh.query.filter_by(
#             id_bagian=id_bagian
#         ).first()

#         if not bagian_exist:
#             return jsonify({
#                 "success": False,
#                 "message": "Bagian tubuh tidak valid"
#             }), 400

#         # ===============================
#         # 4ï¸âƒ£ Ambil Threshold Dynamic
#         # ===============================
#         threshold = KlinisThresholdBagian.query.filter_by(
#             id_bagian=id_bagian
#         ).first()

#         if not threshold:
#             return jsonify({
#                 "success": False,
#                 "message": "Threshold klinis belum dikonfigurasi"
#             }), 400

#         # ===============================
#         # 5ï¸âƒ£ Red Flag Detection (Dynamic)
#         # ===============================
#         red_flag_detail = {
#             key: True
#             for key, value in data.items()
#             if key.startswith("rf_") and value is True
#         }

#         # Auto red flag dari threshold
#         if tingkat_nyeri >= threshold.batas_nyeri_ekstrem:
#             red_flag_detail["rf_nyeri_ekstrem"] = True

#         if durasi_nyeri >= threshold.batas_durasi_kronis:
#             red_flag_detail["rf_durasi_kronis"] = True

#         has_red_flag = bool(red_flag_detail)

#         # ===============================
#         # 6ï¸âƒ£ Rule Engine (Simple & Clean)
#         # ===============================
#         if has_red_flag:
#             rekomendasi = "rujuk"

#         elif 1 <= tingkat_nyeri <= threshold.batas_nyeri_mandiri:
#             rekomendasi = "latihan_mandiri"

#         else:
#             rekomendasi = "rujuk"

#         perlu_evaluasi = durasi_nyeri >= threshold.batas_durasi_kronis

#         # ===============================
#         # 7ï¸âƒ£ Simpan ke Database
#         # ===============================
#         kondisi = KondisiUser(
#             id_form=str(uuid.uuid4())[:8],  # lebih aman dari 4 digit
#             id_user=user_id,
#             id_bagian=id_bagian,
#             tingkat_nyeri=tingkat_nyeri,
#             durasi_nyeri_minggu=durasi_nyeri,
#             has_red_flag=has_red_flag,
#             red_flag_detail=red_flag_detail or None,
#             created_at=datetime.utcnow()
#         )

#         db.session.add(kondisi)
#         db.session.commit()

#         # ===============================
#         # 8ï¸âƒ£ Response
#         # ===============================
#         return jsonify({
#             "success": True,
#             "message": "Kondisi user berhasil disimpan",
#             "data": {
#                 "id_form": kondisi.id_form,
#                 "id_bagian": id_bagian,
#                 "tingkat_nyeri": tingkat_nyeri,
#                 "durasi_nyeri_minggu": durasi_nyeri,
#                 "has_red_flag": has_red_flag,
#                 "red_flag_detail": red_flag_detail or None,
#                 "rekomendasi": rekomendasi,
#                 "perlu_evaluasi": perlu_evaluasi
#             }
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "error": str(e)
#         }), 500
# @kondisi_bp.route("/kondisi-user", methods=["POST"])
# @jwt_required()
# def create_kondisi_user():
#     user_id = str(get_jwt_identity())
#     data = request.get_json() or {}

#     if not data:
#         return jsonify({
#             "success": False,
#             "message": "Payload kosong"
#         }), 400

#     try:
#         id_bagian = data.get("id_bagian")
#         tingkat_nyeri = int(data.get("tingkat_nyeri") or 0)
#         durasi_nyeri = int(
#             data.get("durasi_nyeri_minggu") or
#             data.get("durasi_nyeri") or
#             0
#         )

#         answers = data.get("answers", [])
#         if answers is None:
#             answers = []
#         if not isinstance(answers, list):
#             return jsonify({
#                 "success": False,
#                 "message": "answers harus berupa array"
#             }), 400

#         red_flag_detail = {}

#         for answer in answers:
#             q_id = answer.get("question_id")
#             opt_id = answer.get("option_id")

#             question = Question.query.get(q_id)
#             option = QuestionOption.query.get(opt_id)

#             if not question or not option:
#                 continue

#             if option.key and option.key.startswith("rf_") and int(option.nilai or 0) != 0:
#                 red_flag_detail[option.key] = True

#             if question.category == "PAIN":
#                 tingkat_nyeri = int(option.nilai or 0)

#             elif question.category == "DURATION":
#                 durasi_nyeri = int(option.nilai or 0)

#             elif not question.category or question.category in ["id_bagian", "BAGIAN"] or option.key == "id_bagian":
#                 bagian = BagianTubuh.query.filter(
#                     (BagianTubuh.nama_bagian.ilike(option.label)) |
#                     (BagianTubuh.id_bagian == str(option.key)) |
#                     (BagianTubuh.id_bagian == str(option.nilai))
#                 ).first()
#                 if bagian:
#                     id_bagian = bagian.id_bagian

#         if not id_bagian:
#             return jsonify({
#                 "success": False,
#                 "message": "Bagian tubuh tidak ditemukan"
#             }), 400

#         id_bagian = str(id_bagian)
#         bagian_exist = BagianTubuh.query.filter_by(id_bagian=id_bagian).first()
#         if not bagian_exist:
#             return jsonify({
#                 "success": False,
#                 "message": "Bagian tubuh tidak valid"
#             }), 400

#         has_red_flag = bool(red_flag_detail)
#         perlu_evaluasi = False

#         if has_red_flag:
#             rekomendasi = "rujuk"
#             perlu_evaluasi = True
#         else:
#             threshold = KlinisThresholdBagian.query.filter_by(
#                 id_bagian=id_bagian
#             ).first()

#             if not threshold:
#                 return jsonify({
#                     "success": False,
#                     "message": "Threshold belum dikonfigurasi"
#                 }), 400

#             if tingkat_nyeri >= threshold.batas_nyeri_ekstrem:
#                 rekomendasi = "rujuk"
#             elif durasi_nyeri >= threshold.batas_durasi_kronis:
#                 rekomendasi = "rujuk"
#             elif 1 <= tingkat_nyeri <= threshold.batas_nyeri_mandiri:
#                 rekomendasi = "latihan_mandiri"
#             else:
#                 rekomendasi = "rujuk"

#             perlu_evaluasi = durasi_nyeri >= threshold.batas_durasi_kronis

#         kondisi = KondisiUser(
#             id_form=generate_unique_id_form(),
#             id_user=user_id,
#             id_bagian=id_bagian,
#             tingkat_nyeri=tingkat_nyeri,
#             durasi_nyeri_minggu=durasi_nyeri,
#             has_red_flag=has_red_flag,
#             red_flag_detail=red_flag_detail or None,
#             created_at=datetime.utcnow()
#         )

#         db.session.add(kondisi)
#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "id_form": kondisi.id_form,
#             "message": "Screening berhasil disimpan",
#             "stop": has_red_flag,
#             "has_red_flag": has_red_flag,
#             "red_flag_detail": red_flag_detail or None,
#             "data": {
#                 "id_form": kondisi.id_form,
#                 "id_bagian": id_bagian,
#                 "tingkat_nyeri": tingkat_nyeri,
#                 "durasi_nyeri_minggu": durasi_nyeri,
#                 "has_red_flag": has_red_flag,
#                 "red_flag_detail": red_flag_detail or None,
#                 "rekomendasi": rekomendasi,
#                 "perlu_evaluasi": perlu_evaluasi
#             }
#         }), 201

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "error": str(e)
#         }), 500


@kondisi_bp.route("/kondisi-user", methods=["POST"])
@jwt_required()
def create_kondisi_user():
    user_id = str(get_jwt_identity())
    data = request.get_json() or {}

    if not data:
        return jsonify({
            "success": False,
            "message": "Payload kosong"
        }), 400

    try:
        id_bagian = data.get("id_bagian")

        tingkat_nyeri = int(data.get("tingkat_nyeri") or 0)

        durasi_nyeri = int(
            data.get("durasi_nyeri_minggu") or
            data.get("durasi_nyeri") or
            0
        )

        answers = data.get("answers", [])

        if answers is None:
            answers = []

        if not isinstance(answers, list):
            return jsonify({
                "success": False,
                "message": "answers harus berupa array"
            }), 400

        red_flag_detail = {}
        kondisi_detail = {}

        for answer in answers:
            q_id = answer.get("question_id")
            opt_id = answer.get("option_id")

            question = Question.query.get(q_id)
            option = QuestionOption.query.get(opt_id)

            if not question or not option:
                continue

            category = (question.category or "").upper()
            nilai = int(option.nilai or 0)

            # =========================
            # REDFLAG
            # =========================
            if category == "REDFLAG":
                if nilai != 0 and option.key != "tidak_ada":
                    red_flag_detail[option.key] = True

            # =========================
            # KONDISI
            # =========================
            elif category == "KONDISI":
                kondisi_detail[question.id] = {
                    "question": question.title,
                    "option_key": option.key,
                    "option_label": option.label,
                    "nilai": nilai
                }

            # =========================
            # TINGKAT NYERI
            # =========================
            elif category == "TINGKAT_NYERI":
                tingkat_nyeri = nilai

            # =========================
            # DURASI NYERI
            # =========================
            elif category == "DURASI_NYERI":
                # Kalau nilai option sudah berupa angka minggu, langsung pakai nilai.
                # Contoh:
                # 1 minggu atau kurang = 1
                # lebih dari 1 minggu = 2
                # 3 minggu atau kurang lutut = 3
                # lebih dari 3 minggu lutut = 4
                durasi_nyeri = nilai

        if not id_bagian:
            return jsonify({
                "success": False,
                "message": "Bagian tubuh tidak ditemukan"
            }), 400

        id_bagian = str(id_bagian)

        bagian_exist = BagianTubuh.query.filter_by(id_bagian=id_bagian).first()

        if not bagian_exist:
            return jsonify({
                "success": False,
                "message": "Bagian tubuh tidak valid"
            }), 400

        has_red_flag = bool(red_flag_detail)
        perlu_evaluasi = False

        if has_red_flag:
            rekomendasi = "rujuk"
            perlu_evaluasi = True

        else:
            threshold = KlinisThresholdBagian.query.filter_by(
                id_bagian=id_bagian
            ).first()

            if not threshold:
                return jsonify({
                    "success": False,
                    "message": "Threshold belum dikonfigurasi"
                }), 400

            if tingkat_nyeri >= threshold.batas_nyeri_ekstrem:
                rekomendasi = "rujuk"

            elif durasi_nyeri >= threshold.batas_durasi_kronis:
                rekomendasi = "rujuk"

            elif 1 <= tingkat_nyeri <= threshold.batas_nyeri_mandiri:
                rekomendasi = "latihan_mandiri"

            else:
                rekomendasi = "rujuk"

            perlu_evaluasi = durasi_nyeri >= threshold.batas_durasi_kronis

        kondisi = KondisiUser(
            id_form=generate_unique_id_form(),
            id_user=user_id,
            id_bagian=id_bagian,
            tingkat_nyeri=tingkat_nyeri,
            durasi_nyeri_minggu=durasi_nyeri,
            has_red_flag=has_red_flag,
            red_flag_detail=red_flag_detail or None,
            created_at=datetime.utcnow()
        )

        db.session.add(kondisi)
        db.session.commit()

        return jsonify({
            "success": True,
            "id_form": kondisi.id_form,
            "message": "Screening berhasil disimpan",
            "stop": has_red_flag,
            "has_red_flag": has_red_flag,
            "red_flag_detail": red_flag_detail or None,
            "data": {
                "id_form": kondisi.id_form,
                "id_bagian": id_bagian,
                "tingkat_nyeri": tingkat_nyeri,
                "durasi_nyeri_minggu": durasi_nyeri,
                "has_red_flag": has_red_flag,
                "red_flag_detail": red_flag_detail or None,
                "kondisi_detail": kondisi_detail or None,
                "rekomendasi": rekomendasi,
                "perlu_evaluasi": perlu_evaluasi
            }
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()

        db.session.rollback()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500