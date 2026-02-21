from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity


import uuid
from datetime import datetime, timedelta, timezone

from tensorboard import program

from models import (
    BagianTubuh,
    JadwalLatihanUser,
    JadwalLatihanDetail,
    KondisiUser,
    Latihan,
    Question,
    QuestionOption,
    db,
    generate_random_id
)

from services.id_generator import generate_random_4_digit
latihanuser_bp = Blueprint("latihanUser", __name__)

@latihanuser_bp.route("/jadwal/hari-ini", methods=["GET"])
@jwt_required()
def get_jadwal_hari_ini():
    user_id = str(get_jwt_identity())

    start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    end = start + timedelta(days=1)

    # Ambil semua jadwal untuk hari ini
    jadwal_list = JadwalLatihanUser.query.filter(
        JadwalLatihanUser.id_user == user_id,
        JadwalLatihanUser.tanggal >= start,
        JadwalLatihanUser.tanggal < end
    ).all()

    if not jadwal_list:
        return jsonify({
            "message": "Hari ini jadwal istirahat",
            "program": []
        })

    program = []
    program = []
    for j in jadwal_list:
        # Loop through details because relationship is One-To-Many now
        for detail in j.details:
            lat = detail.latihan
            if not lat:
                continue

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
                    "sisi": detail.sisi, # Added side info
                    "target": {
                        "set": lat.target_set,
                        "repetisi": lat.target_repetisi,
                        "waktu": lat.target_waktu
                    }
                }
            })
       
    return jsonify({
        "tanggal": start.strftime("%Y-%m-%d"),
        "program": program
    })

# @latihanuser_bp.route("/generate-jadwal", methods=["POST"])
# @jwt_required()
# def generate_jadwal_otomatis():
#     user_id = str(get_jwt_identity())

#     # =========================
#     # IDEMPOTENCY
#     # =========================
#     if JadwalLatihanUser.query.filter_by(id_user=user_id).count() > 0:
#         return jsonify({
#             "success": True,
#             "code": "JADWAL_EXIST",
#             "data": {"generated": False}
#         }), 200

#     # =========================
#     # KONDISI TERBARU
#     # =========================
#     kondisi = (
#         KondisiUser.query
#         .filter_by(id_user=user_id)
#         .order_by(KondisiUser.created_at.desc())
#         .first()
#     )

#     if not kondisi:
#         return jsonify({
#             "success": False,
#             "code": "KONDISI_NOT_FOUND"
#         }), 404

#     vas = int(kondisi.tingkat_nyeri)

#     # =========================
#     # STOP NYERI BERAT
#     # =========================
#     if vas >= 7:
#         return jsonify({
#             "success": True,
#             "code": "REKOMENDASI_DOKTER",
#             "data": {"tingkat_nyeri": vas}
#         }), 200

#     # =========================
#     # MAP VAS → FASE
#     # =========================
#     if vas <= 3:
#         fase = "F1"
#         minggu_config = {1: 3, 2: 3}
#     else:
#         fase = "F2"
#         minggu_config = {1: 2, 2: 2, 3: 2}

#     # =========================
#     # FILTER LATIHAN
#     # =========================
#     latihans = Latihan.query.filter(
#         Latihan.id_bagian == kondisi.id_bagian,
#         Latihan.fase == fase
#     ).order_by(Latihan.level.asc()).all()

#     if not latihans:
#         return jsonify({
#             "success": False,
#             "code": "LATIHAN_NOT_AVAILABLE"
#         }), 404

#     # Gunakan fixed offset UTC+7 (WIB) karena Windows mungkin tidak memiliki data timezone IANA
#     wib = timezone(timedelta(hours=7))
#     now = datetime.now(wib).replace(
#         hour=8, minute=0, second=0, microsecond=0
#     )

#     # =========================
#     # GENERATE JADWAL
#     # =========================
#     try:
#         index = 0

#         for minggu, jumlah in minggu_config.items():
#             for i in range(jumlah):
#                 latihan = latihans[index % len(latihans)]
#                 index += 1

#                 tanggal = now + timedelta(
#                     days=(minggu - 1) * 7 + i * 2
#                 )

