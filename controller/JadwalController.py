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

@latihanuser_bp.route("/jadwal/hari-ini", methods=["GET"])
@jwt_required()
def get_jadwal_hari_ini():
    user_id = str(get_jwt_identity())

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
                        "set": rule_for_lat.target_set if rule_for_lat else None,
                        "repetisi": rule_for_lat.target_repetisi if rule_for_lat else None,
                        "waktu": rule_for_lat.target_waktu if rule_for_lat else None,
                        "hold_detik": int(rule_for_lat.hold_detik) if (rule_for_lat and rule_for_lat.hold_detik is not None) else 0
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
        decision = "warning"
        action_result = "maintain"
        can_start_exercise = False
        jadwal.status = "Need Screening"
        rekomendasi = "Nyeri meningkat dibanding sebelumnya. Silakan istirahat sampai besok."
    else:
        decision = "safe"
        action_result = "maintain"
        can_start_exercise = True
        jadwal.status = "Unlocked"
        rekomendasi = "Nyeri aman. Latihan dapat dilanjutkan."

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

# @latihanuser_bp.route("/generate-jadwal", methods=["POST"])
# @jwt_required()
# def generate_jadwal_otomatis():
#     user_id = str(get_jwt_identity())

#     # ======================================================
#     # 1ï¸âƒ£ Ambil kondisi terbaru user
#     # ======================================================
#     kondisi = (
#         KondisiUser.query
#         .filter_by(id_user=user_id)
#         .order_by(KondisiUser.created_at.desc())
#         .first()
#     )

#     if not kondisi:
#         return jsonify({
#             "success": False,
#             "message": "Isi form kondisi terlebih dahulu"
#         }), 404

#     # ======================================================
#     # 2ï¸âƒ£ Cek program aktif
#     # ======================================================
#     active_program = JadwalLatihanUser.query.filter(
#         JadwalLatihanUser.id_user == user_id,
#         JadwalLatihanUser.status.in_(["Unlocked", "Need Screening", "Locked"])
#     ).first()

#     if active_program:
#         return jsonify({
#             "success": False,
#             "message": "Selesaikan program sebelumnya terlebih dahulu"
#         }), 400

#     # ======================================================
#     # 3ï¸âƒ£ Ambil data kondisi
#     # ======================================================
#     vas = int(kondisi.tingkat_nyeri or 0)
#     lama_nyeri = int(kondisi.durasi_nyeri_minggu or 0)
#     id_bagian = kondisi.id_bagian

#     if not id_bagian:
#         return jsonify({
#             "success": False,
#             "message": "bagian tubuh tidak ditemukan"
#         }), 400

#     bagian = BagianTubuh.query.filter_by(id_bagian=id_bagian).first()
#     nama_bagian = bagian.nama_bagian if bagian else "Bagian Tidak Diketahui"

#     rule = RehabRuleBagian.query.filter_by(id_bagian=id_bagian).first()

#     if not rule:
#         return jsonify({
#             "success": False,
#             "message": "Rule untuk bagian tubuh belum dikonfigurasi"
#         }), 400

#     # ======================================================
#     # 4ï¸âƒ£ Decision Logic Fase (RULE DRIVEN)
#     # ======================================================
#     if lama_nyeri > (rule.max_durasi_minggu_home or 21):
#         return jsonify({
#             "success": True,
#             "mode": "rujuk",
#             "message": f"Disarankan kembali ke fisioterapis/dokter karena nyeri menetap > {rule.max_durasi_minggu_home} minggu"
#         }), 200

#     fase = "F2"
#     label = "Fase 2 (Sub-Akut)"

#     if rule.fase_rules:
#         for fr in rule.fase_rules:
#             # Pengecekan VAS
#             vas_min = fr.get("vas_min", 0)
#             vas_max = fr.get("vas_max", 10)

#             # Pengecekan durasi minimal (jika ada) khusus untuk kondisi kronis (opsional)
#             min_durasi = fr.get("min_durasi_minggu", 0)

#             if vas_min <= vas <= vas_max and lama_nyeri >= min_durasi:
#                 fase = fr.get("fase", fase)
#                 label = fr.get("label", label)
#                 break

#     # ======================================================
#     # 5ï¸âƒ£ Ambil latihan sesuai bagian & fase (via many-to-many)
#     # Latihan HARUS:
#     #   - sesuai fase
#     #   - terdaftar di LatihanBagian untuk id_bagian user
#     # ======================================================
#     latihans_pool = (
#         Latihan.query
#         .join(LatihanBagian, LatihanBagian.id_latihan == Latihan.id_latihan)
#         .filter(
#             Latihan.fase == fase,
#             LatihanBagian.id_bagian == id_bagian
#         )
#         .order_by(Latihan.level.asc())
#         .all()
#     )

#     # Batasi sesuai limit RehabRuleBagian dari database
#     latihans_pool = latihans_pool[:rule.max_latihan_per_hari] if rule.max_latihan_per_hari else latihans_pool

#     if not latihans_pool:
#         return jsonify({
#             "success": False,
#             "message": "Latihan untuk fase ini belum tersedia"
#         }), 404

#     # ======================================================
#     # 6ï¸âƒ£ Generate Jadwal
#     # ======================================================
#     try:
#         id_grup = generate_random_id(4)

#         url_gambar = None
#         if latihans_pool:
#             first_lat = latihans_pool[0]
#             # optional logic to get image if valid for the group
#             url_gambar = first_lat.url_gambar

#         jadwal_grup = JadwalLatihanUser(
#             id_jadwal=id_grup,
#             id_user=user_id,
#             id_form=kondisi.id_form,
#             url_gambar=url_gambar,
#             fase=fase,
#             fase_label=label,
#             nama_jadwal=f"Program {nama_bagian} - {label}",
#             tanggal=datetime.utcnow() + timedelta(days=1),
#             status="Pending",
#             created_at=datetime.utcnow()
#         )

#         db.session.add(jadwal_grup)

#         # ======================================================
#         # 7ï¸âƒ£ Insert Detail â€” setiap latihan sudah menjadi 1 record
#         #    (duplikasi kanan/kiri dilakukan saat CREATE LATIHAN)
#         # ======================================================
#         counter = 1

#         for lat in latihans_pool:
#             db.session.add(JadwalLatihanDetail(
#                 id_detail=generate_random_id(8),
#                 id_jadwal=id_grup,
#                 id_latihan=lat.id_latihan,
#                 sisi=None,
#                 urutan=counter
#             ))
#             counter += 1

#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "message": "Program berhasil dibuat",
#             "mode": "home_program",
#             "nama_program": jadwal_grup.nama_jadwal,
#             "fase": fase,
#             "total_latihan": len(latihans_pool),
#             "vas": vas,
#             "lama_nyeri": lama_nyeri
#         }), 201

#     except Exception as e:
#         db.session.rollback()

#         return jsonify({
#             "success": False,
#             "message": "Terjadi kesalahan saat generate program",
#             "error": str(e)
#         }), 500

# @latihanuser_bp.route("/generate-jadwal", methods=["POST"])
# @jwt_required()
# def generate_jadwal_otomatis():
#     user_id = str(get_jwt_identity())

#     # ======================================================
#     # 1ï¸âƒ£ Ambil kondisi terbaru user
#     # ======================================================
#     kondisi = (
#         KondisiUser.query
#         .filter_by(id_user=user_id)
#         .order_by(KondisiUser.created_at.desc())
#         .first()
#     )

#     if not kondisi:
#         return jsonify({
#             "success": False,
#             "message": "Isi form kondisi terlebih dahulu"
#         }), 404

