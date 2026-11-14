from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.security import CurrentUser, DbSession
from app.models import HealthProfile
from app.schemas import ProfileOut, ProfileUpdate
from app.services import audit

router = APIRouter(prefix="/profile", tags=["profile"])


def get_or_create_profile(db, user_id: str) -> HealthProfile:
    profile = db.scalar(select(HealthProfile).where(HealthProfile.user_id == user_id))
    if not profile:
        profile = HealthProfile(user_id=user_id, conditions=[], allergies=[], family_history=[])
        db.add(profile)
        db.flush()
    return profile


@router.get("", response_model=ProfileOut)
def read_profile(user: CurrentUser, db: DbSession) -> ProfileOut:
    profile = get_or_create_profile(db, user.id)
    db.commit()
    return ProfileOut.model_validate(profile)


@router.patch("", response_model=ProfileOut)
def update_profile(payload: ProfileUpdate, user: CurrentUser, db: DbSession) -> ProfileOut:
    profile = get_or_create_profile(db, user.id)
    data = payload.model_dump(exclude_unset=True)
    for field in ["conditions", "allergies", "family_history"]:
        if field in data and data[field] is not None:
            data[field] = [item.model_dump() if hasattr(item, "model_dump") else item for item in data[field]]
    if "conditions" in data and data["conditions"] is None:
        data.pop("conditions")
    for key, value in data.items():
        setattr(profile, key, value)
    audit.record(
        db,
        user_id=user.id,
        action="profile.update",
        resource_type="health_profile",
        resource_id=profile.id,
        detail={"fields": sorted(data.keys())},
    )
    db.commit()
    db.refresh(profile)
    return ProfileOut.model_validate(profile)
