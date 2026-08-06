from app import create_app, db
from models import Question, QuestionOption, RehabRuleBagian
import uuid

def new_id():
    return str(uuid.uuid4())[:8]

def run():
    app = create_app()
    with app.app_context():
        # 1. Update max_durasi_minggu_home
        print("Mulai update max_durasi_minggu_home...")
        rules = RehabRuleBagian.query.all()
        for rule in rules:
            print(f'Updating area {rule.id_bagian}: max_durasi_minggu_home from {rule.max_durasi_minggu_home} to 4')
            rule.max_durasi_minggu_home = 4
        
        # 2. Update Opsi Pertanyaan Durasi Nyeri
        print("\nMulai update opsi DURASI_NYERI...")
        qs = Question.query.filter(Question.category == 'DURASI_NYERI').all()
        for q in qs:
            print(f"Updating Question ID: {q.id}, Text: {q.title}")
            # Hapus option lama
            for opt in q.options:
                db.session.delete(opt)
            
            # Buat option baru
            opt1 = QuestionOption(id=new_id(), key="<2", label="Kurang dari 2 minggu", nilai=1, question_id=q.id)
            opt2 = QuestionOption(id=new_id(), key="2-4", label="2-4 minggu", nilai=4, question_id=q.id)
            opt3 = QuestionOption(id=new_id(), key=">4", label="Lebih dari 4 minggu", nilai=7, question_id=q.id)
            
            db.session.add_all([opt1, opt2, opt3])
        
        db.session.commit()
        print("\nBerhasil! Semua data di database telah diupdate.")

if __name__ == '__main__':
    run()
