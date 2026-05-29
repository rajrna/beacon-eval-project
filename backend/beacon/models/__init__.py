# Import all models here so Alembic's autogenerate can discover them.
# Order matters for forward-reference resolution in type hints.
from beacon.models.user import AuditLog, User
from beacon.models.institution import Institution, Program
from beacon.models.agent import Agent, AgentVersion
from beacon.models.dataset import Dataset, Example
from beacon.models.judge import Judge, JudgeVersion
from beacon.models.eval import EvalResult, EvalRun
from beacon.models.trace import Annotation, ProductionTrace, ReviewQueueItem

__all__ = [
    "User",
    "AuditLog",
    "Institution",
    "Program",
    "Agent",
    "AgentVersion",
    "Dataset",
    "Example",
    "Judge",
    "JudgeVersion",
    "EvalRun",
    "EvalResult",
    "ProductionTrace",
    "Annotation",
    "ReviewQueueItem",
]
