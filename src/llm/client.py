"""
Google Gemini API client with automatic retries, timeout handling, and response caching.

All LLM calls in Causeway go through this client. It handles infrastructure concerns
(retries, timeouts, caching) so reasoning modules can focus on prompt engineering.
"""

import os

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import MAX_TOKENS, MODEL_NAME, TEMPERATURE
from src.llm.cache import LLMCache


class LLMClient:
    """Gemini API client with caching and retry logic."""

    def __init__(self, cache: LLMCache | None = None) -> None:
        """
        Args:
            cache: Optional LLMCache. When None, every call hits the API.
        """
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable not set. "
                "Get one free at https://aistudio.google.com/"
            )
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(MODEL_NAME)
        self._cache = cache

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """
        Calls Gemini and returns a normalised response dict.

        Checks the disk cache first; only hits the API on a miss, then writes
        the result back to the cache so the next identical call is instant.

        Returns:
            {
                "content":     [{"type": "text", "text": str}],
                "usage":       {"input_tokens": int, "output_tokens": int},
                "model":       str,
                "stop_reason": str,
            }
        """
        _model = model or MODEL_NAME
        _temperature = temperature if temperature is not None else TEMPERATURE
        _max_tokens = max_tokens or MAX_TOKENS

        # Both prompts influence the output, so key on their concatenation.
        cache_prompt = f"{system_prompt}\n\n{user_prompt}"

        if self._cache:
            cached = self._cache.get(_model, cache_prompt, _temperature)
            if cached is not None:
                return cached

        response = self._call_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=_model,
            temperature=_temperature,
            max_tokens=_max_tokens,
        )

        if self._cache:
            self._cache.set(_model, cache_prompt, _temperature, response)

        return response

    @retry(
        retry=retry_if_exception_type((
            google_exceptions.ServiceUnavailable,
            google_exceptions.TooManyRequests,
            google_exceptions.InternalServerError,
        )),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        # DeadlineExceeded and InvalidArgument are not retried — a timeout budget
        # won't grow on retry and a malformed request won't heal itself.
        reraise=True,
    )
    def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        """
        Makes one API call, retrying only on transient service errors.

        Gemini has no separate system-prompt parameter, so the system and user
        prompts are joined before sending. Tenacity re-raises after 3 failed
        attempts so the caller sees the original exception.
        """
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        response = self._model.generate_content(
            full_prompt,
            generation_config=generation_config,
        )

        input_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
        output_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0

        stop_reason = (
            response.candidates[0].finish_reason.name
            if response.candidates
            else "UNKNOWN"
        )

        return {
            "content": [{"type": "text", "text": response.text}],
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
            "model": model,
            "stop_reason": stop_reason,
        }
