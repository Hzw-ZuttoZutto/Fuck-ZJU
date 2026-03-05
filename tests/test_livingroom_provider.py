from __future__ import annotations

import json
import unittest
from unittest import mock

import requests

from src.live.providers.livingroom_provider import LivingRoomStreamProvider


class _Resp:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict:
        return self._payload


class LivingRoomProviderTests(unittest.TestCase):
    def test_fetch_streams_from_sub_content_outputs(self) -> None:
        session = mock.Mock(spec=requests.Session)
        sub_content = {
            "output": {
                "m3u8": "https://livepgc.cmc.zju.edu.cn/pgc/teacher.m3u8?auth_key=1-0-0-x",
                "rtmp": "rtmp://livepgc.cmc.zju.edu.cn/pgc/teacher?auth_key=x",
            },
            "output_student": {
                "m3u8": "https://livepgc.cmc.zju.edu.cn/pgc/ppt.m3u8?auth_key=1-0-0-y",
                "rtmp": "rtmp://livepgc.cmc.zju.edu.cn/pgc/ppt?auth_key=y",
            },
        }
        session.get.side_effect = [
            _Resp(
                {
                    "success": True,
                    "data": {
                        "code": 200,
                        "msg": "success",
                        "data": {
                            "id": "1276762",
                            "template_id": "27217",
                            "name": "ai数字教师",
                            "modules": [
                                {"code": "one_videos_live_liu"},
                                {"code": "ppt_live_liu"},
                            ],
                        },
                    },
                }
            ),
            _Resp(
                {
                    "code": 200,
                    "message": "查询成功",
                    "params": {
                        "rtcScreenType": "merge",
                        "rtcStudentStream": 1,
                    },
                }
            ),
            _Resp(
                {
                    "code": 0,
                    "msg": "获取直播课列表成功",
                    "list": [
                        {
                            "sub_id": "1895320",
                            "sub_status": "1",
                            "sub_type": "course_live",
                            "room_type": "0",
                            "sub_content": json.dumps(sub_content, ensure_ascii=False),
                        }
                    ],
                }
            ),
        ]

        provider = LivingRoomStreamProvider(
            session=session,
            token="tok",
            timeout=10,
            course_id=83617,
            sub_id=1895320,
            tenant_code="112",
        )
        result = provider.fetch()

        self.assertTrue(result.success)
        self.assertEqual(len(result.stream_infos), 2)
        by_role = {s.type_name: s for s in result.stream_infos}
        self.assertIn("teacher", by_role)
        self.assertIn("ppt", by_role)
        self.assertTrue(by_role["teacher"].stream_m3u8.endswith("auth_key=1-0-0-x"))
        self.assertTrue(by_role["ppt"].stream_m3u8.endswith("auth_key=1-0-0-y"))
        self.assertEqual(result.diagnostics.get("template_name"), "ai数字教师")
        self.assertEqual(result.diagnostics.get("rtc_screen_type"), "merge")


if __name__ == "__main__":
    unittest.main()
