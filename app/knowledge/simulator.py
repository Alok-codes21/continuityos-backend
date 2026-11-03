
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.core import (
    Project,
    Membership,
    ProjectMember,
    User,
    KnowledgeItem,
    KnowledgeOwnership,
    ContinuityEvent,
)

simulator_bp = Blueprint(
    "departure_simulator",
    __name__,
    url_prefix="/api/projects",
)


def manager_access(project_id, user_id):
    project = Project.query.filter_by(id=project_id).first()

    if not project:
        return None

    membership = Membership.query.filter_by(
        user_id=user_id,
        organisation_id=project.organisation_id,
    ).first()

    if not membership or membership.role not in ("admin", "manager"):
        return None

    return project


@simulator_bp.post("/<project_id>/ownership")
@jwt_required()
def assign_knowledge_owner(project_id):
    actor_id = get_jwt_identity()
    project = manager_access(project_id, actor_id)

    if not project:
        return jsonify({"error": "Project not found or manager access required"}), 403

    data = request.get_json(silent=True) or {}
    item_id = data.get("knowledge_item_id")
    owner_id = data.get("user_id")

    if not item_id or not owner_id:
        return jsonify({
            "error": "knowledge_item_id and user_id are required"
        }), 400

    item = KnowledgeItem.query.filter_by(
        id=item_id,
        project_id=project_id,
    ).first()

    if not item:
        return jsonify({"error": "Knowledge item not found"}), 404

    if item.status != "approved":
        return jsonify({
            "error": "Only approved knowledge items can be assigned"
        }), 409

    member = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=owner_id,
    ).first()

    user = User.query.filter_by(id=owner_id, status="active").first()

    if not member or not user:
        return jsonify({
            "error": "Owner must be an active member of this project"
        }), 400

    existing = KnowledgeOwnership.query.filter_by(
        knowledge_item_id=item_id,
        user_id=owner_id,
    ).first()

    if existing:
        return jsonify({"message": "This ownership assignment already exists"}), 200

    assignment = KnowledgeOwnership(
        project_id=project_id,
        knowledge_item_id=item_id,
        user_id=owner_id,
        assigned_by=actor_id,
    )
    db.session.add(assignment)

    db.session.add(ContinuityEvent(
        project_id=project_id,
        actor_id=actor_id,
        event_type="knowledge.owner_assigned",
        entity_type="knowledge_item",
        entity_id=item_id,
        summary=f"Knowledge item '{item.title}' assigned to {user.name}",
        after_state={
            "owner_id": owner_id,
            "owner_name": user.name,
        },
        evidence_document_id=item.document_id,
    ))

    db.session.commit()

    return jsonify({
        "message": "Knowledge owner assigned",
        "knowledge_item_id": item_id,
        "user_id": owner_id,
        "user_name": user.name,
    }), 201


@simulator_bp.get("/<project_id>/departure-impact")
@jwt_required()
def simulate_departure(project_id):
    actor_id = get_jwt_identity()
    project = manager_access(project_id, actor_id)

    if not project:
        return jsonify({"error": "Project not found or manager access required"}), 403

    departing_user_id = request.args.get("user_id")

    if not departing_user_id:
        return jsonify({"error": "Query parameter user_id is required"}), 400

    departing_member = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=departing_user_id,
    ).first()

    departing_user = User.query.filter_by(
        id=departing_user_id
    ).first()

    if not departing_member or not departing_user:
        return jsonify({"error": "Team member not found in this project"}), 404

    assignments = (
        db.session.query(KnowledgeOwnership, KnowledgeItem)
        .join(
            KnowledgeItem,
            KnowledgeOwnership.knowledge_item_id == KnowledgeItem.id,
        )
        .filter(
            KnowledgeOwnership.project_id == project_id,
            KnowledgeOwnership.user_id == departing_user_id,
        )
        .all()
    )

    affected_items = []

    for assignment, item in assignments:
        affected_items.append({
            "knowledge_item_id": item.id,
            "type": item.item_type,
            "title": item.title,
            "status": item.status,
            "uncertainty": item.uncertainty,
            "evidence": item.evidence_text,
            "document_id": item.document_id,
            "ownership_assigned_at": assignment.created_at.isoformat(),
        })

    type_counts = {}
    for item in affected_items:
        type_counts[item["type"]] = type_counts.get(item["type"], 0) + 1

    result = {
        "project_id": project_id,
        "departing_member": {
            "id": departing_user.id,
            "name": departing_user.name,
        },
        "impact": {
            "assigned_knowledge_items": len(affected_items),
            "by_type": type_counts,
            "affected_items": affected_items,
        },
        "coverage": {
            "assessment": (
                "evidence_found" if affected_items else "no_assignments_found"
            ),
            "limitation": (
                "This simulation only includes knowledge items explicitly "
                "assigned to this member. Unrecorded responsibilities and "
                "unassigned knowledge may also be affected."
            ),
        },
    }

    db.session.add(ContinuityEvent(
        project_id=project_id,
        actor_id=actor_id,
        event_type="departure.simulated",
        entity_type="user",
        entity_id=departing_user_id,
        summary=(
            f"Departure impact simulated for {departing_user.name}: "
            f"{len(affected_items)} assigned knowledge items found"
        ),
        after_state={
            "assigned_knowledge_items": len(affected_items),
            "by_type": type_counts,
        },
    ))

    db.session.commit()

    return jsonify(result), 200
