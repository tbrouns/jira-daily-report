from __future__ import annotations

from openai import OpenAI


class LlmSummarizer:
    def __init__(self, api_key: str, model: str, temperature: float):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def summarize_day(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            temperature=self.temperature,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.output_text.strip()