#     # ======================================================
#     # 2ï¸âƒ£ Cek program aktif
#     # ======================================================
#     active_program = JadwalLatihanUser.query.filter(
#         JadwalLatihanUser.id_user == user_id,
#         JadwalLatihanUser.status.in_(["Unlocked", "Need Screening", "Locked"])
#     ).first()

#     if active_program:
#         return jsonify({
#             "success": False,
#             "message": "Selesaikan program sebelumnya terlebih dahulu"
#         }), 400

#     # ======================================================
#     # 3ï¸âƒ£ Ambil data kondisi
#     # ======================================================
#     vas = int(kondisi.tingkat_nyeri or 0)
#     lama_nyeri = int(kondisi.durasi_nyeri_minggu or 0)
#     # pastikan konsistensi tipe string
#     id_bagian = kondisi.id_bagian
#     if not id_bagian:
#         return jsonify({
#             "success": False,
#             "message": "Bagian tubuh tidak ditemukan"
#         }), 400
#     id_bagian = str(id_bagian)

#     bagian = BagianTubuh.query.filter_by(id_bagian=id_bagian).first()
#     nama_bagian = bagian.nama_bagian if bagian else "Bagian Tidak Diketahui"

#     # ======================================================
#     # 4ï¸âƒ£ RULE (ONLY SAFETY LIMIT, NO FASE)
#     # ======================================================
#     rule = RehabRuleBagian.query.filter_by(id_bagian=id_bagian).first()

#     if not rule:
#         return jsonify({
#             "success": False,
#             "message": "Rule untuk bagian tubuh belum dikonfigurasi"
#         }), 400

#     # RULE RUJUK (hard safety boundary)
#     if lama_nyeri > int(rule.max_durasi_minggu_home or 0):
#         return jsonify({
#             "success": True,
#             "mode": "rujuk",
#             "message": (
#                 f"Disarankan kembali ke fisioterapis/dokter "
#                 f"karena nyeri menetap > {rule.max_durasi_minggu_home} minggu"
#             )
#         }), 200

#     # ======================================================
#     # 5ï¸âƒ£ AMBIL LATIHAN (FULL LIST PER BAGIAN)
#     # ======================================================
#     latihans_pool = (
#         Latihan.query
#         .join(LatihanBagian, LatihanBagian.id_latihan == Latihan.id_latihan)
#         .filter(LatihanBagian.id_bagian == str(id_bagian))
#         .order_by(Latihan.level.asc())
#         .all()
#     )

#     print("ID BAGIAN:", id_bagian)
#     print("TOTAL LATIHAN:", len(latihans_pool))
#     print("LIST LATIHAN:", [l.id_latihan for l in latihans_pool])
#     print("RULE MAX:", rule.max_latihan_per_hari)

#     if not latihans_pool:
#         return jsonify({
#             "success": False,
#             "message": "Latihan untuk bagian ini belum tersedia"
#         }), 404

#     # limit sesuai rule (dilakukan SETELAH cek kosong)
#     max_latihan = int(rule.max_latihan_per_hari or 5)
#     if max_latihan <= 0:
#         max_latihan = 5

#     # Split menjadi beberapa minggu
#     chunks = [latihans_pool[i:i + max_latihan] for i in range(0, len(latihans_pool), max_latihan)]
#     print("TOTAL SETELAH CHUNKING, JUMLAH MINGGU:", len(chunks))

#     # ======================================================
#     # 6ï¸âƒ£ CREATE JADWAL HEADER
#     # ======================================================
#     try:
#         minggu = 1
#         total_sesi = 0
#         for chunk in chunks:
#             # 3 Sesi dalam 1 minggu
#             for sesi in range(1, 4):
#                 total_sesi += 1
#                 id_grup = generate_random_id(4)

#                 # Penjadwalan: jarak 2 hari antar sesi dalam minggu yg sama
#                 # M1 S1: hari + 1
#                 # M1 S2: hari + 3
#                 # M1 S3: hari + 5
#                 # M2 S1: hari + 8
#                 days_offset = 1 + (minggu - 1) * 7 + (sesi - 1) * 2
#                 jadwal_tanggal = datetime.utcnow() + timedelta(days=days_offset)

#                 status = "Unlocked" if minggu == 1 and sesi == 1 else "Locked"

#                 jadwal_grup = JadwalLatihanUser(
#                     id_jadwal=id_grup,
#                     id_user=user_id,
#                     id_form=kondisi.id_form,
#                     fase=f"M{minggu}",  # Max 4 chars in DB
#                     fase_label=f"Minggu {minggu} - Sesi {sesi}",
#                     url_gambar=chunk[0].url_gambar if chunk else None,
#                     nama_jadwal=f"Program {nama_bagian} - M{minggu} Sesi {sesi}",
#                     tanggal=jadwal_tanggal,
#                     status=status,
#                     created_at=datetime.utcnow()
#                 )

#                 db.session.add(jadwal_grup)

#                 # ======================================================
#                 # 7ï¸âƒ£ DETAIL JADWAL
#                 # ======================================================
#                 counter = 1
#                 for lat in chunk:
#                     db.session.add(JadwalLatihanDetail(
#                         id_detail=generate_random_id(8),
#                         id_jadwal=id_grup,
#                         id_latihan=lat.id_latihan,
#                         urutan=counter
#                     ))
#                     counter += 1

#                 notif_res, notif_status = NotificationService.create_notification({
#                     "id_user": user_id,
#                     "judul": "Waktunya Latihan ðŸ’ª",
#                     "pesan": f"Jangan lupa {jadwal_grup.nama_jadwal}",
#                     "tipe": "reminder",
#                     "jadwal_kirim": jadwal_grup.tanggal,
#                     "id_jadwal": jadwal_grup.id_jadwal
#                 })

#                 if notif_status != 201:
#                     raise Exception(f"Gagal membuat notifikasi: {notif_res.get('error')}")

#             minggu += 1

#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "message": "Program berhasil dibuat",
#             "mode": "home_program",
#             "total_minggu": len(chunks),
#             "total_sesi": total_sesi,
#             "vas": vas,
#             "lama_nyeri": lama_nyeri
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "message": "Terjadi kesalahan saat generate program",
#             "error": str(e)
#         }), 500

# @latihanuser_bp.route("/generate-jadwal", methods=["POST"])
# @jwt_required()
# def generate_jadwal_otomatis():
#     user_id = str(get_jwt_identity())

#     # ======================================================
#     # 1ï¸âƒ£ Ambil kondisi terbaru user
#     # ======================================================
#     kondisi = (
#         KondisiUser.query
#         .filter_by(id_user=user_id)
#         .order_by(KondisiUser.created_at.desc())
#         .first()
#     )

#     if not kondisi:
#         return jsonify({
#             "success": False,
#             "message": "Isi form kondisi terlebih dahulu"
#         }), 404

#     # ======================================================
#     # 2ï¸âƒ£ Cek program aktif
#     # ======================================================
#     active_program = JadwalLatihanUser.query.filter(
#         JadwalLatihanUser.id_user == user_id,
#         JadwalLatihanUser.status.in_(["Unlocked", "Need Screening", "Locked"])
#     ).first()

#     if active_program:
#         return jsonify({
#             "success": False,
#             "message": "Selesaikan program sebelumnya terlebih dahulu"
#         }), 400

#     # ======================================================
#     # 3ï¸âƒ£ Ambil data kondisi
#     # ======================================================
#     vas = int(kondisi.tingkat_nyeri or 0)
#     lama_nyeri = int(kondisi.durasi_nyeri_minggu or 0)

