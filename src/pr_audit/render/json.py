from __future__ import annotations

import json
from dataclasses import asdict

from ..models import Audit


def render_json(audit: Audit) -> str:
    return json.dumps(asdict(audit), indent=2, ensure_ascii=False) + "\n"
