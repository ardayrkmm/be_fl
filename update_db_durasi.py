from app import create_app
from models import db, Question, QuestionOption
import uuid

def new_id():
    return str(uuid.uuid4())[:8]

def run_update():
    app = create_app()
    with app.app_context():
        # Cari pertanyaan durasi (category = DURASI_NYERI)
        q = Question.query.filter(Question.category == 'DURASI_NYERI').first()
        if not q:
            q = Question.query.filter(Question.title.like('%durasi%')).first()
            
        if q:
            print("Ditemukan pertanyaan:", q.title)
            # Hapus option lama
            for opt in q.options:
                db.session.delete(opt)
            db.session.commit()
            
            # Buat option baru
            opt1 = QuestionOption(id=new_id(), key="<2", label="Kurang dari 2 minggu", nilai=1, question_id=q.id)
            opt2 = QuestionOption(id=new_id(), key="2-4", label="2-4 minggu", nilai=4, question_id=q.id)
            opt3 = QuestionOption(id=new_id(), key=">4", label="Lebih dari 4 minggu", nilai=7, question_id=q.id)
            
            db.session.add_all([opt1, opt2, opt3])
            db.session.commit()
            print("Berhasil update opsi pertanyaan durasi nyeri.")
        else:
            print("Pertanyaan durasi tidak ditemukan.")

if __name__ == '__main__':
    run_update()
