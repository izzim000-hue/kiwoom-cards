"""원고 로더 (RED 단계 자리표시자: 아무 것도 검증하지 않는다)."""
import json
from pathlib import Path


class SpecError(ValueError):
    pass


ALLOWED_TAGS = ("<g>", "</g>", "<s>", "</s>")


def load_spec(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_legacy_markup(spec):
    return None
