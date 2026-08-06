from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.notification_service import NotificationService
import uuid
from datetime import datetime, timedelta, timezone
import math

from tensorboard import program

from models import (
    BagianTubuh,
    HistoryAktifitas,
    JadwalLatihanUser,
    JadwalLatihanDetail,
    KlinisThresholdBagian,
    KondisiUser,
    Latihan,
    LatihanBagian,
    Question,
    QuestionOption,
    RehabRuleBagian,
    db,
    generate_random_id
)

from services.id_generator import generate_random_4_digit
latihanuser_bp = Blueprint("latihanUser", __name__)

ACTIVE_JADWAL_STATUSES = ("Unlocked", "Need Screening", "Locked")
SWITCHED_JADWAL_STATUS = "Switched"
HIDDEN_JADWAL_STATUSES = ("Closed", "Switched", "Cancelled", "Resolved")


def get_latest_active_program_anchor(user_id):
    return (
        JadwalLatihanUser.query
        .filter(
            JadwalLatihanUser.id_user == user_id,
            JadwalLatihanUser.status.in_(ACTIVE_JADWAL_STATUSES),
            ~JadwalLatihanUser.status.in_(HIDDEN_JADWAL_STATUSES)
        )
        .order_by(
            JadwalLatihanUser.created_at.desc(),
            JadwalLatihanUser.tanggal.desc()
        )
        .first()
    )


def need_select_area_payload(data=None):
    return {
        "success": True,
        "mode": "need_select_area",
        "message": "Silakan pilih area nyeri terlebih dahulu.",
        "redirect": "/body",
        "data": [] if data is None else data
    }


def check_need_final_assessment(user_id):
    latest_jadwal = (
        JadwalLatihanUser.query
        .filter(JadwalLatihanUser.id_user == user_id)
        .order_by(JadwalLatihanUser.created_at.desc(), JadwalLatihanUser.tanggal.desc())
        .first()
    )
    if not latest_jadwal:
        return False, None, None

    if latest_jadwal.status in ["Closed", "Switched", "Resolved"]:
        return False, None, None

    schedules = (
        JadwalLatihanUser.query
        .filter(
            JadwalLatihanUser.id_user == user_id,
            JadwalLatihanUser.id_form == latest_jadwal.id_form,
            ~JadwalLatihanUser.status.in_(HIDDEN_JADWAL_STATUSES)
        )
        .all()
    )

    if not schedules:
        return False, None, None

    all_completed = all(s.status == "Completed" for s in schedules)
    if all_completed:
        kondisi = KondisiUser.query.get(latest_jadwal.id_form)
        id_bagian = kondisi.id_bagian if kondisi else None
        sorted_schedules = sorted(schedules, key=lambda s: s.tanggal)
        last_id_jadwal = sorted_schedules[-1].id_jadwal
        return True, id_bagian, last_id_jadwal

    return False, None, None