#                 jadwal = JadwalLatihanUser(
#                     id_jadwal=generate_random_4_char(),
#                     id_user=user_id,
#                     id_latihan=latihan.id_latihan,
#                     id_form=kondisi.id_form,
#                     tanggal=tanggal,
#                     status="locked",
#                     # tingkat_nyeri=vas, # Field tidak ada di model
#                     # fase=fase,         # Field tidak ada di model
#                     created_at=now
#                 )

#                 db.session.add(jadwal)

#         db.session.commit()

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "code": "GENERATE_FAILED",
#             "error": str(e)
#         }), 500

#     return jsonify({
#         "success": True,
#         "code": "JADWAL_CREATED",
#         "data": {
#             "fase": fase,
#             "tingkat_nyeri": vas
#         }
#     }), 201

# @latihanuser_bp.route("/generate-jadwal", methods=["POST"])
# @jwt_required()
# def generate_jadwal_otomatis():
#     user_id = str(get_jwt_identity())

#     # ======================================================
#     # 1️⃣ Ambil kondisi terbaru user
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
#     # 2️⃣ IDEMPOTENCY CHECK (1 form = 1 program)
#     # ======================================================
#     existing_program = JadwalLatihanUser.query.filter_by(
#     id_user=user_id,
#     id_form=kondisi.id_form,
#     fase="F1"  # cek fase pertama saja
# ).first()

#     if existing_program:
#         return jsonify({
#             "success": True,
#             "message": "Program sudah pernah dibuat untuk kondisi ini",
#             "nama_program": existing_program.nama_jadwal
#         }), 200

#     # ======================================================
#     # 3️⃣ CEK PROGRAM AKTIF
#     # (tidak boleh generate jika masih ada pending)
#     # ======================================================
#     active_program = JadwalLatihanUser.query.filter(
#         JadwalLatihanUser.id_user == user_id,
#         JadwalLatihanUser.status.in_(["Pending", "Locked"])
#     ).first()

#     if active_program:
#         return jsonify({
#             "success": False,
#             "message": "Selesaikan program sebelumnya terlebih dahulu"
#         }), 400

#     # ======================================================
#     # 4️⃣ Ambil data keputusan
#     # ======================================================
#     vas = int(kondisi.tingkat_nyeri or 0)
#     lama_nyeri = int(kondisi.lama_nyeri_hari or 0)
#     id_bagian = kondisi.id_bagian

#     nama_bagian = "Lutut" if id_bagian == "B001" else "Bahu"

#     # ======================================================
#     # 5️⃣ Decision Logic (Mapping VAS → Fase)
#     # ======================================================
#     if vas >= 7 and lama_nyeri > 14:
#         return jsonify({
#             "success": True,
#             "fase": "Rujuk Medis",
#             "message": "Nyeri tinggi menetap >14 hari, disarankan konsultasi dokter/fisioterapis"
#         }), 200

#     if vas >= 7:
#         fase = "F1"
#         label = "Fase 1 (Akut)"
#     elif 4 <= vas <= 6:
#         fase = "F2"
#         label = "Fase 2 (Sub-Akut)"
#     else:
#         fase = "F3"
#         label = "Fase 3 (Kronis/Lanjut)"

#     # ======================================================
#     # 6️⃣ Ambil pool latihan sesuai bagian & fase
#     # ======================================================
#     latihans_pool = Latihan.query.filter_by(
#         id_bagian=id_bagian,
#         fase=fase
#     ).order_by(Latihan.level.asc()).all()

#     if not latihans_pool:
#         return jsonify({
#             "success": False,
#             "message": "Latihan untuk fase ini belum tersedia"
#         }), 404

#     # ======================================================
#     # 7️⃣ Generate Header Jadwal (Grup)
#     # ======================================================
#     try:
#         id_grup = generate_random_id(4)

#         jadwal_grup = JadwalLatihanUser(
#             id_jadwal=id_grup,
#             id_user=user_id,
#             id_form=kondisi.id_form,
#             nama_jadwal=f"Program {nama_bagian} - {label}",
#             tanggal=datetime.utcnow() + timedelta(days=1),
#             status="Pending",
#             created_at=datetime.utcnow()
#         )

#         db.session.add(jadwal_grup)

#         # ======================================================
#         # 8️⃣ Insert Detail Latihan
#         # ======================================================
#         unilateral_keywords = [
#             "lying", "ankle", "lunge", "clamshell", "stretch",
#             "prone", "heel", "pendulum", "isometric",
#             "crawl", "sleeper", "abduction", "flexion"
#         ]

