from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import bcrypt
import os
import binascii
import random
import string

db = SQLAlchemy()

# --- Helper Functions ---
def generate_random_id(length=4):
    charset = string.ascii_uppercase + string.digits
    return "".join(random.choice(charset) for _ in range(length))

# --- Models ---

class User(db.Model):
    __tablename__ = "users"
    id_user = db.Column(db.String(4), primary_key=True)
    nama = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    role = db.Column(db.String(50))
    no_telepon = db.Column(db.String(50))
    verifikasi_status = db.Column(db.Integer)
    password = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    img_url = db.Column(db.String(255), nullable=True)
    fcm_token = db.Column(db.String(255), nullable=True)
    # Relationships
    jadwal_latihan = relationship("JadwalLatihanUser", backref="user")
    kondisi_user = relationship("KondisiUser", backref="user")
    history_user = relationship("HistoryAktifitas", backref="user")
    notifikasi = relationship("Notifikasi", backref="user")

    def check_password(self, password):
        return bcrypt.checkpw(password.encode(), self.password.encode())

    def to_public_user(self):
        return {
            "id_user": self.id_user,
            "nama": self.nama,
            "email": self.email,
            "role": self.role,
            "no_telepon": self.no_telepon,
            "verifikasi_status": self.verifikasi_status,
            "img_url": self.img_url if self.img_url else 'uploads/pl.jpg',
        }

@event.listens_for(User, "before_insert")
def before_insert_user(mapper, connection, target):
    if not target.id_user:
        target.id_user = binascii.hexlify(os.urandom(2)).decode()
    hashed = bcrypt.hashpw(target.password.encode(), bcrypt.gensalt())
    target.password = hashed.decode()

# class BagianTubuh(db.Model):
#     __tablename__ = "bagian_tubuhs"
#     id_bagian = db.Column(db.String(4), primary_key=True)
#     model_key = db.Column(db.String(50))
#     nama_bagian = db.Column(db.String(255))


# # FaseRehabilitasi dihapus — tidak dipakai di controller manapun

# # class Latihan(db.Model):
# #     __tablename__ = "latihans"
# #     id_latihan = db.Column(db.String(8), primary_key=True)
# #     nama_latihan = db.Column(db.String(255))  # Seperti: 'Lying Leg', 'Heel Slide'

# #     # Parameter Decision Table
# #     level = db.Column(db.Integer)
    
# #     # Tambahan Parameter Protokol
# #     hold_detik = db.Column(db.Integer, nullable=True)  # Tahan di posisi puncak
# #     rest_repetisi_detik = db.Column(db.Integer, nullable=False, default=10)
# #     rest_set_detik = db.Column(db.Integer, nullable=False, default=5)

# #     # DATA TEKNIS (Dulu di ListVideoLatihan)
# #     video_url = db.Column(db.String(255))
# #     url_gambar = db.Column(db.String(255)) # Thumbnail
# #     target_set = db.Column(db.Integer)
# #     target_repetisi = db.Column(db.Integer, nullable=True) # Untuk gerakan repitisi
# #     target_waktu = db.Column(db.Float, nullable=True)      # Untuk gerakan waktu/detik
# #     is_unilateral = db.Column(db.Boolean, nullable=False, default=False)
# #     deskripsi = db.Column(db.Text)
# #     created_at = db.Column(db.DateTime, default=datetime.utcnow)

# #     # Many-to-many ke BagianTubuh via LatihanBagian
# #     # Satu latihan bisa dipakai di banyak sendi (lutut, ankle, dst)
# #     bagian_list = relationship("LatihanBagian", back_populates="latihan", cascade="all, delete-orphan")

# class Latihan(db.Model):
#     __tablename__ = "latihans"

#     id_latihan = db.Column(db.String(8), primary_key=True)
#     nama_latihan = db.Column(db.String(255))

#     video_url = db.Column(db.String(255))
#     url_gambar = db.Column(db.String(255))
#     deskripsi = db.Column(db.Text)
#     level = db.Column(db.Integer)

   
#     is_unilateral = db.Column(db.Boolean)

#     bagian_list = relationship("LatihanBagian", back_populates="latihan", cascade="all, delete-orphan")

