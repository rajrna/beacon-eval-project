"""
Regression testing service.

Automatically triggered when a new AgentVersion is created.
Finds all datasets for the agent's program, enqueues eval runs
for the new version, and records baseline scores from the previous
version for comparison.
"""
import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = structlog.get_logger(__name__)


class RegressionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def trigger_regression(
        self,
        agent_id: uuid.UUID,
        new_version_id: uuid.UUID,
        previous_version_id: uuid.UUID | None,
    ) -> list[str]:
        """
        Enqueue regression eval runs for a new agent version.

        Finds all datasets scoped to the agent's program, enqueues one
        eval run per dataset using the default active judge versions.
        Returns list of enqueued run IDs.

        Best-effort — never raises, just logs on failure.
        """
        try:
            return await self._trigger(agent_id, new_version_id, previous_version_id)
        except Exception as exc:
            logger.error(
                "regression_trigger_failed",
                agent_id=str(agent_id),
                new_version_id=str(new_version_id),
                error=str(exc),
            )
            return []

    async def _trigger(
        self,
        agent_id: uuid.UUID,
        new_version_id: uuid.UUID,
        previous_version_id: uuid.UUID | None,
    ) -> list[str]:
        from sqlalchemy import select
        from beacon.models.agent import Agent, AgentVersion
        from beacon.models.eval import EvalRun
        from beacon.models.judge import Judge, JudgeVersion
        from beacon.workers.eval_runner import enqueue_eval_run

        # Load agent to get program_id
        agent_result = await self.session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if not agent:
            logger.warning("regression_agent_not_found", agent_id=str(agent_id))
            return []

        # Load all datasets for this program
        from beacon.models.dataset import Dataset
        datasets_result = await self.session.execute(
            select(Dataset).where(Dataset.program_id == agent.program_id)
        )
        datasets = datasets_result.scalars().all()

        if not datasets:
            logger.info(
                "regression_no_datasets",
                program_id=str(agent.program_id),
                agent_id=str(agent_id),
            )
            return []

        # Get active judge versions (one per judge)
        judge_version_ids = await self._get_active_judge_version_ids()
        if not judge_version_ids:
            logger.warning("regression_no_active_judges")
            return []

        # Enqueue one eval run per dataset
        run_ids = []
        for dataset in datasets:
            try:
                run_id = await self._create_and_enqueue_run(
                    agent_version_id=new_version_id,
                    dataset_id=dataset.id,
                    judge_version_ids=judge_version_ids,
                    is_regression=True,
                    baseline_version_id=previous_version_id,
                )
                run_ids.append(run_id)
                logger.info(
                    "regression_run_enqueued",
                    run_id=run_id,
                    dataset_id=str(dataset.id),
                    dataset_name=dataset.name,
                    new_version_id=str(new_version_id),
                )
            except Exception as exc:
                logger.warning(
                    "regression_run_enqueue_failed",
                    dataset_id=str(dataset.id),
                    error=str(exc),
                )

        logger.info(
            "regression_triggered",
            agent_id=str(agent_id),
            new_version_id=str(new_version_id),
            previous_version_id=str(previous_version_id) if previous_version_id else None,
            datasets_count=len(datasets),
            runs_enqueued=len(run_ids),
        )

        return run_ids

    async def _get_active_judge_version_ids(self) -> list[str]:
        """Get the latest approved (or any) version ID for each judge."""
        from beacon.models.judge import Judge, JudgeVersion

        # Get all judges
        judges_result = await self.session.execute(select(Judge))
        judges = judges_result.scalars().all()

        version_ids = []
        for judge in judges:
            # Prefer approved versions, fall back to latest
            approved_result = await self.session.execute(
                select(JudgeVersion)
                .where(JudgeVersion.judge_id == judge.id)
                .where(JudgeVersion.is_approved == True)
                .order_by(JudgeVersion.version_number.desc())
                .limit(1)
            )
            version = approved_result.scalar_one_or_none()

            if not version:
                # Fall back to latest version
                latest_result = await self.session.execute(
                    select(JudgeVersion)
                    .where(JudgeVersion.judge_id == judge.id)
                    .order_by(JudgeVersion.version_number.desc())
                    .limit(1)
                )
                version = latest_result.scalar_one_or_none()

            if version:
                version_ids.append(str(version.id))

        return version_ids

    async def _create_and_enqueue_run(
        self,
        agent_version_id: uuid.UUID,
        dataset_id: uuid.UUID,
        judge_version_ids: list[str],
        is_regression: bool,
        baseline_version_id: uuid.UUID | None,
    ) -> str:
        """Create an EvalRun row and enqueue it to RQ."""
        from datetime import datetime, timezone
        from beacon.models.eval import EvalRun
        from beacon.workers.eval_runner import enqueue_eval_run

        run = EvalRun(
            id=uuid.uuid4(),
            agent_version_id=agent_version_id,
            dataset_id=dataset_id,
            judge_version_ids=judge_version_ids,
            status="queued",
            is_regression=True,
            baseline_version_id=baseline_version_id,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(run)
        await self.session.flush()

        # Enqueue to RQ (fire and forget)
        enqueue_eval_run(str(run.id))

        return str(run.id)