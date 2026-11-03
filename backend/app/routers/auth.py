import secrets
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..security import ROLE_RANK, audit, current_user, hash_password, make_token, need, org_role, verify_password
from ..services import graph

router = APIRouter(prefix="/api", tags=["auth"])
_FAILS = defaultdict(list)
MAX_FAILS, WINDOW = 5, 300


class Register(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=10, max_length=200)
    org_name: str = Field(min_length=1, max_length=200)
    project_name: str = Field(default="My first project", max_length=200)


class Login(BaseModel):
    email: EmailStr
    password: str


def _check_rate(key):
    now = time.time()
    _FAILS[key] = [t for t in _FAILS[key] if now - t < WINDOW]
    if len(_FAILS[key]) >= MAX_FAILS:
        raise HTTPException(429, "Too many failed attempts. Try again later.")


def reset_rate_limits():
    _FAILS.clear()


@router.post("/auth/register", status_code=201)
def register(body: Register, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.query(m.User).filter_by(email=email).first():
        raise HTTPException(409, "Email already registered")
    u = m.User(email=email, name=body.name, password_hash=hash_password(body.password))
    org = m.Organisation(name=body.org_name, domain=email.split("@")[1])
    db.add_all([u, org])
    db.flush()
    db.add(m.Membership(org_id=org.id, user_id=u.id, role="admin"))
    prj = m.Project(org_id=org.id, name=body.project_name)
    db.add(prj)
    db.flush()
    graph.ensure_person(db, prj.id, u.name)
    audit(db, "register", u, org.id, prj.id)
    db.commit()
    return {"token": make_token(u.id), "user": {"id": u.id, "email": u.email, "name": u.name}, "org_id": org.id, "project_id": prj.id}


@router.post("/auth/login")
def login(body: Login, request: Request, db: Session = Depends(get_db)):
    email = body.email.lower()
    key = f"{email}|{request.client.host if request.client else ''}"
    _check_rate(key)
    u = db.query(m.User).filter_by(email=email).first()
    if not u or not verify_password(body.password, u.password_hash):
        _FAILS[key].append(time.time())
        raise HTTPException(401, "Invalid email or password")
    _FAILS.pop(key, None)
    return {"token": make_token(u.id), "user": {"id": u.id, "email": u.email, "name": u.name}}


@router.get("/auth/me")
def me(user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    mems = db.query(m.Membership).filter_by(user_id=user.id).all()
    return {"id": user.id, "email": user.email, "name": user.name,
            "orgs": [{"org_id": x.org_id, "role": x.role, "name": db.get(m.Organisation, x.org_id).name} for x in mems]}


@router.post("/auth/revoke-all-sessions")
def revoke_all(user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    user.sessions_revoked_at = m.now()
    audit(db, "sessions_revoked", user)
    db.commit()
    return {"ok": True}


class MemberIn(BaseModel):
    email: EmailStr
    name: str = Field(default="", max_length=200)
    role: str = "contributor"


def _org_admin(org_id, db, user, min_role="admin"):
    role = org_role(db, user, org_id)
    if ROLE_RANK[role] < ROLE_RANK[min_role]:
        raise HTTPException(403, f"Requires {min_role} role")
    return role


@router.get("/orgs/{org_id}/members")
def members(org_id: str, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    _org_admin(org_id, db, user, "contributor")
    rows = db.query(m.Membership, m.User).join(m.User, m.User.id == m.Membership.user_id).filter(m.Membership.org_id == org_id).all()
    return [{"user_id": u.id, "name": u.name, "email": u.email, "role": mem.role} for mem, u in rows]


@router.post("/orgs/{org_id}/members", status_code=201)
def add_member(org_id: str, body: MemberIn, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    _org_admin(org_id, db, user)
    if body.role not in ROLE_RANK:
        raise HTTPException(422, "Invalid role")
    email = body.email.lower()
    u = db.query(m.User).filter_by(email=email).first()
    temp = None
    if not u:
        temp = secrets.token_urlsafe(12)
        u = m.User(email=email, name=body.name or email.split("@")[0], password_hash=hash_password(temp))
        db.add(u)
        db.flush()
    if db.query(m.Membership).filter_by(org_id=org_id, user_id=u.id).first():
        raise HTTPException(409, "Already a member")
    db.add(m.Membership(org_id=org_id, user_id=u.id, role=body.role))
    audit(db, "member_added", user, org_id, target_type="user", target_id=u.id, role=body.role)
    db.commit()
    out = {"user_id": u.id, "role": body.role}
    if temp:
        out["temporary_password"] = temp  # shown once, never stored in plain text
    return out


@router.patch("/orgs/{org_id}/members/{user_id}")
def set_role(org_id: str, user_id: str, body: dict, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    _org_admin(org_id, db, user)
    role = body.get("role")
    if role not in ROLE_RANK:
        raise HTTPException(422, "Invalid role")
    mem = db.query(m.Membership).filter_by(org_id=org_id, user_id=user_id).first()
    if not mem:
        raise HTTPException(404, "Not found")
    if mem.role == "admin" and role != "admin" and db.query(m.Membership).filter_by(org_id=org_id, role="admin").count() <= 1:
        raise HTTPException(409, "Cannot demote the last admin")
    mem.role = role
    audit(db, "role_changed", user, org_id, target_type="user", target_id=user_id, role=role)
    db.commit()
    return {"ok": True}


@router.get("/orgs/{org_id}/audit")
def audit_log(org_id: str, limit: int = 100, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    _org_admin(org_id, db, user)
    rows = db.query(m.AuditLog).filter_by(org_id=org_id).order_by(m.AuditLog.created_at.desc()).limit(min(limit, 500)).all()
    return [{"id": r.id, "actor": r.actor_id, "action": r.action, "target_type": r.target_type, "target_id": r.target_id,
             "detail": r.detail, "at": r.created_at.isoformat()} for r in rows]


@router.get("/projects")
def projects(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    out = []
    for mem in db.query(m.Membership).filter_by(user_id=user.id).all():
        for p in db.query(m.Project).filter_by(org_id=mem.org_id):
            if mem.role in ("admin", "manager") or db.query(m.ProjectMember).filter_by(project_id=p.id, user_id=user.id).first():
                out.append({"id": p.id, "org_id": p.org_id, "name": p.name, "role": mem.role})
    return out


@router.post("/orgs/{org_id}/projects", status_code=201)
def create_project(org_id: str, body: dict, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    _org_admin(org_id, db, user, "manager")
    name = str(body.get("name", "")).strip()[:200]
    if not name:
        raise HTTPException(422, "Name required")
    p = m.Project(org_id=org_id, name=name, description=str(body.get("description", ""))[:1000])
    db.add(p)
    audit(db, "project_created", user, org_id)
    db.commit()
    return {"id": p.id, "name": p.name}


@router.post("/projects/{project_id}/members", status_code=201)
def add_project_member(body: dict, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    uid_ = body.get("user_id")
    if not db.query(m.Membership).filter_by(org_id=ctx.org_id, user_id=uid_).first():
        raise HTTPException(404, "User is not in this organisation")
    if not db.query(m.ProjectMember).filter_by(project_id=ctx.pid, user_id=uid_).first():
        db.add(m.ProjectMember(project_id=ctx.pid, user_id=uid_))
    u = db.get(m.User, uid_)
    graph.ensure_person(db, ctx.pid, u.name)
    audit(db, "project_member_added", ctx.user, ctx.org_id, ctx.pid, "user", uid_)
    db.commit()
    return {"ok": True}


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


@router.post('/auth/change-password')
def change_password(body: PasswordChangeIn, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(403, 'Current password is incorrect')
    if body.new_password == body.current_password:
        raise HTTPException(422, 'New password must differ from the current password')
    user.password_hash = hash_password(body.new_password)
    user.sessions_revoked_at = m.now()
    audit(db, 'password_changed', user)
    db.commit()
    return {'ok': True, 'message': 'Password changed. Sign in again.'}
