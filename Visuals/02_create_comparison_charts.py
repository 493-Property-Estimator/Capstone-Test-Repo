#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: E402
    from matplotlib.ticker import FuncFormatter  # noqa: E402
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: matplotlib. Install it with:\n"
        "  pip install matplotlib\n"
        "Then rerun this chart script."
    ) from exc


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
        # if list_price > 10000000 or est_final > 100000000:
        if list_price > 4000000 or est_final > 20000000:
            continue
        valid.append(row)
    return valid


def _create_chart_1(valid: list[dict[str, str]], out_path: Path) -> None:
    listed = [_parse_float(r["list_price"]) for r in valid]
    est_low = [_parse_float(r["estimator_low"]) for r in valid]
    est_final = [_parse_float(r["estimator_final"]) for r in valid]
    est_high = [_parse_float(r["estimator_high"]) for r in valid]

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.scatter(listed, est_low, s=16, alpha=0.5, c="tab:blue", label="Estimator Low")
    ax.scatter(listed, est_final, s=16, alpha=0.5, c="tab:green", label="Estimator Final")
    ax.scatter(listed, est_high, s=16, alpha=0.5, c="tab:red", label="Estimator High")

    ax.set_title("Listed Price vs Estimator Values")
    ax.set_xlabel("Listed Price")
    ax.set_ylabel("Estimator Value")
    ax.xaxis.set_major_formatter(FuncFormatter(_currency))
    ax.yaxis.set_major_formatter(FuncFormatter(_currency))
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    
def _create_chart_1_subelement(valid: list[dict[str, str]], out_paths: list[Path]) -> None:
    listed = [_parse_float(r["list_price"]) for r in valid]
    est_low = [_parse_float(r["estimator_low"]) for r in valid]
    est_final = [_parse_float(r["estimator_final"]) for r in valid]
    est_high = [_parse_float(r["estimator_high"]) for r in valid]

    fig_l, ax_l = plt.subplots(figsize=(12, 8))
    fig_f, ax_f = plt.subplots(figsize=(12, 8))
    fig_h, ax_h = plt.subplots(figsize=(12, 8))
    ax_l.scatter(listed, est_low, s=16, alpha=0.5, c="tab:blue", label="Estimator Low")
    ax_f.scatter(listed, est_final, s=16, alpha=0.5, c="tab:green", label="Estimator Final")
    ax_h.scatter(listed, est_high, s=16, alpha=0.5, c="tab:red", label="Estimator High")
    
    for axis_a in [ax_l, ax_f, ax_h]:
        axis_a.set_title("Listed Price vs Estimator Values")
        axis_a.set_xlabel("Listed Price")
        axis_a.set_ylabel("Estimator Value")
        axis_a.xaxis.set_major_formatter(FuncFormatter(_currency))
        axis_a.yaxis.set_major_formatter(FuncFormatter(_currency))
        axis_a.grid(True, alpha=0.25)
        axis_a.legend()
    for idx, fig_a in enumerate([fig_l, fig_f, fig_h]):
        fig_a.tight_layout()
        fig_a.savefig(out_paths[idx], dpi=180)
        plt.close(fig_a)


def _create_neighborhood_summary(valid: list[dict[str, str]]) -> list[dict[str, float | str]]:
    buckets: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {
            "list_price": [],
            "estimator_final": [],
            "estimator_range": [],
            "list_minus_estimator": [],
        }
    )

    for row in valid:
        neighborhood = (row.get("neighborhood") or "Unknown").strip() or "Unknown"
        list_price = _parse_float(row.get("list_price"))
        est_final = _parse_float(row.get("estimator_final"))
        est_range = _parse_float(row.get("estimator_range"))
        if list_price is None or est_final is None or est_range is None:
            continue
        buckets[neighborhood]["list_price"].append(list_price)
        buckets[neighborhood]["estimator_final"].append(est_final)
        buckets[neighborhood]["estimator_range"].append(est_range)
        buckets[neighborhood]["list_minus_estimator"].append(list_price - est_final)

    summary: list[dict[str, float | str]] = []
    for neighborhood, vals in buckets.items():
        count = len(vals["list_price"])
        if count == 0:
            continue
        summary.append(
            {
                "neighborhood": neighborhood,
                "sample_count": float(count),
                "avg_list_price": sum(vals["list_price"]) / count,
                "avg_estimator_final": sum(vals["estimator_final"]) / count,
                "avg_estimator_range": sum(vals["estimator_range"]) / count,
                "avg_list_minus_estimator": sum(vals["list_minus_estimator"]) / count,
            }
        )
    summary.sort(key=lambda item: str(item["neighborhood"]))
    return summary