@latihanuser_bp.route("/jadwal/hari-ini", methods=["GET"])
@jwt_required()
def get_jadwal_hari_ini():
    user_id = str(get_jwt_identity())

    need_final_eval, final_id_bagian, final_id_jadwal = check_need_final_assessment(user_id)
    if need_final_eval:
        return jsonify({
            "success": True,
            "need_final_assessment": True,
            "final_assessment_id_bagian": final_id_bagian,
            "final_assessment_id_jadwal": final_id_jadwal,
            "mode": "final_assessment",
            "program": []
        }), 200

    active_anchor = get_latest_active_program_anchor(user_id)
    if not active_anchor:
        payload = need_select_area_payload()
        payload["program"] = []
        return jsonify(payload), 200

    start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    end = start + timedelta(days=1)

    jadwal_list = JadwalLatihanUser.query.filter(
        JadwalLatihanUser.id_user == user_id,
        JadwalLatihanUser.id_form == active_anchor.id_form,
        JadwalLatihanUser.tanggal >= start,
        JadwalLatihanUser.tanggal < end,
        ~JadwalLatihanUser.status.in_(HIDDEN_JADWAL_STATUSES)
    ).all()

    if not jadwal_list:
        return jsonify({
            "success": True,
            "mode": "rest_day",
            "message": "Hari ini jadwal istirahat",
            "program": []
        }), 200

    need_screening = next((j for j in jadwal_list if j.status == "Need Screening"), None)
    if need_screening:
        return jsonify({
            "success": True,
            "mode": "pain_screening",
            "message": "Sebelum latihan hari ini, isi tingkat nyeri terlebih dahulu.",
            "data": {
                "id_jadwal": need_screening.id_jadwal,
                "nama_jadwal": need_screening.nama_jadwal,
                "status": need_screening.status,
                "question": {
                    "title": "Berapa tingkat nyeri Anda hari ini?",
                    "subtitle": "Gunakan skala 0 sampai 10",
                    "min": 0,
                    "max": 10
                }
            }
        }), 200

    unlocked_list = [j for j in jadwal_list if j.status == "Unlocked"]
    if not unlocked_list:
        return jsonify({
            "success": True,
            "mode": "rest_day",
            "message": "Tidak ada jadwal yang dapat dimulai hari ini",
            "program": []
        }), 200

    program = []
    for j in unlocked_list:
        kondisi_for_jadwal = KondisiUser.query.get(j.id_form)
        id_bagian_for_jadwal = kondisi_for_jadwal.id_bagian if kondisi_for_jadwal else None
        for detail in j.details:
            lat = detail.latihan
            if not lat:
                continue

            rule_for_lat = None
            if id_bagian_for_jadwal:
                rule_for_lat = LatihanBagian.query.filter_by(
                    id_latihan=lat.id_latihan,
                    id_bagian=id_bagian_for_jadwal
                ).first()

            final_set = rule_for_lat.target_set if rule_for_lat else None
            final_rep = rule_for_lat.target_repetisi if rule_for_lat else None
            final_waktu = rule_for_lat.target_waktu if rule_for_lat else None
            final_hold = int(rule_for_lat.hold_detik) if (rule_for_lat and rule_for_lat.hold_detik is not None) else 0

            if kondisi_for_jadwal and kondisi_for_jadwal.durasi_nyeri_minggu is not None:
                durasi = kondisi_for_jadwal.durasi_nyeri_minggu
                if durasi < 2:
                    final_set = 2
                    if final_waktu is not None and final_waktu > 0:
                        final_waktu = 10
                    else:
                        final_rep = 8
                elif 2 <= durasi <= 4:
                    final_set = 3
                    if final_waktu is not None and final_waktu > 0:
                        final_waktu = 20
                    else:
                        final_rep = 12

            program.append({
                "id_jadwal": j.id_jadwal,
                "nama_jadwal": j.nama_jadwal,
                "status": j.status,
                "latihan": {
                    "id_latihan": lat.id_latihan,
                    "nama_latihan": lat.nama_latihan,
                    "deskripsi": lat.deskripsi,
                    "gambar": lat.url_gambar,
                    "video_url": lat.video_url,
                    "sisi": detail.sisi,
                    "target": {
                        "set": final_set,
                        "repetisi": final_rep,
                        "waktu": final_waktu,
                        "hold_detik": final_hold
                    }
                }
            })

    return jsonify({
        "success": True,
        "mode": "ready_to_exercise",
        "tanggal": start.strftime("%Y-%m-%d"),
        "program": program
    }), 200


