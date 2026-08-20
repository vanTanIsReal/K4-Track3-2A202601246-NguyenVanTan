"""Tracing hooks and span management."""

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.config import get_settings

logger = logging.getLogger(__name__)


class TraceRegistry:
    """In-memory trace collector for evaluation and debugging."""

    _active_spans: list[dict[str, Any]] = []

    @classmethod
    def record_span(cls, span: dict[str, Any]) -> None:
        cls._active_spans.append(span)

    @classmethod
    def get_spans(cls) -> list[dict[str, Any]]:
        return list(cls._active_spans)

    @classmethod
    def clear(cls) -> None:
        cls._active_spans.clear()


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Context manager for tracing agent and service executions.

    Automatically logs timing, metadata, and integrates with LangSmith if configured.
    """
    settings = get_settings()
    if settings.langsmith_api_key and "LANGCHAIN_TRACING_V2" not in os.environ:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

    started = perf_counter()
    span: dict[str, Any] = {
        "name": name,
        "attributes": attributes or {},
        "duration_seconds": 0.0,
        "status": "in_progress",
    }
    try:
        yield span
        span["status"] = "success"
    except Exception as exc:
        span["status"] = "error"
        span["error"] = str(exc)
        raise
    finally:
        span["duration_seconds"] = perf_counter() - started
        TraceRegistry.record_span(span)
        logger.debug(
            f"[Trace] {name} completed in {span['duration_seconds']:.3f}s (status={span['status']})"
        )