#         counter = 1

#         for lat in latihans_pool:

#             is_unilateral = any(
#                 key in lat.nama_latihan.lower()
#                 for key in unilateral_keywords
#             )

#             if is_unilateral:
#                 # Sisi Kanan
#                 db.session.add(JadwalLatihanDetail(
#                     id_detail=generate_random_id(8),
#                     id_jadwal=id_grup,
#                     id_latihan=lat.id_latihan,
#                     sisi="Kanan",
#                     urutan=counter
#                 ))
#                 counter += 1

#                 # Sisi Kiri
#                 db.session.add(JadwalLatihanDetail(
#                     id_detail=generate_random_id(8),
#                     id_jadwal=id_grup,
#                     id_latihan=lat.id_latihan,
#                     sisi="Kiri",
#                     urutan=counter
#                 ))
#             else:
#                 db.session.add(JadwalLatihanDetail(
#                     id_detail=generate_random_id(8),
#                     id_jadwal=id_grup,
#                     id_latihan=lat.id_latihan,
#                     sisi=None,
#                     urutan=counter
#                 ))

#             counter += 1

#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "message": "Program berhasil dibuat",
#             "nama_program": jadwal_grup.nama_jadwal,
#             "fase": fase,
#             "total_latihan": len(latihans_pool)
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         print(f"[ERROR GENERATE JADWAL]: {str(e)}")

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
#     # 1️⃣ Ambil kondisi terbaru user
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
#     # 2️⃣ IDEMPOTENCY CHECK (1 form = 1 program)
#     # ======================================================
#     existing_program = JadwalLatihanUser.query.filter_by(
#         id_user=user_id,
#         id_form=kondisi.id_form,
#         fase="F1"
#     ).first()

#     if existing_program:
#         return jsonify({
#             "success": True,
#             "message": "Program sudah pernah dibuat untuk kondisi ini",
#             "nama_program": existing_program.nama_jadwal
#         }), 200

#     # ======================================================
#     # 3️⃣ CEK PROGRAM AKTIF
#     # ======================================================
#     active_program = JadwalLatihanUser.query.filter(
#         JadwalLatihanUser.id_user == user_id,
#         JadwalLatihanUser.status.in_(["Pending", "Locked"])
#     ).first()

#     if active_program:
#         return jsonify({
#             "success": False,
#             "message": "Selesaikan program sebelumnya terlebih dahulu"
#         }), 400

#     # ======================================================
#     # 4️⃣ Ambil data kondisi
#     # ======================================================
#     vas = int(kondisi.tingkat_nyeri or 0)
#     lama_nyeri = int(kondisi.lama_nyeri_hari or 0)
#     id_bagian = kondisi.id_bagian

#     # Ambil nama bagian dari database (lebih fleksibel)
#     bagian = BagianTubuh.query.filter_by(id_bagian=id_bagian).first()
#     nama_bagian = bagian.nama_bagian if bagian else "Bagian Tidak Diketahui"

#     # ======================================================
#     # 5️⃣ DECISION TABLE LOGIC
#     # ======================================================
#     if vas >= 7 and lama_nyeri > 14:
#         return jsonify({
#             "success": True,
#             "fase": "Rujuk Medis",
#             "message": "Nyeri tinggi menetap >14 hari, disarankan konsultasi dokter/fisioterapis"
#         }), 200

#     if vas >= 7:
#         fase = "F1"
#         label = "Fase 1 (Akut)"

#     elif 4 <= vas <= 6:
#         fase = "F2"
#         label = "Fase 2 (Sub-Akut)"

#     elif vas <= 3 and lama_nyeri > 30:
#         fase = "F3"
#         label = "Fase 3 (Kronis/Lanjut)"

#     else:
#         fase = "F2"
#         label = "Fase 2 (Sub-Akut)"

#     # ======================================================
#     # 6️⃣ Ambil pool latihan sesuai bagian & fase
#     # ======================================================
#     latihans_pool = Latihan.query.filter_by(
#         id_bagian=id_bagian,
#         fase=fase
#     ).order_by(Latihan.level.asc()).all()

#     if not latihans_pool:
#         return jsonify({
#             "success": False,
#             "message": "Latihan untuk fase ini belum tersedia"
#         }), 404

