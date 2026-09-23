"""Load the official CSV or equivalent JSONL without inventing missing data."""
import csv
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional, Union

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data/hackathon-dataset-anonymized.csv"


@dataclass
class Contractor:
    id: str
    anon_name: str
    categories: List[str]
    city: str
    city_imputed: bool
    synthetic: bool
    price_from_kzt: Optional[int]
    price_imputed: bool
    event_formats: List[str]
    languages: List[str]
    max_hours: Optional[float]
    busy_dates: List[str]
    description: str


def _list(value) -> List[str]:
    return list(value) if isinstance(value, list) else [s.strip() for s in (value or "").split("|") if s.strip()]


def _bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value not in ("True", "False"):
        raise ValueError("Boolean must be True or False")
    return value == "True"


def load_profiles(path: Optional[Union[str, Path]] = None) -> List[Contractor]:
    source = Path(path or os.getenv("DATA_PATH") or DEFAULT_PATH)
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = [json.loads(line) for line in stream if line.strip()] if source.suffix == ".jsonl" else list(csv.DictReader(stream))
    profiles = []
    seen = set()
    for row in rows:
        values = dict(row)
        for key in ("categories", "event_formats", "languages", "busy_dates"):
            values[key] = _list(values[key])
        for busy_date in values["busy_dates"]:
            if date.fromisoformat(busy_date).isoformat() != busy_date:
                raise ValueError("busy_dates must use YYYY-MM-DD")
        for key in ("synthetic", "city_imputed", "price_imputed"):
            values[key] = _bool(values[key])
        for key, cast in (("price_from_kzt", int), ("max_hours", float)):
            values[key] = None if values[key] in (None, "") else cast(values[key])
            if values[key] is not None and values[key] < 0:
                raise ValueError("Negative " + key)
        profile = Contractor(**values)
        if profile.id in seen:
            raise ValueError("Duplicate contractor id: " + profile.id)
        seen.add(profile.id)
        profiles.append(profile)
    return profiles
