
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.core import (
    Project,
    Membership,
    ProjectMember,
    ContinuityEvent,
)

ledger_bp = Blueprint(
    "continuity_ledger",
    __name__,
    url_prefix="/api/projects",
)


@ledger_bp.get("/<project_id>/continuity")
@jwt_required()
def get_continuity_history(project_id):
    user_id = get_jwt_identity()

    project = Project.query.filter_by(id=project_id).first()

    if not project:
        return jsonify({"error": "Project not found"}), 404

    membership = Membership.query.filter_by(
        user_id=user_id,
        organisation_id=project.organisation_id,
    ).first()

    project_member = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=user_id,
    ).first()

    if not membership or (
        membership.role not in ("admin", "manager")
        and not project_member
    ):
        return jsonify({"error": "Access denied"}), 403

    if (
        membership.role not in ("admin", "manager")
        and not (project_member.permissions or {}).get(
            "can_view_knowledge", False
        )
    ):
        return jsonify({"error": "Knowledge access denied"}), 403

    limit = request.args.get("limit", default=100, type=int)
    limit = max(1, min(limit, 500))

    events = (
        ContinuityEvent.query
        .filter_by(project_id=project_id)
        .order_by(ContinuityEvent.created_at.desc())
        .limit(limit)
        .all()
    )

    return jsonify({
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "summary": event.summary,
                "before_state": event.before_state,
                "after_state": event.after_state,
                "evidence_document_id": event.evidence_document_id,
                "actor_id": event.actor_id,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
        "total_returned": len(events),
    }), 200
