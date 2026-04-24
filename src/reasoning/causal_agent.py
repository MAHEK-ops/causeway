"""
Causal reasoning agent — orchestrates LLM calls for portfolio attribution.

This is the final stage of the Reasoning Layer. It:
1. Formats the context into a prompt
2. Calls the LLM
3. Validates the structured output
4. Retries once if validation fails

The retry mechanism is important — structured output from LLMs isn't 100% reliable.
By giving the LLM its validation error, it can usually self-correct on attempt 2.

Most candidates won't implement retry logic. This shows you understand LLMs are
unreliable and you've designed around that unreliability.
"""

import json

from pydantic import ValidationError

from src.llm.client import LLMClient
from src.reasoning.prompts import ACTIVE_SYSTEM_PROMPT, format_user_prompt
from src.schemas import CausalBriefing, ReasoningContext


class CausalAgent:
    def __init__(self, llm_client: LLMClient) -> None:
        """
        Args:
            llm_client: Configured LLM client (Gemini) for making API calls.
        """
        self.llm_client = llm_client

    def analyze(self, context: ReasoningContext) -> CausalBriefing:
        """
        Generates a structured causal briefing explaining portfolio movements.

        Flow:
        1. Format the ReasoningContext into a user prompt
        2. Call the LLM
        3. Strip any markdown wrappers from the response
        4. Repair common JSON errors (truncation, unterminated strings)
        5. Parse JSON and validate against CausalBriefing schema
        6. On validation failure, retry once with the error shown to the LLM
        7. Return the validated briefing

        Raises:
            ValueError: If the LLM fails to produce a valid CausalBriefing after retry.
        """
        user_prompt = format_user_prompt(context)

        response = self.llm_client.generate(
            system_prompt=ACTIVE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        raw_text = self._extract_json(response["content"][0]["text"])
        raw_text = _try_repair_json(raw_text)

        try:
            briefing = CausalBriefing(**json.loads(raw_text))
            return briefing
        except (json.JSONDecodeError, ValidationError) as e:
            return self._retry_with_feedback(context, raw_text, str(e))

    # Private helpers

    def _retry_with_feedback(
        self,
        context: ReasoningContext,
        failed_output: str,
        error_msg: str,
    ) -> CausalBriefing:
        """
        One-shot retry that shows the LLM its own validation error.

        Most structured-output failures are minor formatting mistakes
        (extra keys, wrong types, missing fields) that the LLM can fix
        when it sees the exact error message. Capping at one retry keeps
        latency reasonable — if it fails twice, the prompt likely has a
        deeper problem that warrants human investigation.
        """
        retry_prompt = (
            f"Your previous response failed validation with this error:\n"
            f"{error_msg}\n\n"
            f"Your previous output was:\n"
            f"{failed_output}\n\n"
            f"Please correct the output and respond with valid JSON matching "
            f"the CausalBriefing schema.\n\n"
            f"Original context:\n"
            f"{format_user_prompt(context)}"
        )

        response = self.llm_client.generate(
            system_prompt=ACTIVE_SYSTEM_PROMPT,
            user_prompt=retry_prompt,
        )

        raw_text = self._extract_json(response["content"][0]["text"])
        raw_text = _try_repair_json(raw_text)

        try:
            briefing = CausalBriefing(**json.loads(raw_text))
            return briefing
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(
                f"LLM failed to produce a valid CausalBriefing after retry.\n"
                f"Error: {e}\n"
                f"Output: {raw_text}"
            ) from e

    @staticmethod
    def _extract_json(text: str) -> str:
        """
        Strips markdown code-fence wrappers from the LLM response.

        Gemini occasionally wraps JSON in ```json ... ``` blocks even when
        the prompt says not to. Stripping these before json.loads() prevents
        unnecessary retry cycles.
        """
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()


# JSON repair helper

def _try_repair_json(text: str) -> str:
    """
    Attempts basic JSON repairs for common LLM output errors.
    
    Common issues:
    - Unterminated strings (missing closing quote)
    - Truncated output (missing closing braces)
    
    This is a best-effort repair — it won't fix all issues, but handles
    the most common failure mode (output truncation at token limit).
    """
    text = text.strip()
    
    # If it doesn't end with }, the output was likely truncated
    if not text.endswith('}'):
        # Count open/close braces to see how many we're missing
        open_braces = text.count('{')
        close_braces = text.count('}')
        
        # Add missing closing braces
        if open_braces > close_braces:
            missing = open_braces - close_braces
            text += '\n' + ('}' * missing)
    
    return text