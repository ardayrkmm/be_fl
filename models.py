from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
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
        }

@event.listens_for(User, "before_insert")
def before_insert_user(mapper, connection, target):
    if not target.id_user:
        target.id_user = binascii.hexlify(os.urandom(2)).decode()
    hashed = bcrypt.hashpw(target.password.encode(), bcrypt.gensalt())
    target.password = hashed.decode()

class BagianTubuh(db.Model):
    __tablename__ = "bagian_tubuhs"
    id_bagian = db.Column(db.String(4), primary_key=True)
    nama_bagian = db.Column(db.String(255))
    latihan = db.relationship("Latihan", backref="bagian_tubuh")

class FaseRehabilitasi(db.Model):
    __tablename__ = "fase_rehabilitasi"
    id_fase = db.Column(db.String(4), primary_key=True)
    nama_fase = db.Column(db.String(255))
    min_hari = db.Column(db.Integer)
    max_hari = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Latihan(db.Model):
    __tablename__ = "latihans"
    id_latihan = db.Column(db.String(8), primary_key=True)
    nama_latihan = db.Column(db.String(255)) # Seperti: 'Lying Leg', 'Heel Slide'
    id_bagian = db.Column(db.String(4), db.ForeignKey("bagian_tubuhs.id_bagian"))
    
    # Parameter Decision Table
    level = db.Column(db.Integer)
    vas_min = db.Column(db.Integer)
    vas_max = db.Column(db.Integer)
    fase = db.Column(db.String(4)) # Bisa merujuk ke id_fase

    # DATA TEKNIS (Dulu di ListVideoLatihan)
    video_url = db.Column(db.String(255))
    url_gambar = db.Column(db.String(255)) # Thumbnail
    target_set = db.Column(db.Integer)
    target_repetisi = db.Column(db.Integer, nullable=True) # Untuk gerakan repitisi
    target_waktu = db.Column(db.Float, nullable=True)      # Untuk gerakan waktu/detik
    jumlah_sisi = db.Column(db.Integer, default=1)
    deskripsi = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    # jadwal_latihan = relationship("JadwalLatihanUser", backref="latihan")
    history_aktifitas = relationship("HistoryAktifitas", backref="latihan")

class KondisiUser(db.Model):
    __tablename__ = "kondisi_users"
    id_form = db.Column(db.String(4), primary_key=True)
    id_user = db.Column(db.String(4), db.ForeignKey("users.id_user"))
    id_bagian = db.Column(db.String(4), db.ForeignKey("bagian_tubuhs.id_bagian"))

    lama_nyeri_hari = db.Column(db.Integer)
    tingkat_nyeri = db.Column(db.Integer)
    jenis_keluhan = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    jadwal_latihan_user = relationship("JadwalLatihanUser", backref="kondisi_user")

class JadwalLatihanUser(db.Model):
    __tablename__ = "jadwal_latihan_users"

    id_jadwal = db.Column(db.String(8), primary_key=True)
    id_user = db.Column(db.String(4), db.ForeignKey("users.id_user"))
    id_form = db.Column(db.String(4), db.ForeignKey("kondisi_users.id_form"))

    # 🔥 BARU
    fase = db.Column(db.String(4))           # F1 / F2 / F3
    fase_label = db.Column(db.String(100))  # Fase 1 (Akut)
    url_gambar = db.Column(db.String(255))
    nama_jadwal = db.Column(db.String(255))
    tanggal = db.Column(db.DateTime)
    status = db.Column(db.String(50), default="Locked")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    details = relationship(
        "JadwalLatihanDetail",
        backref="parent_jadwal",
        cascade="all, delete-orphan"
    )

class JadwalLatihanDetail(db.Model):
    __tablename__ = "jadwal_latihan_details"
    id_detail = db.Column(db.String(8), primary_key=True)
    id_jadwal = db.Column(db.String(8), db.ForeignKey("jadwal_latihan_users.id_jadwal"))
    id_latihan = db.Column(db.String(8), db.ForeignKey("latihans.id_latihan"))
    
    # Menandai sisi gerakan untuk MediaPipe
    sisi = db.Column(db.String(10), nullable=True) # "Kanan", "Kiri", atau NULL
    urutan = db.Column(db.Integer)
    status_eksekusi = db.Column(db.Boolean, default=False)

    latihan = relationship("Latihan")

class HistoryAktifitas(db.Model):
    __tablename__ = "history_aktifitas"
    id_history_aktifitas = db.Column(db.String(4), primary_key=True)
    id_user = db.Column(db.String(4), db.ForeignKey("users.id_user"))
    id_latihan = db.Column(db.String(8), db.ForeignKey("latihans.id_latihan"))

    tanggal = db.Column(db.DateTime, default=datetime.utcnow)
    set_tercapai = db.Column(db.Integer)
    repetisi_tercapai = db.Column(db.Integer)
    durasi_aktual = db.Column(db.Float)
    nilai_akurasi = db.Column(db.Float)
    
    # Report detail untuk MediaPipe
    jumlah_gerakan_benar = db.Column(db.Integer, default=0)
    jumlah_gerakan_salah = db.Column(db.Integer, default=0)
    nilai_latihan = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.String(10), primary_key=True)
    title = db.Column(db.String(255))
    subtitle = db.Column(db.String(255))
    multiSelect = db.Column(db.Boolean)
    target_field = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    options = relationship("QuestionOption", backref="question")

class QuestionOption(db.Model):
    __tablename__ = "question_options"
    id = db.Column(db.String(10), primary_key=True)
    question_id = db.Column(db.String(10), db.ForeignKey("questions.id"))
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)