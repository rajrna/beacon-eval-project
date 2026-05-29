"""
PII Redaction Pipeline.
Two-layer detection: regex for structured PII, spaCy NER for unstructured.
Raw text never touches disk — redaction runs in worker memory at ingest time.
Stable hashed placeholders: same value in same trace gets same token.
"""
import hashlib
import re
from typing import NamedTuple

import structlog

logger = structlog.get_logger(__name__)

_PATTERNS = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("PHONE", re.compile(r"\b(\+1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("STUDENT_ID", re.compile(r"\b[Ss]\d{6,9}\b|\bID[:\s#]+\d{6,10}\b", re.IGNORECASE)),
    ("CREDIT_CARD", re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b")),
    ("DOB", re.compile(r"\b(?:dob|date\s+of\s+birth)[:\s]+\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b", re.IGNORECASE)),
]

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_lg")
            logger.info("spacy_model_loaded", model="en_core_web_lg")
        except OSError:
            try:
                import spacy
                _nlp = spacy.load("en_core_web_sm")
                logger.warning("spacy_fallback_to_sm")
            except OSError:
                logger.warning("spacy_model_unavailable")
                _nlp = None
    return _nlp


def _make_placeholder(entity_type: str, value: str, trace_salt: str) -> str:
    digest = hashlib.sha256(f"{trace_salt}:{value}".encode()).hexdigest()[:8]
    return f"[{entity_type}_{digest}]"


class RedactionResult(NamedTuple):
    redacted_text: str
    entity_count: int
    entity_types: list


def redact_pii(text: str, trace_salt: str | None = None) -> str:
    if not text:
        return text
    if trace_salt is None:
        import uuid
        trace_salt = str(uuid.uuid4())
    return _redact_with_result(text, trace_salt).redacted_text


def redact_pii_with_result(text: str, trace_salt: str | None = None) -> RedactionResult:
    if not text:
        return RedactionResult(redacted_text=text, entity_count=0, entity_types=[])
    if trace_salt is None:
        import uuid
        trace_salt = str(uuid.uuid4())
    return _redact_with_result(text, trace_salt)


def _redact_with_result(text: str, trace_salt: str) -> RedactionResult:
    entity_types_found: list[str] = []
    redacted = text

    for entity_type, pattern in _PATTERNS:
        def _replace(m: re.Match, et: str = entity_type) -> str:
            placeholder = _make_placeholder(et, m.group(0), trace_salt)
            entity_types_found.append(et)
            return placeholder
        redacted = pattern.sub(_replace, redacted)

    nlp = _get_nlp()
    if nlp is not None:
        try:
            doc = nlp(redacted)
            spans_to_replace = []
            for ent in doc.ents:
                if ent.label_ in ("PERSON", "ORG", "GPE", "LOC", "FAC"):
                    if len(ent.text.strip()) < 3:
                        continue
                    if ent.text.startswith("[") and ent.text.endswith("]"):
                        continue
                    spans_to_replace.append((ent.start_char, ent.end_char, ent.label_, ent.text))
            for start, end, label, value in reversed(spans_to_replace):
                placeholder = _make_placeholder(label, value, trace_salt)
                redacted = redacted[:start] + placeholder + redacted[end:]
                entity_types_found.append(label)
        except Exception as exc:
            logger.warning("spacy_ner_failed", error=str(exc))

    return RedactionResult(
        redacted_text=redacted,
        entity_count=len(entity_types_found),
        entity_types=list(set(entity_types_found)),
    )


def audit_for_missed_pii(text: str) -> list[str]:
    """Scan stored text for patterns that should have been redacted. Used by nightly audit."""
    issues = []
    for entity_type, pattern in _PATTERNS[:4]:
        matches = pattern.findall(text)
        if matches:
            issues.append(f"Potential {entity_type}: {len(matches)} match(es) found")
    return issues
