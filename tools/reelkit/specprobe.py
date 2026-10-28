"""업로드 규격 검사 (RED 단계 자리표시자: 구현은 다음 커밋)."""
from typing import NamedTuple


class Check(NamedTuple):
    item: str
    status: str
    actual: str
    expected: str


def top_atoms(path):
    return []


def probe(path):
    return []


def format_report(path, checks):
    return []


def main(argv):
    return 0