#     # ======================================================
#     # 7️⃣ Generate Header Jadwal
#     # ======================================================
#     try:
#         id_grup = generate_random_id(4)
#         IMAGE_MAP = {
#             "L001": "https://yourdomain.com/images/lunge.jpg",
#             "L002": "https://yourdomain.com/images/clamshell.jpg",
#         }
#         url_gambar = IMAGE_MAP.get(lat.id_latihan)

#         jadwal_grup = JadwalLatihanUser(
#             id_jadwal=id_grup,
#             id_user=user_id,
#             id_form=kondisi.id_form,
#             fase=fase,
#             nama_jadwal=f"Program {nama_bagian} - {label}",
#             tanggal=datetime.utcnow() + timedelta(days=1),
#             url_gambar=url_gambar,
#             status="Pending",
#             created_at=datetime.utcnow()
#         )

#         db.session.add(jadwal_grup)

#         # ======================================================
#         # 8️⃣ Insert Detail Latihan
#         # ======================================================
#         unilateral_keywords = [
#             "left", "right", "single", "lunge", "clamshell",
#             "stretch", "abduction", "flexion", "extension",
#             "pendulum", "heel", "crawl", "isometric"
#         ]

#         counter = 1

#         for lat in latihans_pool:

#             is_unilateral = any(
#                 key in lat.nama_latihan.lower()
#                 for key in unilateral_keywords
#             )

#             if is_unilateral:

#                 # Kanan
#                 db.session.add(JadwalLatihanDetail(
#                     id_detail=generate_random_id(8),
#                     id_jadwal=id_grup,
#                     id_latihan=lat.id_latihan,
#                     sisi="Kanan",
#                     urutan=counter
#                 ))
#                 counter += 1

#                 # Kiri
#                 db.session.add(JadwalLatihanDetail(
#                     id_detail=generate_random_id(8),
#                     id_jadwal=id_grup,
#                     id_latihan=lat.id_latihan,
#                     sisi="Kiri",
#                     urutan=counter
#                 ))
#                 counter += 1

#             else:
#                 db.session.add(JadwalLatihanDetail(
#                     id_detail=generate_random_id(8),
#                     id_jadwal=id_grup,
#                     id_latihan=lat.id_latihan,
#                     sisi=None,
#                     urutan=counter
#                 ))
#                 counter += 1

#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "message": "Program berhasil dibuat",
#             "nama_program": jadwal_grup.nama_jadwal,
#             "fase": fase,
#             "total_latihan": len(latihans_pool),
#             "vas": vas,
#             "lama_nyeri": lama_nyeri
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         print(f"[ERROR GENERATE JADWAL]: {str(e)}")

#         return jsonify({
#             "success": False,
#             "message": "Terjadi kesalahan saat generate program",
#             "error": str(e)
#         }), 500

