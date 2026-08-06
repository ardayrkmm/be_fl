from app import create_app
from models import db
from models import Question, QuestionOption, RehabRuleBagian, KlinisThresholdBagian, BagianTubuh
import uuid

app = create_app()
with app.app_context():
    # 1. Update max_durasi_minggu_home sesuai permintaan
    mapping_minggu = {
        "pinggul": 2,
        "paha": 3,
        "lutut": 3,
        "tungkai bawah": 2,
        "ankle": 1,
        "engkel": 1,
        "kaki": 2
    }
    
    bagians = BagianTubuh.query.all()
    for b in bagians:
        if b.nama_bagian and b.nama_bagian.lower() in mapping_minggu:
            rule = RehabRuleBagian.query.filter_by(id_bagian=b.id_bagian).first()
            if rule:
                max_m = mapping_minggu[b.nama_bagian.lower()]
                rule.max_durasi_minggu_home = max_m
                print(f"Updated max_durasi_minggu_home for {b.nama_bagian} to {max_m} minggu.")
        
    thresholds = KlinisThresholdBagian.query.all()
    for t in thresholds:
        t.batas_durasi_kronis = 5
        
    # 2. Update Opsi Pertanyaan Durasi Nyeri
    qs = Question.query.filter(Question.category == 'DURASI_NYERI').all()
    print("Found DURASI_NYERI questions:", len(qs))
    for q in qs:
        # Hapus option lama
        for opt in q.options:
            db.session.delete(opt)
        
        # Buat option baru (3 opsi sesuai permintaan)
        opt1 = QuestionOption(id=str(uuid.uuid4())[:8], key="<2", label="Kurang dari 2 minggu", nilai=1, question_id=q.id)
        opt2 = QuestionOption(id=str(uuid.uuid4())[:8], key="2-4", label="2 - 4 minggu", nilai=4, question_id=q.id)
        opt3 = QuestionOption(id=str(uuid.uuid4())[:8], key=">4", label="Lebih dari 4 minggu", nilai=7, question_id=q.id)
        
        db.session.add_all([opt1, opt2, opt3])
        print("Updated options for question:", q.title)
        
    db.session.commit()
    print("DB Updated Successfully.")