#     id_bagian = kondisi.id_bagian
#     if not id_bagian:
#         return jsonify({
#             "success": False,
#             "message": "Bagian tubuh tidak ditemukan"
#         }), 400

#     id_bagian = str(id_bagian)

#     bagian = BagianTubuh.query.filter_by(id_bagian=id_bagian).first()
#     nama_bagian = bagian.nama_bagian if bagian else "Bagian Tidak Diketahui"

#     # ======================================================
#     # 4ï¸âƒ£ RULE
#     # ======================================================
#     rule = RehabRuleBagian.query.filter_by(id_bagian=id_bagian).first()

#     if not rule:
#         return jsonify({
#             "success": False,
#             "message": "Rule untuk bagian tubuh belum dikonfigurasi"
#         }), 400

#     # RULE RUJUK (safety boundary)
#     if lama_nyeri > int(rule.max_durasi_minggu_home or 0):
#         return jsonify({
#             "success": True,
#             "mode": "rujuk",
#             "message": (
#                 f"Disarankan kembali ke fisioterapis/dokter "
#                 f"karena nyeri menetap > {rule.max_durasi_minggu_home} minggu"
#             )
#         }), 200

#     # ======================================================
#     # 5ï¸âƒ£ AMBIL LATIHAN FULL (TIDAK DI CHUNK)
#     # ======================================================
#     latihans_pool = (
#         Latihan.query
#         .join(LatihanBagian, LatihanBagian.id_latihan == Latihan.id_latihan)
#         .filter(LatihanBagian.id_bagian == id_bagian)
#         .order_by(Latihan.level.asc())
#         .all()
#     )

#     if not latihans_pool:
#         return jsonify({
#             "success": False,
#             "message": "Latihan untuk bagian ini belum tersedia"
#         }), 404

#     print("TOTAL LATIHAN:", len(latihans_pool))

#     # ======================================================
#     # 6ï¸âƒ£ CONFIG SCHEDULE
#     # ======================================================
#     sessions_per_week = 3

#     lat_index = 0
#     total_latihan = len(latihans_pool)

#     minggu = 1
#     total_sesi = 0

#     try:
#         # ======================================================
#         # 7ï¸âƒ£ GENERATE JADWAL (CORE FIX)
#         # ======================================================
#         while lat_index < total_latihan:

#             for sesi in range(1, sessions_per_week + 1):

#                 if lat_index >= total_latihan:
#                     break

#                 total_sesi += 1
#                 id_grup = generate_random_id(4)

#                 # 3 sesi per minggu (jarak 2 hari)
#                 days_offset = 1 + (minggu - 1) * 7 + (sesi - 1) * 2
#                 jadwal_tanggal = datetime.utcnow() + timedelta(days=days_offset)

#                 status = "Unlocked" if minggu == 1 and sesi == 1 else "Locked"

#                 jadwal_grup = JadwalLatihanUser(
#                     id_jadwal=id_grup,
#                     id_user=user_id,
#                     id_form=kondisi.id_form,
#                     fase=f"M{minggu}",
#                     fase_label=f"Minggu {minggu} - Sesi {sesi}",
#                     url_gambar=latihans_pool[lat_index].url_gambar if lat_index < total_latihan else None,
#                     nama_jadwal=f"Program {nama_bagian} - M{minggu} Sesi {sesi}",
#                     tanggal=jadwal_tanggal,
#                     status=status,
#                     created_at=datetime.utcnow()
#                 )

#                 db.session.add(jadwal_grup)

#                 # ======================================================
#                 # 8ï¸âƒ£ DETAIL JADWAL (1 latihan per sesi, sequential)
#                 # ======================================================
#                 if lat_index < total_latihan:
#                     lat = latihans_pool[lat_index]

#                     db.session.add(JadwalLatihanDetail(
#                         id_detail=generate_random_id(8),
#                         id_jadwal=id_grup,
#                         id_latihan=lat.id_latihan,
#                         urutan=1
#                     ))

#                     lat_index += 1

#                 # ======================================================
#                 # 9ï¸âƒ£ NOTIFIKASI
#                 # ======================================================
#                 notif_res, notif_status = NotificationService.create_notification({
#                     "id_user": user_id,
#                     "judul": "Waktunya Latihan ðŸ’ª",
#                     "pesan": f"Jangan lupa {jadwal_grup.nama_jadwal}",
#                     "tipe": "reminder",
#                     "jadwal_kirim": jadwal_grup.tanggal,
#                     "id_jadwal": jadwal_grup.id_jadwal
#                 })

#                 if notif_status != 201:
#                     raise Exception(f"Gagal membuat notifikasi: {notif_res.get('error')}")

#             minggu += 1

#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "message": "Program berhasil dibuat",
#             "mode": "home_program",
#             "total_minggu": minggu - 1,
#             "total_sesi": total_sesi,
#             "vas": vas,
#             "lama_nyeri": lama_nyeri
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "message": "Terjadi kesalahan saat generate program",
#             "error": str(e)
#         }), 500

# @latihanuser_bp.route("/generate-jadwal", methods=["POST"])
# @jwt_required()
# def generate_jadwal_otomatis():
#     user_id = str(get_jwt_identity())

#     # ======================================================
#     # 1ï¸âƒ£ Ambil kondisi terbaru user
#     # ======================================================
#     kondisi = (
#         KondisiUser.query
#         .filter_by(id_user=user_id)
#         .order_by(KondisiUser.created_at.desc())
#         .first()
#     )

#     if not kondisi:
#         return jsonify({
#             "success": False,
#             "message": "Isi form kondisi terlebih dahulu"
#         }), 404

#     # ======================================================
#     # 2ï¸âƒ£ Cek program aktif
#     # ======================================================
#     active_program = JadwalLatihanUser.query.filter(
#         JadwalLatihanUser.id_user == user_id,
#         JadwalLatihanUser.status.in_(["Unlocked", "Need Screening", "Locked"])
#     ).first()

#     if active_program:
#         return jsonify({
#             "success": False,
#             "message": "Selesaikan program sebelumnya terlebih dahulu"
#         }), 400

#     # ======================================================
#     # 3ï¸âƒ£ DATA KONDISI
#     # ======================================================
#     vas = int(kondisi.tingkat_nyeri or 0)
#     lama_nyeri = int(kondisi.durasi_nyeri_minggu or 0)

#     id_bagian = str(kondisi.id_bagian) if kondisi.id_bagian else None

#     if not id_bagian:
#         return jsonify({
#             "success": False,
#             "message": "Bagian tubuh tidak ditemukan"
#         }), 400

#     bagian = BagianTubuh.query.filter_by(id_bagian=id_bagian).first()
#     nama_bagian = bagian.nama_bagian if bagian else "Bagian Tidak Diketahui"

#     # ======================================================
#     # 4ï¸âƒ£ RULE
#     # ======================================================
#     rule = RehabRuleBagian.query.filter_by(id_bagian=id_bagian).first()

#     if not rule:
#         return jsonify({
#             "success": False,
#             "message": "Rule untuk bagian tubuh belum dikonfigurasi"
#         }), 400

#     max_minggu = int(rule.max_durasi_minggu_home or 0)

#     # RULE RUJUK (safety boundary)
#     if lama_nyeri > max_minggu:
#         return jsonify({
#             "success": True,
#             "mode": "rujuk",
#             "message": (
#                 f"Disarankan kembali ke fisioterapis/dokter "
#                 f"karena nyeri menetap > {max_minggu} minggu"
#             )
#         }), 200

