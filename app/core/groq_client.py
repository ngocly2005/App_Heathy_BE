"""Backend-only Groq adapter for meal chat and food-photo estimates."""

import base64
import json
import logging
import re
from typing import TypeVar

from fastapi import HTTPException
from groq import APIError, APIStatusError, Groq
from groq.types.chat import ChatCompletionContentPartParam, ChatCompletionMessageParam
from httpx import RequestError
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)
logger = logging.getLogger(__name__)


def ask_groq(
    *,
    system_instruction: str,
    prompt: str,
    response_schema: type[ResponseModel],
    image_data: bytes | None = None,
    image_mime_type: str | None = None,
) -> ResponseModel:
    settings = get_settings()
    api_key = (
        settings.groq_api_key.get_secret_value().strip() if settings.groq_api_key else ""
    )
    if not api_key:
        raise HTTPException(status_code=503, detail="Configure GROQ_API_KEY")

    content: str | list[ChatCompletionContentPartParam] = prompt
    if image_data is not None:
        if not image_mime_type:
            raise ValueError("image_mime_type is required for image_data")
        encoded = base64.b64encode(image_data).decode("ascii")
        content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image_mime_type};base64,{encoded}"},
            },
        ]

    # JSON mode guarantees syntax, not our field names or nutrition limits.
    # Supply the existing schema as instructions and validate it locally below.
    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": (
                f"{system_instruction}\n"
                "Return only a JSON object matching this JSON Schema:\n"
                f"{json.dumps(response_schema.model_json_schema(), ensure_ascii=False)}"
            ),
        },
        {"role": "user", "content": content},
    ]
    try:
        with Groq(
            api_key=api_key,
            base_url="https://api.groq.com",
            timeout=30.0,
            max_retries=0,
        ) as client:
            response = client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                response_format={"type": "json_object"},
                reasoning_format="hidden",
                temperature=0.2,
                max_completion_tokens=4096,
            )
    except (APIError, RequestError, ValueError) as error:
        # Provider bodies can echo API keys, health context or base64 images.
        # Log only diagnostic metadata, never the exception text or body.
        logger.warning(
            "Groq request failed: error_type=%s upstream_status_code=%s model=%s",
            type(error).__name__,
            error.status_code if isinstance(error, APIStatusError) else None,
            settings.groq_model,
        )
        raise HTTPException(
            status_code=502, detail="AI provider could not complete request"
        ) from error

    if not response.choices:
        raise HTTPException(status_code=502, detail="AI returned no usable result")
    choice = response.choices[0]
    if choice.finish_reason != "stop" or not choice.message.content:
        raise HTTPException(status_code=502, detail="AI returned no usable result")

    text = re.sub(r"\A\s*<think>.*?</think>\s*", "", choice.message.content, flags=re.S).strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.S | re.I)
    if fenced:
        text = fenced.group(1)
    try:
        return response_schema.model_validate_json(text)
    except ValidationError as error:
        raise HTTPException(status_code=502, detail="AI returned invalid data") from error
