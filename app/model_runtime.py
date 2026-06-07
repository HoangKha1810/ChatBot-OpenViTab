from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import requests

from app.config import (
    ANSWER_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_TIMEOUT_SECONDS,
    SCHEMA_EMBED_MODEL,
    TABLEQA_REQUIRE_MODELS,
    TABLEQA_USE_MODELS,
    TEXT_TO_SQL_MODEL,
    VERIFIER_MODEL,
)


class ModelUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelSettings:
    enabled: bool = TABLEQA_USE_MODELS
    required: bool = TABLEQA_REQUIRE_MODELS
    backend: str = "ollama"
    base_url: str = OLLAMA_BASE_URL
    schema_embed_model: str = SCHEMA_EMBED_MODEL
    text_to_sql_model: str = TEXT_TO_SQL_MODEL
    answer_model: str = ANSWER_MODEL
    verifier_model: str = VERIFIER_MODEL

    @property
    def required_models(self) -> tuple[str, ...]:
        return (
            self.schema_embed_model,
            self.text_to_sql_model,
            self.answer_model,
            self.verifier_model,
        )


class OllamaRuntime:
    def __init__(self, settings: ModelSettings | None = None) -> None:
        self.settings = settings or ModelSettings()

    def status(self) -> dict[str, Any]:
        if not self.settings.enabled:
            return {
                "enabled": False,
                "backend": self.settings.backend,
                "base_url": self.settings.base_url,
                "required": self.settings.required,
                "available": False,
                "models": [],
                "missing": list(dict.fromkeys(self.settings.required_models)),
            }

        try:
            available = self.list_models()
        except Exception as exc:
            return {
                "enabled": True,
                "backend": self.settings.backend,
                "base_url": self.settings.base_url,
                "required": self.settings.required,
                "available": False,
                "error": str(exc),
                "models": [],
                "missing": list(dict.fromkeys(self.settings.required_models)),
            }

        missing = self.missing_models(available)
        return {
            "enabled": True,
            "backend": self.settings.backend,
            "base_url": self.settings.base_url,
            "required": self.settings.required,
            "available": not missing,
            "models": available,
            "missing": missing,
            "task_models": {
                "schema_linking": self.settings.schema_embed_model,
                "text_to_sql": self.settings.text_to_sql_model,
                "answer_synthesis": self.settings.answer_model,
                "verification": self.settings.verifier_model,
            },
        }

    def ensure_ready(self) -> None:
        if not self.settings.enabled:
            if self.settings.required:
                raise ModelUnavailableError("TABLEQA_USE_MODELS=0 nhưng TABLEQA_REQUIRE_MODELS=1.")
            return

        status = self.status()
        if status.get("available"):
            return

        missing = ", ".join(status.get("missing") or [])
        base = self.settings.base_url
        message = (
            "Model thật chưa sẵn sàng. Cần Ollama đang chạy tại "
            f"{base} và các model: {missing}. Chạy `python scripts/setup_ollama_models.py`."
        )
        if self.settings.required:
            raise ModelUnavailableError(message)

    def list_models(self) -> list[str]:
        response = requests.get(f"{self.settings.base_url}/api/tags", timeout=5)
        response.raise_for_status()
        payload = response.json()
        names = [item.get("name", "") for item in payload.get("models", [])]
        return sorted(name for name in names if name)

    def missing_models(self, available: list[str] | None = None) -> list[str]:
        available_names = set(available if available is not None else self.list_models())
        missing = []
        for model in dict.fromkeys(self.settings.required_models):
            aliases = {model, f"{model}:latest"} if ":" not in model else {model}
            if not (aliases & available_names):
                missing.append(model)
        return missing

    def chat_json(self, model: str, system: str, user: str, temperature: float = 0.0) -> tuple[dict[str, Any], float, str]:
        started = time.perf_counter()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
                "top_p": 0.8,
                "num_ctx": 8192,
            },
        }
        response = requests.post(
            f"{self.settings.base_url}/api/chat",
            json=payload,
            timeout=OLLAMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", "")
        parsed = _parse_json_object(content)
        return parsed, round((time.perf_counter() - started) * 1000, 2), content

    def embed(self, model: str, texts: list[str]) -> tuple[list[list[float]], float]:
        started = time.perf_counter()
        response = requests.post(
            f"{self.settings.base_url}/api/embed",
            json={"model": model, "input": texts},
            timeout=OLLAMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list):
            raise ModelUnavailableError(f"Ollama embed response không hợp lệ cho model {model}.")
        return embeddings, round((time.perf_counter() - started) * 1000, 2)


def get_runtime() -> OllamaRuntime:
    return OllamaRuntime()


def _parse_json_object(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Model không trả về JSON object.")
    return data
