from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.config import Settings


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def estimate_cost(input_tokens: int, output_tokens: int, settings: Settings) -> float:
    return round(
        (input_tokens / 1000 * settings.estimated_input_cost_per_1k)
        + (output_tokens / 1000 * settings.estimated_output_cost_per_1k),
        8,
    )


def write_trace(settings: Settings, trace: dict[str, Any]) -> None:
    path = settings.log_path
    path.parent.mkdir(parents=True, exist_ok=True)
    trace = {"created_at_epoch": time.time(), **trace}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(trace, default=str) + "\n")
