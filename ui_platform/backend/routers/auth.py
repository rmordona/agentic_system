from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db import get_db
from models.user import User
from services.auth_service import hash_password, verify_password, generate_tokens
from auth.jwt import decode_refresh_token
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str
    # role: str = "user"

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str

@router.post("/signup", response_model=TokenResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    # Check if user/email exists
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # Create user
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    access, refresh = generate_tokens(user.id, user.username)
    return TokenResponse(access_token=access, refresh_token=refresh, username=user.username)

@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access, refresh = generate_tokens(user.id, user.username)
    return TokenResponse(access_token=access, refresh_token=refresh, username=user.username)

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_refresh_token(req.refresh_token)
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    access, refresh = generate_tokens(user.id, user.username)
    return TokenResponse(access_token=access, refresh_token=refresh, username=user.username)
