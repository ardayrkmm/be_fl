import json
from app import create_app
from models import db, User, KondisiUser
from services.schedule_service import ScheduleService

app = create_app()

with app.app_context():
    # take any user with a kondisi
    user = KondisiUser.query.first()
    if user:
        print("Testing with user:", user.id_user)
        data = {"id_user": user.id_user}
        try:
            res = ScheduleService.generate_schedule(data)
            print("Result:", res)
        except Exception as e:
            import traceback
            traceback.print_exc()
    else:
        print("No KondisiUser found.")
