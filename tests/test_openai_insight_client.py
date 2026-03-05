from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.live.insight.models import KeywordConfig
from src.live.insight.openai_client import OpenAIInsightClient


class _FakeAudioTranscriptions:
    def create(self, **kwargs):
        return type("Resp", (), {"text": "今天讲了微积分和导数"})()


class _FakeAudio:
    def __init__(self) -> None:
        self.transcriptions = _FakeAudioTranscriptions()


class _FakeResponses:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text

    def create(self, **kwargs):
        return type("Resp", (), {"output_text": self.output_text})()


class _FakeOpenAI:
    def __init__(self, *, api_key: str, timeout: float) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.audio = _FakeAudio()
        self.responses = _FakeResponses(
            '{"important": true, "summary": "提到微积分", '
            '"context_summary": "老师在讲极限和导数关系", '
            '"matched_terms": ["微积分", "导数"], "reason": "keyword_hit"}'
        )


class OpenAIInsightClientTests(unittest.TestCase):
    def test_transcribe_and_analyze_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            chunk = Path(td) / "chunk.mp3"
            chunk.write_bytes(b"audio-bytes")
            with mock.patch("src.live.insight.openai_client._load_openai_cls", return_value=_FakeOpenAI):
                client = OpenAIInsightClient(api_key="k", timeout_sec=12.0)
                text = client.transcribe_chunk(
                    chunk_path=chunk,
                    stt_model="gpt-4o-mini-transcribe",
                    timeout_sec=5.0,
                )
                result = client.analyze_text(
                    analysis_model="gpt-5-mini",
                    keywords=KeywordConfig(important_terms=["微积分"]),
                    current_text=text,
                    context_text="无历史文本块",
                    timeout_sec=5.0,
                )
        self.assertIn("微积分", text)
        self.assertTrue(result.important)
        self.assertIn("导数", result.matched_terms)

    def test_transcribe_timeout_raises(self) -> None:
        class _TimeoutAudioTranscriptions:
            def create(self, **kwargs):
                raise TimeoutError("transcribe timeout")

        class _TimeoutOpenAI:
            def __init__(self, *, api_key: str, timeout: float) -> None:
                self.audio = type("Audio", (), {"transcriptions": _TimeoutAudioTranscriptions()})()
                self.responses = _FakeResponses("{}")

        with tempfile.TemporaryDirectory() as td:
            chunk = Path(td) / "chunk.mp3"
            chunk.write_bytes(b"audio-bytes")
            with mock.patch(
                "src.live.insight.openai_client._load_openai_cls",
                return_value=_TimeoutOpenAI,
            ):
                client = OpenAIInsightClient(api_key="k", timeout_sec=12.0)
                with self.assertRaises(TimeoutError):
                    client.transcribe_chunk(
                        chunk_path=chunk,
                        stt_model="gpt-4o-mini-transcribe",
                        timeout_sec=2.0,
                    )

    def test_analyze_invalid_json(self) -> None:
        class _BadOpenAI:
            def __init__(self, *, api_key: str, timeout: float) -> None:
                self.audio = _FakeAudio()
                self.responses = _FakeResponses("not-json")

        with mock.patch("src.live.insight.openai_client._load_openai_cls", return_value=_BadOpenAI):
            client = OpenAIInsightClient(api_key="k", timeout_sec=12.0)
            with self.assertRaises(ValueError):
                client.analyze_text(
                    analysis_model="gpt-5-mini",
                    keywords=KeywordConfig(),
                    current_text="文本",
                    context_text="无历史文本块",
                    timeout_sec=2.0,
                )


if __name__ == "__main__":
    unittest.main()
