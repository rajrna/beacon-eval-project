"""
Langfuse client wrapper.
Handles trace creation, score writing, and dataset mirroring.
Beacon uses Langfuse as the source of truth for raw traces and scores.
All writes are best-effort — a Langfuse outage never blocks eval runs.
"""
from typing import Any

import structlog

from beacon.core.settings import get_settings

logger = structlog.get_logger(__name__)


class LangfuseClient:
    """Thin wrapper around the Langfuse Python SDK."""

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
        """Create a Langfuse trace. Returns the trace ID or None if disabled."""
        if not self._enabled or not self._client:
            return None
        try:
            trace = self._client.trace(
                name=name,
                metadata=metadata or {},
                tags=tags or [],
            )
            return trace.id
        except Exception as exc:
            logger.warning("langfuse_create_trace_failed", error=str(exc))
            return None

    def score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
        observation_id: str | None = None,
    ) -> None:
        """Write a score to a Langfuse trace. Best-effort."""
        if not self._enabled or not self._client:
            return
        try:
            kwargs: dict[str, Any] = {
                "trace_id": trace_id,
                "name": name,
                "value": value,
            }
            if comment:
                kwargs["comment"] = comment
            if observation_id:
                kwargs["observation_id"] = observation_id
            self._client.score(**kwargs)
        except Exception as exc:
            logger.warning("langfuse_score_failed", trace_id=trace_id, error=str(exc))

    def create_run(self, dataset_name: str, run_name: str, metadata: dict | None = None) -> str | None:
        """Create a Langfuse dataset run. Returns run name or None."""
        if not self._enabled or not self._client:
            return None
        try:
            self._client.create_dataset_run(
                dataset_name=dataset_name,
                run_name=run_name,
                metadata=metadata or {},
            )
            return run_name
        except Exception as exc:
            logger.warning("langfuse_create_run_failed", error=str(exc))
            return None

    def flush(self) -> None:
        """Flush pending writes. Call at end of eval run."""
        if self._enabled and self._client:
            try:
                self._client.flush()
            except Exception as exc:
                logger.warning("langfuse_flush_failed", error=str(exc))


# Module-level singleton
_langfuse: LangfuseClient | None = None


def get_langfuse_client() -> LangfuseClient:
    global _langfuse
    if _langfuse is None:
        _langfuse = LangfuseClient()
    return _langfuse
