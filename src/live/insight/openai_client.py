from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.live.insight.models import KeywordConfig
from src.live.insight.prompting import build_system_prompt, build_user_prompt


class OpenAIClientUnavailableError(RuntimeError):
    pass


def _load_openai_cls():
    try:
        from openai import OpenAI  # type: ignore

        return OpenAI
    except Exception as exc:  # pragma: no cover - import error path
        raise OpenAIClientUnavailableError(
            "openai sdk is unavailable; install dependencies from requirements.txt"
        ) from exc


@dataclass
class InsightModelResult:
    important: bool
    summary: str
    context_summary: str
    matched_terms: list[str]
    reason: str


class OpenAIInsightClient:
    def __init__(self, *, api_key: str, timeout_sec: float) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is empty")
        openai_cls = _load_openai_cls()
        self.client = openai_cls(api_key=api_key, timeout=max(2.0, float(timeout_sec)))

    def transcribe_chunk(
        self,
        *,
        chunk_path: Path,
        stt_model: str,
        timeout_sec: float,
    ) -> str:
        if not stt_model:
            raise ValueError("stt_model is empty")
        with chunk_path.open("rb") as handle:
            response = self.client.audio.transcriptions.create(
                model=stt_model,
                file=handle,
                timeout=max(1.0, float(timeout_sec)),
            )
        return _extract_transcript_text(response)

    def analyze_text(
        self,
        *,
        analysis_model: str,
        keywords: KeywordConfig,
        current_text: str,
        context_text: str,
        timeout_sec: float,
    ) -> InsightModelResult:
        if not analysis_model:
            raise ValueError("analysis_model is empty")
        response = self.client.responses.create(
            model=analysis_model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": build_system_prompt()}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": build_user_prompt(
                                keywords=keywords,
                                current_text=current_text,
                                context_text=context_text,
                            ),
                        }
                    ],
                },
            ],
            temperature=0,
            max_output_tokens=320,
            timeout=max(1.0, float(timeout_sec)),
        )
        output_text = _extract_output_text(response)
        payload = _parse_json_payload(output_text)
        return InsightModelResult(
            important=_to_bool(payload.get("important")),
            summary=str(payload.get("summary", "")).strip(),
            context_summary=str(payload.get("context_summary", "")).strip(),
            matched_terms=_to_str_list(payload.get("matched_terms")),
            reason=str(payload.get("reason", "")).strip(),
        )


def _extract_transcript_text(response: Any) -> str:
    text = ""
    if isinstance(response, dict):
        text = str(response.get("text", "")).strip()
    else:
        text = str(getattr(response, "text", "")).strip()
        if not text and hasattr(response, "model_dump"):
            dumped = response.model_dump()
            text = str(dumped.get("text", "")).strip()
    if not text:
        raise ValueError("transcription response has no text")
    return text


def _extract_output_text(response: Any) -> str:
    direct = getattr(response, "output_text", None)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    output = getattr(response, "output", None)
    text = _extract_text_from_output(output)
    if text:
        return text

    if hasattr(response, "model_dump"):
        dumped = response.model_dump()
        text = _extract_text_from_output(dumped.get("output"))
        if text:
            return text
    raise ValueError("model response has no output_text")


def _extract_text_from_output(output: Any) -> str:
    if not isinstance(output, list):
        return ""
    parts: list[str] = []
    for item in output:
        content = None
        if isinstance(item, dict):
            content = item.get("content")
        else:
            content = getattr(item, "content", None)
            if content is None and hasattr(item, "model_dump"):
                content = item.model_dump().get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict):
                block_type = block.get("type")
                if block_type in {"output_text", "text"}:
                    text = str(block.get("text", "")).strip()
                    if text:
                        parts.append(text)
            else:
                block_type = getattr(block, "type", "")
                if block_type in {"output_text", "text"}:
                    text = str(getattr(block, "text", "")).strip()
                    if text:
                        parts.append(text)
    return "\n".join(parts).strip()


def _parse_json_payload(text: str) -> dict:
    raw = text.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"model output is not valid JSON: {text}") from exc
    if not isinstance(payload, dict):
        raise ValueError("model output JSON must be object")
    return payload


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes", "y"}:
            return True
        if text in {"false", "0", "no", "n"}:
            return False
    if isinstance(value, int):
        return value != 0
    return False


def _to_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            items.append(text)
    return items
