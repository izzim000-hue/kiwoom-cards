"""장면 목록을 프레임 상태 목록으로 펼치고 길이와 표지 시점을 계산한다."""
from typing import NamedTuple

from .constants import LINE, HOLD


class State(NamedTuple):
    top: str
    lines: list
    k: int        # 드러난 줄 수 (1..len(lines))
    dur: float    # 이 상태가 화면에 머무는 시간(초)
    scene: int    # 0부터 시작하는 장면 번호


def build_states(spec):
    states = []
    for si, sc in enumerate(spec["scenes"]):
        n = len(sc["lines"])
        for k in range(1, n + 1):
            states.append(State(sc["top"], sc["lines"], k, LINE if k < n else HOLD, si))
    return states


def total_duration(states):
    # 부동소수 합산 순서가 기존 reel.py와 같아야 -t 와 출력 길이가 일치한다
    return sum(s.dur for s in states)


def progress_values(states):
    total = total_duration(states)
    t = 0
    out = []
    for s in states:
        t += s.dur
        out.append(t / total)
    return out


def cover_ms(spec):
    first = len(spec["scenes"][0]["lines"])
    return round((LINE * (first - 1) + 0.4) * 1000)