#     # ======================================================
#     # 5ï¸âƒ£ AMBIL LATIHAN
#     # ======================================================
#     latihans_pool = (
#         Latihan.query
#         .join(LatihanBagian, LatihanBagian.id_latihan == Latihan.id_latihan)
#         .filter(LatihanBagian.id_bagian == id_bagian)
#         .order_by(Latihan.level.asc())
#         .all()
#     )

#     if not latihans_pool:
#         return jsonify({
#             "success": False,
#             "message": "Latihan untuk bagian ini belum tersedia"
#         }), 404

#     print("TOTAL LATIHAN:", len(latihans_pool))
#     print("MAX MINGGU:", max_minggu)

#     # ======================================================
#     # 6ï¸âƒ£ CONFIG
#     # ======================================================
#     sessions_per_week = 3

#     lat_index = 0
#     total_latihan = len(latihans_pool)

#     minggu = 1
#     sesi = 1
#     total_sesi = 0

#     try:

#         # ======================================================
#         # 7ï¸âƒ£ GENERATE (FIXED + CONTROLLED MINGGU)
#         # ======================================================
#         while lat_index < total_latihan and minggu <= max_minggu:

#             id_grup = generate_random_id(4)

#             # ======================================================
#             # 8ï¸âƒ£ HITUNG TANGGAL STABIL
#             # ======================================================
#             days_offset = (minggu - 1) * 7 + (sesi - 1) * 2
#             jadwal_tanggal = datetime.utcnow() + timedelta(days=days_offset)

#             status = "Unlocked" if minggu == 1 and sesi == 1 else "Locked"

#             jadwal_grup = JadwalLatihanUser(
#                 id_jadwal=id_grup,
#                 id_user=user_id,
#                 id_form=kondisi.id_form,
#                 fase=f"M{minggu}",
#                 fase_label=f"Minggu {minggu} - Sesi {sesi}",
#                 url_gambar=latihans_pool[lat_index].url_gambar if lat_index < total_latihan else None,
#                 nama_jadwal=f"Program {nama_bagian} - M{minggu} Sesi {sesi}",
#                 tanggal=jadwal_tanggal,
#                 status=status,
#                 created_at=datetime.utcnow()
#             )

#             db.session.add(jadwal_grup)

#             # ======================================================
#             # 9ï¸âƒ£ DETAIL (1 latihan per sesi)
#             # ======================================================
#             lat = latihans_pool[lat_index]

#             db.session.add(JadwalLatihanDetail(
#                 id_detail=generate_random_id(8),
#                 id_jadwal=id_grup,
#                 id_latihan=lat.id_latihan,
#                 urutan=1
#             ))

#             lat_index += 1
#             total_sesi += 1

#             # ======================================================
#             # ðŸ”Ÿ NOTIFIKASI
#             # ======================================================
#             notif_res, notif_status = NotificationService.create_notification({
#                 "id_user": user_id,
#                 "judul": "Waktunya Latihan ðŸ’ª",
#                 "pesan": f"Jangan lupa {jadwal_grup.nama_jadwal}",
#                 "tipe": "reminder",
#                 "jadwal_kirim": jadwal_grup.tanggal,
#                 "id_jadwal": jadwal_grup.id_jadwal
#             })

#             if notif_status != 201:
#                 raise Exception(f"Gagal membuat notifikasi: {notif_res.get('error')}")

#             # ======================================================
#             # ðŸ” CONTROL SESI & MINGGU
#             # ======================================================
#             sesi += 1

#             if sesi > sessions_per_week:
#                 sesi = 1
#                 minggu += 1

#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "message": "Program berhasil dibuat",
#             "mode": "home_program",
#             "total_minggu": min(minggu, max_minggu),
#             "total_sesi": total_sesi,
#             "vas": vas,
#             "lama_nyeri": lama_nyeri
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "message": "Terjadi kesalahan saat generate program",
#             "error": str(e)
#         }), 500

# @latihanuser_bp.route("/jadwal/meta", methods=["GET"])
# @jwt_required()
# def get_jadwal_meta():
#     user_id = str(get_jwt_identity())

#     count_jadwal = JadwalLatihanUser.query.filter_by(id_user=user_id).count()

#     has_kondisi = KondisiUser.query.filter_by(id_user=user_id).count() > 0

#     if not has_kondisi:
#          return jsonify({
#             "success": False,
#             "code": "KONDISI_NOT_FOUND",
#             "data": None
#         }), 404

#     if count_jadwal == 0:
#         return jsonify({
#             "success": True,
#             "code": "JADWAL_EMPTY",
#              "data": {
#                 "available_weeks": [],
#                 "total_jadwal": 0
#             }
#         }), 200

#     return jsonify({
#         "success": True,
#         "code": "JADWAL_META_OK",
#         "data": {
#             "available_weeks": [1, 2, 3],
#             "total_jadwal": int(count_jadwal)
#         }
#     }), 200


# @latihanuser_bp.route("/jadwal/fase", methods=["GET"])
# @jwt_required()
# def get_jadwal_per_fase():
#     user_id = str(get_jwt_identity())

#     # ======================================================
#     # 1ï¸âƒ£ Ambil program aktif
#     # ======================================================
#     active_program = (
#         JadwalLatihanUser.query
#         .filter(
#             JadwalLatihanUser.id_user == user_id,
#             JadwalLatihanUser.status.in_(["Unlocked", "Need Screening", "Locked"])
#         )
#         .order_by(JadwalLatihanUser.created_at.desc())
#         .options(
#             db.joinedload(JadwalLatihanUser.details)
#               .joinedload(JadwalLatihanDetail.latihan)
#         )
#         .first()
#     )

#     if not active_program:
#         return jsonify({
#             "success": False,
#             "code": "ACTIVE_PROGRAM_NOT_FOUND",
#             "data": None
#         }), 404

#     # ======================================================
#     # 2ï¸âƒ£ Group berdasarkan id_latihan
#     # ======================================================
#     latihan_map = {}

#     for detail in active_program.details:
#         lat = detail.latihan
#         if not lat:
#             continue

#         if lat.id_latihan not in latihan_map:
#             latihan_map[lat.id_latihan] = {
#                 "id_latihan": lat.id_latihan,
#                 "nama_latihan": lat.nama_latihan,
#                 "deskripsi": lat.deskripsi,
#                 "image_url": lat.url_gambar,
#                 "level": int(lat.level) if lat.level else 1,
#                 "duration": int(lat.target_waktu or 0),
#                 "target": {
#                     "set": lat.target_set,
#                     "repetisi": lat.target_repetisi,
#                     "waktu": lat.target_waktu
#                 },
#                 "video_url": lat.video_url,
#                 "is_unilateral": lat.is_unilateral,
#                 "sisi": []
#             }

#         # Tambahkan sisi jika ada
#         if detail.sisi:
#             latihan_map[lat.id_latihan]["sisi"].append(detail.sisi)

#     # ======================================================
#     # 3ï¸âƒ£ Final list
#     # ======================================================
#     result = list(latihan_map.values())

#     return jsonify({
#         "success": True,
#         "code": "GET_JADWAL_PER_FASE_SUCCESS",
#         "data": {
#             "program_id": active_program.id_jadwal,
#             "nama_program": active_program.nama_jadwal,
#             "fase": active_program.fase,
#             "tanggal_mulai": active_program.tanggal.strftime("%Y-%m-%d"),
#             "total_latihan": len(result),
#             "latihan": result
#         }
#     }), 200

# @latihanuser_bp.route("/jadwal/semua", methods=["GET"])
# @jwt_required()
# def get_jadwal_semua():
#     user_id = str(get_jwt_identity())