@latihanuser_bp.route("/jadwal/<id_jadwal>/pain-screening", methods=["POST"])
@jwt_required()
def submit_pain_screening(id_jadwal):
    user_id = str(get_jwt_identity())
    data = request.get_json() or {}

    if "tingkat_nyeri" not in data:
        return jsonify({"success": False, "message": "tingkat_nyeri wajib diisi"}), 400

    try:
        tingkat_nyeri = float(data.get("tingkat_nyeri"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "tingkat_nyeri harus berupa angka"}), 400

    if tingkat_nyeri < 0 or tingkat_nyeri > 10:
        return jsonify({"success": False, "message": "tingkat_nyeri harus berada di rentang 0 sampai 10"}), 400

    jadwal = JadwalLatihanUser.query.filter_by(id_jadwal=id_jadwal, id_user=user_id).first()

    if not jadwal:
        return jsonify({"success": False, "message": "Jadwal tidak ditemukan"}), 404
    if jadwal.status in HIDDEN_JADWAL_STATUSES:
        return jsonify({"success": False, "message": "Program latihan ini sudah ditutup"}), 400
    if jadwal.status == "Locked":
        return jsonify({"success": False, "message": "Jadwal masih terkunci"}), 400
    if jadwal.status == "Completed":
        return jsonify({"success": False, "message": "Jadwal sudah selesai"}), 400

    kondisi = KondisiUser.query.get(jadwal.id_form) if jadwal.id_form else None
    threshold = KlinisThresholdBagian.query.filter_by(id_bagian=kondisi.id_bagian).first() if kondisi else None
    batas_nyeri_ekstrem = threshold.batas_nyeri_ekstrem if threshold and threshold.batas_nyeri_ekstrem is not None else 8
    batas_nyeri_mandiri = threshold.batas_nyeri_mandiri if threshold and threshold.batas_nyeri_mandiri is not None else 4

    last_history = (
        db.session.query(HistoryAktifitas)
        .join(JadwalLatihanUser, HistoryAktifitas.id_jadwal == JadwalLatihanUser.id_jadwal)
        .filter(
            HistoryAktifitas.id_user == user_id,
            JadwalLatihanUser.id_form == jadwal.id_form,
            HistoryAktifitas.id_jadwal != jadwal.id_jadwal
        )
        .order_by(HistoryAktifitas.tanggal.desc())
        .first()
    )

    previous_pain = None
    if last_history and last_history.vas_sesudah is not None:
        previous_pain = last_history.vas_sesudah
    elif kondisi and kondisi.tingkat_nyeri is not None:
        try:
            previous_pain = float(kondisi.tingkat_nyeri)
        except ValueError:
            pass

    is_zero = tingkat_nyeri == 0

    rule_global = RehabRuleBagian.query.filter_by(id_bagian=kondisi.id_bagian).order_by(RehabRuleBagian.id.asc()).first() if kondisi else None
    max_minggu = int(rule_global.max_durasi_minggu_home or 1) if rule_global else 12

    if is_zero:
        decision = "resolved"
        action_result = "resolved"
        can_start_exercise = True
        jadwal.status = "Unlocked"
        rekomendasi = "Nyeri sudah hilang. Anda bisa tetap lanjut sesi ini atau memilih area nyeri lain."
    elif tingkat_nyeri >= batas_nyeri_ekstrem:
        decision = "stop"
        action_result = "stop"
        can_start_exercise = False
        jadwal.status = "Stopped"
        rekomendasi = "Nyeri terlalu tinggi. Sebaiknya hentikan latihan mandiri dan konsultasikan ke tenaga kesehatan."
    elif tingkat_nyeri > batas_nyeri_mandiri:
        decision = "warning"
        action_result = "maintain"
        can_start_exercise = False
        jadwal.status = "Need Screening"
        rekomendasi = "Nyeri masih cukup tinggi. Sebaiknya istirahat hari ini."
    elif previous_pain is not None and tingkat_nyeri > previous_pain:
        if jadwal.minggu >= max_minggu:
            decision = "stop"
            action_result = "stop"
            can_start_exercise = False
            jadwal.status = "Stopped"
            rekomendasi = "Batas waktu program mandiri telah tercapai tanpa penurunan nyeri. Silakan rujuk ke tenaga kesehatan."
        else:
            decision = "warning"
            action_result = "maintain"
            can_start_exercise = False
            jadwal.status = "Need Screening"
            rekomendasi = "Nyeri meningkat dibanding sebelumnya. Silakan istirahat sampai besok."
    elif previous_pain is not None and tingkat_nyeri == previous_pain:
        if jadwal.minggu >= max_minggu:
            decision = "stop"
            action_result = "stop"
            can_start_exercise = False
            jadwal.status = "Stopped"
            rekomendasi = "Batas waktu program mandiri telah tercapai tanpa penurunan nyeri. Silakan rujuk ke tenaga kesehatan."
        else:
            decision = "safe"
            action_result = "maintain"
            can_start_exercise = True
            jadwal.status = "Unlocked"
            rekomendasi = "Nyeri masih stabil di angka yang sama. Latihan dapat dilanjutkan."
    else:
        decision = "safe"
        action_result = "maintain"
        can_start_exercise = True
        jadwal.status = "Unlocked"
        rekomendasi = "Nyeri aman. Latihan dapat dilanjutkan."

    if kondisi:
        kondisi.tingkat_nyeri = int(tingkat_nyeri) if tingkat_nyeri.is_integer() else tingkat_nyeri

    db.session.commit()

    is_decreased = previous_pain is not None and tingkat_nyeri < previous_pain
    offer_other_pain = is_zero or (can_start_exercise and is_decreased)

    question_text = "Nyeri Anda menurun. Apakah Anda ingin pindah latihan untuk area tubuh yang lain?"
    if is_zero:
        question_text = "Nyeri Anda sudah hilang (0). Apakah Anda ingin pindah latihan untuk area tubuh yang lain?"

    next_action = {
        "type": "ask_other_pain",
        "question": question_text,
        "on_yes": "continue_exercise",
        "on_no": "go_to_initial_assessment"
    } if offer_other_pain else None
    tingkat_nyeri_value = int(tingkat_nyeri) if tingkat_nyeri.is_integer() else tingkat_nyeri

    return jsonify({
        "success": True,
        "message": rekomendasi,
        "data": {
            "id_jadwal": jadwal.id_jadwal,
            "status_jadwal": jadwal.status,
            "tingkat_nyeri": tingkat_nyeri_value,
            "decision": decision,
            "action_result": action_result,
            "can_start_exercise": can_start_exercise,
            "offer_other_pain": offer_other_pain,
            "next_action": next_action,
            "rekomendasi": rekomendasi
        }
    }), 200


