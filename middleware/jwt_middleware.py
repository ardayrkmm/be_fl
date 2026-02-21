import os
from datetime import timedelta
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    get_jwt
)

from flask_jwt_extended import verify_jwt_in_request, get_jwt

def require_user():
    verify_jwt_in_request()
    claims = get_jwt()
    return claims.get("user_id")

def generate_token(user_id, email, name):
    additional_claims = {
        "email": email,
        "name": name
    }
    return create_access_token(
        identity=user_id,
        additional_claims=additional_claims,
        expires_delta=timedelta(hours=24)
    )


def get_user_id_from_jwt():
    return get_jwt_identity()