#     # ======================================================
#     # 1ï¸âƒ£ Ambil semua program milik user
#     # ======================================================
#     semua_program = (
#         JadwalLatihanUser.query
#         .filter(JadwalLatihanUser.id_user == user_id)
#         .order_by(JadwalLatihanUser.created_at.desc())
#         .options(
#             db.joinedload(JadwalLatihanUser.details)
#               .joinedload(JadwalLatihanDetail.latihan)
#         )
#         .all()
#     )

#     if not semua_program:
#         return jsonify({
#             "success": True,
#             "code": "PROGRAM_EMPTY",
#             "data": []
#         }), 200

#     # ======================================================
#     # 2ï¸âƒ£ Format response per program
#     # ======================================================
#     hasil = []

#     for prog in semua_program:
#         latihan_map = {}

#         for detail in prog.details:
#             lat = detail.latihan
#             if not lat:
#                 continue

#             if lat.id_latihan not in latihan_map:
#                 latihan_map[lat.id_latihan] = {
#                     "id_latihan": lat.id_latihan,
#                     "nama_latihan": lat.nama_latihan,
#                     "deskripsi": lat.deskripsi,
#                     "image_url": lat.url_gambar,
#                     "level": int(lat.level) if lat.level else 1,
#                     "duration": int(lat.target_waktu or 0),
#                     "target": {
#                         "set": lat.target_set,
#                         "repetisi": lat.target_repetisi,
#                         "waktu": lat.target_waktu
#                     },
#                     "video_url": lat.video_url,
#                     "is_unilateral": lat.is_unilateral,
#                     "sisi": []
#                 }

#             # Tambahkan sisi jika ada
#             if detail.sisi:
#                 latihan_map[lat.id_latihan]["sisi"].append(detail.sisi)

#         # Convert sisi array to string to match Dart's expected String format
#         for lat_id in latihan_map:
#             if latihan_map[lat_id]["sisi"]:
#                 latihan_map[lat_id]["sisi"] = ", ".join(latihan_map[lat_id]["sisi"])
#             else:
#                 latihan_map[lat_id]["sisi"] = None

#         result_latihan = list(latihan_map.values())

#         hasil.append({
#             "program_id": prog.id_jadwal,
#             "nama_program": prog.nama_jadwal,
#             "fase": prog.fase or "F1",
#             "tanggal_mulai": prog.tanggal.strftime("%Y-%m-%d"),
#             "total_latihan": len(result_latihan),
#             "latihan": result_latihan
#         })

#     return jsonify({
#         "success": True,
#         "code": "GET_JADWAL_SEMUA_SUCCESS",
#         "data": hasil
#     }), 200

#diperbarui

# @latihanuser_bp.route("/generate-jadwal", methods=["POST"])
# @jwt_required()
# def generate_jadwal_otomatis():
#     user_id = str(get_jwt_identity())

#     kondisi = (
#         KondisiUser.query
#         .filter_by(id_user=user_id)
#         .order_by(KondisiUser.created_at.desc())
#         .first()
#     )

#     if not kondisi:
#         return jsonify({"success": False, "message": "Isi form kondisi terlebih dahulu"}), 404

#     active_program = JadwalLatihanUser.query.filter(
#         JadwalLatihanUser.id_user == user_id,
#         JadwalLatihanUser.status.in_(["Unlocked", "Need Screening", "Locked"])
#     ).first()

#     if active_program:
#         return jsonify({
#             "success": False,
#             "message": "Selesaikan program sebelumnya terlebih dahulu"
#         }), 400

#     vas = int(kondisi.tingkat_nyeri or 0)
#     lama_nyeri = int(kondisi.durasi_nyeri_minggu or 0)
#     id_bagian = str(kondisi.id_bagian)

#     bagian = BagianTubuh.query.filter_by(id_bagian=id_bagian).first()
#     nama_bagian = bagian.nama_bagian if bagian else "Unknown"

#     rule_global = RehabRuleBagian.query.filter_by(id_bagian=id_bagian).first()

#     if not rule_global:
#         return jsonify({"success": False, "message": "Rule belum ada"}), 400

#     max_minggu = int(rule_global.max_durasi_minggu_home or 0)

#     if lama_nyeri > max_minggu:
#         return jsonify({
#             "success": True,
#             "mode": "rujuk",
#             "message": f"Nyeri > {max_minggu} minggu"
#         }), 200

#     # ðŸ”¥ JOIN KE RULE (INI KUNCI)
#     latihans_pool = (
#         db.session.query(Latihan, LatihanRuleBagian)
#         .join(LatihanRuleBagian, Latihan.id_latihan == LatihanRuleBagian.id_latihan)
#         .filter(LatihanRuleBagian.id_bagian == id_bagian)
#         .order_by(Latihan.level.asc())
#         .all()
#     )

#     if not latihans_pool:
#         return jsonify({
#             "success": False,
#             "message": "Latihan belum tersedia"
#         }), 404

#     sessions_per_week = 3
#     lat_index = 0
#     total_latihan = len(latihans_pool)

#     minggu = 1
#     sesi = 1
#     total_sesi = 0

#     try:
#         while lat_index < total_latihan and minggu <= max_minggu:

#             id_grup = generate_random_id(4)

#             days_offset = (minggu - 1) * 7 + (sesi - 1) * 2
#             jadwal_tanggal = datetime.utcnow() + timedelta(days=days_offset)

#             status = "Unlocked" if minggu == 1 and sesi == 1 else "Locked"

#             # ðŸ”¥ sekarang tuple
#             lat, rule = latihans_pool[lat_index]

#             jadwal_grup = JadwalLatihanUser(
#                 id_jadwal=id_grup,
#                 id_user=user_id,
#                 id_form=kondisi.id_form,
#                 fase=f"M{minggu}",
#                 fase_label=f"Minggu {minggu} - Sesi {sesi}",
#                 url_gambar=lat.url_gambar,
#                 nama_jadwal=f"Program {nama_bagian} - M{minggu} Sesi {sesi}",
#                 tanggal=jadwal_tanggal,
#                 status=status,
#                 created_at=datetime.utcnow()
#             )

#             db.session.add(jadwal_grup)

#             db.session.add(JadwalLatihanDetail(
#                 id_detail=generate_random_id(8),
#                 id_jadwal=id_grup,
#                 id_latihan=lat.id_latihan,
#                 urutan=1
#             ))

#             lat_index += 1
#             total_sesi += 1

#             NotificationService.create_notification({
#                 "id_user": user_id,
#                 "judul": "Waktunya Latihan ðŸ’ª",
#                 "pesan": f"Jangan lupa {jadwal_grup.nama_jadwal}",
#                 "tipe": "reminder",
#                 "jadwal_kirim": jadwal_grup.tanggal,
#                 "id_jadwal": jadwal_grup.id_jadwal
#             })

#             sesi += 1
#             if sesi > sessions_per_week:
#                 sesi = 1
#                 minggu += 1

#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "message": "Program berhasil dibuat",
#             "mode": "home_program",
#             "total_minggu": min(minggu, max_minggu),
#             "total_sesi": total_sesi,
#             "vas": vas,
#             "lama_nyeri": lama_nyeri
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "message": "Terjadi kesalahan",
#             "error": str(e)
#         }), 500



