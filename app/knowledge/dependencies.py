
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.core import (
    Project,
    Membership,
    ProjectMember,
    KnowledgeItem,
    KnowledgeDependency,
    AuditEvent,
    ContinuityEvent,
)

dependencies_bp = Blueprint(
    "knowledge_dependencies",
    __name__,
    url_prefix="/api/projects",
)

ALLOWED_RELATIONSHIPS = {
    "depends_on",
    "blocks",
    "owned_by",
    "related_to",
}


def get_access(project_id, user_id, require_manage=False):
    project = Project.query.filter_by(id=project_id).first()

    if not project:
        return None, None, None

    membership = Membership.query.filter_by(
        user_id=user_id,
        organisation_id=project.organisation_id,
    ).first()

    member = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=user_id,
    ).first()

    if not membership:
        return None, None, None

    is_manager = membership.role in ("admin", "manager")

    if not is_manager and not member:
        return None, None, None

    permissions = (member.permissions or {}) if member else {}

    if not is_manager and not permissions.get("can_view_knowledge", False):
        return None, None, None

    if require_manage and not is_manager and not permissions.get(
        "can_manage_members", False
    ):
        return None, None, None

    return project, membership, member


def serialize_dependency(item):
    return {
        "id": item.id,
        "project_id": item.project_id,
        "source_item_id": item.source_item_id,
        "target_item_id": item.target_item_id,
        "relationship_type": item.relationship_type,
        "description": item.description,
        "created_by": item.created_by,
        "created_at": item.created_at.isoformat(),
    }


@dependencies_bp.get("/<project_id>/dependencies")
@jwt_required()
def list_dependencies(project_id):
    user_id = get_jwt_identity()

    project, _, _ = get_access(project_id, user_id)

    if not project:
        return jsonify({"error": "Project not found or access denied"}), 404

    dependencies = (
        KnowledgeDependency.query
        .filter_by(project_id=project_id)
        .order_by(KnowledgeDependency.created_at.desc())
        .all()
    )

    return jsonify({
        "dependencies": [
            serialize_dependency(item) for item in dependencies
        ],
        "total": len(dependencies),
    }), 200


@dependencies_bp.post("/<project_id>/dependencies")
@jwt_required()
def create_dependency(project_id):
    user_id = get_jwt_identity()

    project, membership, member = get_access(
        project_id, user_id, require_manage=True
    )

    if not project:
        return jsonify({"error": "Project not found or access denied"}), 404

    if not (membership.role in ("admin", "manager")):
        permissions = (member.permissions or {}) if member else {}
        if not permissions.get("can_view_knowledge", False):
            return jsonify({"error": "Knowledge access denied"}), 403

    data = request.get_json(silent=True) or {}

    source_id = data.get("source_item_id")
    target_id = data.get("target_item_id")
    relationship_type = data.get("relationship_type", "related_to")
    description = (data.get("description") or "").strip()

    if not source_id or not target_id:
        return jsonify({
            "error": "source_item_id and target_item_id are required"
        }), 400

    if source_id == target_id:
        return jsonify({
            "error": "An item cannot depend on itself"
        }), 400

    if relationship_type not in ALLOWED_RELATIONSHIPS:
        return jsonify({
            "error": "Invalid relationship_type",
            "allowed": sorted(ALLOWED_RELATIONSHIPS),
        }), 400

    source = KnowledgeItem.query.filter_by(
        id=source_id,
        project_id=project_id,
    ).first()

    target = KnowledgeItem.query.filter_by(
        id=target_id,
        project_id=project_id,
    ).first()

    if not source or not target:
        return jsonify({
            "error": "Both knowledge items must belong to this project"
        }), 404

    existing = KnowledgeDependency.query.filter_by(
        project_id=project_id,
        source_item_id=source_id,
        target_item_id=target_id,
        relationship_type=relationship_type,
    ).first()

    if existing:
        return jsonify({
            "error": "This relationship already exists",
            "dependency": serialize_dependency(existing),
        }), 409

    dependency = KnowledgeDependency(
        project_id=project_id,
        source_item_id=source_id,
        target_item_id=target_id,
        relationship_type=relationship_type,
        description=description or None,
        created_by=user_id,
    )

    db.session.add(dependency)
    db.session.flush()

    db.session.add(AuditEvent(
        organisation_id=project.organisation_id,
        actor_id=user_id,
        action="dependency.created",
        resource_type="knowledge_dependency",
        resource_id=dependency.id,
    ))

    db.session.add(ContinuityEvent(
        project_id=project_id,
        actor_id=user_id,
        event_type="dependency.created",
        entity_type="knowledge_dependency",
        entity_id=dependency.id,
        summary=(
            f"Relationship created: {source.title} "
            f"{relationship_type} {target.title}"
        ),
        after_state={
            "source_item_id": source_id,
            "target_item_id": target_id,
            "relationship_type": relationship_type,
            "description": description,
        },
    ))

    db.session.commit()

    return jsonify({
        "message": "Dependency relationship created",
        "dependency": serialize_dependency(dependency),
    }), 201


@dependencies_bp.delete("/<project_id>/dependencies/<dependency_id>")
@jwt_required()
def delete_dependency(project_id, dependency_id):
    user_id = get_jwt_identity()

    project, _, _ = get_access(
        project_id, user_id, require_manage=True
    )

    if not project:
        return jsonify({"error": "Project not found or access denied"}), 404

    dependency = KnowledgeDependency.query.filter_by(
        id=dependency_id,
        project_id=project_id,
    ).first()

    if not dependency:
        return jsonify({"error": "Relationship not found"}), 404

    previous_state = serialize_dependency(dependency)

    db.session.add(AuditEvent(
        organisation_id=project.organisation_id,
        actor_id=user_id,
        action="dependency.deleted",
        resource_type="knowledge_dependency",
        resource_id=dependency.id,
    ))

    db.session.add(ContinuityEvent(
        project_id=project_id,
        actor_id=user_id,
        event_type="dependency.deleted",
        entity_type="knowledge_dependency",
        entity_id=dependency.id,
        summary="Knowledge dependency relationship deleted",
        before_state=previous_state,
    ))

    db.session.delete(dependency)
    db.session.commit()

    return jsonify({"message": "Relationship deleted"}), 200
