"""
LLM call tracing with Langfuse integration and JSONL fallback.

Langfuse is the preferred observability backend — it provides:
- Web UI for viewing traces
- Token usage analytics
- Latency histograms
- Error tracking

But Langfuse requires API keys and network access. If either is unavailable,
this module gracefully falls back to JSONL file logging in traces/ directory.

Why both?
- Development: JSONL is zero-setup, works offline
- Production: Langfuse provides rich analytics and team collaboration
- Graceful degradation: Code works regardless of Langfuse availability

Usage:
    tracer = LLMTracer(enabled=True)

    with tracer.trace_generation(
        name="causal_reasoning",
        input_data={"portfolio_id": "P001"},
        metadata={"model": "gemini-2.5-flash"}
    ) as trace:
        result = llm_client.generate(...)
        trace.update(output=result, tokens=result["usage"])
"""

import json
import time
from collections.abc import Generator
from contextlib import contextmanager

from src.config import (
    LANGFUSE_HOST,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    TRACES_DIR,
)


class LLMTracer:
    def __init__(self, enabled: bool = True) -> None:
        """
        Args:
            enabled: If False, all tracing is a no-op (no files written, no API calls).
        """
        self.enabled = enabled
        self.langfuse = None

        if not enabled:
            return

        try:
            from langfuse import Langfuse  # optional dependency

            if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
                self.langfuse = Langfuse(
                    public_key=LANGFUSE_PUBLIC_KEY,
                    secret_key=LANGFUSE_SECRET_KEY,
                    host=LANGFUSE_HOST,
                )
        except (ImportError, Exception) as e:
            # Credentials missing or Langfuse unreachable — fall back silently.
            print(f"Langfuse initialization failed: {e}. Falling back to JSONL logging.")
            self.langfuse = None

    @contextmanager
    def trace_generation(
        self,
        name: str,
        input_data: dict,
        metadata: dict | None = None,
    ) -> Generator:
        """
        Context manager that records one LLM generation call.

        Yields either a Langfuse generation object, a _JSONLTrace, or a _NoOpTrace
        depending on configuration. The caller calls .update() on the yielded object
        to attach output and token counts after the LLM call completes.

        Usage:
            with tracer.trace_generation(name="...", input_data={...}) as trace:
                result = llm_client.generate(...)
                trace.update(output=result, tokens=result["usage"])
        """
        if not self.enabled:
            yield _NoOpTrace()
            return

        start_time = time.time()

        if self.langfuse:
            generation = self.langfuse.generation(
                name=name,
                input=input_data,
                metadata=metadata or {},
            )
            yield generation
            generation.end()
        else:
            trace_data: dict = {
                "name": name,
                "input": input_data,
                "metadata": metadata or {},
                "start_time": start_time,
            }
            yield _JSONLTrace(trace_data, self._log_to_jsonl)

    def _log_to_jsonl(self, trace_data: dict) -> None:
        """Appends a completed trace dict as one line in the JSONL trace file."""
        TRACES_DIR.mkdir(exist_ok=True)
        trace_file = TRACES_DIR / "llm_traces.jsonl"
        with open(trace_file, "a") as f:
            f.write(json.dumps(trace_data) + "\n")


# ---------------------------------------------------------------------------
# Internal trace objects
# ---------------------------------------------------------------------------

class _NoOpTrace:
    """Returned when tracing is disabled — every method is a silent no-op."""

    def update(self, **kwargs) -> None:  # noqa: ANN003
        pass


class _JSONLTrace:
    """Mimics the Langfuse generation API for JSONL-backed tracing."""

    def __init__(self, trace_data: dict, log_fn) -> None:  # noqa: ANN001
        self._trace_data = trace_data
        self._log_fn = log_fn

    def update(self, **kwargs) -> None:  # noqa: ANN003
        """
        Stamps the trace with output/token data and flushes to disk.

        Called once by the caller after the LLM responds. Subsequent calls
        overwrite previous values — that's intentional for simple use cases.
        """
        self._trace_data.update(kwargs)
        end_time = time.time()
        self._trace_data["end_time"] = end_time
        self._trace_data["duration_ms"] = int(
            (end_time - self._trace_data["start_time"]) * 1000
        )
        self._log_fn(self._trace_data)
