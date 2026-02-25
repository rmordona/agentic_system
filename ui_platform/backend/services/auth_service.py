from passlib.context import CryptContext
from auth.jwt import create_access_token, create_refresh_token

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def generate_tokens(user_id: int, username: str):
    access_token = create_access_token({"sub": str(user_id), "username": username})
    refresh_token = create_refresh_token({"sub": str(user_id)})
    return access_token, refresh_token
