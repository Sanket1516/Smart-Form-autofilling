import jwt
from datetime import datetime, timedelta, UTC
from app.core.config import get_settings

def get_token():
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=60)
    data = {"sub": "test-user-123", "exp": expire}
    encoded_jwt = jwt.encode(data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

if __name__ == "__main__":
    print(get_token())