# class LatihanBagian(db.Model):
#     __tablename__ = "latihan_bagians"

#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     id_latihan = db.Column(db.String(8), db.ForeignKey("latihans.id_latihan"), nullable=False)
#     id_bagian = db.Column(db.String(4), db.ForeignKey("bagian_tubuhs.id_bagian"), nullable=False)

#     latihan = relationship("Latihan", back_populates="bagian_list")
#     bagian = relationship("BagianTubuh")

#     # Pastikan satu latihan tidak didaftarkan dua kali ke sendi yang sama
#     __table_args__ = (
#         db.UniqueConstraint("id_latihan", "id_bagian", name="uq_latihan_bagian"),
#     )
# class LatihanRuleBagian(db.Model):
#     __tablename__ = "latihan_rule_bagian"

#     id = db.Column(db.Integer, primary_key=True)

#     id_latihan = db.Column(db.String(8), db.ForeignKey("latihans.id_latihan"))
#     id_bagian = db.Column(db.String(4), db.ForeignKey("bagian_tubuhs.id_bagian"))

#     # === 6 kolom FULL pindahan dari latihans ===
#     target_set = db.Column(db.Integer)
#     target_repetisi = db.Column(db.Integer)
#     target_waktu = db.Column(db.Integer)

#     hold_detik = db.Column(db.Integer)
#     rest_repetisi_detik = db.Column(db.Integer)
#     rest_set_detik = db.Column(db.Integer)

# class RehabRuleBagian(db.Model):
#     __tablename__ = "rehab_rule_bagian"

#     id = db.Column(db.Integer, primary_key=True)
#     id_bagian = db.Column(db.String(4), db.ForeignKey("bagian_tubuhs.id_bagian"))

#     sessions_per_week = db.Column(db.Integer, default=6)
#     max_durasi_minggu_home = db.Column(db.Integer, default=3)
    


# class KlinisThresholdBagian(db.Model):
#     __tablename__ = "klinis_threshold_bagians"
    
#     id_bagian = db.Column(db.String(4), db.ForeignKey("bagian_tubuhs.id_bagian"), primary_key=True)
    
#     # Aturan red flag otomatis
#     batas_nyeri_ekstrem = db.Column(db.Integer, default=8)
#     batas_durasi_kronis = db.Column(db.Integer, default=12)
    
#     # Aturan fase & rekomendasi (Dynamic)
#     batas_nyeri_mandiri = db.Column(db.Integer, default=4)

#     bagian = relationship("BagianTubuh", backref="klinis_threshold")


# class KondisiUser(db.Model):
#     __tablename__ = "kondisi_users"

#     id_form = db.Column(db.String(4), primary_key=True)

#     # Relasi user & lokasi sendi
#     id_user = db.Column(db.String(4), db.ForeignKey("users.id_user"))
#     id_bagian = db.Column(db.String(4), db.ForeignKey("bagian_tubuhs.id_bagian"))

#     # Asesmen nyeri utama
#     tingkat_nyeri = db.Column(db.Integer)       # Skala VAS 0–10
#     durasi_nyeri_minggu = db.Column(db.Integer)  # Lama keluhan dalam minggu

    
#     has_red_flag = db.Column(db.Boolean, default=False)
#     red_flag_detail = db.Column(JSON, nullable=True)

#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

   


# class JadwalLatihanUser(db.Model):
#     __tablename__ = "jadwal_latihan_users"

#     id_jadwal = db.Column(db.String(8), primary_key=True)
#     id_user = db.Column(db.String(4), db.ForeignKey("users.id_user"))
#     id_form = db.Column(db.String(4), db.ForeignKey("kondisi_users.id_form"))