@latihanuser_bp.route("/jadwal/<id_jadwal>/switch-area", methods=["POST"])
@jwt_required()
def switch_pain_area(id_jadwal):
    user_id = str(get_jwt_identity())

    jadwal = JadwalLatihanUser.query.filter_by(
        id_jadwal=id_jadwal,
        id_user=user_id
    ).first()

    if not jadwal:
        return jsonify({"success": False, "message": "Jadwal tidak ditemukan"}), 404

    old_form_id = jadwal.id_form
    if not old_form_id:
        return jsonify({
            "success": False,
            "message": "id_form jadwal lama tidak ditemukan"
        }), 400

    try:
        old_schedules = JadwalLatihanUser.query.filter(
            JadwalLatihanUser.id_user == user_id,
            JadwalLatihanUser.id_form == old_form_id,
            ~JadwalLatihanUser.status.in_(HIDDEN_JADWAL_STATUSES)
        ).all()

        for schedule in old_schedules:
            schedule.status = SWITCHED_JADWAL_STATUS

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Program lama ditutup. Silakan pilih area nyeri baru.",
            "redirect": "/body",
            "need_new_screening": True,
            "old_form_id": old_form_id,
            "old_jadwal_id": jadwal.id_jadwal,
            "switched_count": len(old_schedules)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Gagal menutup program lama",
            "error": str(e)
        }), 500




