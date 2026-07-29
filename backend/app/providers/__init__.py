"""Multimodal provider adapter (Task 6.1).

We define a pluggable provider interface. The default adapter speaks the
OpenAI-compatible chat/completions API with image inputs, which works with
OpenAI, Azure OpenAI, OpenRouter, Together, Anyscale, vLLM, Ollama
(``/v1/chat/completions``), and LM Studio. Other providers can be added by
implementing the same Protocol.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

from app.core.config import AppConfig
from app.core.errors import ProviderError
from app.core.logging import get_logger
from app.services import secrets


@dataclass
class AnalysisContext:
    """Inputs we send to the model. NEVER includes secrets."""

    goal: str
    artifact_local_paths: list[str]
    workflow_json: str | None
    metadata_summary: dict[str, str]
    confirmed_evaluations: list[dict[str, Any]]
    include_comparison_context: bool


@dataclass
class AnalysisResult:
    raw_response: dict[str, Any]
    suggestions: dict[str, Any]


class MultimodalProvider(Protocol):
    kind: str

    def analyze(
        self,
        config: AppConfig,
        api_key_ref: str,
        base_url: str,
        model: str,
        context: AnalysisContext,
    ) -> AnalysisResult:
        ...


class OpenAICompatibleProvider:
    kind = "openai_compatible"

    def analyze(
        self,
        config: AppConfig,
        api_key_ref: str,
        base_url: str,
        model: str,
        context: AnalysisContext,
    ) -> AnalysisResult:
        log = get_logger("provider.openai_compatible")
        api_key_bytes = secrets.read_secret(config, api_key_ref)
        api_key = api_key_bytes.decode("utf-8").strip()
        if not api_key:
            raise ProviderError("Provider API key is missing", details={"ref": api_key_ref})

        # Build the multimodal message: text + images.
        text_prompt = _build_prompt(context)
        content: list[dict[str, Any]] = [{"type": "text", "text": text_prompt}]
        for path in context.artifact_local_paths:
            data = Path(path).read_bytes()
            b64 = base64.b64encode(data).decode("ascii")
            mime = _guess_mime(path)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                }
            )

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an image-editing assistant. The user is iterating on a "
                        "ComfyUI experiment. Inspect the image(s) and the goal, then "
                        "respond with structured JSON only. Include keys: "
                        "failure_causes (list of strings), quality_scores "
                        "(object with dimension key -> integer 1-10), overall_score "
                        "(integer 1-10), status (one of success|partial_success|failure), "
                        "and next_steps (list of strings)."
                    ),
                },
                {"role": "user", "content": content},
            ],
            # Ask for strict JSON when supported; harmless otherwise.
            "response_format": {"type": "json_object"},
        }

        url = base_url.rstrip("/") + "/chat/completions"
        try:
            response = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=config.http_timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            log.info("provider.timeout", base_url=base_url, model=model)
            raise ProviderError(
                f"Provider timed out after {config.http_timeout_seconds}s",
                details={"model": model},
            ) from exc
        except httpx.HTTPError as exc:
            log.info("provider.network_error", base_url=base_url)
            raise ProviderError(f"Network error: {exc}", details={"base_url": base_url}) from exc

        if response.status_code >= 400:
            log.info("provider.http_error", status=response.status_code)
            raise ProviderError(
                f"Provider returned HTTP {response.status_code}",
                details={"body_excerpt": response.text[:300]},
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError("Provider returned invalid JSON") from exc

        try:
            inner = data["choices"][0]["message"]["content"]
            parsed = json.loads(inner) if isinstance(inner, str) else inner
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise ProviderError(
                "Provider response did not include parseable JSON suggestions"
            ) from exc

        suggestions = {
            "failure_causes": list(parsed.get("failure_causes", [])),
            "quality_scores": dict(parsed.get("quality_scores", {})),
            "overall_score": parsed.get("overall_score"),
            "status": parsed.get("status"),
            "next_steps": list(parsed.get("next_steps", [])),
        }
        return AnalysisResult(raw_response=data, suggestions=suggestions)


def get_provider(kind: str) -> MultimodalProvider:
    """Pluggable provider registry. New kinds are added here."""
    registry: dict[str, MultimodalProvider] = {
        "openai_compatible": OpenAICompatibleProvider(),
    }
    if kind not in registry:
        raise ProviderError(
            f"Unknown provider kind: {kind}",
            details={"known": sorted(registry)},
        )
    return registry[kind]


def _guess_mime(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }.get(ext, "application/octet-stream")


def _build_prompt(context: AnalysisContext) -> str:
    lines = [f"Goal: {context.goal or '(not set)'}"]
    if context.workflow_json:
        lines.append(f"Workflow JSON (excerpt): {context.workflow_json[:2000]}")
    if context.metadata_summary:
        lines.append("Metadata:")
        for k, v in context.metadata_summary.items():
            lines.append(f"- {k}: {v or '<unknown>'}")
    if context.confirmed_evaluations:
        lines.append("Confirmed evaluations on related candidates:")
        for ev in context.confirmed_evaluations:
            lines.append(f"- {ev}")
    if context.include_comparison_context:
        lines.append(
            "Multiple candidate images are attached. Compare them and explain the trade-offs."
        )
    else:
        lines.append("One candidate image is attached.")
    lines.append(
        "Respond with JSON only: keys failure_causes, quality_scores, "
        "overall_score, status, next_steps."
    )
    return "\n".join(lines)
