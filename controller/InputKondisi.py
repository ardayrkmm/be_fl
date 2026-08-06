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
        durasi_nyeri_label = ""

        for answer in answers:
            q_id = answer.get("question_id")
            opt_id = answer.get("option_id")

            question = Question.query.get(q_id)
            if not question:
                continue

            category = (question.category or "").upper()

            # =========================
            # TINGKAT NYERI
            # =========================
            if category == "TINGKAT_NYERI":
                try:
                    tingkat_nyeri = int(opt_id)
                except (ValueError, TypeError):
                    pass
                continue

            option = QuestionOption.query.get(opt_id)

            if not option:
                continue

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
                durasi_nyeri_label = option.label.lower()

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

        # Cek jika ada jawaban kuesioner pada kategori KONDISI yang bernilai positif
        has_kondisi_true = any(
            info.get("option_key") in ["sakit", "sensitif", "kaku"]
            for info in kondisi_detail.values()
        )

        threshold = KlinisThresholdBagian.query.filter_by(
            id_bagian=id_bagian
        ).first()

        if not threshold:
            return jsonify({
                "success": False,
                "message": "Threshold belum dikonfigurasi"
            }), 400

        if has_red_flag:
            rekomendasi = "rujuk"
            perlu_evaluasi = True
        elif tingkat_nyeri >= threshold.batas_nyeri_ekstrem:
            rekomendasi = "rujuk"
            perlu_evaluasi = True

        elif has_kondisi_true:
            rekomendasi = "latihan_mandiri"
            perlu_evaluasi = False
        elif tingkat_nyeri <= threshold.batas_nyeri_mandiri:
            rekomendasi = "latihan_mandiri"
            perlu_evaluasi = False
        else:
            rekomendasi = "rujuk"
            perlu_evaluasi = True

        existing = KondisiUser.query.filter_by(
            id_user=user_id,
            id_bagian=id_bagian
        ).first()

        if existing:
            existing.tingkat_nyeri = tingkat_nyeri
            existing.durasi_nyeri_minggu = durasi_nyeri
            existing.has_red_flag = has_red_flag
            existing.red_flag_detail = red_flag_detail or None
            existing.session_count = 0
            existing.last_session_date = None
            kondisi = existing
            mode = "updated"
        else:
            kondisi = KondisiUser(
                id_form=generate_unique_id_form(),
                id_user=user_id,
                id_bagian=id_bagian,
                tingkat_nyeri=tingkat_nyeri,
                durasi_nyeri_minggu=durasi_nyeri,
                has_red_flag=has_red_flag,
                red_flag_detail=red_flag_detail or None,
                session_count=0,
                last_session_date=None,
                created_at=datetime.utcnow()
            )
            db.session.add(kondisi)
            mode = "created"

        db.session.commit()

        stop_screening = has_red_flag or rekomendasi == "rujuk"
        message_res = "Screening berhasil disimpan"
        if stop_screening:
            message_res = "Silakan ke dokter atau fisioterapi terdekat. (Saran tambahan: Arummy Fisioterapi)"

        return jsonify({
            "success": True,
            "id_form": kondisi.id_form,
            "message": message_res,
            "stop": stop_screening,
            "has_red_flag": has_red_flag,
            "red_flag_detail": red_flag_detail or None,
            "mode": mode,
            "data": {
                "id_form": kondisi.id_form,
                "id_bagian": id_bagian,
                "tingkat_nyeri": tingkat_nyeri,
                "durasi_nyeri_minggu": durasi_nyeri,
                "has_red_flag": has_red_flag,
                "red_flag_detail": red_flag_detail or None,
                "kondisi_detail": kondisi_detail or None,
                "rekomendasi": rekomendasi,
                "perlu_evaluasi": perlu_evaluasi,
                "stop": stop_screening,
                "mode": mode
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