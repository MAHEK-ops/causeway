"""
Disk-based cache for LLM responses keyed by (model, prompt, temperature).

Prevents redundant API calls during development and makes demo runs instant.
A cache hit saves ~2-4 seconds and $0.01-0.05 per call.
"""

import hashlib
from pathlib import Path

import diskcache


class LLMCache:
    def __init__(self, cache_dir: Path, enabled: bool = True) -> None:
        """
        Args:
            cache_dir: Directory to store cached responses on disk.
            enabled: If False, all gets return None (cache is transparent bypass).
        """
        self.enabled = enabled
        self._cache = diskcache.Cache(str(cache_dir))

    def _make_key(self, model: str, prompt: str, temperature: float) -> str:
        """
        Deterministic cache key from (model, prompt, temperature).

        SHA-256 of the concatenated inputs gives a fixed-length, collision-resistant
        key even when prompts are thousands of tokens long.
        """
        raw = f"{model}|{prompt}|{temperature}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, model: str, prompt: str, temperature: float) -> dict | None:
        """Return the cached response dict, or None on miss / when disabled."""
        if not self.enabled:
            return None
        key = self._make_key(model, prompt, temperature)
        return self._cache.get(key)  # type: ignore[return-value]

    def set(self, model: str, prompt: str, temperature: float, response: dict) -> None:
        """Persist a response dict under the derived cache key."""
        if not self.enabled:
            return
        key = self._make_key(model, prompt, temperature)
        self._cache.set(key, response)