def _write_summary(summary: list[dict[str, float | str]], out_csv: Path) -> None:
    fieldnames = [
        "neighborhood",
        "sample_count",
        "avg_list_price",
        "avg_estimator_final",
        "avg_estimator_range",
        "avg_list_minus_estimator",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary:
            writer.writerow(row)


def _create_chart_2(summary: list[dict[str, float | str]], out_path: Path) -> None:
    x = [float(row["avg_estimator_range"]) for row in summary]
    y = [float(row["avg_list_minus_estimator"]) for row in summary]
    c = [float(row["avg_list_price"]) for row in summary]
    labels = [str(row["neighborhood"]) for row in summary]

    fig, ax = plt.subplots(figsize=(12, 8))
    scatter = ax.scatter(x, y, c=c, cmap="viridis", s=60, alpha=0.9, edgecolors="black", linewidths=0.3)
    colorbar = fig.colorbar(scatter, ax=ax)
    colorbar.set_label("Average Listed Price")

    annotate_count = len(labels) if len(labels) <= 80 else 80
    ranked = sorted(range(len(labels)), key=lambda i: abs(y[i]), reverse=True)[:annotate_count]
    for idx in ranked:
        ax.annotate(labels[idx], (x[idx], y[idx]), fontsize=7, alpha=0.85)

    ax.set_title("Neighborhood Average: Price Difference vs Estimator Range")
    ax.set_xlabel("Average Estimator Total Range (High - Low)")
    ax.set_ylabel("Average (Listed Price - Estimator Final)")
    ax.xaxis.set_major_formatter(FuncFormatter(_currency))
    ax.yaxis.set_major_formatter(FuncFormatter(_currency))
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create comparison charts from saved estimator comparison data."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=REPO_ROOT / "Visuals/property_estimator_comparison.csv",
        help="Input comparison CSV from 01_generate_estimator_comparison_data.py",
    )
    parser.add_argument(
        "--chart-1",
        type=Path,
        default=REPO_ROOT / "Visuals/chart_listed_vs_estimator_values.png",
        help="Output image path for listed price vs estimator values chart.",
    )
    parser.add_argument(
        "--chart-2",
        type=Path,
        default=REPO_ROOT / "Visuals/chart_neighborhood_diff_vs_range.png",
        help="Output image path for neighborhood summary chart.",
    )
    parser.add_argument(
        "--summary-csv",
        type=Path,
        default=REPO_ROOT / "Visuals/neighborhood_summary.csv",
        help="Output CSV path for neighborhood-level aggregated stats.",
    )
    args = parser.parse_args()

    if not args.input_csv.exists():
        raise SystemExit(f"Input comparison CSV not found: {args.input_csv}")

    args.chart_1.parent.mkdir(parents=True, exist_ok=True)
    args.chart_2.parent.mkdir(parents=True, exist_ok=True)
    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = _load_rows(args.input_csv)
    valid = _valid_rows(rows)
    if not valid:
        raise SystemExit("No valid rows found in comparison CSV (all rows had errors or missing values).")

    _create_chart_1(valid, args.chart_1)
    chart_name = args.chart_1
    print(type(chart_name))
    subcharts_names = [Path(str(chart_name).replace("vs_estimator_values", "vs_estimator_values_low")),
                       Path(str(chart_name).replace("vs_estimator_values", "vs_estimator_values_final")),
                       Path(str(chart_name).replace("vs_estimator_values", "vs_estimator_values_high"))]
    _create_chart_1_subelement(valid, subcharts_names)
    summary = _create_neighborhood_summary(valid)
    if not summary:
        raise SystemExit("No neighborhood summary points could be built from valid rows.")
    _write_summary(summary, args.summary_csv)
    _create_chart_2(summary, args.chart_2)

    print(f"Chart 1 written: {args.chart_1}")
    print(f"Chart 2 written: {args.chart_2}")
    print(f"Summary CSV written: {args.summary_csv}")
    print(f"Valid property rows used: {len(valid)}")
    print(f"Neighborhood points plotted: {len(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
