from flask import Blueprint, current_app, request, jsonify
from models import db, HistoryAktifitas, HistoryAktifitasDetail, JadwalLatihanUser, JadwalLatihanDetail, Latihan, generate_random_id, KondisiUser, BagianTubuh
from sqlalchemy import func, or_
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta, timezone
history_bp = Blueprint('history_bp', __name__)

DAY_LABELS = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
AREA_DISPLAY_ORDER = {
    "pinggul": 0,
    "paha": 1,
    "lutut": 2,
    "tungkai bawah": 3,
    "pergelangan kaki": 4,
    "telapak kaki": 5,
}


def _sort_bagian_tubuh(bagian):
    nama_bagian = (bagian.nama_bagian or "").strip()
    return (
        AREA_DISPLAY_ORDER.get(nama_bagian.lower(), len(AREA_DISPLAY_ORDER)),
        nama_bagian.lower(),
    )


def _normalize_id_bagian_param(id_bagian):
    if not id_bagian:
        return "all"

    normalized = str(id_bagian).strip()
    if not normalized:
        return "all"

    if normalized.lower() in ["all", "semua", "null", "none", "undefined"]:
        return "all"

    return normalized


def _selected_area_label(id_bagian, fallback=None):
    if id_bagian == "all":
        return "Semua Area"
    if fallback:
        return fallback
    bagian = BagianTubuh.query.get(id_bagian)
    return bagian.nama_bagian if bagian and bagian.nama_bagian else "Area Tidak Diketahui"


def _analytics_date_range(range_key):
    if not range_key:
        return None, None

    today = datetime.utcnow().date()
    normalized_range = str(range_key).strip().lower()

    if normalized_range == "month":
        start_date = today.replace(day=1)
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        end_date = next_month - timedelta(days=1)
        return start_date, end_date

    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=6)
    return start_date, end_date


def _empty_analytics_response(id_bagian, selected_label=None):
    return {
        "selected_id_bagian": id_bagian,
        "selected_area_label": _selected_area_label(id_bagian, selected_label),
        "summary": {
            "total_latihan": 0,
            "rata_rata_akurasi": 0,
            "rata_rata_durasi": 0,
            "rata_rata_nyeri_sebelum": 0,
            "rata_rata_nyeri_sesudah": 0,
            "perubahan_nyeri": 0,
        },
        "chart": [],
    }


def _round_number(value, digits=2):
    if value is None:
        return 0
    rounded = round(float(value), digits)
    return int(rounded) if rounded.is_integer() else rounded


def _status_history_label(status):
    status_map = {
        "done": "Selesai",
        "completed": "Selesai",
        "warning": "Perlu Evaluasi",
        "stop": "Dihentikan",
    }
    if not status:
        return "Selesai"
    return status_map.get(str(status).strip().lower(), str(status))


def _debug_aktifitas_query(endpoint, user_id, raw_id_bagian, selected_id_bagian, rows):
    nama_bagian_list = sorted({
        (row[-1].nama_bagian if row[-1] and row[-1].nama_bagian else "Area Tidak Diketahui")
        for row in rows
    })
    current_app.logger.debug(
        "[Aktifitas:%s] id_user=%s, id_bagian_diterima=%s, "
        "id_bagian_dipakai=%s, jumlah_data=%s, nama_bagian=%s",
        endpoint,
        user_id,
        raw_id_bagian,
        selected_id_bagian,
        len(rows),
        nama_bagian_list,
    )


@history_bp.route("/aktifitas/bagian-tubuh", methods=["GET"])
def get_aktifitas_bagian_tubuh():
    try:
        bagian_list = sorted(BagianTubuh.query.all(), key=_sort_bagian_tubuh)

        return jsonify({
            "success": True,
            "message": "Daftar bagian tubuh berhasil diambil",
            "data": [
                {
                    "id_bagian": bagian.id_bagian,
                    "nama_bagian": bagian.nama_bagian,
                    "model_key": bagian.model_key,
                }
                for bagian in bagian_list
            ],
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Terjadi kesalahan saat mengambil daftar bagian tubuh",
            "error": str(e),
        }), 500


