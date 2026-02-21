from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

# Initialize extensions here to avoid circular imports
socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')
# db is already initialized in models.py, but good practice to have extensions central.
# keeping existing db in models.py for now to avoid breaking changes.