#     # 🔥 BARU
#     fase = db.Column(db.String(4))           # F1 / F2 / F3
#     fase_label = db.Column(db.String(100))  # Fase 1 (Akut)
#     url_gambar = db.Column(db.String(255))
#     nama_jadwal = db.Column(db.String(255))
#     tanggal = db.Column(db.DateTime)
#     status = db.Column(db.String(50), default="Locked")
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     details = relationship(
#         "JadwalLatihanDetail",
#         backref="parent_jadwal",
#         cascade="all, delete-orphan"
#     )
#     history_aktifitas = relationship(
#         "HistoryAktifitas", 
#         backref="jadwal_latihan",
#         cascade="all, delete-orphan"
#     )

# class JadwalLatihanDetail(db.Model):
#     __tablename__ = "jadwal_latihan_details"
#     id_detail = db.Column(db.String(8), primary_key=True)
#     id_jadwal = db.Column(db.String(8), db.ForeignKey("jadwal_latihan_users.id_jadwal"))
#     id_latihan = db.Column(db.String(8), db.ForeignKey("latihans.id_latihan"))
    
#     # Menandai sisi gerakan untuk MediaPipe
#     sisi = db.Column(db.String(10), nullable=True) # "Kanan", "Kiri", atau NULL
#     urutan = db.Column(db.Integer)
#     status_eksekusi = db.Column(db.Boolean, default=False)

#     latihan = relationship("Latihan")

# class HistoryAktifitas(db.Model):
#     __tablename__ = "history_aktifitas"
    
#     id_history = db.Column(db.String(8), primary_key=True)
#     id_user = db.Column(db.String(4), db.ForeignKey("users.id_user"))
#     id_jadwal = db.Column(db.String(8), db.ForeignKey("jadwal_latihan_users.id_jadwal"))

#     tanggal = db.Column(db.DateTime, default=datetime.utcnow)

#     # Rangkuman total 1 sesi jadwal
#     durasi_total = db.Column(db.Float)   # Total waktu seluruh jadwal (detik)
#     akurasi_total = db.Column(db.Float)  # Rata-rata akurasi semua latihan (%)

#     # Status sesi: 'done' | 'warning' | 'stop'
#     # done    → selesai normal
#     # warning → vas naik signifikan, perlu evaluasi
#     # stop    → dihentikan karena nyeri berlebihan
#     status = db.Column(db.String(20), default="done")

#     # Tracking VAS (nyeri) sebelum & sesudah latihan
#     vas_sebelum = db.Column(db.Integer, nullable=True)
#     vas_sesudah = db.Column(db.Integer, nullable=True)
#     delta_vas = db.Column(db.Integer, nullable=True)   # Positif = nyeri naik, negatif = membaik
#     rekomendasi = db.Column(db.String(255), nullable=True)

#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     # Relasi ke detail (tiap latihan)
#     details = relationship(
#         "HistoryAktifitasDetail", 
#         backref="parent_history", 
#         cascade="all, delete-orphan"
#     )

# class HistoryAktifitasDetail(db.Model):
#     __tablename__ = "history_aktifitas_details"
    
#     id_history_detail = db.Column(db.String(8), primary_key=True)
#     id_history = db.Column(db.String(8), db.ForeignKey("history_aktifitas.id_history"))
    
#     # Menunjuk ke latihan apa yang direkam
#     id_latihan = db.Column(db.String(8), db.ForeignKey("latihans.id_latihan"))
#     sisi = db.Column(db.String(10), nullable=True) # "Kanan" / "Kiri" (opsional, jika unilateral)
#     latihan_ref = relationship("Latihan")
    
#     # 🎯 HASIL DARI TIAP LATIHAN (Ringkas & khusus breakdown)
#     repetisi_tercapai = db.Column(db.Integer, default=0)
#     akurasi_latihan = db.Column(db.Float)  # Akurasi spesifik gerakan ini
# =========================
# BAGIAN TUBUH
# =========================
class BagianTubuh(db.Model):
    __tablename__ = "bagian_tubuhs"

    id_bagian = db.Column(db.String(4), primary_key=True)
    model_key = db.Column(db.String(50))
    nama_bagian = db.Column(db.String(255))


# =========================
# LATIHAN
# =========================
class Latihan(db.Model):
    __tablename__ = "latihans"

    id_latihan = db.Column(db.String(8), primary_key=True)
    nama_latihan = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    url_gambar = db.Column(db.String(255))
    deskripsi = db.Column(db.Text)
    level = db.Column(db.Integer)
    is_unilateral = db.Column(db.Boolean)

    bagian_list = relationship("LatihanBagian", back_populates="latihan", cascade="all, delete-orphan")


class LatihanBagian(db.Model):
    __tablename__ = "latihan_bagians"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_latihan = db.Column(db.String(8), db.ForeignKey("latihans.id_latihan"))
    id_bagian = db.Column(db.String(4), db.ForeignKey("bagian_tubuhs.id_bagian"))

    latihan = relationship("Latihan", back_populates="bagian_list")
    bagian = relationship("BagianTubuh")
    target_set = db.Column(db.Integer, default=3)

    target_repetisi = db.Column(db.Integer, default=10)

    target_waktu = db.Column(db.Integer, nullable=True)

    hold_detik = db.Column(db.Integer, default=5)

    rest_repetisi_detik = db.Column(db.Integer, default=10)

    rest_set_detik = db.Column(db.Integer, default=30)

    # =====================
    # PROGRESSION
    # =====================

    progression_repetisi = db.Column(db.Integer, default=2)

    progression_hold = db.Column(db.Integer, default=5)

    __table_args__ = (
        db.UniqueConstraint("id_latihan", "id_bagian", name="uq_latihan_bagian"),
    )




# =========================
# REHAB RULE
# =========================
class RehabRuleBagian(db.Model):
    __tablename__ = "rehab_rule_bagian"

    id = db.Column(db.Integer, primary_key=True)
    id_bagian = db.Column(db.String(4), db.ForeignKey("bagian_tubuhs.id_bagian"))

    sessions_per_week = db.Column(db.Integer, default=6)
    max_durasi_minggu_home = db.Column(db.Integer, default=3)
    progression_interval_session = db.Column(
        db.Integer,
        default=2
    )


# =========================
# KLINIS THRESHOLD
# =========================
class KlinisThresholdBagian(db.Model):
    __tablename__ = "klinis_threshold_bagians"

    id_bagian = db.Column(db.String(4), db.ForeignKey("bagian_tubuhs.id_bagian"), primary_key=True)

    batas_nyeri_ekstrem = db.Column(db.Integer, default=8)
    batas_durasi_kronis = db.Column(db.Integer, default=12)
    batas_nyeri_mandiri = db.Column(db.Integer, default=4)


# =========================
# KONDISI USER
# =========================
class KondisiUser(db.Model):
    __tablename__ = "kondisi_users"

    id_form = db.Column(db.String(4), primary_key=True)
    id_user = db.Column(db.String(4), db.ForeignKey("users.id_user"))
    id_bagian = db.Column(db.String(4), db.ForeignKey("bagian_tubuhs.id_bagian"))

    tingkat_nyeri = db.Column(db.Integer)
    durasi_nyeri_minggu = db.Column(db.Integer)

    has_red_flag = db.Column(db.Boolean, default=False)
    red_flag_detail = db.Column(JSON, nullable=True)

    # 🔥 EXTENSION
    session_count = db.Column(db.Integer, default=0)
    last_session_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =========================
# JADWAL LATIHAN
# =========================
class JadwalLatihanUser(db.Model):
    __tablename__ = "jadwal_latihan_users"

    id_jadwal = db.Column(db.String(8), primary_key=True)
    id_user = db.Column(db.String(4), db.ForeignKey("users.id_user"))
    id_form = db.Column(db.String(4), db.ForeignKey("kondisi_users.id_form"))

    fase = db.Column(db.String(4))
    fase_label = db.Column(db.String(100))
    url_gambar = db.Column(db.String(255))
    nama_jadwal = db.Column(db.String(255))
    tanggal = db.Column(db.DateTime)
    status = db.Column(db.String(50), default="Locked")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 🔥 EXTENSION
    screening_stage = db.Column(db.Integer, default=1)

    details = relationship("JadwalLatihanDetail", backref="parent_jadwal", cascade="all, delete-orphan")
    # History harus tetap tersimpan walaupun program/jadwal ditutup.
    # Untuk switch area gunakan soft close via status, bukan hard delete jadwal.
    history_aktifitas = relationship(
        "HistoryAktifitas",
        backref="jadwal_latihan",
        cascade="save-update, merge",
        passive_deletes=True
    )


class JadwalLatihanDetail(db.Model):
    __tablename__ = "jadwal_latihan_details"

    id_detail = db.Column(db.String(8), primary_key=True)
    id_jadwal = db.Column(db.String(8), db.ForeignKey("jadwal_latihan_users.id_jadwal"))
    id_latihan = db.Column(db.String(8), db.ForeignKey("latihans.id_latihan"))

    sisi = db.Column(db.String(10))
    urutan = db.Column(db.Integer)
    status_eksekusi = db.Column(db.Boolean, default=False)

    latihan = relationship("Latihan")

    # 🔥 EXTENSION
    current_target_repetisi = db.Column(db.Integer)
    current_target_set = db.Column(db.Integer)


# =========================
# HISTORY
# =========================
class HistoryAktifitas(db.Model):
    __tablename__ = "history_aktifitas"

    id_history = db.Column(db.String(8), primary_key=True)
    id_user = db.Column(db.String(4), db.ForeignKey("users.id_user"))
    id_jadwal = db.Column(db.String(8), db.ForeignKey("jadwal_latihan_users.id_jadwal"))

    tanggal = db.Column(db.DateTime, default=datetime.utcnow)

    durasi_total = db.Column(db.Float)
    akurasi_total = db.Column(db.Float)
    status = db.Column(db.String(20), default="done")
    action_result = db.Column(db.String(50))  # "progression", "maintain", "regression" 
    vas_sebelum = db.Column(db.Integer)
    vas_sesudah = db.Column(db.Integer)
    delta_vas = db.Column(db.Integer)
    rekomendasi = db.Column(db.String(255))

    # 🔥 EXTENSION
    decision_flag = db.Column(db.String(50))

    details = relationship("HistoryAktifitasDetail", backref="parent_history", cascade="all, delete-orphan")


class HistoryAktifitasDetail(db.Model):
    __tablename__ = "history_aktifitas_details"

    id_history_detail = db.Column(db.String(8), primary_key=True)
    id_history = db.Column(db.String(8), db.ForeignKey("history_aktifitas.id_history"))
    id_latihan = db.Column(db.String(8), db.ForeignKey("latihans.id_latihan"))

    sisi = db.Column(db.String(10))
    repetisi_tercapai = db.Column(db.Integer, default=0)
    akurasi_latihan = db.Column(db.Float)

    latihan_ref = relationship("Latihan")

class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.String(10), primary_key=True)
    title = db.Column(db.String(255))
    subtitle = db.Column(db.String(255))
    multiSelect = db.Column(db.Boolean)
    category = db.Column(db.String(50))


    # Context-aware: filter pertanyaan berdasarkan sendi yang dipilih user
    # NULL  → pertanyaan umum, ditampilkan untuk SEMUA sendi
    # KNEE  → khusus lutut
    # ANKL  → khusus ankle
    # Scalable: cukup tambah id_bagian baru di BagianTubuh untuk sendi baru
    id_bagian = db.Column(db.String(4), db.ForeignKey("bagian_tubuhs.id_bagian"), nullable=True)

    urutan = db.Column(db.Integer, nullable=True)  # Urutan tampil dalam kuesioner

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    options = relationship("QuestionOption", backref="question", cascade="all, delete-orphan")

class QuestionOption(db.Model):
    __tablename__ = "question_options"
    id = db.Column(db.String(10), primary_key=True)
    question_id = db.Column(db.String(10), db.ForeignKey("questions.id"))
    
    key = db.Column(db.String(50))  # 🔥 WAJIB
    nilai = db.Column(db.Integer)
    label = db.Column(db.String(255))

class Notifikasi(db.Model):
    __tablename__ = "notifikasi"

    id_notifikasi = db.Column(db.String(4), primary_key=True)
    id_user = db.Column(db.String(4), db.ForeignKey("users.id_user"))

    judul = db.Column(db.String(255))
    pesan = db.Column(db.Text)
    tipe = db.Column(db.String(50))

    status_baca = db.Column(db.Boolean, default=False)

    # 🔥 BARU (CORE REMINDER SYSTEM)
    jadwal_kirim = db.Column(db.DateTime, nullable=True)
    is_sent = db.Column(db.Boolean, default=False)
    id_jadwal = db.Column(db.String(8), db.ForeignKey("jadwal_latihan_users.id_jadwal"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