@latihanuser_bp.route("/generate-jadwal", methods=["POST"])
@jwt_required()
def generate_jadwal_otomatis():
    user_id = str(get_jwt_identity())

    # ======================================================
    # 1️⃣ Ambil kondisi terbaru user
    # ======================================================
    kondisi = (
        KondisiUser.query
        .filter_by(id_user=user_id)
        .order_by(KondisiUser.created_at.desc())
        .first()
    )

    if not kondisi:
        return jsonify({
            "success": False,
            "message": "Isi form kondisi terlebih dahulu"
        }), 404

    # ======================================================
    # 2️⃣ Cek program aktif
    # ======================================================
    active_program = JadwalLatihanUser.query.filter(
        JadwalLatihanUser.id_user == user_id,
        JadwalLatihanUser.status.in_(["Pending", "Locked"])
    ).first()

    if active_program:
        return jsonify({
            "success": False,
            "message": "Selesaikan program sebelumnya terlebih dahulu"
        }), 400

    # ======================================================
    # 3️⃣ Ambil data kondisi
    # ======================================================
    vas = int(kondisi.tingkat_nyeri or 0)
    lama_nyeri = int(kondisi.lama_nyeri_hari or 0)
    id_bagian = kondisi.id_bagian

    bagian = BagianTubuh.query.filter_by(id_bagian=id_bagian).first()
    nama_bagian = bagian.nama_bagian if bagian else "Bagian Tidak Diketahui"

    # ======================================================
    # 4️⃣ Decision Logic Fase
    # ======================================================
    if vas >= 7 and lama_nyeri > 14:
        return jsonify({
            "success": True,
            "fase": "Rujuk Medis",
            "message": "Nyeri tinggi menetap >14 hari, disarankan konsultasi dokter/fisioterapis"
        }), 200

    if vas >= 7:
        fase = "F1"
        label = "Fase 1 (Akut)"
    elif 4 <= vas <= 6:
        fase = "F2"
        label = "Fase 2 (Sub-Akut)"
    elif vas <= 3 and lama_nyeri > 30:
        fase = "F3"
        label = "Fase 3 (Kronis/Lanjut)"
    else:
        fase = "F2"
        label = "Fase 2 (Sub-Akut)"

    # ======================================================
    # 5️⃣ Ambil latihan sesuai bagian & fase
    # ======================================================
    latihans_pool = (
        Latihan.query
        .filter_by(id_bagian=id_bagian, fase=fase)
        .order_by(Latihan.level.asc())
        .all()
    )

    if not latihans_pool:
        return jsonify({
            "success": False,
            "message": "Latihan untuk fase ini belum tersedia"
        }), 404

    # ======================================================
    # 6️⃣ Generate Jadwal
    # ======================================================
    try:
        id_grup = generate_random_id(4)

        url_gambar = None
        if latihans_pool:
            first_lat = latihans_pool[0]
            # optional logic to get image if valid for the group
            url_gambar = first_lat.url_gambar
        
        jadwal_grup = JadwalLatihanUser(
            id_jadwal=id_grup,
            id_user=user_id,
            id_form=kondisi.id_form,
            url_gambar=url_gambar,
            fase=fase,
            fase_label=label,
            nama_jadwal=f"Program {nama_bagian} - {label}",
            tanggal=datetime.utcnow() + timedelta(days=1),
            status="Pending",
            created_at=datetime.utcnow()
        )

        db.session.add(jadwal_grup)

        # ======================================================
        # 7️⃣ Insert Detail Berdasarkan jumlah_sisi
        # ======================================================
        counter = 1

        for lat in latihans_pool:

            # Jika 1 sisi → bilateral
            if lat.jumlah_sisi == 1:
                db.session.add(JadwalLatihanDetail(
                    id_detail=generate_random_id(8),
                    id_jadwal=id_grup,
                    id_latihan=lat.id_latihan,
                    sisi=None,
                    urutan=counter
                ))
                counter += 1

            # Jika 2 sisi → kanan & kiri
            elif lat.jumlah_sisi == 2:
                for side in ["Kanan", "Kiri"]:
                    db.session.add(JadwalLatihanDetail(
                        id_detail=generate_random_id(8),
                        id_jadwal=id_grup,
                        id_latihan=lat.id_latihan,
                        sisi=side,
                        urutan=counter
                    ))
                    counter += 1

            # Jika lebih dari 2 (future-proof)
            else:
                for i in range(lat.jumlah_sisi):
                    db.session.add(JadwalLatihanDetail(
                        id_detail=generate_random_id(8),
                        id_jadwal=id_grup,
                        id_latihan=lat.id_latihan,
                        sisi=f"Sisi-{i+1}",
                        urutan=counter
                    ))
                    counter += 1

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Program berhasil dibuat",
            "nama_program": jadwal_grup.nama_jadwal,
            "fase": fase,
            "total_latihan": len(latihans_pool),
            "vas": vas,
            "lama_nyeri": lama_nyeri
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Terjadi kesalahan saat generate program",
            "error": str(e)
        }), 500

@latihanuser_bp.route("/jadwal/meta", methods=["GET"])
@jwt_required()
def get_jadwal_meta():
    user_id = str(get_jwt_identity())

    count_jadwal = JadwalLatihanUser.query.filter_by(id_user=user_id).count()
    
    has_kondisi = KondisiUser.query.filter_by(id_user=user_id).count() > 0

    if not has_kondisi:
         return jsonify({
            "success": False,
            "code": "KONDISI_NOT_FOUND",
            "data": None
        }), 404

    if count_jadwal == 0:
        return jsonify({
            "success": True,
            "code": "JADWAL_EMPTY",
             "data": {
                "available_weeks": [],
                "total_jadwal": 0
            }
        }), 200

    return jsonify({
        "success": True,
        "code": "JADWAL_META_OK",
        "data": {
            "available_weeks": [1, 2, 3],
            "total_jadwal": int(count_jadwal)
        }
    }), 200


