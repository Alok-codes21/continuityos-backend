
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.core import (
    Project,
    Membership,
    ProjectMember,
    Document,
    KnowledgeItem,
    KnowledgeDependency,
)

graph_bp = Blueprint(
    "knowledge_graph",
    __name__,
    url_prefix="/api/projects",
)


@graph_bp.get("/<project_id>/graph")
@jwt_required()
def get_project_graph(project_id):
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

    documents = Document.query.filter_by(
        project_id=project_id
    ).all()

    knowledge_items = KnowledgeItem.query.filter_by(
        project_id=project_id
    ).all()

    nodes = [{
        "id": f"project:{project.id}",
        "type": "project",
        "label": project.name,
        "status": project.status,
    }]

    edges = []

    for document in documents:
        document_node_id = f"document:{document.id}"

        nodes.append({
            "id": document_node_id,
            "type": "document",
            "label": document.original_name,
            "status": document.status,
        })

        edges.append({
            "id": f"contains:{document.id}",
            "source": f"project:{project.id}",
            "target": document_node_id,
            "type": "contains",
            "evidence": None,
        })

        dependencies = KnowledgeDependency.query.filter_by(
        project_id=project_id
    ).all()

    for dependency in dependencies:
        edges.append({
            "id": f"dependency:{dependency.id}",
            "source": f"knowledge:{dependency.source_item_id}",
            "target": f"knowledge:{dependency.target_item_id}",
            "type": dependency.relationship_type,
            "evidence": dependency.description,
        })

    for item in knowledge_items:
        item_node_id = f"knowledge:{item.id}"
        document_node_id = f"document:{item.document_id}"

        nodes.append({
            "id": item_node_id,
            "type": item.item_type,
            "label": item.title,
            "status": item.status,
            "uncertainty": item.uncertainty,
        })

        edges.append({
            "id": f"evidence:{item.id}",
            "source": document_node_id,
            "target": item_node_id,
            "type": "evidences",
            "evidence": item.evidence_text,
        })

    return jsonify({
        "project_id": project_id,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "documents": len(documents),
            "knowledge_items": len(knowledge_items),
            "approved": sum(
                1 for item in knowledge_items
                if item.status == "approved"
            ),
            "needs_review": sum(
                1 for item in knowledge_items
                if item.status == "needs_review"
            ),
        },
    }), 200