@latihanuser_bp.route("/generate-jadwal", methods=["POST"])
@jwt_required()
def generate_jadwal_otomatis():
    user_id = str(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    
    requested_id_form = data.get("id_form")
    requested_id_bagian = data.get("id_bagian")

    requested_id_form = str(requested_id_form).strip() if requested_id_form is not None else None
    requested_id_bagian = str(requested_id_bagian).strip() if requested_id_bagian is not None else None

    requested_id_form = requested_id_form or None
    requested_id_bagian = requested_id_bagian or None

    if requested_id_form:
        kondisi = KondisiUser.query.filter(
            KondisiUser.id_user == user_id,
            KondisiUser.id_form == requested_id_form
        ).first()

    elif requested_id_bagian:
        kondisi = KondisiUser.query.filter(
            KondisiUser.id_user == user_id,
            KondisiUser.id_bagian == requested_id_bagian
        ).order_by(KondisiUser.created_at.desc()).first()

    else:
        return jsonify({
            "success": False,
            "message": "id_form atau id_bagian wajib dikirim untuk generate jadwal"
        }), 400

    if not kondisi:
        return jsonify({
            "success": False,
            "message": "Kondisi user tidak ditemukan"
        }), 404

    # ======================================================
    # 2ï¸âƒ£ CEK PROGRAM AKTIF
    # ======================================================
    active_program = (
        JadwalLatihanUser.query
        .filter(
            JadwalLatihanUser.id_user == user_id,
            JadwalLatihanUser.status.in_(ACTIVE_JADWAL_STATUSES),
            ~JadwalLatihanUser.status.in_(HIDDEN_JADWAL_STATUSES)
        )
        .order_by(
            JadwalLatihanUser.created_at.desc(),
            JadwalLatihanUser.tanggal.desc()
        )
        .first()
    )

    if active_program:
        return jsonify({
            "success": False,
            "message": "Selesaikan program sebelumnya terlebih dahulu"
        }), 400

    vas = int(kondisi.tingkat_nyeri or 0)
    lama_nyeri = int(kondisi.durasi_nyeri_minggu or 0)
    id_bagian = str(kondisi.id_bagian)

    bagian = BagianTubuh.query.get(id_bagian)
    nama_bagian = bagian.nama_bagian if bagian else "Unknown"

  
    rule_global = (
        RehabRuleBagian.query
        .filter_by(id_bagian=id_bagian)
        .order_by(RehabRuleBagian.id.asc())
        .first()
    )

    if not rule_global:
        return jsonify({"success": False, "message": "Rule belum ada"}), 400

    max_minggu = int(rule_global.max_durasi_minggu_home or 1)

    # ======================================================
    # 4.1. CHECK SAFETY OF ASSESSMENT (UNSAFE / RUJUK)
    # ======================================================
    thresholds = KlinisThresholdBagian.query.filter_by(id_bagian=id_bagian).first()
    batas_nyeri_ekstrem = thresholds.batas_nyeri_ekstrem if thresholds else 8
    batas_nyeri_mandiri = thresholds.batas_nyeri_mandiri if thresholds else 4

    # 1. Red Flag check
    if kondisi.has_red_flag:
        return jsonify({
            "success": True,
            "mode": "unsafe_assessment",
            "message": "Latihan mandiri belum disarankan berdasarkan hasil assessment Anda.",
            "reason": "Terdapat tanda bahaya (red flag) yang memerlukan pemeriksaan klinis.",
            "recommendation": "Silakan konsultasikan kondisi Anda ke dokter atau fisioterapis terlebih dahulu.",
            "redirect": "/body",
            "can_generate": False
        }), 200

    # 2. Extreme pain check (VAS >= batas_nyeri_ekstrem)
    if vas >= batas_nyeri_ekstrem:
        return jsonify({
            "success": True,
            "mode": "unsafe_assessment",
            "message": "Latihan mandiri belum disarankan berdasarkan hasil assessment Anda.",
            "reason": f"Tingkat nyeri Anda sangat tinggi (Skala {vas} dari 10).",
            "recommendation": "Silakan konsultasikan kondisi Anda ke dokter atau fisioterapis terlebih dahulu.",
            "redirect": "/body",
            "can_generate": False
        }), 200

    # 3. Pain exceeds self-management limit (VAS > batas_nyeri_mandiri)
    if vas > batas_nyeri_mandiri:
        return jsonify({
            "success": True,
            "mode": "unsafe_assessment",
            "message": "Latihan mandiri belum disarankan berdasarkan hasil assessment Anda.",
            "reason": f"Tingkat nyeri Anda (Skala {vas}) berada di luar batas aman latihan mandiri (Maksimal Skala {batas_nyeri_mandiri}).",
            "recommendation": "Silakan konsultasikan kondisi Anda ke dokter atau fisioterapis terlebih dahulu.",
            "redirect": "/body",
            "can_generate": False
        }), 200

    # 4. Duration check
    if lama_nyeri > max_minggu:
        return jsonify({
            "success": True,
            "mode": "rujuk",
            "message": "Latihan mandiri belum disarankan.",
            "reason": f"Nyeri berlangsung selama {lama_nyeri} minggu (Batas maksimal latihan mandiri adalah {max_minggu} minggu).",
            "recommendation": "Silakan konsultasikan kondisi Anda ke dokter atau fisioterapis terlebih dahulu.",
            "redirect": "/body",
            "can_generate": False
        }), 200

   
    latihans_pool = (
        db.session.query(Latihan, LatihanBagian)
        .join(LatihanBagian, Latihan.id_latihan == LatihanBagian.id_latihan)
        .filter(LatihanBagian.id_bagian == id_bagian)
        .order_by(Latihan.level.asc())
        .all()
    )

    if not latihans_pool:
        return jsonify({
            "success": False,
            "message": "Latihan belum tersedia"
        }), 404

   
    sessions_per_week = 3  # bebas ubah nanti kalau mau dynamic

    minggu = 1
    sesi = 1
    total_sesi = 0
    status_jadwal_pertama = None

    try:
        while minggu <= max_minggu:

            for sesi in range(1, sessions_per_week + 1):

                id_grup = generate_random_id(4)

                days_offset = (minggu - 1) * 7 + (sesi - 1) * 2
                jadwal_tanggal = datetime.utcnow() + timedelta(days=days_offset)

                status = "Unlocked" if minggu == 1 and sesi == 1 else "Locked"
                if status_jadwal_pertama is None:
                    status_jadwal_pertama = status

                jadwal_grup = JadwalLatihanUser(
                    id_jadwal=id_grup,
                    id_user=user_id,
                    id_form=kondisi.id_form,
                    fase=f"M{minggu}",
                    fase_label=f"Minggu {minggu} - Sesi {sesi}",
                    url_gambar=latihans_pool[0][0].url_gambar if latihans_pool else None,
                    nama_jadwal=f"Program {nama_bagian} - M{minggu} Sesi {sesi}",
                    tanggal=jadwal_tanggal,
                    status=status,
                    created_at=datetime.utcnow()
                )

                db.session.add(jadwal_grup)

                # ======================================================
                # ðŸ”¥ MASUKKAN SEMUA LATIHAN KE 1 SESI
                # ======================================================
                urutan = 1

                for lat, rule in latihans_pool:

                    if lat.is_unilateral:
                        db.session.add(JadwalLatihanDetail(
                            id_detail=generate_random_id(8),
                            id_jadwal=id_grup,
                            id_latihan=lat.id_latihan,
                            sisi="Kanan",
                            urutan=urutan
                        ))
                        urutan += 1

                        db.session.add(JadwalLatihanDetail(
                            id_detail=generate_random_id(8),
                            id_jadwal=id_grup,
                            id_latihan=lat.id_latihan,
                            sisi="Kiri",
                            urutan=urutan
                        ))
                        urutan += 1
                    else:
                        db.session.add(JadwalLatihanDetail(
                            id_detail=generate_random_id(8),
                            id_jadwal=id_grup,
                            id_latihan=lat.id_latihan,
                            urutan=urutan
                        ))
                        urutan += 1

                total_sesi += 1

                # ======================================================
                # NOTIFIKASI
                # ======================================================
                NotificationService.create_notification({
            "id_user": user_id,
            "judul": f"Latihan {nama_bagian} Hari Ini",
            "pesan": f"{jadwal_grup.fase_label} sudah tersedia. Yuk mulai latihan mandiri Anda.",
            "tipe": "reminder",
            "jadwal_kirim": jadwal_grup.tanggal,
            "id_jadwal": jadwal_grup.id_jadwal
            })

            minggu += 1

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Program berhasil dibuat",
            "mode": "home_program",
            "id_form": kondisi.id_form,
            "jumlah_jadwal_dibuat": total_sesi,
            "status_jadwal_pertama": status_jadwal_pertama,
            "sessions_per_week": sessions_per_week,
            "total_minggu": max_minggu,
            "total_sesi": total_sesi,
            "vas": vas,
            "lama_nyeri": lama_nyeri,
            "data": {
                "id_form": kondisi.id_form,
                "jumlah_jadwal_dibuat": total_sesi,
                "status_jadwal_pertama": status_jadwal_pertama
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Terjadi kesalahan",
            "error": str(e)
        }), 500

