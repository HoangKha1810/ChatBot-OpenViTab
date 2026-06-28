from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any

import requests

from app.config import (
    ANSWER_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_PREDICT,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT_SECONDS,
    OLLAMA_TOP_P,
    SCHEMA_EMBED_FALLBACK_MODEL,
    SCHEMA_EMBED_MODEL,
    TABLEQA_REQUIRE_GPU,
    TABLEQA_REQUIRE_MODELS,
    TABLEQA_USE_MODELS,
    TEXT_TO_SQL_MODEL,
    VERIFIER_MODEL,
)
from app.progress import add_progress


class ModelUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelSettings:
    enabled: bool = TABLEQA_USE_MODELS
    required: bool = TABLEQA_REQUIRE_MODELS
    backend: str = "ollama"
    base_url: str = OLLAMA_BASE_URL
    schema_embed_model: str = SCHEMA_EMBED_MODEL
    schema_embed_fallback_model: str = SCHEMA_EMBED_FALLBACK_MODEL
    text_to_sql_model: str = TEXT_TO_SQL_MODEL
    answer_model: str = ANSWER_MODEL
    verifier_model: str = VERIFIER_MODEL
    keep_alive: str = OLLAMA_KEEP_ALIVE
    num_ctx: int = OLLAMA_NUM_CTX
    num_predict: int = OLLAMA_NUM_PREDICT
    temperature: float = OLLAMA_TEMPERATURE
    top_p: float = OLLAMA_TOP_P

    @property
    def required_models(self) -> tuple[str, ...]:
        return (
            self.schema_embed_model,
            self.schema_embed_fallback_model,
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
                "schema_linking_fallback": self.settings.schema_embed_fallback_model,
                "text_to_sql": self.settings.text_to_sql_model,
                "answer_synthesis": self.settings.answer_model,
                "verification": self.settings.verifier_model,
            },
            "ollama_options": {
                "keep_alive": self.settings.keep_alive,
                "num_ctx": self.settings.num_ctx,
                "num_predict": self.settings.num_predict,
                "temperature": self.settings.temperature,
                "top_p": self.settings.top_p,
            },
        }

    def ensure_ready(self, request_id: str = "startup") -> None:
        if not self.settings.enabled:
            if self.settings.required:
                raise ModelUnavailableError("TABLEQA_USE_MODELS=0 but TABLEQA_REQUIRE_MODELS=1.")
            add_progress(request_id, "models", "Model runtime disabled by TABLEQA_USE_MODELS=0.")
            return

        add_progress(request_id, "models", f"Checking Ollama at {self.settings.base_url}.")
        status = self.status()
        if status.get("available"):
            models = ", ".join(status.get("models") or [])
            add_progress(request_id, "models", f"Required models ready: {models}.")
            return

        missing = ", ".join(status.get("missing") or [])
        base = self.settings.base_url
        message = (
            "Real model runtime is not ready. Ollama must be running at "
            f"{base} with these models installed: {missing}. Run `python scripts/setup_ollama_models.py`."
        )
        if self.settings.required:
            add_progress(request_id, "models", f"Not ready: {message}")
            raise ModelUnavailableError(message)

    def ensure_gpu(self, request_id: str = "startup") -> None:
        if not TABLEQA_REQUIRE_GPU:
            add_progress(request_id, "gpu", "TABLEQA_REQUIRE_GPU=0, skipping hard GPU requirement.")
            return
        if shutil.which("nvidia-smi") is None:
            raise ModelUnavailableError("TABLEQA_REQUIRE_GPU=1 but `nvidia-smi` was not found.")
        try:
            output = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader",
                ],
                text=True,
                timeout=10,
            ).strip()
        except Exception as exc:
            raise ModelUnavailableError(f"Could not check the NVIDIA GPU: {exc}") from exc
        if not output:
            raise ModelUnavailableError("TABLEQA_REQUIRE_GPU=1 but `nvidia-smi` returned no GPU.")
        add_progress(request_id, "gpu", f"NVIDIA GPU detected: {output.splitlines()[0]}.")

    def warmup(self, request_id: str = "startup") -> None:
        if not self.settings.enabled:
            add_progress(request_id, "warmup", "Model runtime disabled, skipping Ollama warm-up.")
            return

        add_progress(request_id, "warmup", f"Warming up embedding model {self.settings.schema_embed_model}.")
        self.embed(self.settings.schema_embed_model, ["GPU check for Vietnamese TableQA"], request_id=request_id)

        for model in dict.fromkeys(
            [
                self.settings.text_to_sql_model,
                self.settings.answer_model,
                self.settings.verifier_model,
            ]
        ):
            add_progress(request_id, "warmup", f"Warming up chat model {model}.")
            self._post_ollama_json(
                "/api/chat",
                {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Return JSON only."},
                        {"role": "user", "content": '{"ok": true}'},
                    ],
                    "stream": False,
                    "format": "json",
                    "keep_alive": self.settings.keep_alive,
                    "options": {
                        "temperature": self.settings.temperature,
                        "top_p": self.settings.top_p,
                        "num_ctx": self.settings.num_ctx,
                        "num_predict": 64,
                        "seed": 42,
                    },
                },
                request_id,
                "warmup",
            )
            add_progress(request_id, "warmup", f"{model} warm-up OK.")

    def ensure_ollama_gpu_loaded(self, request_id: str = "startup") -> None:
        if not TABLEQA_REQUIRE_GPU:
            return
        if shutil.which("ollama") is None:
            raise ModelUnavailableError("TABLEQA_REQUIRE_GPU=1 but the `ollama` command was not found.")
        try:
            output = subprocess.check_output(["ollama", "ps"], text=True, timeout=10).strip()
        except Exception as exc:
            raise ModelUnavailableError(f"Could not run `ollama ps` to check GPU loading: {exc}") from exc
        add_progress(request_id, "gpu", f"ollama ps: {output or 'no loaded models'}")
        if "gpu" not in output.lower():
            raise ModelUnavailableError("Ollama loaded a model, but `ollama ps` does not report GPU usage. Check the CUDA/NVIDIA runtime.")

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

    def chat_json(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float | None = None,
        request_id: str = "ollama",
    ) -> tuple[dict[str, Any], float, str]:
        add_progress(request_id, "ollama_chat", f"Calling {model}.")
        started = time.perf_counter()
        temperature = self.settings.temperature if temperature is None else temperature
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "keep_alive": self.settings.keep_alive,
            "options": {
                "temperature": temperature,
                "top_p": self.settings.top_p,
                "num_ctx": self.settings.num_ctx,
                "num_predict": self.settings.num_predict,
                "seed": 42,
            },
        }
        response = self._post_ollama_json("/api/chat", payload, request_id, "ollama_chat")
        content = response.json().get("message", {}).get("content", "")
        parsed = _parse_json_object(content)
        latency = round((time.perf_counter() - started) * 1000, 2)
        add_progress(request_id, "ollama_chat", f"{model} completed in {latency} ms.")
        return parsed, latency, content

    def embed(self, model: str, texts: list[str], request_id: str = "ollama") -> tuple[list[list[float]], float]:
        add_progress(request_id, "ollama_embed", f"Calling {model} for {len(texts)} text(s).")
        started = time.perf_counter()
        try:
            embeddings = self._embed_once(model, texts, request_id)
            latency = round((time.perf_counter() - started) * 1000, 2)
            add_progress(request_id, "ollama_embed", f"{model} completed in {latency} ms.")
            return embeddings, latency
        except Exception as exc:
            fallback = self.settings.schema_embed_fallback_model
            if not fallback or fallback == model or model != self.settings.schema_embed_model:
                raise
            add_progress(request_id, "ollama_embed", f"{model} failed ({exc}); retrying with fallback {fallback}.")
            fallback_started = time.perf_counter()
            embeddings = self._embed_once(fallback, texts, request_id)
            latency = round((time.perf_counter() - fallback_started) * 1000, 2)
            add_progress(request_id, "ollama_embed", f"{fallback} fallback completed in {latency} ms.")
            return embeddings, latency

    def _embed_once(self, model: str, texts: list[str], request_id: str) -> list[list[float]]:
        response = self._post_ollama_json(
            "/api/embed",
            {"model": model, "input": texts, "keep_alive": self.settings.keep_alive},
            request_id,
            "ollama_embed",
        )
        payload = response.json()
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list):
            raise ModelUnavailableError(f"Ollama returned an invalid embed response for model {model}.")
        return embeddings

    def _post_ollama_json(
        self,
        endpoint: str,
        payload: dict[str, Any],
        request_id: str,
        stage: str,
        attempts: int = 2,
    ) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                response = requests.post(
                    f"{self.settings.base_url}{endpoint}",
                    json=payload,
                    timeout=OLLAMA_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                detail = _describe_response_error(exc)
                if attempt < attempts:
                    add_progress(request_id, stage, f"{endpoint} failed on attempt {attempt}; retrying. {detail}")
                    time.sleep(1.5)
                    continue
                raise ModelUnavailableError(f"Ollama {endpoint} failed after {attempts} attempts. {detail}") from exc
        raise ModelUnavailableError(f"Ollama {endpoint} failed: {last_error}")


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
        raise ValueError("Model did not return a JSON object.")
    return data


def _describe_response_error(exc: requests.RequestException) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return str(exc)
    body = (response.text or "").strip().replace("\n", " ")
    if len(body) > 500:
        body = f"{body[:500]}..."
    return f"{exc}; body={body or '<empty>'}"
