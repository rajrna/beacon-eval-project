"""
Safety tests for PII redaction, FERPA classification, and crisis detection.
These are deterministic (no LLM calls) and run fast.
Every PR touching beacon/safety/ must pass these.
"""
import pytest

from beacon.safety.redaction import redact_pii, redact_pii_with_result, audit_for_missed_pii
from beacon.safety.ferpa import classify_ferpa, is_access_permitted
from beacon.safety.crisis_detection import (
    detect_crisis_keywords,
    detect_crisis_combined,
    get_crisis_priority,
)


# ── PII Redaction Tests ───────────────────────────────────────────────────────

class TestPIIRedaction:

    def test_email_redacted(self):
        text = "Please email me at john.doe@westbrook.edu for more info."
        result = redact_pii(text, trace_salt="test")
        assert "john.doe@westbrook.edu" not in result
        assert "[EMAIL_" in result

    def test_phone_redacted(self):
        text = "Call me at (555) 123-4567 or 555-987-6543."
        result = redact_pii(text, trace_salt="test")
        assert "555" not in result or "[PHONE_" in result

    def test_ssn_redacted(self):
        text = "My SSN is 123-45-6789."
        result = redact_pii(text, trace_salt="test")
        assert "123-45-6789" not in result
        assert "[SSN_" in result

    def test_student_id_redacted(self):
        text = "Student ID: S1234567 needs help with enrollment."
        result = redact_pii(text, trace_salt="test")
        assert "S1234567" not in result

    def test_stable_placeholders_same_salt(self):
        """Same value + same salt = same placeholder."""
        text1 = "Email john@test.com about john@test.com"
        result = redact_pii_with_result(text1, trace_salt="fixed-salt")
        # Both occurrences should get the same placeholder
        placeholders = [w for w in result.redacted_text.split() if w.startswith("[EMAIL_")]
        assert len(placeholders) == 2
        assert placeholders[0] == placeholders[1]

    def test_different_salts_different_placeholders(self):
        """Same value + different salt = different placeholder."""
        text = "Email: test@example.com"
        result1 = redact_pii(text, trace_salt="salt-1")
        result2 = redact_pii(text, trace_salt="salt-2")
        assert result1 != result2

    def test_no_pii_unchanged(self):
        text = "What are the admission requirements for the MBA program?"
        result = redact_pii(text, trace_salt="test")
        assert result == text

    def test_empty_string(self):
        assert redact_pii("") == ""
        assert redact_pii(None) is None  # type: ignore

    def test_entity_count_tracked(self):
        text = "Contact jane@example.com or call 555-123-4567"
        result = redact_pii_with_result(text, trace_salt="test")
        assert result.entity_count >= 2

    def test_audit_finds_missed_email(self):
        text = "The student's email is hidden@test.com in the record."
        issues = audit_for_missed_pii(text)
        assert any("EMAIL" in i for i in issues)

    def test_audit_clean_text_no_issues(self):
        text = "What financial aid options are available for MBA students?"
        issues = audit_for_missed_pii(text)
        assert len(issues) == 0

    def test_credit_card_redacted(self):
        text = "My card is 4111 1111 1111 1111"
        result = redact_pii(text, trace_salt="test")
        assert "4111 1111 1111 1111" not in result


# ── FERPA Classification Tests ────────────────────────────────────────────────

class TestFERPAClassification:

    def test_public_no_name_no_academic(self):
        text = "What are the tuition rates for the MBA program?"
        assert classify_ferpa(text) == "public"

    def test_public_general_question(self):
        text = "When does the fall semester start?"
        assert classify_ferpa(text) == "public"

    def test_directory_name_only(self):
        # After redaction, name becomes a placeholder
        text = "I'm [PERSON_abc12345] and I need help with my application."
        assert classify_ferpa(text) == "directory"

    def test_confidential_name_plus_grades(self):
        text = "[PERSON_abc12345] has a GPA of 3.2 and is enrolled in 12 credits."
        assert classify_ferpa(text) == "confidential"

    def test_confidential_name_plus_financial_aid(self):
        text = "I'm [PERSON_abc12345] and I have questions about my financial aid package."
        assert classify_ferpa(text) == "confidential"

    def test_confidential_name_plus_enrollment(self):
        text = "[PERSON_abc12345] needs to withdraw from the program."
        assert classify_ferpa(text) == "confidential"

    def test_confidential_ssn_present(self):
        # Even without a name, SSN = confidential
        text = "SSN [SSN_abc12345] is associated with this record."
        assert classify_ferpa(text) == "confidential"

    def test_confidential_student_id_present(self):
        text = "Student ID [STUDENT_ID_abc12345] grade report."
        assert classify_ferpa(text) == "confidential"

    def test_empty_text_public(self):
        assert classify_ferpa("") == "public"
        assert classify_ferpa(None) == "public"  # type: ignore

    def test_access_admin_can_access_confidential(self):
        assert is_access_permitted("confidential", "admin") is True

    def test_access_sme_can_access_confidential(self):
        assert is_access_permitted("confidential", "sme") is True

    def test_access_engineer_cannot_access_confidential(self):
        assert is_access_permitted("confidential", "engineer") is False

    def test_access_viewer_cannot_access_directory(self):
        assert is_access_permitted("directory", "viewer") is False

    def test_access_own_record_always_permitted(self):
        assert is_access_permitted("confidential", "viewer", is_own_record=True) is True


