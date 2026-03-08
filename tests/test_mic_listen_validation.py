from __future__ import annotations

import unittest

from src.cli.parser import build_parser
from src.live.mic import run_mic_listen


class MicListenValidationTests(unittest.TestCase):
    def test_chunk_mode_requires_explicit_stt_model(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["mic-listen", "--mic-upload-token", "token-1"])
        code = run_mic_listen(args)
        self.assertEqual(code, 1)

    def test_stream_mode_requires_explicit_asr_model(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "mic-listen",
                "--mic-upload-token",
                "token-1",
                "--rt-pipeline-mode",
                "stream",
            ]
        )
        code = run_mic_listen(args)
        self.assertEqual(code, 1)

    def test_stream_mode_requires_valid_hotwords_file(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "mic-listen",
                "--mic-upload-token",
                "token-1",
                "--rt-pipeline-mode",
                "stream",
                "--rt-asr-model",
                "paraformer-realtime-v2",
                "--rt-hotwords-file",
                "/tmp/not_found_hotwords.json",
            ]
        )
        code = run_mic_listen(args)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
