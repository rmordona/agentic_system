from jose import jwt
from jose.exceptions import JWTError
from datetime import datetime, timedelta

from config import JWT_SECRET_KEY, JWT_REFRESH_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm="HS256")

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, algorithm="HS256")

def decode_access_token(token: str):
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])

def decode_refresh_token(token: str):
    return jwt.decode(token, JWT_REFRESH_SECRET_KEY, algorithms=["HS256"])
