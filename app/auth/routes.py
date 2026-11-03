
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select

from app.extensions import db
from app.models import Organisation, User, Membership, AuditEvent

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
password_hasher = PasswordHasher()

ALLOWED_ROLES = {"admin", "manager", "incoming_member"}


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    organisation_name = (data.get("organisation") or "").strip()

    if not all([name, email, password, organisation_name]):
        return jsonify({"error": "All fields are required."}), 400

    if len(password) < 12:
        return jsonify({"error": "Password must contain at least 12 characters."}), 400

    if db.session.scalar(select(User).where(User.email == email)):
        return jsonify({"error": "An account with this email already exists."}), 409

    try:
        organisation = Organisation(name=organisation_name)
        user = User(
            name=name,
            email=email,
            password_hash=password_hasher.hash(password)
        )

        db.session.add_all([organisation, user])
        db.session.flush()

        membership = Membership(
            user_id=user.id,
            organisation_id=organisation.id,
            role="admin"
        )

        event = AuditEvent(
            organisation_id=organisation.id,
            actor_id=user.id,
            action="organisation.created",
            resource_type="organisation",
            resource_id=organisation.id
        )

        db.session.add_all([membership, event])
        db.session.commit()

        token = create_access_token(
            identity=user.id,
            additional_claims={"organisation_id": organisation.id}
        )

        return jsonify({
            "message": "Organisation created successfully.",
            "access_token": token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": "admin"
            },
            "organisation": {
                "id": organisation.id,
                "name": organisation.name
            }
        }), 201

    except Exception:
        db.session.rollback()
        raise


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = db.session.scalar(select(User).where(User.email == email))

    if not user or user.status != "active":
        return jsonify({"error": "Invalid email or password."}), 401

    try:
        password_hasher.verify(user.password_hash, password)
    except VerifyMismatchError:
        return jsonify({"error": "Invalid email or password."}), 401

    membership = db.session.scalar(
        select(Membership).where(Membership.user_id == user.id)
    )

    if not membership:
        return jsonify({"error": "No organisation membership found."}), 403

    token = create_access_token(
        identity=user.id,
        additional_claims={
            "organisation_id": membership.organisation_id
        }
    )

    return jsonify({
        "access_token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": membership.role
        },
        "organisation_id": membership.organisation_id
    }), 200
