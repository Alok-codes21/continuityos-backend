import base64
import hashlib
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .config import settings
from .crypto import fernet
from .db import get_db
from . import models as m

_ph = PasswordHasher()  # Argon2id by default

ROLE_RANK = {"incoming": 0, "contributor": 1, "manager": 2, "admin": 3}


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, pw)
    except (VerifyMismatchError, InvalidHashError):
        return False


def make_token(user_id: str, jti: str = "") -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_hours)
    return jwt.encode({"sub": user_id, "exp": exp, "iat": datetime.now(timezone.utc)}, settings.jwt_secret, algorithm="HS256")


def _fernet() -> Fernet:
    return fernet()


def encrypt_token(t: str) -> str:
    return _fernet().encrypt(t.encode()).decode() if t else ""


def decrypt_token(t: str) -> str:
    return _fernet().decrypt(t.encode()).decode() if t else ""


def current_user(request: Request, db: Session = Depends(get_db)) -> m.User:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    try:
        data = jwt.decode(auth[7:], settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(m.User, data["sub"])
    if not user:
        raise HTTPException(401, "Unknown user")
    if user.sessions_revoked_at and data.get("iat", 0) < int(user.sessions_revoked_at.replace(tzinfo=timezone.utc).timestamp()):
        raise HTTPException(401, "Session revoked")
    return user


def org_role(db: Session, user: m.User, org_id: str) -> str:
    mem = db.query(m.Membership).filter_by(org_id=org_id, user_id=user.id).first()
    if not mem:
        raise HTTPException(404, "Not found")  # do not reveal other organisations
    return mem.role


class ProjectCtx:
    def __init__(self, project, org_role_, user):
        self.project, self.org_role, self.user = project, org_role_, user

    @property
    def org_id(self):
        return self.project.org_id

    @property
    def pid(self):
        return self.project.id


def project_ctx(project_id: str, min_role: str, db: Session, user: m.User) -> ProjectCtx:
    """Server-side permission check. Admins/managers see every project in their org; others need project membership."""
    prj = db.get(m.Project, project_id)
    if not prj:
        raise HTTPException(404, "Not found")
    role = org_role(db, user, prj.org_id)
    if role not in ("admin", "manager"):
        pm = db.query(m.ProjectMember).filter_by(project_id=prj.id, user_id=user.id).first()
        if not pm:
            raise HTTPException(404, "Not found")
    if ROLE_RANK[role] < ROLE_RANK[min_role]:
        raise HTTPException(403, f"Requires {min_role} role")
    return ProjectCtx(prj, role, user)


def need(min_role: str):
    def dep(project_id: str, db: Session = Depends(get_db), user: m.User = Depends(current_user)) -> ProjectCtx:
        return project_ctx(project_id, min_role, db, user)
    return dep


def audit(db: Session, action: str, user=None, org_id=None, project_id=None, target_type=None, target_id=None, **detail):
    db.add(m.AuditLog(org_id=org_id, project_id=project_id, actor_id=getattr(user, "id", user), action=action,
                      target_type=target_type, target_id=target_id, detail=detail))
