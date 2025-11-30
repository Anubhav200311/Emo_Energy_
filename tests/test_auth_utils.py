import jwt
from datetime import timedelta

from app.utils.auth import hash_password, verify_password, create_access_token
from app.config import settings

def test_hash_and_verify_password_success():
    password = "UltraSecret!42"
    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password)


def test_create_access_token_contains_claims():
    token = create_access_token({"sub": "user-123"}, expires_delta=timedelta(minutes=5))
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert decoded["sub"] == "user-123"
    assert "exp" in decoded
