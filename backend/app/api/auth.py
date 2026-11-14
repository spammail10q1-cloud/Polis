from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from app.core.config import settings
from app.core.limits import login_limit
from app.core.security import (
    CurrentUser,
    DbSession,
    clear_session_cookie,
    create_access_token,
    hash_password,
    set_session_cookie,
    verify_password,
)
from app.models import AuditLog, PrivacyBudget, User, UserConsent
from app.schemas import AuthResponse, ConsentOut, LoginRequest, RegisterRequest, UserOut
from app.services import audit
from app.services.seed import seed_all

router = APIRouter(prefix="/auth", tags=["auth"])
_DUMMY_HASH = hash_password("polis-dummy-password-1")


def _auth_response(user: User, consent: UserConsent) -> AuthResponse:
    return AuthResponse(user=UserOut.model_validate(user), consent=ConsentOut.model_validate(consent))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, response: Response, db: DbSession) -> AuthResponse:
    if not settings.allow_registration:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Registration is disabled for this deployment.")
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    now = datetime.now(UTC)
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="member",
        is_demo=False,
    )
    db.add(user)
    db.flush()
    consent = UserConsent(
        user_id=user.id,
        terms_accepted=True,
        ai_processing=payload.ai_processing,
        research_participation=payload.research_participation,
        federated_learning=False,
        analytics=False,
        consented_at=now,
    )
    db.add(consent)
    db.add(PrivacyBudget(user_id=user.id, epsilon_spent=0.0, epsilon_limit=settings.federated_privacy_budget))
    audit.record(db, user_id=user.id, action="auth.register", resource_type="user", resource_id=user.id)
    db.commit()
    db.refresh(user)
    db.refresh(consent)
    token = create_access_token(user.id)
    set_session_cookie(response, token)
    return _auth_response(user, consent)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: DbSession) -> AuthResponse:
    login_limit(request)
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    valid = verify_password(payload.password, user.password_hash) if user else verify_password(payload.password, _DUMMY_HASH)
    if not user or not valid or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    consent = db.scalar(select(UserConsent).where(UserConsent.user_id == user.id))
    if not consent:
        now = datetime.now(UTC)
        consent = UserConsent(user_id=user.id, terms_accepted=True, consented_at=now)
        db.add(consent)
        db.flush()
    user.last_login_at = datetime.now(UTC)
    audit.record(db, user_id=user.id, action="auth.login", resource_type="session")
    db.commit()
    db.refresh(user)
    db.refresh(consent)
    set_session_cookie(response, create_access_token(user.id))
    return _auth_response(user, consent)


@router.post("/demo", response_model=AuthResponse)
def demo_login(request: Request, response: Response, db: DbSession) -> AuthResponse:
    login_limit(request)
    if not settings.demo_seed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="The demonstration account is disabled for this deployment.")
    user = db.scalar(select(User).where(User.email == settings.demo_email, User.is_demo == True))  # noqa: E712
    if not user:
        seed_all(db)
        user = db.scalar(select(User).where(User.email == settings.demo_email, User.is_demo == True))  # noqa: E712
    if not user:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="The demonstration account is not available.")
    consent = db.scalar(select(UserConsent).where(UserConsent.user_id == user.id))
    if not consent:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Demo consent state is unavailable.")
    user.last_login_at = datetime.now(UTC)
    audit.record(
        db,
        user_id=user.id,
        action="auth.demo_login",
        resource_type="session",
        detail={"notice": "Demonstration account: synthetic data"},
    )
    db.commit()
    set_session_cookie(response, create_access_token(user.id))
    return _auth_response(user, consent)


@router.post("/logout")
def logout(response: Response, db: DbSession, user: CurrentUser) -> dict:
    audit.record(db, user_id=user.id, action="auth.logout", resource_type="session")
    db.commit()
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=AuthResponse)
def me(user: CurrentUser, db: DbSession) -> AuthResponse:
    consent = db.scalar(select(UserConsent).where(UserConsent.user_id == user.id))
    if not consent:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Consent record missing.")
    return _auth_response(user, consent)
