"""timeline.cover_ms 반올림 시험 (렌더 없음)."""
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from reelkit import timeline  # noqa: E402


def spec_with_first_scene(n):
    return {"scenes": [{"top": "", "lines": ["줄"] * n}]}


class CoverMs(unittest.TestCase):
    def test_exact_values_for_every_first_scene_length(self):
        # 0.85초 * (줄 수 - 1) + 0.4초 를 밀리초로. 4줄·10줄은 부동소수 때문에 내림되면 1ms 어긋난다
        for n in range(1, 13):
            expected = 850 * (n - 1) + 400
            self.assertEqual(timeline.cover_ms(spec_with_first_scene(n)), expected, f"first scene {n} lines")

    def test_four_and_ten_lines_are_not_truncated(self):
        self.assertEqual(timeline.cover_ms(spec_with_first_scene(4)), 2950)
        self.assertEqual(timeline.cover_ms(spec_with_first_scene(10)), 8050)


if __name__ == "__main__":
    unittest.main()
