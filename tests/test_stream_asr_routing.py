from __future__ import annotations

import types
import unittest
from unittest import mock

from src.live.insight.stream_asr import DashScopeRealtimeAsrClient


class _FakeRealtimeClient:
    def __init__(self) -> None:
        self.started = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False


class _FakeCallbackBase:
    pass


class _FakeClientWithKwargs:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class StreamAsrRoutingTests(unittest.TestCase):
    @staticmethod
    def _build_client(*, scene: str, model: str) -> DashScopeRealtimeAsrClient:
        return DashScopeRealtimeAsrClient(
            scene=scene,
            model=model,
            api_key="test-key",
            endpoint="wss://dashscope.aliyuncs.com/api-ws/v1/inference",
            hotwords=[],
            translation_target_languages=["zh"],
            on_event=lambda _event: None,
            on_error=lambda _msg: None,
            log_fn=lambda _msg: None,
        )

    def test_multi_paraformer_routes_to_recognition_client(self) -> None:
        client = self._build_client(scene="multi", model="paraformer-realtime-v2")
        dashscope_module = types.SimpleNamespace(api_key="", base_websocket_api_url="")
        asr_module = object()
        with (
            mock.patch("src.live.insight.stream_asr.importlib.import_module") as import_mod,
            mock.patch.object(client, "_build_recognition_client", return_value=_FakeRealtimeClient()) as build_rec,
            mock.patch.object(client, "_build_multi_client", return_value=_FakeRealtimeClient()) as build_multi,
        ):
            import_mod.side_effect = lambda name: dashscope_module if name == "dashscope" else asr_module
            client.start()
            client.stop()
        build_rec.assert_called_once()
        build_multi.assert_not_called()

    def test_gummy_routes_to_translation_client(self) -> None:
        client = self._build_client(scene="zh", model="gummy-realtime-v1")
        dashscope_module = types.SimpleNamespace(api_key="", base_websocket_api_url="")
        asr_module = object()
        with (
            mock.patch("src.live.insight.stream_asr.importlib.import_module") as import_mod,
            mock.patch.object(client, "_build_recognition_client", return_value=_FakeRealtimeClient()) as build_rec,
            mock.patch.object(client, "_build_multi_client", return_value=_FakeRealtimeClient()) as build_multi,
        ):
            import_mod.side_effect = lambda name: dashscope_module if name == "dashscope" else asr_module
            client.start()
            client.stop()
        build_multi.assert_called_once()
        build_rec.assert_not_called()

    def test_recognition_callback_close_and_complete_report_error(self) -> None:
        errors: list[str] = []
        client = DashScopeRealtimeAsrClient(
            scene="zh",
            model="paraformer-realtime-v2",
            api_key="test-key",
            endpoint="wss://dashscope.aliyuncs.com/api-ws/v1/inference",
            hotwords=[],
            translation_target_languages=["zh"],
            on_event=lambda _event: None,
            on_error=errors.append,
            log_fn=lambda _msg: None,
        )
        asr_module = types.SimpleNamespace(
            Recognition=_FakeClientWithKwargs,
            RecognitionCallback=_FakeCallbackBase,
        )
        built = client._build_recognition_client(asr_module)
        callback = built.kwargs["callback"]
        callback.on_close()
        callback.on_complete()
        self.assertEqual(
            errors,
            [
                "dashscope recognition connection closed",
                "dashscope recognition completed",
            ],
        )

    def test_translation_callback_close_and_complete_report_error(self) -> None:
        errors: list[str] = []
        client = DashScopeRealtimeAsrClient(
            scene="multi",
            model="gummy-realtime-v1",
            api_key="test-key",
            endpoint="wss://dashscope.aliyuncs.com/api-ws/v1/inference",
            hotwords=[],
            translation_target_languages=["zh"],
            on_event=lambda _event: None,
            on_error=errors.append,
            log_fn=lambda _msg: None,
        )
        asr_module = types.SimpleNamespace(
            TranslationRecognizerRealtime=_FakeClientWithKwargs,
            TranslationRecognizerCallback=_FakeCallbackBase,
        )
        built = client._build_multi_client(asr_module)
        callback = built.kwargs["callback"]
        callback.on_close()
        callback.on_complete()
        self.assertEqual(
            errors,
            [
                "dashscope translation connection closed",
                "dashscope translation completed",
            ],
        )


if __name__ == "__main__":
    unittest.main()