@latihanuser_bp.route("/jadwal/fase", methods=["GET"])
@jwt_required()
def get_jadwal_per_fase():
    user_id = str(get_jwt_identity())

    # ======================================================
    # 1️⃣ Ambil program aktif
    # ======================================================
    active_program = (
        JadwalLatihanUser.query
        .filter(
            JadwalLatihanUser.id_user == user_id,
            JadwalLatihanUser.status.in_(["Pending", "Locked"])
        )
        .order_by(JadwalLatihanUser.created_at.desc())
        .options(
            db.joinedload(JadwalLatihanUser.details)
              .joinedload(JadwalLatihanDetail.latihan)
        )
        .first()
    )

    if not active_program:
        return jsonify({
            "success": False,
            "code": "ACTIVE_PROGRAM_NOT_FOUND",
            "data": None
        }), 404

    # ======================================================
    # 2️⃣ Group berdasarkan id_latihan
    # ======================================================
    latihan_map = {}

    for detail in active_program.details:
        lat = detail.latihan
        if not lat:
            continue

        if lat.id_latihan not in latihan_map:
            latihan_map[lat.id_latihan] = {
                "id_latihan": lat.id_latihan,
                "nama_latihan": lat.nama_latihan,
                "deskripsi": lat.deskripsi,
                "image_url": lat.url_gambar,
                "level": int(lat.level) if lat.level else 1,
                "duration": int(lat.target_waktu or 0),
                "target": {
                    "set": lat.target_set,
                    "repetisi": lat.target_repetisi,
                    "waktu": lat.target_waktu
                },
                "video_url": lat.video_url,
                "jumlah_sisi": lat.jumlah_sisi,
                "sisi": []
            }

        # Tambahkan sisi jika ada
        if detail.sisi:
            latihan_map[lat.id_latihan]["sisi"].append(detail.sisi)

    # ======================================================
    # 3️⃣ Final list
    # ======================================================
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

    # ======================================================
    # 1️⃣ Ambil semua program milik user
    # ======================================================
    semua_program = (
        JadwalLatihanUser.query
        .filter(JadwalLatihanUser.id_user == user_id)
        .order_by(JadwalLatihanUser.created_at.desc())
        .options(
            db.joinedload(JadwalLatihanUser.details)
              .joinedload(JadwalLatihanDetail.latihan)
        )
        .all()
    )

    if not semua_program:
        return jsonify({
            "success": True,
            "code": "PROGRAM_EMPTY",
            "data": []
        }), 200

    # ======================================================
    # 2️⃣ Format response per program
    # ======================================================
    hasil = []
    
    for prog in semua_program:
        latihan_map = {}

        for detail in prog.details:
            lat = detail.latihan
            if not lat:
                continue

            if lat.id_latihan not in latihan_map:
                latihan_map[lat.id_latihan] = {
                    "id_latihan": lat.id_latihan,
                    "nama_latihan": lat.nama_latihan,
                    "deskripsi": lat.deskripsi,
                    "image_url": lat.url_gambar,
                    "level": int(lat.level) if lat.level else 1,
                    "duration": int(lat.target_waktu or 0),
                    "target": {
                        "set": lat.target_set,
                        "repetisi": lat.target_repetisi,
                        "waktu": lat.target_waktu
                    },
                    "video_url": lat.video_url,
                    "jumlah_sisi": lat.jumlah_sisi,
                    "sisi": []
                }

            # Tambahkan sisi jika ada
            if detail.sisi:
                latihan_map[lat.id_latihan]["sisi"].append(detail.sisi)

        # Convert sisi array to string to match Dart's expected String format
        for lat_id in latihan_map:
            if latihan_map[lat_id]["sisi"]:
                latihan_map[lat_id]["sisi"] = ", ".join(latihan_map[lat_id]["sisi"])
            else:
                latihan_map[lat_id]["sisi"] = None

        result_latihan = list(latihan_map.values())

        hasil.append({
            "program_id": prog.id_jadwal,
            "nama_program": prog.nama_jadwal,
            "fase": prog.fase or "F1",
            "tanggal_mulai": prog.tanggal.strftime("%Y-%m-%d"),
            "total_latihan": len(result_latihan),
            "latihan": result_latihan
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
#     # Validasi Minimal
#     # =========================
#     # Ditambah vas_min dan vas_max karena sekarang wajib untuk sistem pakar
#     required_fields = ["nama_latihan", "id_bagian", "level", "vas_min", "vas_max"]
#     for field in required_fields:
#         if field not in data:
#             return jsonify({
#                 "message": f"{field} wajib diisi"
#             }), 400

#     try:
#         # Generate ID Latihan (8 karakter sesuai model)
#         id_latihan = generate_random_id(8) 

#         # Membuat objek Latihan langsung dengan data teknisnya
#         latihan = Latihan(
#             id_latihan=id_latihan,
#             nama_latihan=data["nama_latihan"],
#             id_bagian=data["id_bagian"],
#             level=data["level"],
#             vas_min=data["vas_min"],
#             vas_max=data["vas_max"],
#             fase=data.get("fase"), # Opsional: F1, F2, dst
            
#             # Data Teknis yang sudah digabung
#             video_url=data.get("video_url"),
#             url_gambar=data.get("url_gambar"),
#             target_set=data.get("target_set", 3), # Default 3 set jika kosong
#             target_repetisi=data.get("target_repetisi"),
#             target_waktu=data.get("target_waktu"),
            
#             deskripsi=data.get("deskripsi"),
#             created_at=datetime.utcnow()
#         )

#         # =========================
#         # TRANSACTION
#         # =========================
#         db.session.add(latihan)
#         db.session.commit()

#         return jsonify({
#             "message": "latihan berhasil dibuat",
#             "data": {
#                 "id_latihan": latihan.id_latihan,
#                 "nama_latihan": latihan.nama_latihan,
#                 "id_bagian": latihan.id_bagian,
#                 "level": latihan.level,
#                 "vas_range": f"{latihan.vas_min}-{latihan.vas_max}",
#                 "target": {
#                     "set": latihan.target_set,
#                     "repetisi": latihan.target_repetisi,
#                     "waktu": latihan.target_waktu
#                 },
#                 "video_url": latihan.video_url
#             }
#         }), 201

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
    # Validasi Fields
    # =========================
    required_fields = ["nama_latihan", "id_bagian", "level", "vas_min", "vas_max"]
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"{field} wajib diisi"}), 400

    try:
        id_latihan = generate_random_id(8) 
        latihan = Latihan(
            id_latihan=id_latihan,
            nama_latihan=data["nama_latihan"], 
            id_bagian=data["id_bagian"],
            level=data["level"],
            vas_min=data["vas_min"],
            vas_max=data["vas_max"],
            fase=data.get("fase"),
            video_url=data.get("video_url"),
            url_gambar=data.get("url_gambar"),
            target_set=data.get("target_set", 3),
            target_repetisi=data.get("target_repetisi"),
            target_waktu=data.get("target_waktu"),
            deskripsi=data.get("deskripsi")
        )

        db.session.add(latihan)
        db.session.commit()

        # ===========================================================
        # LOGIKA UPDATE: Tambahkan keyword untuk Bahu (Shoulder)
        # ===========================================================
        # Keyword Lutut: lying, ankle, lunge, clamshell, prone, heel
        # Keyword Bahu: pendulum, isometric, wall crawl, sleeper, abduction, flexion
        unilateral_keywords = [
            "lying", "ankle", "lunge", "clamshell", "stretch", "prone", "heel",
            "pendulum", "isometric", "crawl", "sleeper", "abduction", "flexion"
        ]
        
        # Cek apakah nama_latihan mengandung salah satu keyword di atas
        is_unilateral = any(key in latihan.nama_latihan.lower() for key in unilateral_keywords)

        # Bangun Response JSON
        res_target = {
            "set": latihan.target_set,
            "repetisi": latihan.target_repetisi,
            "waktu": latihan.target_waktu
        }

        # Jika unilateral, tambahkan flag 'sisi' agar MediaPipe tahu harus switch
        if is_unilateral:
            res_target["mode"] = "unilateral"
            res_target["sisi_tersedia"] = ["kanan", "kiri"]
        else:
            res_target["mode"] = "bilateral" # Dilakukan bersamaan (cth: Bridge atau Scapular Squeeze)

        return jsonify({
            "message": "latihan berhasil dibuat",
            "data": {
                "id_latihan": latihan.id_latihan,
                "nama_latihan": latihan.nama_latihan,
                "target": res_target,
                "video_url": latihan.video_url
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "gagal", "error": str(e)}), 500