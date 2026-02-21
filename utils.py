# utils.py
from flask import abort

def to_int(val, default=0):
    try:
        return int(val)
    except:
        return default

def to_float(val, default=0.0):
    try:
        return float(val)
    except:
        return default

def require_user():
    from flask import g
    if not hasattr(g, "user_id") or not g.user_id:
        abort(401, description="Unauthorized")
    return g.user_id
