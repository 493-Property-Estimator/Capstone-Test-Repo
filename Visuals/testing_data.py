import argparse
import csv
from collections import defaultdict
from pathlib import Path
import matplotlib


REPO_ROOT = Path(__file__).resolve().parent.parent


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _currency(x: float, _pos: object) -> str:
    return f"${x:,.0f}"


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
    
def _valid_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    valid: list[dict[str, str]] = []
    for row in rows:
        if (row.get("error") or "").strip():
            continue
        list_price = _parse_float(row.get("list_price"))
        est_low = _parse_float(row.get("estimator_low"))
        est_final = _parse_float(row.get("estimator_final"))
        est_high = _parse_float(row.get("estimator_high"))
        if list_price is None or est_low is None or est_final is None or est_high is None:
            continue
        valid.append(row)
    return valid


def main():
    rows = _load_rows(Path(REPO_ROOT / "Visuals/property_estimator_comparison.csv"))
    valid = _valid_rows(rows)
    if not valid:
        raise SystemExit("No valid rows found in comparison CSV (all rows had errors or missing values).")