# ── Crisis Detection Tests ────────────────────────────────────────────────────

class TestCrisisDetection:

    # True positives — these MUST be detected
    @pytest.mark.parametrize("text", [
        "I don't want to get out of bed anymore. Can you help me drop my classes?",
        "I don't know if I want to go on anymore.",
        "I've been thinking about suicide lately.",
        "I want to kill myself, school is too much.",
        "I've been self-harming and I don't know what to do.",
        "There's no reason to live anymore.",
        "I want to end it all.",
        "I'm completely hopeless and can't go on.",
    ])
    def test_explicit_crisis_detected(self, text):
        assert detect_crisis_keywords(text) is True, f"Should detect crisis in: {text!r}"

    # True negatives — these must NOT be flagged as crisis
    @pytest.mark.parametrize("text", [
        "What are the tuition payment deadlines?",
        "I want to kill my presentation tomorrow, any tips?",
        "I'm so excited to start the program!",
        "Can you help me with my course registration?",
        "What financial aid options are available?",
        "I'm a little stressed about finals but managing okay.",
    ])
    def test_non_crisis_not_detected(self, text):
        assert detect_crisis_keywords(text) is False, f"Should NOT detect crisis in: {text!r}"

    def test_combined_detection_explicit_is_crisis(self):
        text = "I want to die. Can you drop all my classes?"
        is_crisis, priority = detect_crisis_combined(text)
        assert is_crisis is True
        assert priority == "crisis"

    def test_combined_detection_implicit_concerning(self):
        text = "I'm so overwhelmed and hopeless. I can't handle this anymore. I want to withdraw."
        is_crisis, priority = detect_crisis_combined(text)
        assert is_crisis is True

    def test_combined_detection_tool_call_with_distress(self):
        text = "I'm overwhelmed and exhausted and can't cope."
        tool_calls = [{"name": "drop_course", "args": {"course_id": "ENG101"}}]
        is_crisis, priority = detect_crisis_combined(text, tool_calls)
        assert is_crisis is True
        assert priority in ("crisis", "concerning")

    def test_combined_detection_normal_drop_no_crisis(self):
        text = "I'd like to drop MATH201 because of schedule conflicts."
        tool_calls = [{"name": "drop_course", "args": {"course_id": "MATH201"}}]
        is_crisis, priority = detect_crisis_combined(text, tool_calls)
        assert is_crisis is False

    def test_get_crisis_priority_crisis(self):
        text = "I want to end my life."
        assert get_crisis_priority(text) == "crisis"

    def test_get_crisis_priority_none(self):
        text = "What is the cost per credit hour?"
        assert get_crisis_priority(text) is None

    def test_empty_text_not_crisis(self):
        assert detect_crisis_keywords("") is False
        assert detect_crisis_keywords(None) is False  # type: ignore

    @pytest.mark.safety_critical
    def test_sarcastic_okay_not_flagged(self):
        """'I'm totally fine' sarcasm — hard case, should not false-positive on keyword alone."""
        text = "Yeah I'm totally fine lol, just need to know the MBA tuition."
        # This should NOT trigger keyword detection (no explicit crisis words)
        assert detect_crisis_keywords(text) is False

    @pytest.mark.safety_critical
    def test_idiom_kill_not_flagged(self):
        """'Kill my presentation' is an idiom, not a crisis signal."""
        text = "I want to kill my presentation tomorrow. Any tips?"
        assert detect_crisis_keywords(text) is False
