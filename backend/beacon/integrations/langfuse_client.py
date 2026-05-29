"""
Langfuse client wrapper — compatible with Langfuse SDK v4.
Handles trace creation, score writing, and eval run tracking.
All writes are best-effort — a Langfuse outage never blocks eval runs.
"""
from typing import Any

import structlog

from beacon.core.settings import get_settings

logger = structlog.get_logger(__name__)


class LangfuseClient:
    """Wrapper around the Langfuse Python SDK v4."""

    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = bool(settings.langfuse_public_key and settings.langfuse_secret_key)
        self._client: Any = None

        if self._enabled:
            try:
                from langfuse import Langfuse
                self._client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                )
                logger.info("langfuse_client_initialized", host=settings.langfuse_host)
            except Exception as exc:
                logger.warning("langfuse_init_failed", error=str(exc))
                self._enabled = False
        else:
            logger.info("langfuse_disabled_no_keys")

    def create_trace(
        self,
        name: str,
        run_id: str,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> str | None:
        """Create a Langfuse trace for an eval run. Returns a trace ID."""
        if not self._enabled or not self._client:
            return None
        try:
            # v4: use create_trace_id to generate a stable ID, then
            # start an observation which creates the trace implicitly
            trace_id = self._client.create_trace_id(seed=run_id)
            obs = self._client.start_observation(
                name=name,
                as_type="span",
                metadata={**(metadata or {}), "run_id": run_id},
                trace_context={"trace_id": trace_id},
            )
            obs.end()
            logger.debug("langfuse_trace_created", trace_id=trace_id)
            return trace_id
        except Exception as exc:
            logger.warning("langfuse_create_trace_failed", error=str(exc))
            return None

    def score_trace(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
        observation_id: str | None = None,
    ) -> None:
        """Write a numeric score to a Langfuse trace. Best-effort."""
        if not self._enabled or not self._client:
            return
        try:
            self._client.create_score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment,
                observation_id=observation_id,
                data_type="NUMERIC",
            )
        except Exception as exc:
            logger.warning("langfuse_score_failed", trace_id=trace_id, name=name, error=str(exc))

    # Keep old name as alias for backward compatibility with eval_runner
    def score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
        observation_id: str | None = None,
    ) -> None:
        self.score_trace(trace_id, name, value, comment, observation_id)

    def create_run(
        self,
        dataset_name: str,
        run_name: str,
        metadata: dict | None = None,
    ) -> str | None:
        """
        Create a Langfuse dataset run reference.
        In v4, dataset runs are created via create_dataset_item calls.
        We return a stable run ID derived from run_name.
        """
        if not self._enabled or not self._client:
            return None
        try:
            # Ensure dataset exists
            try:
                self._client.create_dataset(name=dataset_name)
            except Exception:
                pass  # Dataset may already exist

            logger.debug("langfuse_run_reference_created", run_name=run_name)
            return run_name
        except Exception as exc:
            logger.warning("langfuse_create_run_failed", error=str(exc))
            return None

    def log_eval_result(
        self,
        dataset_name: str,
        run_name: str,
        input: str,
        output: str,
        metadata: dict | None = None,
        scores: dict[str, float] | None = None,
    ) -> None:
        """
        Log one eval result to a Langfuse dataset run.
        Creates a dataset item and attaches scores.
        """
        if not self._enabled or not self._client:
            return
        try:
            # Create a trace for this eval result
            trace_id = self._client.create_trace_id()
            obs = self._client.start_observation(
                name=f"{run_name}_result",
                as_type="generation",
                input=input,
                output=output,
                metadata=metadata or {},
                trace_context={"trace_id": trace_id},
            )
            obs.end()

            # Write scores
            if scores:
                for score_name, score_value in scores.items():
                    self._client.create_score(
                        trace_id=trace_id,
                        name=score_name,
                        value=score_value,
                        data_type="NUMERIC",
                    )

            # Create dataset item linking to this trace
            self._client.create_dataset_item(
                dataset_name=dataset_name,
                input=input,
                expected_output=output,
                metadata={**(metadata or {}), "run_name": run_name, "trace_id": trace_id},
            )
        except Exception as exc:
            logger.warning("langfuse_log_eval_result_failed", error=str(exc))

    def get_trace_url(self, trace_id: str) -> str | None:
        """Get the Langfuse UI URL for a trace."""
        if not self._enabled or not self._client:
            return None
        try:
            return self._client.get_trace_url(trace_id=trace_id)
        except Exception:
            settings = get_settings()
            return f"{settings.langfuse_host}/trace/{trace_id}"

    def flush(self) -> None:
        """Flush pending writes. Call at end of eval run."""
        if self._enabled and self._client:
            try:
                self._client.flush()
                logger.debug("langfuse_flushed")
            except Exception as exc:
                logger.warning("langfuse_flush_failed", error=str(exc))


# Module-level singleton
_langfuse: LangfuseClient | None = None


def get_langfuse_client() -> LangfuseClient:
    global _langfuse
    if _langfuse is None:
        _langfuse = LangfuseClient()
    return _langfuse
