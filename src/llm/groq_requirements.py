from __future__ import annotations

import json
import time

from groq import Groq
from pydantic import ValidationError

from src.config.settings import settings
from src.domain.models import HiringRequirements


class RequirementExtractionError(RuntimeError):
    pass


def _make_schema_strict(value: object) -> None:
    """Apply Groq's structured-output constraints to a Pydantic JSON schema."""
    if isinstance(value, dict):
        if value.get("type") == "object" or "properties" in value:
            value["additionalProperties"] = False
            properties = value.get("properties")
            if isinstance(properties, dict):
                value["required"] = list(properties)
        for child in value.values():
            _make_schema_strict(child)
    elif isinstance(value, list):
        for child in value:
            _make_schema_strict(child)


SYSTEM_PROMPT = """You extract hiring requirements from job descriptions.
Return only factual requirements stated or strongly implied by the text.
Do not rank candidates. Do not invent requirements. Consolidate synonyms.
Use concise noun phrases. If a field is absent, use an empty list or null/zero.
"""


class GroqRequirementExtractor:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or settings.groq_api_key
        if not key:
            raise RequirementExtractionError("GROQ_API_KEY is not configured.")
        self.client = Groq(api_key=key)
        self.model = model or settings.groq_model

    def extract(self, job_description: str) -> HiringRequirements:
        schema = HiringRequirements.model_json_schema()
        _make_schema_strict(schema)
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": job_description[:30000]},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "hiring_requirements",
                            "strict": True,
                            "schema": schema,
                        },
                    },
                )
                content = response.choices[0].message.content or "{}"
                return HiringRequirements.model_validate(json.loads(content))
            except (json.JSONDecodeError, ValidationError, Exception) as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(0.5)
        raise RequirementExtractionError(f"Groq requirement extraction failed: {last_error}")
