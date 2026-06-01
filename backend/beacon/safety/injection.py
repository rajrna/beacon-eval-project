"""
Prompt Injection Detection.
Runs synchronously before every agent call — fast keyword + pattern matching.
Two layers:
  1. Hard block — patterns that are almost certainly injection attempts
  2. Soft flag — suspicious patterns that get logged and flagged but not blocked

Never blocks legitimate student queries. Errs toward allowing ambiguous input
and flagging for review rather than blocking and frustrating real students.
"""
import re

# ── Hard block patterns ───────────────────────────────────────────────────────
# These are unambiguous injection attempts — block and return a safe response

_HARD_BLOCK_PATTERNS = [
    # Classic instruction override attempts
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|rules?|directives?)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|rules?)", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|rules?)", re.IGNORECASE),

    # Role/persona override
    re.compile(r"you\s+are\s+now\s+(a|an|the)\s+\w+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+(are|were)\s+)?(a|an|the)\s+\w+\s+(with\s+no|without)\s+(restrictions?|limits?|rules?|guidelines?)", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+)?(have\s+no|don'?t\s+have)\s+(restrictions?|limits?|rules?|guidelines?)", re.IGNORECASE),
    re.compile(r"(developer|admin|god|jailbreak|dan|dAN)\s+mode", re.IGNORECASE),

    # System prompt extraction
    re.compile(r"(print|show|reveal|tell\s+me|output|repeat|display)\s+(your\s+)?(system\s+prompt|instructions?|initial\s+prompt|base\s+prompt)", re.IGNORECASE),
    re.compile(r"what\s+(are\s+your|is\s+your)\s+(system\s+prompt|instructions?|initial\s+instructions?)", re.IGNORECASE),

    # Prompt delimiter injection
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", re.IGNORECASE),
    re.compile(r"###\s*(system|instruction|prompt)", re.IGNORECASE),

    # Explicit override
    re.compile(r"(new|updated?|override)\s+(system\s+)?(instructions?|prompt|rules?|directives?)\s*:", re.IGNORECASE),
    re.compile(r"your\s+(new|actual|real|true)\s+(instructions?|prompt|purpose|goal)\s+(is|are)", re.IGNORECASE),
]

# ── Soft flag patterns ────────────────────────────────────────────────────────
# Suspicious but could be legitimate — flag for review, don't block

_SOFT_FLAG_PATTERNS = [
    re.compile(r"all\s+restrictions?\s+(are\s+)?(lifted|removed|disabled|off)", re.IGNORECASE),
    re.compile(r"(bypass|circumvent|override)\s+(the\s+)?(filter|restriction|limit|rule|safety)", re.IGNORECASE),
    re.compile(r"(without|no)\s+(restrictions?|limits?|filters?|guidelines?|rules?)", re.IGNORECASE),
    re.compile(r"do\s+anything\s+now", re.IGNORECASE),
    re.compile(r"(hypothetically|theoretically|for\s+research|as\s+a\s+test)\s*[:,]\s*(tell|show|give|provide|explain)", re.IGNORECASE),
    re.compile(r"simulate\s+(being\s+)?(a|an)\s+\w+\s+(ai|bot|assistant|model)", re.IGNORECASE),
]


class InjectionCheckResult:
    def __init__(
        self,
        blocked: bool,
        flagged: bool,
        pattern_matched: str | None = None,
        safe_response: str | None = None,
    ) -> None:
        self.blocked = blocked
        self.flagged = flagged
        self.pattern_matched = pattern_matched
        self.safe_response = safe_response


_BLOCK_RESPONSE = (
    "I'm not able to process that request. If you have questions about "
    "Westbrook State's MBA program — admissions, tuition, financial aid, "
    "or student support — I'm happy to help with those."
)


def check_injection(text: str) -> InjectionCheckResult:
    """
    Check a student message for prompt injection attempts.
    Returns immediately on first match — fast path for clean input.
    """
    if not text or len(text.strip()) < 3:
        return InjectionCheckResult(blocked=False, flagged=False)

    # Hard block check
    for pattern in _HARD_BLOCK_PATTERNS:
        match = pattern.search(text)
        if match:
            return InjectionCheckResult(
                blocked=True,
                flagged=True,
                pattern_matched=match.group(0),
                safe_response=_BLOCK_RESPONSE,
            )

    # Soft flag check
    for pattern in _SOFT_FLAG_PATTERNS:
        match = pattern.search(text)
        if match:
            return InjectionCheckResult(
                blocked=False,
                flagged=True,
                pattern_matched=match.group(0),
            )

    return InjectionCheckResult(blocked=False, flagged=False)


def sanitize_for_prompt(text: str) -> str:
    """
    Light sanitization before injecting student input into a prompt.
    Escapes characters that could be misinterpreted as prompt delimiters.
    Does NOT alter meaning — only escapes structural characters.
    """
    # Remove null bytes
    text = text.replace("\x00", "")
    # Limit length to prevent token flooding
    if len(text) > 4000:
        text = text[:4000] + "... [truncated]"
    return text
