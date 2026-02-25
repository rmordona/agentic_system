# password.py
from passlib.context import CryptContext

# Choose hashing scheme(s)
# bcrypt is still used but will safely handle long passwords
# Optionally, you can switch to argon2 for unlimited password length
pwd_context = CryptContext(
    schemes=["argon2"],  # or ["argon2"] if you want no 72-byte limit
    deprecated="auto"
)

MAX_BCRYPT_BYTES = 72  # bcrypt limitation

def hash_password(password: str) -> str:
    """
    Hash a plaintext password safely for storage.
    If using bcrypt, truncates to 72 bytes automatically.
    """
    if password is None:
        raise ValueError("Password cannot be None")

    # Encode to bytes and truncate if necessary (bcrypt limitation)
    truncated_password = password.encode("utf-8")[:MAX_BCRYPT_BYTES].decode("utf-8", errors="ignore")
    
    return pwd_context.hash(truncated_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored hash.
    Automatically handles truncation if bcrypt is used.
    """
    if plain_password is None:
        return False

    truncated_password = plain_password.encode("utf-8")[:MAX_BCRYPT_BYTES].decode("utf-8", errors="ignore")
    
    return pwd_context.verify(truncated_password, hashed_password)