from __future__ import annotations

import unittest

from src.live.models import StreamInfo
from src.live_ppt import select_ppt_stream
from src.live_video import select_teacher_stream


def mk_stream(type_name: str, voice: bool | None, video: bool | None, m3u8: str) -> StreamInfo:
    return StreamInfo(
        type=None,
        type_name=type_name,
        id="1",
        sub_id="2",
        source_id="3",
        stream_id="4",
        stream_name=type_name,
        video_track=video,
        video_track_on=video,
        voice_track=voice,
        voice_track_on=voice,
        is_gortc=None,
        stream_m3u8=m3u8,
        stream_play="",
        stream_m3u8_meta={},
        stream_play_meta={},
    )


class LiveSelectionTests(unittest.TestCase):
    def test_teacher_prefers_voice_enabled(self) -> None:
        streams = [
            mk_stream("teacher", False, True, "https://a.zju.edu.cn/1.m3u8"),
            mk_stream("teacher", True, True, "https://a.zju.edu.cn/2.m3u8"),
        ]
        best = select_teacher_stream(streams)
        self.assertIsNotNone(best)
        assert best is not None
        self.assertTrue(best.voice_track_on)
        self.assertEqual(best.stream_m3u8, "https://a.zju.edu.cn/2.m3u8")

    def test_ppt_prefers_ppt_type(self) -> None:
        streams = [
            mk_stream("blackboard", None, True, "https://a.zju.edu.cn/1.m3u8"),
            mk_stream("ppt", None, True, "https://a.zju.edu.cn/2.m3u8"),
        ]
        best = select_ppt_stream(streams)
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.type_name, "ppt")

    def test_teacher_prefers_class_when_teacher_has_no_audio(self) -> None:
        streams = [
            mk_stream("teacher", False, True, "https://a.zju.edu.cn/t.m3u8"),
            mk_stream("class", True, True, "https://a.zju.edu.cn/c.m3u8"),
        ]
        best = select_teacher_stream(streams)
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.type_name, "class")


if __name__ == "__main__":
    unittest.main()
