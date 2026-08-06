from app import create_app, db
from models import RehabRuleBagian

def run():
    app = create_app()
    with app.app_context():
        rules = RehabRuleBagian.query.all()
        for rule in rules:
            print(f'Updating {rule.id_bagian}: max_durasi_minggu_home from {rule.max_durasi_minggu_home} to 4')
            rule.max_durasi_minggu_home = 4
        db.session.commit()
        print('Berhasil update max_durasi_minggu_home ke 4')

if __name__ == '__main__':
    run()
