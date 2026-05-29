from beacon.judges.accuracy import AccuracyJudge
from beacon.judges.academic_integrity import AcademicIntegrityJudge
from beacon.judges.base import BaseJudge, JudgeResult
from beacon.judges.completeness import CompletenessJudge
from beacon.judges.ferpa_compliance import FERPAComplianceJudge
from beacon.judges.mental_health_safety import MentalHealthSafetyJudge
from beacon.judges.tone import ToneJudge

# Registry — maps slug → judge class
JUDGE_REGISTRY: dict[str, type[BaseJudge]] = {
    AccuracyJudge.slug: AccuracyJudge,
    ToneJudge.slug: ToneJudge,
    CompletenessJudge.slug: CompletenessJudge,
    MentalHealthSafetyJudge.slug: MentalHealthSafetyJudge,
    AcademicIntegrityJudge.slug: AcademicIntegrityJudge,
    FERPAComplianceJudge.slug: FERPAComplianceJudge,
}


def get_judge(slug: str) -> BaseJudge:
    """Instantiate a judge by slug. Raises KeyError if not found."""
    cls = JUDGE_REGISTRY.get(slug)
    if cls is None:
        raise KeyError(f"No judge registered with slug '{slug}'")
    return cls()


def get_all_quality_judges() -> list[BaseJudge]:
    return [AccuracyJudge(), ToneJudge(), CompletenessJudge()]


def get_all_safety_judges() -> list[BaseJudge]:
    return [MentalHealthSafetyJudge(), AcademicIntegrityJudge(), FERPAComplianceJudge()]


__all__ = [
    "BaseJudge", "JudgeResult",
    "AccuracyJudge", "ToneJudge", "CompletenessJudge",
    "MentalHealthSafetyJudge", "AcademicIntegrityJudge", "FERPAComplianceJudge",
    "JUDGE_REGISTRY", "get_judge", "get_all_quality_judges", "get_all_safety_judges",
]
