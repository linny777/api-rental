import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
def register(body: schemas.RegisterRequest, db: Session = Depends(get_db)):
    if not EMAIL_RE.match(body.email):
        raise HTTPException(400, "Invalid email format")
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(400, "Email already registered")

    user = models.User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        phone_number=body.phone_number,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(user.id)}


@router.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    # Support login by email OR username
    login_val = body.email.strip()
    user = (
        db.query(models.User).filter(models.User.email == login_val).first()
        or db.query(models.User).filter(models.User.username == login_val).first()
    )
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")
    return {"access_token": create_access_token(user.id)}


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=schemas.UserOut)
def update_profile(
    body: schemas.UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if body.username is not None:
        current_user.username = body.username
    if body.phone_number is not None:
        current_user.phone_number = body.phone_number
    if body.avatar_path is not None:
        current_user.avatar_path = body.avatar_path
    db.commit()
    db.refresh(current_user)
    return current_user
