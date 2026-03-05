from __future__ import annotations

import unittest

from src.live.templates import render_player_html


class TemplateTests(unittest.TestCase):
    def test_player_requires_manual_click_to_start(self) -> None:
        html = render_player_html("teacher", 20)
        self.assertIn('id="video"', html)
        self.assertNotIn("autoplay", html)
        self.assertIn('id="play-layer"', html)
        self.assertIn('id="play-btn"', html)
        self.assertIn('id="play-state"', html)
        self.assertIn("等待手动播放", html)
        self.assertIn("let userStarted = false", html)
        self.assertIn("playBtn.addEventListener('click'", html)
        self.assertIn("if (!userStarted)", html)
        self.assertNotIn('id="sound-btn"', html)
        self.assertIn("video.controls = false", html)
        self.assertIn("tryUnlockAudio", html)
        self.assertIn("voice_track=0", html)


if __name__ == "__main__":
    unittest.main()