@latihanuser_bp.route("/jadwal/fase", methods=["GET"])
@jwt_required()
def get_jadwal_per_fase():
    user_id = str(get_jwt_identity())

    active_anchor = get_latest_active_program_anchor(user_id)
    if not active_anchor:
        payload = need_select_area_payload(data=None)
        payload["data"] = None
        payload["code"] = "ACTIVE_PROGRAM_NOT_FOUND"
        return jsonify(payload), 200

    active_program = (
        JadwalLatihanUser.query
        .filter(
            JadwalLatihanUser.id_user == user_id,
            JadwalLatihanUser.id_form == active_anchor.id_form,
            JadwalLatihanUser.status.in_(ACTIVE_JADWAL_STATUSES),
            ~JadwalLatihanUser.status.in_(HIDDEN_JADWAL_STATUSES)
        )
        .order_by(
            JadwalLatihanUser.created_at.desc(),
            JadwalLatihanUser.tanggal.desc()
        )
        .options(
            db.joinedload(JadwalLatihanUser.details)
              .joinedload(JadwalLatihanDetail.latihan)
        )
        .first()
    )

    kondisi = KondisiUser.query.get(active_program.id_form)
    id_bagian = kondisi.id_bagian if kondisi else None

    latihan_map = {}

    for detail in active_program.details:
        lat = detail.latihan
        if not lat:
            continue
        rule = LatihanBagian.query.filter_by(
            id_latihan=lat.id_latihan,
            id_bagian=id_bagian
        ).first()

        if lat.id_latihan not in latihan_map:
            final_set = rule.target_set if rule else None
            final_rep = rule.target_repetisi if rule else None
            final_waktu = rule.target_waktu if rule else None
            final_hold = int(rule.hold_detik) if (rule and rule.hold_detik is not None) else 0

            if kondisi and kondisi.durasi_nyeri_minggu is not None:
                durasi = kondisi.durasi_nyeri_minggu
                if durasi < 2:
                    final_set = 2
                    if final_waktu is not None and final_waktu > 0:
                        final_waktu = 10
                    else:
                        final_rep = 8
                elif 2 <= durasi <= 4:
                    final_set = 3
                    if final_waktu is not None and final_waktu > 0:
                        final_waktu = 20
                    else:
                        final_rep = 12

            latihan_map[lat.id_latihan] = {
                "id_latihan": lat.id_latihan,
                "nama_latihan": lat.nama_latihan,
                "deskripsi": lat.deskripsi,
                "image_url": lat.url_gambar,
                "level": int(lat.level) if lat.level else 1,
                "duration": int(final_waktu or 0),
                "target": {
                    "set": final_set,
                    "repetisi": final_rep,
                    "waktu": final_waktu,
                    "hold_detik": final_hold
                },
                "video_url": lat.video_url,
                "is_unilateral": lat.is_unilateral,
                "sisi": []
            }

        if detail.sisi:
            latihan_map[lat.id_latihan]["sisi"].append(detail.sisi)

    result = list(latihan_map.values())

    return jsonify({
        "success": True,
        "code": "GET_JADWAL_PER_FASE_SUCCESS",
        "data": {
            "program_id": active_program.id_jadwal,
            "nama_program": active_program.nama_jadwal,
            "fase": active_program.fase,
            "tanggal_mulai": active_program.tanggal.strftime("%Y-%m-%d"),
            "total_latihan": len(result),
            "latihan": result
        }
    }), 200

