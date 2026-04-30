from __future__ import annotations

import logging
import random
import re
import time

from openai import OpenAI, RateLimitError

logger = logging.getLogger(__name__)

RETRY_AFTER_SECONDS_RE = re.compile(r"Please try again in\s+([0-9]+(?:\.[0-9]+)?)s", re.IGNORECASE)


class LlmSummarizer:
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        max_retries: int = 5,
        initial_backoff_seconds: float = 2.0,
        max_backoff_seconds: float = 30.0,
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.initial_backoff_seconds = initial_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds

    def summarize_day(self, system_prompt: str, user_prompt: str) -> str:
        return self._summarize(system_prompt=system_prompt, user_prompt=user_prompt)

    def summarize_month_overview(self, system_prompt: str, user_prompt: str) -> str:
        return self._summarize(system_prompt=system_prompt, user_prompt=user_prompt)

    def _summarize(self, system_prompt: str, user_prompt: str) -> str:
        attempt = 0

        while True:
            try:
                response = self.client.responses.create(
                    model=self.model,
                    temperature=self.temperature,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return response.output_text.strip()
            except RateLimitError as exc:
                if attempt >= self.max_retries:
                    raise

                delay_seconds = self._compute_retry_delay(exc=exc, attempt=attempt)
                logger.warning(
                    "OpenAI rate limit hit for model %s. Retrying in %.2fs (attempt %d/%d).",
                    self.model,
                    delay_seconds,
                    attempt + 1,
                    self.max_retries,
                )
                time.sleep(delay_seconds)
                attempt += 1

    def _compute_retry_delay(self, *, exc: RateLimitError, attempt: int) -> float:
        retry_after = self._extract_retry_after_seconds(exc)
        if retry_after is not None:
            return min(max(retry_after, 0.0) + 0.5, self.max_backoff_seconds)

        exponential = min(self.initial_backoff_seconds * (2**attempt), self.max_backoff_seconds)
        jitter = random.uniform(0.0, 0.5)
        return exponential + jitter

    @staticmethod
    def _extract_retry_after_seconds(exc: RateLimitError) -> float | None:
        message = str(exc)
        match = RETRY_AFTER_SECONDS_RE.search(message)
        if not match:
            return None
        return float(match.group(1))
