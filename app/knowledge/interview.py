
from datetime import datetime, timezone

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
    InterviewSession,
    InterviewQuestion,
    InterviewAnswer,
    ContinuityEvent,
)

interview_bp = Blueprint(
    "handover_interview",
    __name__,
    url_prefix="/api/projects",
)


def get_manager_project(project_id, user_id):
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


def get_session_access(session_id, user_id):
    session = InterviewSession.query.filter_by(id=session_id).first()
    if not session:
        return None, None

    project = Project.query.filter_by(id=session.project_id).first()
    if not project:
        return None, None

    membership = Membership.query.filter_by(
        user_id=user_id,
        organisation_id=project.organisation_id,
    ).first()

    is_manager = bool(
        membership and membership.role in ("admin", "manager")
    )
    is_departing_member = session.departing_user_id == user_id

    if not (is_manager or is_departing_member):
        return None, None

    return session, project


@interview_bp.post("/<project_id>/handover/interviews")
@jwt_required()
def create_interview(project_id):
    manager_id = get_jwt_identity()
    project = get_manager_project(project_id, manager_id)

    if not project:
        return jsonify({"error": "Manager access required"}), 403

    data = request.get_json(silent=True) or {}
    departing_user_id = data.get("departing_user_id")

    if not departing_user_id:
        return jsonify({"error": "departing_user_id is required"}), 400

    member = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=departing_user_id,
    ).first()

    departing_user = User.query.filter_by(
        id=departing_user_id,
        status="active",
    ).first()

    if not member or not departing_user:
        return jsonify({"error": "Active project member not found"}), 404

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

    if not assignments:
        return jsonify({
            "error": "No assigned knowledge found. Assign approved knowledge items first."
        }), 409

    session = InterviewSession(
        project_id=project_id,
        departing_user_id=departing_user_id,
        created_by=manager_id,
    )
    db.session.add(session)
    db.session.flush()

    for assignment, item in assignments:
        question_text = (
            f"You are listed as the owner of '{item.title}' "
            f"({item.item_type}). What should your replacement know "
            f"to understand, maintain, or continue this work?"
        )

        db.session.add(InterviewQuestion(
            session_id=session.id,
            knowledge_item_id=item.id,
            question=question_text,
            question_type=item.item_type,
        ))

    # General questions capture knowledge not yet represented in the ledger.
    general_questions = [
        (
            "undocumented_knowledge",
            "What important project knowledge have we not captured in the existing documents?"
        ),
        (
            "next_steps",
            "What are the most important next steps, and what could prevent them from being completed?"
        ),
        (
            "contacts",
            "Which people or teams should the incoming member coordinate with, and for what?"
        ),
        (
            "advice",
            "What would you do differently if you were starting this work again?"
        ),
    ]

    for question_type, question_text in general_questions:
        db.session.add(InterviewQuestion(
            session_id=session.id,
            question=question_text,
            question_type=question_type,
        ))

    db.session.add(ContinuityEvent(
        project_id=project_id,
        actor_id=manager_id,
        event_type="handover.interview_created",
        entity_type="interview_session",
        entity_id=session.id,
        summary=f"Handover interview created for {departing_user.name}",
        after_state={"question_count": len(assignments) + len(general_questions)},
    ))

    db.session.commit()

    return jsonify({
        "message": "Handover interview created",
        "session_id": session.id,
        "question_count": len(assignments) + len(general_questions),
        "status": session.status,
    }), 201


@interview_bp.get("/handover/interviews/<session_id>")
@jwt_required()
def get_interview(session_id):
    user_id = get_jwt_identity()
    session, project = get_session_access(session_id, user_id)

    if not session:
        return jsonify({"error": "Interview not found or access denied"}), 404

    questions = InterviewQuestion.query.filter_by(
        session_id=session.id
    ).order_by(InterviewQuestion.created_at.asc()).all()

    result = []

    for question in questions:
        answer = InterviewAnswer.query.filter_by(
            question_id=question.id
        ).first()

        result.append({
            "id": question.id,
            "question": question.question,
            "type": question.question_type,
            "knowledge_item_id": question.knowledge_item_id,
            "answer": answer.answer if answer else None,
            "answer_status": answer.status if answer else "not_answered",
            "reviewer_note": (
                answer.reviewer_note if answer and answer.reviewer_note else None
            ),
        })

    return jsonify({
        "session_id": session.id,
        "project_id": session.project_id,
        "departing_user_id": session.departing_user_id,
        "status": session.status,
        "questions": result,
    }), 200