@history_bp.route("/aktifitas/analytics", methods=["GET"])
@jwt_required()
def get_aktifitas_analytics():
    user_id = str(get_jwt_identity())
    raw_id_bagian = request.args.get("id_bagian")
    selected_id_bagian = _normalize_id_bagian_param(raw_id_bagian)
    range_key = request.args.get("range")
    start_date, end_date = _analytics_date_range(range_key)
    selected_bagian = (
        BagianTubuh.query.get(selected_id_bagian)
        if selected_id_bagian != "all"
        else None
    )
    selected_label = (
        selected_bagian.nama_bagian
        if selected_bagian and selected_bagian.nama_bagian
        else _selected_area_label(selected_id_bagian)
    )

    try:
        base_query = (
            db.session.query(HistoryAktifitas, BagianTubuh)
            .join(
                JadwalLatihanUser,
                HistoryAktifitas.id_jadwal == JadwalLatihanUser.id_jadwal
            )
            .join(
                KondisiUser,
                JadwalLatihanUser.id_form == KondisiUser.id_form
            )
            .join(
                BagianTubuh,
                KondisiUser.id_bagian == BagianTubuh.id_bagian
            )
            .filter(
                HistoryAktifitas.id_user == user_id,
            )
        )

        if start_date and end_date:
            base_query = base_query.filter(
                HistoryAktifitas.tanggal.isnot(None),
                func.date(HistoryAktifitas.tanggal) >= start_date,
                func.date(HistoryAktifitas.tanggal) <= end_date,
            )

        if selected_id_bagian != "all":
            base_query = base_query.filter(
                KondisiUser.id_bagian == selected_id_bagian
            )

        rows = base_query.order_by(HistoryAktifitas.tanggal.asc()).all()
        _debug_aktifitas_query(
            "analytics",
            user_id,
            raw_id_bagian,
            selected_id_bagian,
            rows,
        )

        if not rows:
            return jsonify({
                "success": True,
                "message": "Data analitik aktivitas berhasil diambil",
                "data": _empty_analytics_response(
                    selected_id_bagian,
                    selected_label
                )
            }), 200

        histories = [row[0] for row in rows]

        total_latihan = len(histories)
        valid_akurasi = [h.akurasi_total for h in histories if h.akurasi_total is not None]
        valid_durasi = [h.durasi_total for h in histories if h.durasi_total is not None]
        valid_nyeri_sebelum = [h.vas_sebelum for h in histories if h.vas_sebelum is not None]
        valid_nyeri_sesudah = [h.vas_sesudah for h in histories if h.vas_sesudah is not None]

        rata_nyeri_sebelum = (
            sum(valid_nyeri_sebelum) / len(valid_nyeri_sebelum)
            if valid_nyeri_sebelum else 0
        )
        rata_nyeri_sesudah = (
            sum(valid_nyeri_sesudah) / len(valid_nyeri_sesudah)
            if valid_nyeri_sesudah else 0
        )

        grouped_by_date = {}
        for history in histories:
            if not history.tanggal:
                continue
            tanggal = history.tanggal.date()
            grouped_by_date.setdefault(tanggal, []).append(history)

        chart = []
        for tanggal in sorted(grouped_by_date.keys()):
            daily_histories = grouped_by_date[tanggal]

            daily_nyeri_sebelum = [
                h.vas_sebelum for h in daily_histories if h.vas_sebelum is not None
            ]
            daily_nyeri_sesudah = [
                h.vas_sesudah for h in daily_histories if h.vas_sesudah is not None
            ]
            daily_akurasi = [
                h.akurasi_total for h in daily_histories if h.akurasi_total is not None
            ]
            daily_durasi = [
                h.durasi_total for h in daily_histories if h.durasi_total is not None
            ]

            chart.append({
                "tanggal": tanggal.strftime("%Y-%m-%d"),
                "label": DAY_LABELS[tanggal.weekday()],
                "nyeri_sebelum": _round_number(
                    sum(daily_nyeri_sebelum) / len(daily_nyeri_sebelum)
                    if daily_nyeri_sebelum else 0
                ),
                "nyeri_sesudah": _round_number(
                    sum(daily_nyeri_sesudah) / len(daily_nyeri_sesudah)
                    if daily_nyeri_sesudah else 0
                ),
                "akurasi": _round_number(
                    sum(daily_akurasi) / len(daily_akurasi)
                    if daily_akurasi else 0
                ),
                "durasi_total": _round_number(sum(daily_durasi)),
            })

        return jsonify({
            "success": True,
            "message": "Data analitik aktivitas berhasil diambil",
            "data": {
                "selected_id_bagian": selected_id_bagian,
                "selected_area_label": selected_label,
                "summary": {
                    "total_latihan": total_latihan,
                    "rata_rata_akurasi": _round_number(
                        sum(valid_akurasi) / len(valid_akurasi)
                        if valid_akurasi else 0
                    ),
                    "rata_rata_durasi": _round_number(
                        sum(valid_durasi) / len(valid_durasi)
                        if valid_durasi else 0
                    ),
                    "rata_rata_nyeri_sebelum": _round_number(rata_nyeri_sebelum),
                    "rata_rata_nyeri_sesudah": _round_number(rata_nyeri_sesudah),
                    "perubahan_nyeri": _round_number(
                        rata_nyeri_sesudah - rata_nyeri_sebelum
                    ),
                },
                "chart": chart,
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Terjadi kesalahan saat mengambil analitik aktivitas",
            "error": str(e)
        }), 500


@history_bp.route("/aktifitas/history", methods=["GET"])
@jwt_required()
def get_aktifitas_history():
    user_id = str(get_jwt_identity())
    raw_id_bagian = request.args.get("id_bagian")
    selected_id_bagian = _normalize_id_bagian_param(raw_id_bagian)

    try:
        query = (
            db.session.query(HistoryAktifitas, JadwalLatihanUser, BagianTubuh)
            .join(
                JadwalLatihanUser,
                HistoryAktifitas.id_jadwal == JadwalLatihanUser.id_jadwal
            )
            .join(
                KondisiUser,
                JadwalLatihanUser.id_form == KondisiUser.id_form
            )
            .join(
                BagianTubuh,
                KondisiUser.id_bagian == BagianTubuh.id_bagian
            )
            .filter(
                HistoryAktifitas.id_user == user_id,
            )
        )

        if selected_id_bagian != "all":
            query = query.filter(KondisiUser.id_bagian == selected_id_bagian)

        rows = query.order_by(HistoryAktifitas.tanggal.desc()).all()
        _debug_aktifitas_query(
            "history",
            user_id,
            raw_id_bagian,
            selected_id_bagian,
            rows,
        )

        data = []
        for history, jadwal, bagian in rows:
            area_value = bagian.id_bagian if bagian else None
            area_label = (
                bagian.nama_bagian
                if bagian and bagian.nama_bagian
                else _selected_area_label(area_value or "all")
            )

            data.append({
                "id_history": history.id_history,
                "id_jadwal": history.id_jadwal,
                "id_bagian": area_value,
                "nama_bagian": area_label,
                "area": area_value,
                "area_label": area_label,
                "tanggal": (
                    history.tanggal.isoformat()
                    if history.tanggal else None
                ),
                "nama_jadwal": (
                    jadwal.nama_jadwal
                    if jadwal and jadwal.nama_jadwal
                    else "Program Latihan"
                ),
                "status": _status_history_label(history.status),
                "durasi_total": _round_number(history.durasi_total),
                "akurasi_total": _round_number(history.akurasi_total),
                "vas_sebelum": history.vas_sebelum or 0,
                "vas_sesudah": history.vas_sesudah or 0,
                "delta_vas": history.delta_vas or 0,
                "rekomendasi": (
                    history.rekomendasi
                    if history.rekomendasi
                    else "Latihan dapat dilanjutkan"
                ),
            })

        return jsonify({
            "success": True,
            "message": "Riwayat latihan berhasil diambil",
            "data": data,
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Terjadi kesalahan saat mengambil riwayat latihan",
            "error": str(e)
        }), 500


@history_bp.route("/aktifitas/history/<id_history>", methods=["GET"])
@jwt_required()
def get_detail_aktifitas_history(id_history):
    user_id = str(get_jwt_identity())

    try:
        row = (
            db.session.query(HistoryAktifitas, JadwalLatihanUser, BagianTubuh)
            .outerjoin(
                JadwalLatihanUser,
                HistoryAktifitas.id_jadwal == JadwalLatihanUser.id_jadwal
            )
            .outerjoin(
                KondisiUser,
                JadwalLatihanUser.id_form == KondisiUser.id_form
            )
            .outerjoin(
                BagianTubuh,
                KondisiUser.id_bagian == BagianTubuh.id_bagian
            )
            .filter(
                HistoryAktifitas.id_history == id_history,
                HistoryAktifitas.id_user == user_id,
                or_(
                    JadwalLatihanUser.id_user == user_id,
                    JadwalLatihanUser.id_user.is_(None)
                ),
            )
            .first()
        )

        if not row:
            return jsonify({
                "success": False,
                "message": "Riwayat latihan tidak ditemukan"
            }), 404

        history, jadwal, bagian = row

        detail_rows = (
            db.session.query(HistoryAktifitasDetail, Latihan)
            .outerjoin(
                Latihan,
                HistoryAktifitasDetail.id_latihan == Latihan.id_latihan
            )
            .filter(HistoryAktifitasDetail.id_history == history.id_history)
            .order_by(HistoryAktifitasDetail.id_history_detail.asc())
            .all()
        )

        area_value = bagian.id_bagian if bagian else None
        area_label = (
            bagian.nama_bagian
            if bagian and bagian.nama_bagian
            else _selected_area_label(area_value or "all")
        )

        sesi_latihan = []
        for detail, latihan in detail_rows:
            sesi_latihan.append({
                "id_history_detail": detail.id_history_detail,
                "nama_latihan": (
                    latihan.nama_latihan
                    if latihan and latihan.nama_latihan
                    else "Latihan"
                ),
                "sisi": detail.sisi,
                "repetisi_tercapai": detail.repetisi_tercapai or 0,
                "akurasi_latihan": _round_number(detail.akurasi_latihan),
            })

        return jsonify({
            "success": True,
            "message": "Detail riwayat latihan berhasil diambil",
            "data": {
                "id_history": history.id_history,
                "area": area_value,
                "area_label": area_label,
                "tanggal": (
                    history.tanggal.isoformat()
                    if history.tanggal else None
                ),
                "nama_jadwal": (
                    jadwal.nama_jadwal
                    if jadwal and jadwal.nama_jadwal
                    else "Program Latihan"
                ),
                "fase": jadwal.fase if jadwal else None,
                "fase_label": jadwal.fase_label if jadwal else None,
                "status": _status_history_label(history.status),
                "durasi_total": _round_number(history.durasi_total),
                "akurasi_total": _round_number(history.akurasi_total),
                "vas_sebelum": history.vas_sebelum or 0,
                "vas_sesudah": history.vas_sesudah or 0,
                "delta_vas": history.delta_vas or 0,
                "rekomendasi": (
                    history.rekomendasi
                    if history.rekomendasi
                    else "Latihan dapat dilanjutkan"
                ),
                "sesi_latihan": sesi_latihan,
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Terjadi kesalahan saat mengambil detail riwayat latihan",
            "error": str(e)
        }), 500

@history_bp.route("/jadwal/selesai-sesi", methods=["POST"])
@jwt_required()
def simpan_history_dan_selesai():
    user_id = str(get_jwt_identity())
    data = request.get_json() or {}

    print(f"[DEBUG] Payload dari Flutter: {data}")

    id_jadwal = data.get("id_jadwal")
    if not id_jadwal:
        return jsonify({
            "success": False,
            "message": "id_jadwal wajib diisi"
        }), 400

    details_data = data.get("details", [])
    if not isinstance(details_data, list) or not details_data:
        return jsonify({
            "success": False,
            "message": "details wajib diisi dan tidak boleh kosong"
        }), 400

    def parse_vas(field_name):
        value = data.get(field_name)
        if value is None:
            return None, f"{field_name} wajib diisi"
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None, f"{field_name} harus berupa angka"
        if parsed < 0 or parsed > 10:
            return None, f"{field_name} harus berada di rentang 0 sampai 10"
        return int(parsed) if parsed.is_integer() else parsed, None

    vas_sebelum, error = parse_vas("vas_sebelum")
    if error:
        return jsonify({"success": False, "message": error}), 400

    vas_sesudah, error = parse_vas("vas_sesudah")
    if error:
        return jsonify({"success": False, "message": error}), 400

    try:
        jadwal = JadwalLatihanUser.query.filter_by(
            id_jadwal=id_jadwal,
            id_user=user_id
        ).first()

        if not jadwal:
            return jsonify({
                "success": False,
                "message": "Jadwal tidak ditemukan"
            }), 404

        if jadwal.status == "Completed":
            return jsonify({
                "success": False,
                "message": "Jadwal sudah diselesaikan sebelumnya"
            }), 400

        kondisi = KondisiUser.query.get(jadwal.id_form) if jadwal.id_form else None
        if not kondisi:
            kondisi = (
                KondisiUser.query
                .filter_by(id_user=user_id)
                .order_by(KondisiUser.created_at.desc())
                .first()
            )

        def normalize_vas(value):
            if value is None:
                return None
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                return None
            return int(parsed) if parsed.is_integer() else parsed

        # Jika vas_sebelum dikirim 0 dari Flutter sebagai placeholder,
        # ambil baseline valid: history sebelumnya, lalu fallback ke kondisi awal.
        if vas_sebelum == 0 or vas_sebelum is None:
            history_query = (
                db.session.query(HistoryAktifitas)
                .join(
                    JadwalLatihanUser,
                    HistoryAktifitas.id_jadwal == JadwalLatihanUser.id_jadwal
                )
                .filter(
                    HistoryAktifitas.id_user == user_id,
                    HistoryAktifitas.id_jadwal != jadwal.id_jadwal
                )
            )

            if jadwal.id_form:
                history_query = history_query.filter(
                    JadwalLatihanUser.id_form == jadwal.id_form
                )

            last_history = history_query.order_by(
                HistoryAktifitas.tanggal.desc()
            ).first()

            previous_vas = normalize_vas(
                last_history.vas_sesudah if last_history else None
            )
            initial_vas = normalize_vas(
                kondisi.tingkat_nyeri if kondisi else None
            )

            if previous_vas is not None:
                vas_sebelum = previous_vas
            elif initial_vas is not None:
                vas_sebelum = initial_vas

        delta_vas = vas_sesudah - vas_sebelum
        durasi_total = data.get("durasi_total", 0.0)
        akurasi_total = data.get("akurasi_total", 0.0)

        id_history = generate_random_id(8)
        new_history = HistoryAktifitas(
            id_history=id_history,
            id_user=user_id,
            id_jadwal=id_jadwal,
            tanggal=datetime.utcnow(),
            durasi_total=durasi_total,
            akurasi_total=akurasi_total,
            status="done",
            action_result="maintain",
            vas_sebelum=vas_sebelum,
            vas_sesudah=vas_sesudah,
            delta_vas=delta_vas,
            rekomendasi="Sesi latihan berhasil disimpan.",
            decision_flag="completed"
        )
        db.session.add(new_history)

        for item in details_data:
            id_latihan = item.get("id_latihan")
            if not id_latihan:
                db.session.rollback()
                return jsonify({
                    "success": False,
                    "message": "Setiap detail wajib memiliki id_latihan"
                }), 400

            detail = HistoryAktifitasDetail(
                id_history_detail=generate_random_id(8),
                id_history=id_history,
                id_latihan=id_latihan,
                sisi=item.get("sisi"),
                repetisi_tercapai=item.get("repetisi_tercapai", 0),
                akurasi_latihan=item.get("akurasi_latihan", 0.0)
            )
            db.session.add(detail)

            id_detail_jadwal = item.get("id_detail_jadwal")
            if id_detail_jadwal:
                jd = JadwalLatihanDetail.query.get(id_detail_jadwal)
                if jd and jd.id_jadwal == jadwal.id_jadwal:
                    jd.status_eksekusi = True

        jadwal.status = "Completed"

        next_jadwal = JadwalLatihanUser.query.filter(
            JadwalLatihanUser.id_user == user_id,
            JadwalLatihanUser.id_form == jadwal.id_form,
            JadwalLatihanUser.tanggal > jadwal.tanggal,
            JadwalLatihanUser.status == "Locked"
        ).order_by(JadwalLatihanUser.tanggal.asc()).first()

        next_jadwal_payload = None
        if next_jadwal:
            next_jadwal.status = "Need Screening"
            next_jadwal_payload = {
                "id_jadwal": next_jadwal.id_jadwal,
                "status": next_jadwal.status,
                "tanggal": next_jadwal.tanggal.strftime("%Y-%m-%d") if next_jadwal.tanggal else None
            }

        db.session.commit()

        response_data = {
            "id_history": id_history,
            "vas_sebelum": vas_sebelum,
            "vas_sesudah": vas_sesudah,
            "delta_vas": delta_vas,
            "status_jadwal": jadwal.status,
            "next_jadwal": next_jadwal_payload
        }

        if next_jadwal:
            return jsonify({
                "success": True,
                "mode": "session_completed",
                "program_finished": False,
                "next_status": "Need Screening",
                "redirect": None,
                "message": "Sesi berhasil disimpan. Sesi berikutnya membutuhkan screening nyeri.",
                "data": response_data
            }), 201

        return jsonify({
            "success": True,
            "mode": "program_completed",
            "program_finished": True,
            "redirect": None,
            "message": "Program latihan selesai.",
            "data": {
                **response_data,
                "next_jadwal": None
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Terjadi kesalahan pada server",
            "error": str(e)
        }), 500

# @history_bp.route("/history/me", methods=["GET"])
# @jwt_required()
# def get_my_history():
#     user_id = str(get_jwt_identity())
    
#     # Ambil 10 riwayat jadwal terakhir
#     histories = HistoryAktifitas.query.filter_by(id_user=user_id)\
#                 .order_by(HistoryAktifitas.tanggal.desc()).limit(10).all()

#     result = []
#     for h in histories:
#         # Menghitung total latihan yang dilakukan dalam jadwal ini
#         total_latihan = len(h.details)
        
#         result.append({
#             "id_history": h.id_history,
#             "tanggal": h.tanggal.strftime("%Y-%m-%d %H:%M"),
#             "durasi_total_menit": round(h.durasi_total / 60, 1), # Konversi detik ke menit
#             "akurasi_total": h.akurasi_total,
#             "total_gerakan": total_latihan,
#             "nama_jadwal": h.jadwal_latihan.nama_jadwal if h.jadwal_latihan else "Program Latihan",
#             # Mengirimkan detail gerakan secara ringkas
#             "latihan_dilakukan": [
#                 {
#                     "nama_latihan": d.latihan_ref.nama_latihan if d.latihan_ref else "Unknown",
#                     "sisi": d.sisi,
#                     "akurasi": d.akurasi_latihan
#                 } for d in h.details
#             ]
#         })

#     return jsonify({"success": True, "data": result}), 200


@history_bp.route("/history/me", methods=["GET"])
@jwt_required()
def get_my_history():
    user_id = str(get_jwt_identity())
    
    histories = HistoryAktifitas.query.filter_by(id_user=user_id)\
                .order_by(HistoryAktifitas.tanggal.desc()).limit(10).all()

    result = []

    total_durasi = 0
    total_akurasi = 0
    total_delta = 0
    count_delta = 0

    for h in histories:
        total_latihan = len(h.details)

        # ===== Hitung summary global =====
        total_durasi += (h.durasi_total or 0)
        total_akurasi += (h.akurasi_total or 0)

        if h.delta_vas is not None:
            total_delta += h.delta_vas
            count_delta += 1

        # ===== Interpretasi =====
        ringkasan = "Stabil"
        if h.delta_vas is not None:
            if h.delta_vas < 0:
                ringkasan = "Membaik"
            elif h.delta_vas > 0:
                ringkasan = "Meningkat"

        kualitas = "Kurang"
        if (h.akurasi_total or 0) >= 80:
            kualitas = "Baik"
        elif (h.akurasi_total or 0) >= 60:
            kualitas = "Cukup"

        result.append({
            "id_history": h.id_history,
            "tanggal": h.tanggal.strftime("%Y-%m-%d %H:%M"),
            "durasi_total_menit": round((h.durasi_total or 0) / 60, 1),
            "akurasi_total": h.akurasi_total,
            "total_gerakan": total_latihan,
            "nama_jadwal": h.jadwal_latihan.nama_jadwal if h.jadwal_latihan else "Program Latihan",

            # 🔥 DATA KLINIS (WAJIB UNTUK REPORT)
            "vas_sebelum": h.vas_sebelum,
            "vas_sesudah": h.vas_sesudah,
            "delta_vas": h.delta_vas,
            "status": h.status,
            "rekomendasi": h.rekomendasi,

            # 🔥 INTERPRETASI
            "ringkasan": ringkasan,
            "kualitas_latihan": kualitas,

            # Detail gerakan
            "latihan_dilakukan": [
                {
                    "nama_latihan": d.latihan_ref.nama_latihan if d.latihan_ref else "Unknown",
                    "sisi": d.sisi,
                    "akurasi": d.akurasi_latihan
                } for d in h.details
            ]
        })

    # ===== SUMMARY REPORT =====
    total_sesi = len(histories)

    avg_durasi = round((total_durasi / total_sesi) / 60, 1) if total_sesi > 0 else 0
    avg_akurasi = round(total_akurasi / total_sesi, 1) if total_sesi > 0 else 0
    avg_delta = round(total_delta / count_delta, 1) if count_delta > 0 else 0

    tren_nyeri = "Stabil"
    if avg_delta < 0:
        tren_nyeri = "Membaik"
    elif avg_delta > 0:
        tren_nyeri = "Meningkat"

    return jsonify({
        "success": True,
        "summary": {
            "total_sesi": total_sesi,
            "rata_durasi_menit": avg_durasi,
            "rata_akurasi": avg_akurasi,
            "rata_perubahan_nyeri": avg_delta,
            "tren_nyeri": tren_nyeri
        },
        "data": result
    }), 200

# @history_bp.route("/analitik", methods=["GET"])
# @jwt_required()
# def get_analitik():
#     user_id = str(get_jwt_identity())
    
#     # 1. Ambil query parameter 'date' (Format: YYYY-MM-DD), default hari ini
#     date_str = request.args.get('date')
#     if date_str:
#         try:
#             selected_date = datetime.strptime(date_str, "%Y-%m-%d")
#         except ValueError:
#             return jsonify({"success": False, "message": "Format tanggal salah. Gunakan YYYY-MM-DD"}), 400
#     else:
#         selected_date = datetime.utcnow()

#     # 2. Hitung Hari Senin s/d Minggu untuk Chart Mingguan
#     # weekday(): 0 = Senin, 6 = Minggu
#     start_of_week = selected_date - timedelta(days=selected_date.weekday())
#     end_of_week = start_of_week + timedelta(days=6)

#     try:
#         # --- A. QUERY CHART MINGGUAN ---
#         # Ambil semua history di minggu tersebut
#         histories_week = HistoryAktifitas.query.filter(
#             HistoryAktifitas.id_user == user_id,
#             func.date(HistoryAktifitas.tanggal) >= start_of_week.date(),
#             func.date(HistoryAktifitas.tanggal) <= end_of_week.date()
#         ).all()

#         # Inisialisasi array 7 hari (Senin - Minggu) dengan nilai 0
#         weekly_data = [0, 0, 0, 0, 0, 0, 0]
        
#         for h in histories_week:
#             # Cari index hari (0 untuk Senin, dst)
#             day_index = h.tanggal.weekday()
#             # Tambahkan durasi (konversi detik ke menit)
#             durasi_menit = (h.durasi_total or 0) / 60.0
#             weekly_data[day_index] += durasi_menit

#         # Format agar 1 angka di belakang koma, atau bulatkan ke int
#         weekly_data = [round(val) for val in weekly_data]

#         # --- B. QUERY LATIHAN HARIAN (Pada tanggal yang dipilih) ---
#         histories_day = HistoryAktifitas.query.filter(
#             HistoryAktifitas.id_user == user_id,
#             func.date(HistoryAktifitas.tanggal) == selected_date.date()
#         ).order_by(HistoryAktifitas.tanggal.desc()).all()

#         harian_data = []
#         for hd in histories_day:
#             jadwal = hd.jadwal_latihan
#             nama_program = jadwal.nama_jadwal if jadwal else "Program Bebas"
#             url_gambar = jadwal.url_gambar if jadwal else "Program Bebas"
            
#             # Rangkum detail gerakan
#             detail_gerakan = []
            
#             for d in hd.details:
#                 detail_gerakan.append({
#                     "nama_latihan": d.latihan_ref.nama_latihan if d.latihan_ref else "Gerakan",
#                     "sisi": d.sisi,
#                     "akurasi": d.akurasi_latihan,
#                     "repetisi": d.repetisi_tercapai
#                 })

#             harian_data.append({
#                 "id_history": hd.id_history,
#                 "nama_program": nama_program,
#                 "waktu": hd.tanggal.strftime("%H:%M"),
#                 "durasi_menit": round((hd.durasi_total or 0) / 60.0),
#                 "akurasi_total": hd.akurasi_total,
#                 "url_gambar": url_gambar,
#                 "detail_gerakan": detail_gerakan
#             })

#         # --- C. RESPONSE JSON ---
#         return jsonify({
#             "success": True,
#             "data": {
#                 "selected_date": selected_date.strftime("%Y-%m-%d"),
#                 "mingguan": {
#                     "label": ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"],
#                     "data": weekly_data
#                 },
#                 "harian": harian_data
#             }
#         }), 200

#     except Exception as e:
#         return jsonify({"success": False, "error": str(e)}), 500



# @history_bp.route("/analitik", methods=["GET"])
# @jwt_required()
# def get_analitik():
#     user_id = str(get_jwt_identity())
    
#     # 1. Ambil query parameter 'date' (Format: YYYY-MM-DD)
#     date_str = request.args.get('date')
#     if date_str:
#         try:
#             selected_date = datetime.strptime(date_str, "%Y-%m-%d")
#         except ValueError:
#             return jsonify({"success": False, "message": "Format tanggal salah. Gunakan YYYY-MM-DD"}), 400
#     else:
#         selected_date = datetime.utcnow()

#     # 2. Hitung range minggu (Senin - Minggu)
#     start_of_week = selected_date - timedelta(days=selected_date.weekday())
#     end_of_week = start_of_week + timedelta(days=6)

#     try:
#         # =====================================================
#         # A. DATA MINGGUAN
#         # =====================================================
#         histories_week = HistoryAktifitas.query.filter(
#             HistoryAktifitas.id_user == user_id,
#             func.date(HistoryAktifitas.tanggal) >= start_of_week.date(),
#             func.date(HistoryAktifitas.tanggal) <= end_of_week.date()
#         ).all()

#         # Durasi
#         weekly_duration = [0, 0, 0, 0, 0, 0, 0]

#         # Delta VAS
#         weekly_vas_total = [0, 0, 0, 0, 0, 0, 0]
#         weekly_vas_count = [0, 0, 0, 0, 0, 0, 0]

#         for h in histories_week:
#             idx = h.tanggal.weekday()

#             # Durasi
#             durasi_menit = (h.durasi_total or 0) / 60.0
#             weekly_duration[idx] += durasi_menit

#             # Delta VAS
#             if h.delta_vas is not None:
#                 weekly_vas_total[idx] += h.delta_vas
#                 weekly_vas_count[idx] += 1

#         # Format durasi
#         weekly_duration = [round(val) for val in weekly_duration]

#         # Rata-rata delta VAS
#         weekly_vas_avg = [
#             round(weekly_vas_total[i] / weekly_vas_count[i], 2) if weekly_vas_count[i] > 0 else 0
#             for i in range(7)
#         ]

#         # =====================================================
#         # B. DATA HARIAN
#         # =====================================================
#         histories_day = HistoryAktifitas.query.filter(
#             HistoryAktifitas.id_user == user_id,
#             func.date(HistoryAktifitas.tanggal) == selected_date.date()
#         ).order_by(HistoryAktifitas.tanggal.desc()).all()

#         harian_data = []

#         for hd in histories_day:
#             jadwal = hd.jadwal_latihan
#             nama_program = jadwal.nama_jadwal if jadwal else "Program Bebas"
#             url_gambar = jadwal.url_gambar if jadwal else None

#             detail_gerakan = []
#             for d in hd.details:
#                 detail_gerakan.append({
#                     "nama_latihan": d.latihan_ref.nama_latihan if d.latihan_ref else "Gerakan",
#                     "sisi": d.sisi,
#                     "akurasi": d.akurasi_latihan,
#                     "repetisi": d.repetisi_tercapai
#                 })

#             harian_data.append({
#                 "id_history": hd.id_history,
#                 "nama_program": nama_program,
#                 "waktu": hd.tanggal.strftime("%H:%M"),
#                 "durasi_menit": round((hd.durasi_total or 0) / 60.0),
#                 "akurasi_total": hd.akurasi_total,

#                 # 🔥 KUNCI CLINICAL
#                 "vas_sebelum": hd.vas_sebelum,
#                 "vas_sesudah": hd.vas_sesudah,
#                 "delta_vas": hd.delta_vas,
#                 "status": hd.status,
#                 "rekomendasi": hd.rekomendasi,

#                 "url_gambar": url_gambar,
#                 "detail_gerakan": detail_gerakan
#             })

#         # =====================================================
#         # C. SUMMARY HARIAN
#         # =====================================================
#         total_sesi = len(histories_day)

#         valid_delta = [h.delta_vas for h in histories_day if h.delta_vas is not None]
#         avg_delta = round(sum(valid_delta) / len(valid_delta), 2) if valid_delta else None

#         # =====================================================
#         # D. RESPONSE
#         # =====================================================
#         return jsonify({
#             "success": True,
#             "data": {
#                 "selected_date": selected_date.strftime("%Y-%m-%d"),

#                 "mingguan": {
#                     "label": ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"],
#                     "durasi": weekly_duration,
#                     "rata_delta_vas": weekly_vas_avg
#                 },

#                 "summary": {
#                     "total_sesi": total_sesi,
#                     "rata_delta_vas": avg_delta
#                 },

#                 "harian": harian_data
#             }
#         }), 200

#     except Exception as e:
#         return jsonify({
#             "success": False,
#             "message": "Terjadi kesalahan",
#             "error": str(e)
#         }), 500

@history_bp.route("/analitik", methods=["GET"])
@jwt_required()
def get_analitik():
    user_id = str(get_jwt_identity())
    
    # 1. Ambil query parameter 'date'
    date_str = request.args.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({
                "success": False,
                "message": "Format tanggal salah. Gunakan YYYY-MM-DD"
            }), 400
    else:
        selected_date = datetime.utcnow()

    # 2. Range minggu (Senin - Minggu)
    start_of_week = selected_date - timedelta(days=selected_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    try:
        # =====================================================
        # A. DATA MINGGUAN
        # =====================================================
        histories_week = HistoryAktifitas.query.filter(
            HistoryAktifitas.id_user == user_id,
            func.date(HistoryAktifitas.tanggal) >= start_of_week.date(),
            func.date(HistoryAktifitas.tanggal) <= end_of_week.date()
        ).all()

        # Durasi & VAS
        weekly_duration = [0] * 7
        weekly_vas_total = [0] * 7
        weekly_vas_count = [0] * 7

        for h in histories_week:
            idx = h.tanggal.weekday()  # 0 = Senin

            # Durasi (menit)
            durasi_menit = (h.durasi_total or 0) / 60.0
            weekly_duration[idx] += durasi_menit

            # ✅ PAKAI vas_sesudah (FIX)
            if h.vas_sesudah is not None:
                weekly_vas_total[idx] += h.vas_sesudah
                weekly_vas_count[idx] += 1

        # Format durasi
        weekly_duration = [round(val) for val in weekly_duration]

        # Rata-rata VAS per hari
        weekly_vas_avg = [
            round(weekly_vas_total[i] / weekly_vas_count[i], 2)
            if weekly_vas_count[i] > 0 else 0
            for i in range(7)
        ]

        # =====================================================
        # B. DATA HARIAN
        # =====================================================
        histories_day = HistoryAktifitas.query.filter(
            HistoryAktifitas.id_user == user_id,
            func.date(HistoryAktifitas.tanggal) == selected_date.date()
        ).order_by(HistoryAktifitas.tanggal.desc()).all()

        harian_data = []

        for hd in histories_day:
            jadwal = hd.jadwal_latihan

            detail_gerakan = [
                {
                    "nama_latihan": d.latihan_ref.nama_latihan if d.latihan_ref else "Gerakan",
                    "sisi": d.sisi,
                    "akurasi": d.akurasi_latihan,
                    "repetisi": d.repetisi_tercapai
                }
                for d in hd.details
            ]

            harian_data.append({
                "id_history": hd.id_history,
                "nama_program": jadwal.nama_jadwal if jadwal else "Program Bebas",
                "waktu": hd.tanggal.strftime("%H:%M"),
                "durasi_menit": round((hd.durasi_total or 0) / 60.0),
                "akurasi_total": hd.akurasi_total,

                # ✅ DATA CLINICAL (dipakai Flutter)
                "vas_sebelum": hd.vas_sebelum,
                "vas_sesudah": hd.vas_sesudah,
                "delta_vas": hd.delta_vas,
                "status": hd.status,
                "rekomendasi": hd.rekomendasi,

                "url_gambar": jadwal.url_gambar if jadwal else None,
                "detail_gerakan": detail_gerakan
            })

        # =====================================================
        # C. SUMMARY HARIAN (PAKAI vas_sesudah)
        # =====================================================
        total_sesi = len(histories_day)

        valid_vas = [h.vas_sesudah for h in histories_day if h.vas_sesudah is not None]
        avg_vas = round(sum(valid_vas) / len(valid_vas), 2) if valid_vas else None

        # =====================================================
        # D. RESPONSE
        # =====================================================
        return jsonify({
            "success": True,
            "data": {
                "selected_date": selected_date.strftime("%Y-%m-%d"),

                "mingguan": {
                    "label": ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"],
                    "durasi": weekly_duration,
                    "rata_vas_sesudah": weekly_vas_avg   # ✅ FIX
                },

                "summary": {
                    "total_sesi": total_sesi,
                    "rata_vas_sesudah": avg_vas          # ✅ FIX
                },

                "harian": harian_data
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Terjadi kesalahan",
            "error": str(e)
        }), 500
