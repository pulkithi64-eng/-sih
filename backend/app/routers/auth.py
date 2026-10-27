from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..db import get_db
from ..config import get_settings
from ..models import User
from ..rate_limiter import login_limiter
from ..schemas import LoginRequest, PasswordChangeRequest, user_out
from ..security import (
    create_token,
    get_current_user,
    hash_password,
    inspect_token,
    validate_password_strength,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    username = body.username.strip()
    login_limiter.check_attempt(request, username)

    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is not None and not get_settings().demo_mode and verify_password("Demo@2026", user.password_hash):
        raise HTTPException(401, "Demo accounts are disabled outside demo mode")
    if user is None or not user.active or not verify_password(body.password, user.password_hash):
        lockout = login_limiter.record_failure(request, username)
        audit.record(
            db,
            username[:64] or "anonymous",
            "LOGIN_FAILED",
            "User",
            username[:64],
            {"reason": "invalid_credentials", "ip": request.client.host if request.client else "unknown"},
            actor_role="ANONYMOUS",
        )
        if lockout > 0:
            raise HTTPException(
                429,
                f"Too many failed login attempts. Locked out for {lockout // 60} minutes.",
            )
        raise HTTPException(401, "Invalid username or password")

    login_limiter.record_success(request, username)
    token = create_token(user)
    audit.record(db, user, "LOGIN", "User", user.id, {"ip": request.client.host if request.client else "unknown"})
    return {"accessToken": token, "tokenType": "bearer", "user": user_out(user)}


@router.post("/refresh")
def refresh_token_endpoint(user: User = Depends(get_current_user)):
    new_token = create_token(user)
    return {"accessToken": new_token, "tokenType": "bearer", "user": user_out(user)}


@router.get("/session")
def session_status(request: Request, user: User = Depends(get_current_user)):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""
    token_info = inspect_token(token) if token else {}
    return {
        "authenticated": True,
        "user": user_out(user),
        "remainingSeconds": token_info.get("remainingSeconds", 0),
        "role": user.role,
    }


@router.post("/change-password")
def change_password(
    body: PasswordChangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")

    is_valid, msg = validate_password_strength(body.new_password)
    if not is_valid:
        raise HTTPException(400, msg)

    user.password_hash = hash_password(body.new_password)
    db.commit()
    audit.record(db, user, "PASSWORD_CHANGED", "User", user.id, {})
    return {"status": "ok", "message": "Password updated successfully"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_out(user)