@latihanuser_bp.route("/jadwal/semua", methods=["GET"])
@jwt_required()
def get_jadwal_semua():
    user_id = str(get_jwt_identity())

    # ==============================
    # 1. Ambil program aktif terbaru (mencakup status Completed)
    # ==============================
    latest_jadwal = (
        JadwalLatihanUser.query
        .filter(
            JadwalLatihanUser.id_user == user_id,
            ~JadwalLatihanUser.status.in_(HIDDEN_JADWAL_STATUSES)
        )
        .order_by(JadwalLatihanUser.created_at.desc(), JadwalLatihanUser.tanggal.desc())
        .first()
    )
    if not latest_jadwal:
        payload = need_select_area_payload()
        payload["code"] = "ACTIVE_PROGRAM_NOT_FOUND"
        return jsonify(payload), 200

    kondisi = KondisiUser.query.get(latest_jadwal.id_form)

    id_bagian = kondisi.id_bagian if kondisi else None

    # ==============================
    # 2. Ambil jadwal dari program aktif terbaru saja
    # ==============================
    semua_program = (
        JadwalLatihanUser.query
        .filter(
            JadwalLatihanUser.id_user == user_id,
            JadwalLatihanUser.id_form == latest_jadwal.id_form,
            ~JadwalLatihanUser.status.in_(HIDDEN_JADWAL_STATUSES)
        )
        .order_by(
            JadwalLatihanUser.tanggal.asc(),
            JadwalLatihanUser.created_at.asc()
        )
        .options(
            db.joinedload(JadwalLatihanUser.details)
              .joinedload(JadwalLatihanDetail.latihan)
        )
        .all()
    )

    hasil = []

    # ==============================
    # 3. Loop tiap program
    # ==============================
    for prog in semua_program:

        latihan_list = []

        for detail in prog.details:
            lat = detail.latihan
            if not lat:
                continue

            # ==============================
            # 4. Ambil rule berdasarkan bagian
            # ==============================
            rule = None
            if id_bagian:
                rule = LatihanBagian.query.filter_by(
                    id_latihan=lat.id_latihan,
                    id_bagian=id_bagian
                ).first()

            # ==============================
            # 5. Build 1 item = 1 gerakan
            # ==============================
            latihan_item = {
                "id_latihan": lat.id_latihan,
                "nama_latihan": lat.nama_latihan,
                "deskripsi": lat.deskripsi,
                "image_url": lat.url_gambar,
                "video_url": lat.video_url,
                "level": int(lat.level) if lat.level else 1,

                # ðŸ”¥ TARGET LATIHAN
                "target": {
                    "set": rule.target_set if rule else None,
                    "repetisi": rule.target_repetisi if rule else None,
                    "waktu": rule.target_waktu if rule else None,
                    "hold_detik": int(rule.hold_detik) if (rule and rule.hold_detik is not None) else 0
                },

                # ðŸ”¥ DURASI fallback
                "duration": int(rule.target_waktu or 0) if rule else 0,

                # ðŸ”¥ PENTING: sisi tidak di-merge
                "sisi": detail.sisi,

                # ðŸ”¥ FLAG
                "is_unilateral": lat.is_unilateral,

                # ðŸ”¥ tracking penting untuk history nanti
                "id_detail_jadwal": detail.id_detail,
                "urutan": detail.urutan
            }

            latihan_list.append(latihan_item)

        # ==============================
        # 6. SORT berdasarkan urutan
        # ==============================
        latihan_list = sorted(
            latihan_list,
            key=lambda x: x["urutan"] if x["urutan"] is not None else 0
        )

        # ==============================
        # 7. Append ke hasil
        # ==============================
        hasil.append({
            "program_id": prog.id_jadwal,
            "nama_program": prog.nama_jadwal,
            "fase": prog.fase or "F1",
            "fase_label": prog.fase_label,
            "tanggal_mulai": prog.tanggal.strftime("%Y-%m-%d"),
            "status": prog.status,
            "id_bagian": str(id_bagian) if id_bagian else "",
            "total_latihan": len(latihan_list),
            "latihan": latihan_list
        })

    need_final_eval, final_id_bagian, final_id_jadwal = check_need_final_assessment(user_id)

    return jsonify({
        "success": True,
        "code": "GET_JADWAL_SEMUA_SUCCESS",
        "need_final_assessment": need_final_eval,
        "final_assessment_id_bagian": final_id_bagian,
        "final_assessment_id_jadwal": final_id_jadwal,
        "data": hasil
    }), 200



