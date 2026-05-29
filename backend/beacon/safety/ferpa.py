"""
FERPA Classification.
Classifies each trace as public, directory, or confidential.

Rules (simplified from FERPA):
  confidential = name + academic record (grades, enrollment, financial aid, GPA)
  directory    = name alone (without academic record)
  public       = neither name nor academic record
"""
import re

# Academic record indicators
_ACADEMIC_PATTERNS = re.compile(
    r"\b(gpa|grade[s]?|transcript|enrollment|financial\s+aid|tuition\s+balance|"
    r"academic\s+standing|credit\s+hour[s]?|degree\s+audit|scholarship|"
    r"loan[s]?|fafsa|aid\s+package|registration|drop|withdraw|academic\s+record)\b",
    re.IGNORECASE,
)

# Name indicators — after redaction, [PERSON_...] placeholders signal a name was present
_NAME_PATTERN = re.compile(r"\[PERSON_[a-f0-9]+\]")

# Direct PII that makes something confidential regardless
_CONFIDENTIAL_DIRECT = re.compile(
    r"\[SSN_[a-f0-9]+\]|\[STUDENT_ID_[a-f0-9]+\]|\[CREDIT_CARD_[a-f0-9]+\]|\[DOB_[a-f0-9]+\]"
)


def classify_ferpa(redacted_text: str) -> str:
    """
    Classify a redacted trace for FERPA.
    Input should be the ALREADY-REDACTED text (placeholders in place of PII).
    Returns: 'public' | 'directory' | 'confidential'
    """
    if not redacted_text:
        return "public"

    # Direct PII present = always confidential
    if _CONFIDENTIAL_DIRECT.search(redacted_text):
        return "confidential"

    has_name = bool(_NAME_PATTERN.search(redacted_text))
    has_academic = bool(_ACADEMIC_PATTERNS.search(redacted_text))

    if has_name and has_academic:
        return "confidential"
    elif has_name:
        return "directory"
    else:
        return "public"


def is_access_permitted(ferpa_class: str, user_role: str, is_own_record: bool = False) -> bool:
    """
    Check whether a user role may access a trace of a given FERPA classification.
    Students may always access their own records.
    """
    if is_own_record:
        return True
    if ferpa_class == "public":
        return True
    if ferpa_class == "directory":
        return user_role in ("admin", "engineer", "sme")
    if ferpa_class == "confidential":
        return user_role in ("admin", "sme")
    return False
