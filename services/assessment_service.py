from models import db
from models import KondisiUser, generate_random_id

# Helper: Hitung kategori VAS tanpa tabel VASNyeri
def get_vas_kategori(skor):
    if skor == 0:
        return "Tidak ada nyeri"
    elif 1 <= skor <= 2:
        return "Nyeri sangat ringan"
    elif 3 <= skor <= 4:
        return "Nyeri ringan"
    elif 5 <= skor <= 6:
        return "Nyeri sedang"
    elif 7 <= skor <= 8:
        return "Nyeri berat"
    elif skor >= 9:
        return "Nyeri sangat berat"
    return "Tidak valid"

class AssessmentService:
    @staticmethod
    def process_assessment(data):
        """
        Rule-Based Decision System:
          IF has_red_flag == True        → rujuk
          ELSE IF tingkat_nyeri 1–4     → latihan mandiri
          ELSE (>4)                     → rujuk
          IF durasi_nyeri_minggu > 3    → evaluasi lebih lanjut
        """
        try:
            tingkat_nyeri = data.get('tingkat_nyeri', 0)
            durasi_nyeri_minggu = data.get('durasi_nyeri_minggu', 0)

            # --- Red Flag Detection (universal, berbasis JSON) ---
            # Ambil semua kunci boolean red flag dari payload
            red_flag_keys = [
                'tidak_bisa_menapak', 'trauma_langsung',
                'bengkak_cepat_besar', 'demam_kemerahan',
                'nyeri_malam', 'lutut_locking', 'instabilitas'
            ]
            red_flag_detail = {k: data.get(k, False) for k in red_flag_keys if data.get(k, False)}
            has_red_flag = bool(red_flag_detail)

            # Tambahkan red flag otomatis jika nyeri > 7 atau durasi > 12 minggu
            if tingkat_nyeri >= 8:
                has_red_flag = True
                red_flag_detail['nyeri_ekstrem'] = True
            if durasi_nyeri_minggu and durasi_nyeri_minggu >= 12:
                has_red_flag = True
                red_flag_detail['durasi_kronis'] = True

            # --- Rule-Based Output ---
            if has_red_flag:
                rekomendasi = "rujuk"
                fase = None
            elif 1 <= tingkat_nyeri <= 4:
                rekomendasi = "latihan_mandiri"
                # Tentukan fase berdasarkan durasi
                if durasi_nyeri_minggu <= 1:
                    fase = 'F1'
                elif durasi_nyeri_minggu <= 3:
                    fase = 'F2'
                else:
                    fase = 'F3'
            else:
                rekomendasi = "rujuk"
                fase = None

            # Flag evaluasi tambahan jika durasi > 3 minggu
            perlu_evaluasi = (durasi_nyeri_minggu or 0) > 3

            # --- Simpan ke database ---
            id_form = generate_random_id(4)
            kondisi = KondisiUser(
                id_form=id_form,
                id_user=data.get('id_user'),
                id_bagian=data.get('id_bagian'),
                tingkat_nyeri=tingkat_nyeri,
                durasi_nyeri_minggu=durasi_nyeri_minggu,
                has_red_flag=has_red_flag,
                red_flag_detail=red_flag_detail if red_flag_detail else None,
            )

            db.session.add(kondisi)
            db.session.commit()

            return {
                "status": "success",
                "id_form": id_form,
                "fase": fase,
                "has_red_flag": has_red_flag,
                "red_flag_detail": red_flag_detail,
                "rekomendasi": rekomendasi,
                "perlu_evaluasi": perlu_evaluasi,
                "vas_kategori": get_vas_kategori(tingkat_nyeri),
                "message": "Assessment berhasil disimpan"
            }, 200

        except Exception as e:
            db.session.rollback()
            return {"status": "error", "message": str(e)}, 500