@latihanuser_bp.route("/generate-jadwal", methods=["POST"])
@jwt_required()
def generate_jadwal_otomatis():
    user_id = str(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    requested_id_form = data.get("id_form")
    requested_id_form = (
        str(requested_id_form).strip()
        if requested_id_form is not None else
        None
    )
    requested_id_form = requested_id_form or None

    # ======================================================
    # 1ï¸âƒ£ KONDISI USER
    # ======================================================
    if requested_id_form:
        kondisi = (
            KondisiUser.query
            .filter(
                KondisiUser.id_user == user_id,
                KondisiUser.id_form == requested_id_form
            )
            .order_by(
                KondisiUser.created_at.desc(),
                KondisiUser.id_form.desc()
            )
            .first()
        )
    else:
        kondisi = (
            KondisiUser.query
            .filter_by(id_user=user_id)
            .order_by(
                KondisiUser.created_at.desc(),
                KondisiUser.id_form.desc()
            )
            .first()
        )

    if not kondisi:
        message = (
            "Kondisi user tidak ditemukan"
            if requested_id_form else
            "Isi form kondisi terlebih dahulu"
        )
        return jsonify({"success": False, "message": message}), 404

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

    # ======================================================
    # 3ï¸âƒ£ DATA DASAR
    # ======================================================
    vas = int(kondisi.tingkat_nyeri or 0)
    lama_nyeri = int(kondisi.durasi_nyeri_minggu or 0)
    id_bagian = str(kondisi.id_bagian)

    bagian = BagianTubuh.query.get(id_bagian)
    nama_bagian = bagian.nama_bagian if bagian else "Unknown"

    # ======================================================
    # 4ï¸âƒ£ RULE GLOBAL
    # ======================================================
    rule_global = (
        RehabRuleBagian.query
        .filter_by(id_bagian=id_bagian)
        .order_by(RehabRuleBagian.id.asc())
        .first()
    )

    if not rule_global:
        return jsonify({"success": False, "message": "Rule belum ada"}), 400

    max_minggu = int(rule_global.max_durasi_minggu_home or 1)

    if lama_nyeri > max_minggu:
        return jsonify({
            "success": True,
            "mode": "rujuk",
            "message": f"Nyeri > {max_minggu} minggu"
        }), 200

    # ======================================================
    # 5ï¸âƒ£ AMBIL SEMUA LATIHAN + RULE
    # ======================================================
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

    # ======================================================
    # ðŸ”¥ 6ï¸âƒ£ SESSION CONFIG (FIXED PER MINGGU)
    # ======================================================
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
                NotificationService.create_notification_and_push({
                    "id_user": user_id,
                    "judul": "Waktunya Latihan ðŸ’ª",
                    "pesan": f"Jangan lupa {jadwal_grup.nama_jadwal}",
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
            latihan_map[lat.id_latihan] = {
                "id_latihan": lat.id_latihan,
                "nama_latihan": lat.nama_latihan,
                "deskripsi": lat.deskripsi,
                "image_url": lat.url_gambar,
                "level": int(lat.level) if lat.level else 1,
                "duration": int(rule.target_waktu or 0) if rule else 0,
                "target": {
                    "set": rule.target_set if rule else None,
                    "repetisi": rule.target_repetisi if rule else None,
                    "waktu": rule.target_waktu if rule else None,
                    "hold_detik": int(rule.hold_detik) if (rule and rule.hold_detik is not None) else 0
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


# @latihanuser_bp.route("/jadwal/semua", methods=["GET"])
# @jwt_required()
# def get_jadwal_semua():
#     user_id = str(get_jwt_identity())

#     kondisi = (
#         KondisiUser.query
#         .filter_by(id_user=user_id)
#         .order_by(KondisiUser.created_at.desc())
#         .first()
#     )

#     id_bagian = kondisi.id_bagian if kondisi else None

#     semua_program = (
#         JadwalLatihanUser.query
#         .filter(JadwalLatihanUser.id_user == user_id)
#         .order_by(JadwalLatihanUser.created_at.desc())
#         .options(
#             db.joinedload(JadwalLatihanUser.details)
#               .joinedload(JadwalLatihanDetail.latihan)
#         )
#         .all()
#     )

#     hasil = []

#     for prog in semua_program:
#         latihan_map = {}

#         for detail in prog.details:
#             lat = detail.latihan
#             if not lat:
#                 continue

#             rule = LatihanRuleBagian.query.filter_by(
#                 id_latihan=lat.id_latihan,
#                 id_bagian=id_bagian
#             ).first()

#             if lat.id_latihan not in latihan_map:
#                 latihan_map[lat.id_latihan] = {
#                     "id_latihan": lat.id_latihan,
#                     "nama_latihan": lat.nama_latihan,
#                     "deskripsi": lat.deskripsi,
#                     "image_url": lat.url_gambar,
#                     "level": int(lat.level) if lat.level else 1,
#                     "duration": int(rule.target_waktu or 0) if rule else 0,
#                     "target": {
#                         "set": rule.target_set if rule else None,
#                         "repetisi": rule.target_repetisi if rule else None,
#                         "waktu": rule.target_waktu if rule else None
#                     },
#                     "video_url": lat.video_url,
#                     "is_unilateral": lat.is_unilateral,
#                     "sisi": []
#                 }

#             if detail.sisi:
#                 latihan_map[lat.id_latihan]["sisi"].append(detail.sisi)

#         for lat_id in latihan_map:
#             if latihan_map[lat_id]["sisi"]:
#                 latihan_map[lat_id]["sisi"] = ", ".join(latihan_map[lat_id]["sisi"])
#             else:
#                 latihan_map[lat_id]["sisi"] = None

#         hasil.append({
#             "program_id": prog.id_jadwal,
#             "nama_program": prog.nama_jadwal,
#             "fase": prog.fase or "F1",
#             "tanggal_mulai": prog.tanggal.strftime("%Y-%m-%d"),
#             "total_latihan": len(latihan_map),
#             "latihan": list(latihan_map.values())
#         })

#     return jsonify({
#         "success": True,
#         "code": "GET_JADWAL_SEMUA_SUCCESS",
#         "data": hasil
#     }), 200

@latihanuser_bp.route("/jadwal/semua", methods=["GET"])
@jwt_required()
def get_jadwal_semua():
    user_id = str(get_jwt_identity())

    # ==============================
    # 1. Ambil program aktif terbaru
    # ==============================
    active_anchor = get_latest_active_program_anchor(user_id)
    if not active_anchor:
        payload = need_select_area_payload()
        payload["code"] = "ACTIVE_PROGRAM_NOT_FOUND"
        return jsonify(payload), 200

    kondisi = KondisiUser.query.get(active_anchor.id_form)

    id_bagian = kondisi.id_bagian if kondisi else None

    # ==============================
    # 2. Ambil jadwal dari program aktif terbaru saja
    # ==============================
    semua_program = (
        JadwalLatihanUser.query
        .filter(
            JadwalLatihanUser.id_user == user_id,
            JadwalLatihanUser.id_form == active_anchor.id_form,
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
            "total_latihan": len(latihan_list),
            "latihan": latihan_list
        })

    return jsonify({
        "success": True,
        "code": "GET_JADWAL_SEMUA_SUCCESS",
        "data": hasil
    }), 200

# @latihanuser_bp.route("/latihan", methods=["POST"])
# def create_latihan():
#     data = request.get_json()

#     # =========================
#     # Validasi Fields
#     # =========================
#     required_fields = ["nama_latihan", "id_bagian"]
#     for field in required_fields:
#         if field not in data:
#             return jsonify({"message": f"{field} wajib diisi"}), 400

#     id_bagian_list = data["id_bagian"]
#     if not isinstance(id_bagian_list, list) or len(id_bagian_list) == 0:
#         return jsonify({"message": "id_bagian harus berupa array dan tidak boleh kosong"}), 400

#     # Baca flag is_unilateral dari request (default False)
#     is_unilateral = bool(data.get("is_unilateral", False))
#     nama_latihan_input = data["nama_latihan"]

#     # Shared fields antar record
#     shared_fields = dict(
#         level=data.get("level", 1),
#         video_url=data.get("video_url"),
#         url_gambar=data.get("url_gambar"),
#         target_set=data.get("target_set", 3),
#         target_repetisi=data.get("target_repetisi"),
#         target_waktu=data.get("target_waktu"),
#         deskripsi=data.get("deskripsi"),
#         is_unilateral=is_unilateral,
#     )

#     try:
#         if not is_unilateral:
#             # ======================================================
#             # CASE 1 â€” Bilateral: buat 1 record, nama tetap
#             # ======================================================
#             latihan = Latihan(
#                 id_latihan=generate_random_id(8),
#                 nama_latihan=nama_latihan_input,
#                 **shared_fields
#             )
#             db.session.add(latihan)
#             db.session.flush()

#             for bagian in id_bagian_list:
#                 relasi = LatihanBagian(
#                     id_latihan=latihan.id_latihan,
#                     id_bagian=bagian
#                 )
#                 db.session.add(relasi)

#             db.session.commit()

#             return jsonify({
#                 "message": "latihan berhasil dibuat",
#                 "jumlah_dibuat": 1,
#                 "target": {
#                     "set": latihan.target_set,
#                     "repetisi": latihan.target_repetisi,
#                     "waktu": latihan.target_waktu,
#                     "mode": "bilateral"
#                 }
#             }), 201

#         else:
#             # ======================================================
#             # CASE 2 â€” Unilateral: buat 2 record (Kanan & Kiri)
#             # ======================================================
#             latihan_kanan = Latihan(
#                 id_latihan=generate_random_id(8),
#                 nama_latihan=f"{nama_latihan_input} - Kanan",
#                 **shared_fields
#             )
#             latihan_kiri = Latihan(
#                 id_latihan=generate_random_id(8),
#                 nama_latihan=f"{nama_latihan_input} - Kiri",
#                 **shared_fields
#             )

#             db.session.add(latihan_kanan)
#             db.session.add(latihan_kiri)
#             db.session.flush()

#             for id_latihan in [latihan_kanan.id_latihan, latihan_kiri.id_latihan]:
#                 for bagian in id_bagian_list:
#                     relasi = LatihanBagian(
#                         id_latihan=id_latihan,
#                         id_bagian=bagian
#                     )
#                     db.session.add(relasi)

#             db.session.commit()

#             return jsonify({
#                 "message": "latihan berhasil dibuat",
#                 "jumlah_dibuat": 2,
#                 "target": {
#                     "set": latihan_kanan.target_set,
#                     "repetisi": latihan_kanan.target_repetisi,
#                     "waktu": latihan_kanan.target_waktu,
#                     "mode": "unilateral",
#                     "sisi_tersedia": ["kanan", "kiri"]
#                 }
#             }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"message": "gagal membuat latihan", "error": str(e)}), 500



# @latihanuser_bp.route("/latihan", methods=["POST"])
# def create_latihan():
#     data = request.get_json()

#     # =========================
#     # Validasi
#     # =========================
#     if "nama_latihan" not in data:
#         return jsonify({"message": "nama_latihan wajib diisi"}), 400

#     try:
#         latihan = Latihan(
#             id_latihan=generate_random_id(8),
#             nama_latihan=data["nama_latihan"],
#             video_url=data.get("video_url"),
#             url_gambar=data.get("url_gambar"),
#             deskripsi=data.get("deskripsi"),
#         )

#         db.session.add(latihan)
#         db.session.commit()

#         return jsonify({
#             "message": "latihan berhasil dibuat",
#             "id_latihan": latihan.id_latihan
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "message": "gagal membuat latihan",
#             "error": str(e)
#         }), 500

# @latihanuser_bp.route("/latihan", methods=["POST"])
# def create_latihan():
#     data = request.get_json()

#     # =========================
#     # Validasi
#     # =========================
#     required_fields = ["nama_latihan", "id_bagian"]
#     for field in required_fields:
#         if field not in data:
#             return jsonify({"message": f"{field} wajib diisi"}), 400

#     id_bagian_list = data["id_bagian"]

#     if not isinstance(id_bagian_list, list) or len(id_bagian_list) == 0:
#         return jsonify({
#             "message": "id_bagian harus berupa array dan tidak boleh kosong"
#         }), 400

#     is_unilateral = bool(data.get("is_unilateral", False))
#     nama_latihan_input = data["nama_latihan"]

#     # ðŸ”¥ shared field (TANPA target)
#     shared_fields = dict(
#         level=data.get("level", 1),
#         video_url=data.get("video_url"),
#         url_gambar=data.get("url_gambar"),
#         deskripsi=data.get("deskripsi"),
#         is_unilateral=is_unilateral,
#     )

#     try:
#         # ======================================================
#         # CASE 1 â€” BILATERAL
#         # ======================================================
#         if not is_unilateral:

#             latihan = Latihan(
#                 id_latihan=generate_random_id(8),
#                 nama_latihan=nama_latihan_input,
#                 **shared_fields
#             )

#             db.session.add(latihan)
#             db.session.flush()

#             # relasi ke bagian
#             for bagian in id_bagian_list:
#                 db.session.add(LatihanBagian(
#                     id_latihan=latihan.id_latihan,
#                 id_bagian=bagian,

#                 target_set=data.get("target_set", 3),

#                 target_repetisi=data.get("target_repetisi", 10),

#                 target_waktu=data.get("target_waktu"),

#                 hold_detik=data.get("hold_detik", 5),

#                 rest_repetisi_detik=data.get("rest_repetisi_detik", 10),

#                     rest_set_detik=data.get("rest_set_detik", 30),

#                     progression_repetisi=data.get("progression_repetisi", 2),

#                 progression_hold=data.get("progression_hold", 5),
#             ))


#             db.session.commit()

#             return jsonify({
#                 "message": "latihan berhasil dibuat",
#                 "jumlah_dibuat": 1,
#                 "mode": "bilateral"
#             }), 201

#         # ======================================================
#         # CASE 2 â€” UNILATERAL
#         # ======================================================
#         else:

#             latihan_kanan = Latihan(
#                 id_latihan=generate_random_id(8),
#                 nama_latihan=f"{nama_latihan_input} - Kanan",
#                 **shared_fields
#             )

#             latihan_kiri = Latihan(
#                 id_latihan=generate_random_id(8),
#                 nama_latihan=f"{nama_latihan_input} - Kiri",
#                 **shared_fields
#             )

#             db.session.add(latihan_kanan)
#             db.session.add(latihan_kiri)
#             db.session.flush()

#             # relasi ke bagian (dua-duanya)
#             for lat in [latihan_kanan, latihan_kiri]:
#                 for bagian in id_bagian_list:
#                     db.session.add(LatihanBagian(
#             id_latihan=lat.id_latihan,
#             id_bagian=bagian,

#             target_set=data.get("target_set", 3),

#             target_repetisi=data.get("target_repetisi", 10),

#             target_waktu=data.get("target_waktu"),

#             hold_detik=data.get("hold_detik", 5),

#             rest_repetisi_detik=data.get("rest_repetisi_detik", 10),

#             rest_set_detik=data.get("rest_set_detik", 30),

#             progression_repetisi=data.get("progression_repetisi", 2),

#             progression_hold=data.get("progression_hold", 5),
#             ))


#             db.session.commit()

#             return jsonify({
#                 "message": "latihan berhasil dibuat",
#                 "jumlah_dibuat": 2,
#                 "mode": "unilateral",
#                 "sisi_tersedia": ["kanan", "kiri"]
#             }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "message": "gagal membuat latihan",
#             "error": str(e)
#         }), 500

# @latihanuser_bp.route("/latihan", methods=["POST"])
# def create_latihan():
#     data = request.get_json()

#     # =========================
#     # Validasi
#     # =========================
#     required_fields = ["nama_latihan", "bagian_config"]

#     for field in required_fields:
#         if field not in data:
#             return jsonify({
#                 "message": f"{field} wajib diisi"
#             }), 400

#     bagian_config = data["bagian_config"]

#     if not isinstance(bagian_config, list) or len(bagian_config) == 0:
#         return jsonify({
#             "message": "bagian_config harus berupa array dan tidak boleh kosong"
#         }), 400

#     is_unilateral = bool(data.get("is_unilateral", False))

#     nama_latihan_input = data["nama_latihan"]

#     # =========================
#     # Shared field
#     # =========================
#     shared_fields = dict(
#         level=data.get("level", 1),
#         video_url=data.get("video_url"),
#         url_gambar=data.get("url_gambar"),
#         deskripsi=data.get("deskripsi"),
#         is_unilateral=is_unilateral,
#     )

#     try:

#         # ======================================================
#         # CASE 1 â€” BILATERAL
#         # ======================================================
#         if not is_unilateral:

#             latihan = Latihan(
#                 id_latihan=generate_random_id(8),
#                 nama_latihan=nama_latihan_input,
#                 **shared_fields
#             )

#             db.session.add(latihan)
#             db.session.flush()

#             # ==========================================
#             # Insert konfigurasi per bagian
#             # ==========================================
#             for bagian in bagian_config:

#                 db.session.add(
#                     LatihanBagian(
#                         id_latihan=latihan.id_latihan,

#                         id_bagian=bagian["id_bagian"],

#                         target_set=bagian.get("target_set", 3),

#                         target_repetisi=bagian.get("target_repetisi"),

#                         target_waktu=bagian.get("target_waktu"),

#                         hold_detik=bagian.get("hold_detik", 5),

#                         rest_repetisi_detik=bagian.get(
#                             "rest_repetisi_detik",
#                             10
#                         ),

#                         rest_set_detik=bagian.get(
#                             "rest_set_detik",
#                             30
#                         ),

#                         progression_repetisi=bagian.get(
#                             "progression_repetisi",
#                             2
#                         ),

#                         progression_hold=bagian.get(
#                             "progression_hold",
#                             5
#                         ),
#                     )
#                 )

#             db.session.commit()

#             return jsonify({
#                 "message": "latihan berhasil dibuat",
#                 "jumlah_dibuat": 1,
#                 "mode": "bilateral",
#                 "id_latihan": latihan.id_latihan
#             }), 201

#         # ======================================================
#         # CASE 2 â€” UNILATERAL
#         # ======================================================
#         else:

#             latihan_kanan = Latihan(
#                 id_latihan=generate_random_id(8),
#                 nama_latihan=f"{nama_latihan_input} - Kanan",
#                 **shared_fields
#             )

#             latihan_kiri = Latihan(
#                 id_latihan=generate_random_id(8),
#                 nama_latihan=f"{nama_latihan_input} - Kiri",
#                 **shared_fields
#             )

#             db.session.add(latihan_kanan)
#             db.session.add(latihan_kiri)

#             db.session.flush()

#             # ==========================================
#             # Insert konfigurasi per bagian
#             # ==========================================
#             for lat in [latihan_kanan, latihan_kiri]:

#                 for bagian in bagian_config:

#                     db.session.add(
#                         LatihanBagian(
#                             id_latihan=lat.id_latihan,

#                             id_bagian=bagian["id_bagian"],

#                             target_set=bagian.get(
#                                 "target_set",
#                                 3
#                             ),

#                             target_repetisi=bagian.get(
#                                 "target_repetisi"
#                             ),

#                             target_waktu=bagian.get(
#                                 "target_waktu"
#                             ),

#                             hold_detik=bagian.get(
#                                 "hold_detik",
#                                 5
#                             ),

#                             rest_repetisi_detik=bagian.get(
#                                 "rest_repetisi_detik",
#                                 10
#                             ),

#                             rest_set_detik=bagian.get(
#                                 "rest_set_detik",
#                                 30
#                             ),

#                             progression_repetisi=bagian.get(
#                                 "progression_repetisi",
#                                 2
#                             ),

#                             progression_hold=bagian.get(
#                                 "progression_hold",
#                                 5
#                             ),
#                         )
#                     )

#             db.session.commit()

#             return jsonify({
#                 "message": "latihan berhasil dibuat",
#                 "jumlah_dibuat": 2,
#                 "mode": "unilateral",
#                 "sisi_tersedia": ["kanan", "kiri"],
#                 "id_latihan_kanan": latihan_kanan.id_latihan,
#                 "id_latihan_kiri": latihan_kiri.id_latihan
#             }), 201

#     except Exception as e:

#         db.session.rollback()

#         return jsonify({
#             "message": "gagal membuat latihan",
#             "error": str(e)
#         }), 500

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

# @latihanuser_bp.route("/latihan", methods=["POST"])
# def create_latihan():
#     data = request.get_json()

#     # =========================
#     # Validasi
#     # =========================
#     required_fields = ["nama_latihan", "id_bagian"]
#     for field in required_fields:
#         if field not in data:
#             return jsonify({"message": f"{field} wajib diisi"}), 400

#     id_bagian_list = data["id_bagian"]

#     if not isinstance(id_bagian_list, list) or len(id_bagian_list) == 0:
#         return jsonify({
#             "message": "id_bagian harus berupa array dan tidak boleh kosong"
#         }), 400

#     try:
#         latihan = Latihan(
#             id_latihan=generate_random_id(8),
#             nama_latihan=data["nama_latihan"],  # ðŸ”¥ tetap clean (AI safe)
#             level=data.get("level", 1),
#             video_url=data.get("video_url"),
#             url_gambar=data.get("url_gambar"),
#             deskripsi=data.get("deskripsi"),
#             is_unilateral=bool(data.get("is_unilateral", False))
#         )

#         db.session.add(latihan)
#         db.session.flush()

#         # relasi ke bagian
#         for bagian in id_bagian_list:
#             db.session.add(LatihanBagian(
#                 id_latihan=latihan.id_latihan,
#                 id_bagian=bagian
#             ))

#         db.session.commit()

#         return jsonify({
#             "message": "latihan berhasil dibuat",
#             "id_latihan": latihan.id_latihan,
#             "is_unilateral": latihan.is_unilateral
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "message": "gagal membuat latihan",
#             "error": str(e)
#         }), 500

# @latihanuser_bp.route("/latihan-rule", methods=["POST"])
# def create_latihan_rule():
#     data = request.get_json()

#     required_fields = [
#         "id_latihan",
#         "id_bagian",
#         "target_set",
#         "target_repetisi"
#     ]

#     for field in required_fields:
#         if field not in data:
#             return jsonify({"message": f"{field} wajib diisi"}), 400

#     try:
#         rule = LatihanRuleBagian(
#             id_latihan=data["id_latihan"],
#             id_bagian=data["id_bagian"],

#             target_set=data["target_set"],
#             target_repetisi=data["target_repetisi"],
#             target_waktu=data.get("target_waktu"),

#             hold_detik=data.get("hold_detik"),
#             rest_repetisi_detik=data.get("rest_repetisi_detik"),
#             rest_set_detik=data.get("rest_set_detik"),
#         )

#         db.session.add(rule)
#         db.session.commit()

#         return jsonify({
#             "message": "rule berhasil dibuat"
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "message": "gagal membuat rule",
#             "error": str(e)
#         }), 500
