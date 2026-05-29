"""
Crisis Detection.
Two-layer: fast keyword matching (synchronous, pre-DB) + pattern scoring.
Runs on RAW (pre-redaction) text so no signal is lost.
Errs heavily toward false positives — a missed crisis is far worse than a false alarm.
"""
import re

# ── Explicit crisis signals ───────────────────────────────────────────────────
_EXPLICIT_CRISIS = [
    "want to die", "want to kill myself", "kill myself", "end my life",
    "take my life", "suicide", "suicidal", "self-harm", "self harm",
    "hurt myself", "hurt myself", "cutting myself", "no reason to live",
    "don't want to live", "dont want to live", "not worth living",
    "end it all", "end everything",
]

# ── Implicit / indirect signals ───────────────────────────────────────────────
_IMPLICIT_CRISIS = [
    "don't want to get out of bed", "dont want to get out of bed",
    "no reason to go on", "can't go on", "cant go on",
    "so overwhelmed i can't", "so overwhelmed i cant",
    "hopeless", "completely hopeless", "utterly hopeless",
    "nothing matters anymore", "nothing matters to me",
    "don't see the point", "dont see the point",
    "giving up on everything", "want to give up on everything",
    "can't do this anymore", "cant do this anymore",
    "no point in continuing","don't know if i want to go on",
    "dont know if i want to go on",
]

# ── Sensitive tool calls that combined with distress = escalate ───────────────
_SENSITIVE_TOOLS = {"drop_course", "withdraw_from_program", "cancel_enrollment", "leave_of_absence"}

# ── Negative affect words (used in combination scoring) ──────────────────────
_NEGATIVE_AFFECT = re.compile(
    r"\b(overwhelmed|hopeless|exhausted|devastated|desperate|worthless|"
    r"alone|isolated|trapped|numb|empty|broken|lost|miserable|depressed|"
    r"anxious|terrified|can'?t\s+cope|giving\s+up)\b",
    re.IGNORECASE,
)

# ── Academic crisis words ─────────────────────────────────────────────────────
_ACADEMIC_DISTRESS = re.compile(
    r"\b(drop\s+out|dropping\s+out|quit\s+school|leave\s+school|"
    r"withdraw\s+from|failing\s+everything|can'?t\s+keep\s+up|"
    r"too\s+much\s+to\s+handle|can'?t\s+handle\s+this)\b",
    re.IGNORECASE,
)


def detect_crisis_keywords(text: str) -> bool:
    """
    Fast keyword-based crisis detection. Runs synchronously before any DB write.
    Returns True if any crisis signal detected.
    Intentionally conservative — false positives are reviewed by humans.
    """
    if not text:
        return False

    text_lower = text.lower()

    # Explicit signals — immediate flag
    for signal in _EXPLICIT_CRISIS:
        if signal in text_lower:
            return True

    # Implicit signals — immediate flag
    for signal in _IMPLICIT_CRISIS:
        if signal in text_lower:
            return True

    return False


def detect_crisis_combined(text: str, tool_calls: list[dict] | None = None) -> tuple[bool, str]:
    """
    Extended crisis detection combining keyword + negative affect scoring + tool calls.
    Returns (is_crisis, priority) where priority is 'crisis' | 'concerning' | 'routine'.
    """
    if not text:
        return False, "routine"

    text_lower = text.lower()

    # Explicit crisis — highest priority
    for signal in _EXPLICIT_CRISIS:
        if signal in text_lower:
            return True, "crisis"

    # Implicit crisis — high priority
    for signal in _IMPLICIT_CRISIS:
        if signal in text_lower:
            return True, "crisis"

    # Negative affect + academic distress combo
    negative_count = len(_NEGATIVE_AFFECT.findall(text))
    has_academic_distress = bool(_ACADEMIC_DISTRESS.search(text))

    if negative_count >= 3 and has_academic_distress:
        return True, "concerning"

    if negative_count >= 2 and has_academic_distress:
        # Check for sensitive tool calls combined with distress
        if tool_calls:
            tool_names = {tc.get("name", "") for tc in tool_calls}
            if tool_names & _SENSITIVE_TOOLS:
                return True, "concerning"

    # Single negative affect + sensitive tool
    if negative_count >= 1 and tool_calls:
        tool_names = {tc.get("name", "") for tc in tool_calls}
        if tool_names & _SENSITIVE_TOOLS:
            return True, "concerning"

    return False, "routine"


def get_crisis_priority(text: str, tool_calls: list[dict] | None = None) -> str | None:
    """
    Returns the priority level if a crisis is detected, None otherwise.
    'crisis' | 'concerning' | None
    """
    is_crisis, priority = detect_crisis_combined(text, tool_calls)
    return priority if is_crisis else None