@interview_bp.post("/handover/interviews/<session_id>/answers")
@jwt_required()
def submit_interview_answer(session_id):
    user_id = get_jwt_identity()
    session, project = get_session_access(session_id, user_id)

    if not session:
        return jsonify({"error": "Interview not found or access denied"}), 404

    if session.departing_user_id != user_id:
        return jsonify({"error": "Only the departing member can submit answers"}), 403

    if session.status != "in_progress":
        return jsonify({"error": "This interview is no longer accepting answers"}), 409

    data = request.get_json(silent=True) or {}
    question_id = data.get("question_id")
    answer_text = (data.get("answer") or "").strip()

    if not question_id or not answer_text:
        return jsonify({"error": "question_id and answer are required"}), 400

    if len(answer_text) > 20000:
        return jsonify({"error": "Answer must be 20,000 characters or fewer"}), 400

    question = InterviewQuestion.query.filter_by(
        id=question_id,
        session_id=session_id,
    ).first()

    if not question:
        return jsonify({"error": "Question not found in this interview"}), 404

    answer = InterviewAnswer.query.filter_by(question_id=question_id).first()

    if answer and answer.status == "approved":
        return jsonify({"error": "This answer has already been approved"}), 409

    if not answer:
        answer = InterviewAnswer(
            question_id=question_id,
            answer=answer_text,
        )
        db.session.add(answer)
    else:
        answer.answer = answer_text
        answer.status = "pending_review"
        answer.reviewed_by = None
        answer.reviewed_at = None
        answer.reviewer_note = None

    db.session.commit()

    return jsonify({
        "message": "Answer submitted for manager review",
        "answer_id": answer.id,
        "status": answer.status,
    }), 201


@interview_bp.post("/handover/interviews/<session_id>/answers/<answer_id>/review")
@jwt_required()
def review_interview_answer(session_id, answer_id):
    manager_id = get_jwt_identity()
    session, project = get_session_access(session_id, manager_id)

    if not session or not get_manager_project(session.project_id, manager_id):
        return jsonify({"error": "Manager access required"}), 403

    answer = (
        db.session.query(InterviewAnswer)
        .join(InterviewQuestion, InterviewAnswer.question_id == InterviewQuestion.id)
        .filter(
            InterviewAnswer.id == answer_id,
            InterviewQuestion.session_id == session_id,
        )
        .first()
    )

    if not answer:
        return jsonify({"error": "Answer not found"}), 404

    data = request.get_json(silent=True) or {}
    decision = data.get("decision")

    if decision not in ("approve", "reject"):
        return jsonify({"error": "decision must be approve or reject"}), 400

    previous_status = answer.status
    answer.status = "approved" if decision == "approve" else "rejected"
    answer.reviewed_by = manager_id
    answer.reviewed_at = datetime.now(timezone.utc)
    answer.reviewer_note = (data.get("note") or "").strip() or None

    question = InterviewQuestion.query.filter_by(id=answer.question_id).first()

    db.session.add(ContinuityEvent(
        project_id=session.project_id,
        actor_id=manager_id,
        event_type=f"handover.answer_{decision}d",
        entity_type="interview_answer",
        entity_id=answer.id,
        summary=f"Handover answer {decision}d",
        before_state={"status": previous_status},
        after_state={"status": answer.status},
    ))

    db.session.commit()

    return jsonify({
        "message": f"Answer {answer.status}",
        "answer_id": answer.id,
        "status": answer.status,
        "knowledge_item_id": question.knowledge_item_id,
    }), 200


@interview_bp.post("/handover/interviews/<session_id>/complete")
@jwt_required()
def complete_interview(session_id):
    user_id = get_jwt_identity()
    session, project = get_session_access(session_id, user_id)

    if not session:
        return jsonify({"error": "Interview not found or access denied"}), 404

    if session.departing_user_id != user_id:
        return jsonify({"error": "Only the departing member can submit the interview"}), 403

    unanswered = (
        InterviewQuestion.query
        .outerjoin(
            InterviewAnswer,
            InterviewQuestion.id == InterviewAnswer.question_id,
        )
        .filter(
            InterviewQuestion.session_id == session_id,
            InterviewAnswer.id.is_(None),
        )
        .count()
    )

    if unanswered:
        return jsonify({
            "error": "Answer all interview questions before completing",
            "unanswered": unanswered,
        }), 409

    session.status = "submitted_for_review"

    db.session.add(ContinuityEvent(
        project_id=session.project_id,
        actor_id=user_id,
        event_type="handover.interview_submitted",
        entity_type="interview_session",
        entity_id=session.id,
        summary="Departing member submitted interview for review",
        after_state={"status": session.status},
    ))

    db.session.commit()

    return jsonify({
        "message": "Interview submitted for manager review",
        "status": session.status,
    }), 200
