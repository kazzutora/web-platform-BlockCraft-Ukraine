"""Recorded real answers of the sources (R1.2); see _requests.json in each folder."""

import json
from functools import cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent / "fixtures"


@cache
def _text(source: str, name: str) -> str:
    return (ROOT / source / f"{name}.json").read_text(encoding="utf-8")


def load(source: str, name: str) -> Any:
    """A fresh copy every time, so a test may change it."""
    return json.loads(_text(source, name))
