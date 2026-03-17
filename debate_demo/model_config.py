"""Shared model configuration for debate agents."""
from __future__ import annotations

import os
from dataclasses import dataclass

from langchain_openai import ChatOpenAI


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


@dataclass(frozen=True)
class ModelSettings:
    model_name: str
    api_token: str
    base_url: str | None = None


def load_model_settings() -> ModelSettings:
    model_name = _first_env("DEBATE_MODEL_NAME", "LLM_MODEL_NAME", "OPENAI_MODEL")
    api_token = _first_env(
        "DEBATE_API_TOKEN",
        "LLM_API_TOKEN",
        "OPENAI_API_TOKEN",
        "DEBATE_API_KEY",
        "LLM_API_KEY",
        "OPENAI_API_KEY",
    )
    base_url = _first_env("DEBATE_BASE_URL", "LLM_BASE_URL", "OPENAI_BASE_URL")

    using_custom_endpoint = any(
        [
            _first_env("DEBATE_BASE_URL", "LLM_BASE_URL", "OPENAI_BASE_URL"),
            _first_env("DEBATE_MODEL_NAME", "LLM_MODEL_NAME", "OPENAI_MODEL"),
            _first_env("DEBATE_API_TOKEN", "LLM_API_TOKEN", "OPENAI_API_TOKEN"),
        ]
    )

    if not api_token:
        raise RuntimeError(
            "Missing API token/key. Set one of: DEBATE_API_TOKEN, LLM_API_TOKEN, "
            "OPENAI_API_TOKEN, DEBATE_API_KEY, LLM_API_KEY, OPENAI_API_KEY."
        )

    if using_custom_endpoint and not base_url:
        raise RuntimeError(
            "Missing base URL for custom model. Set DEBATE_BASE_URL, "
            "LLM_BASE_URL, or OPENAI_BASE_URL."
        )

    if using_custom_endpoint and not model_name:
        raise RuntimeError(
            "Missing model name for custom model. Set DEBATE_MODEL_NAME, "
            "LLM_MODEL_NAME, or OPENAI_MODEL."
        )

    return ModelSettings(
        model_name=model_name or "gpt-4o",
        api_token=api_token,
        base_url=base_url,
    )


def build_chat_model() -> ChatOpenAI:
    settings = load_model_settings()
    kwargs = {
        "model": settings.model_name,
        "api_key": settings.api_token,
        # Company gateway requires upstream LLM calls to use streaming/SSE.
        "streaming": True,
        "disable_streaming": False,
    }
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
    return ChatOpenAI(**kwargs)
