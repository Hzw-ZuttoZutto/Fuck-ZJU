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


if __name__ == "__main__":
    unittest.main()
