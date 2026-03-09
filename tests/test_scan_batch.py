from __future__ import annotations

import unittest
from unittest import mock

from src.scan.service import CourseScanTarget, scan_courses_batch


class ScanBatchTests(unittest.TestCase):
    def test_scan_batch_reverse_and_stop_when_all_found(self) -> None:
        targets = [
            CourseScanTarget(title="课程A", teacher="老师甲"),
            CourseScanTarget(title="课程B", teacher="老师乙"),
        ]

        def _fake_query(_session, _token, _timeout, course_id, _retries):
            if course_id == 102:
                return {"title": "课程A", "teachers": [{"realname": "老师甲"}]}
            if course_id == 100:
                return {"title": "课程B", "teachers": [{"realname": "老师乙"}]}
            return {"title": "其他课", "teachers": [{"realname": "其他老师"}]}

        with mock.patch("src.scan.service.query_course_detail", side_effect=_fake_query) as query_mock:
            result = scan_courses_batch(
                token="tok",
                timeout=5,
                retries=0,
                center=100,
                radius=3,
                targets=targets,
                workers=1,
                reverse=True,
                stop_when_all_found=True,
                verbose=False,
                on_progress=None,
            )

        self.assertEqual(result.total_candidates, 7)
        self.assertEqual(result.scanned, 4)
        self.assertEqual(query_mock.call_count, 4)
        self.assertEqual(result.matched_count, 2)
        self.assertEqual(result.matches[("课程A", "老师甲")].course_id, 102)
        self.assertEqual(result.matches[("课程B", "老师乙")].course_id, 100)
        self.assertEqual(result.missing_keys, [])

    def test_scan_batch_missing_target(self) -> None:
        targets = [
            CourseScanTarget(title="课程A", teacher="老师甲"),
            CourseScanTarget(title="课程B", teacher="老师乙"),
        ]

        with mock.patch(
            "src.scan.service.query_course_detail",
            return_value={"title": "课程A", "teachers": [{"realname": "老师甲"}]},
        ):
            result = scan_courses_batch(
                token="tok",
                timeout=5,
                retries=0,
                center=100,
                radius=1,
                targets=targets,
                workers=1,
                reverse=True,
                stop_when_all_found=True,
                verbose=False,
                on_progress=None,
            )

        self.assertEqual(result.matched_count, 1)
        self.assertEqual(result.matches[("课程A", "老师甲")].course_id, 101)
        self.assertEqual(result.missing_keys, [("课程B", "老师乙")])


if __name__ == "__main__":
    unittest.main()
