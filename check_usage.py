import os
import re

columns = [
    "id_user", "nama", "email", "role", "no_telepon", "verifikasi_status", "password", "created_at", "img_url", "fcm_token",
    "id_bagian", "model_key", "nama_bagian",
    "id_latihan", "nama_latihan", "video_url", "url_gambar", "deskripsi", "level", "is_unilateral",
    "id", "target_set", "target_repetisi", "target_waktu", "hold_detik", "rest_repetisi_detik", "rest_set_detik",
    "sessions_per_week", "max_durasi_minggu_home", "progression_interval_session",
    "batas_nyeri_ekstrem", "batas_durasi_kronis", "batas_nyeri_mandiri",
    "id_form", "tingkat_nyeri", "durasi_nyeri_minggu", "has_red_flag", "red_flag_detail", "session_count", "last_session_date", "updated_at",
    "id_jadwal", "fase", "fase_label", "nama_jadwal", "tanggal", "status", "screening_stage",
    "id_detail", "sisi", "urutan", "status_eksekusi", "current_target_repetisi", "current_target_set",
    "id_history", "durasi_total", "akurasi_total", "action_result", "vas_sebelum", "vas_sesudah", "delta_vas", "rekomendasi", "decision_flag",
    "id_history_detail", "repetisi_tercapai", "akurasi_latihan",
    "title", "subtitle", "multiSelect", "category", "urutan",
    "question_id", "key", "nilai", "label",
    "id_notifikasi", "judul", "pesan", "tipe", "status_baca", "jadwal_kirim", "is_sent"
]

dirs_to_check = [
    r"d:\kmpl\Aplikasi\be_fl_fisio",
    r"d:\kmpl\Aplikasi\frontend_fisio"
]

usage_counts = {col: 0 for col in columns}

def check_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            for col in columns:
                if col in content:
                    # simplistic check, to be more robust we could use regex
                    # but simple string match is good for a start
                    matches = len(re.findall(r'\b' + re.escape(col) + r'\b', content))
                    usage_counts[col] += matches
    except Exception:
        pass

for d in dirs_to_check:
    for root, dirs, files in os.walk(d):
        if 'node_modules' in root or '.git' in root or 'venv' in root or '__pycache__' in root or '.dart_tool' in root or 'build' in root or 'migrations' in root:
            continue
        for file in files:
            # only check code files
            if file.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.dart', '.html', '.dart')):
                if file == 'models.py' or file == 'check_usage.py':
                    continue
                check_file(os.path.join(root, file))

print("Unused columns:")
for col, count in usage_counts.items():
    if count == 0:
        print(f"- {col}")
