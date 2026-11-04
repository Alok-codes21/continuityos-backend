"""Keep application-authored templates and optional model instructions in English."""
from types import SimpleNamespace

from app.services import handover, interview, llm, rag


def test_application_fallback_and_interview_templates_are_english():
    assert rag.NO_ANSWER == (
        "I don't have verified knowledge about that in the sources you can access. "
        "It has been recorded as a knowledge gap."
    )
    cases = {
        "no_documented_owner": "Who owns",
        "missing_procedure": "Please describe",
        "undocumented_decision": "Why was this decided",
        "conflict": "Our sources disagree",
        "unresolved_bug": "What is the current status",
    }
    for gap_type, prefix in cases.items():
        gap = SimpleNamespace(gap_type=gap_type, entity_key="payments:rollback",
                              description="Knowledge gap: payments", found="Sources disagree")
        assert interview._gap_question(gap).startswith(prefix)
    assert ("limitations", "Known limitations of this handover") in handover.SECTIONS


def test_optional_model_prompts_request_english(monkeypatch):
    prompts = []

    def capture(prompt):
        prompts.append(prompt)
        return "What steps are missing?"

    monkeypatch.setattr(llm, "_rephrase_raw", capture)
    llm._rephrase("Who owns payments?", ["Priya owns payments."])
    llm.followup("How do you deploy?", "Run the deployment.")
    llm.entails("Priya owns payments.", "Priya owns payments.")
    assert all("English" in prompt for prompt in prompts)
    assert len(prompts) == 3
