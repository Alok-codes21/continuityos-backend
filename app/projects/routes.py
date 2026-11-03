
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import select

from app.extensions import db
from app.models import Project, Membership, AuditEvent
from app.models import ProjectMember

projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")


@projects_bp.get("/")
@jwt_required()
def list_projects():
    claims = get_jwt()
    organisation_id = claims.get("organisation_id")

    if not organisation_id:
        return jsonify({"error": "Invalid organisation context."}), 403

    projects = db.session.scalars(
        select(Project).where(
            Project.organisation_id == organisation_id
        ).order_by(Project.created_at.desc())
    ).all()

    return jsonify({
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "status": p.status,
                "created_at": p.created_at.isoformat()
            }
            for p in projects
        ],
        "count": len(projects)
    })


@projects_bp.post("/")
@jwt_required()
def create_project():
    claims = get_jwt()
    organisation_id = claims.get("organisation_id")
    user_id = get_jwt_identity()

    if not organisation_id:
        return jsonify({"error": "Invalid organisation context."}), 403

    membership = db.session.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.organisation_id == organisation_id
        )
    )

    if not membership or membership.role not in {"admin", "manager"}:
        return jsonify({"error": "You cannot create projects."}), 403

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()

    if not name:
        return jsonify({"error": "Project name is required."}), 400

   
    project = Project(
        organisation_id=organisation_id,
        name=name,
        description=description
    )

    db.session.add(project)
    db.session.flush()

    project_member = ProjectMember(
        project_id=project.id,
        user_id=user_id,
        permissions={
            "can_upload": True,
            "can_view_knowledge": True,
            "can_manage_members": True
        }
    )

    event = AuditEvent(
        organisation_id=organisation_id,
        actor_id=user_id,
        action="project.created",
        resource_type="project",
        resource_id=project.id
    )

    db.session.add_all([project_member, event])
    db.session.commit()


    return jsonify({
        "message": "Project created.",
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status
        }
    }), 201