@latihanuser_bp.route("/latihan", methods=["POST"])
def create_latihan():

    data = request.get_json()

    # =========================
    # Validasi
    # =========================
    required_fields = [
        "nama_latihan",
        "bagian_config"
    ]

    for field in required_fields:

        if field not in data:

            return jsonify({
                "message": f"{field} wajib diisi"
            }), 400

    bagian_config = data["bagian_config"]

    if not isinstance(bagian_config, list) or len(bagian_config) == 0:

        return jsonify({
            "message": "bagian_config harus berupa array dan tidak boleh kosong"
        }), 400

    # =========================
    # Shared field
    # =========================
    shared_fields = dict(
        level=data.get("level", 1),
        video_url=data.get("video_url"),
        url_gambar=data.get("url_gambar"),
        deskripsi=data.get("deskripsi"),
        is_unilateral=bool(data.get("is_unilateral", False)),
    )

    try:

        # =========================
        # Create latihan
        # =========================
        latihan = Latihan(
            id_latihan=generate_random_id(8),
            nama_latihan=data["nama_latihan"],
            **shared_fields
        )

        db.session.add(latihan)

        db.session.flush()

        # =========================
        # Insert bagian config
        # =========================
        for bagian in bagian_config:

            db.session.add(
                LatihanBagian(
                    id_latihan=latihan.id_latihan,

                    id_bagian=bagian["id_bagian"],

                    target_set=bagian.get(
                        "target_set",
                        3
                    ),

                    target_repetisi=bagian.get(
                        "target_repetisi"
                    ),

                    target_waktu=bagian.get(
                        "target_waktu"
                    ),

                    hold_detik=bagian.get(
                        "hold_detik",
                        5
                    ),

                    rest_repetisi_detik=bagian.get(
                        "rest_repetisi_detik",
                        10
                    ),

                    rest_set_detik=bagian.get(
                        "rest_set_detik",
                        30
                    ),

                    progression_repetisi=bagian.get(
                        "progression_repetisi",
                        2
                    ),

                    progression_hold=bagian.get(
                        "progression_hold",
                        5
                    ),
                )
            )

        db.session.commit()

        return jsonify({
            "message": "latihan berhasil dibuat",
            "id_latihan": latihan.id_latihan,
            "is_unilateral": latihan.is_unilateral
        }), 201

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "message": "gagal membuat latihan",
            "error": str(e)
        }), 500