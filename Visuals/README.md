# Visuals

Scripts in this folder generate saved comparison data and charts for listed prices vs estimator values.

## Prerequisite

Install plotting dependency:

```bash
pip install matplotlib
```

## 1) Generate comparison data

Run from repo root:

```bash
python3 Visuals/01_generate_estimator_comparison_data.py
```

This reads:

- `src/estimator/cleaned_edmonton_realtor_cards.csv`
- `src/data_sourcing/open_data.db`

And writes:

- `Visuals/property_estimator_comparison.csv`

Useful options:

```bash
python3 Visuals/01_generate_estimator_comparison_data.py --limit 500
python3 Visuals/01_generate_estimator_comparison_data.py --db-path src/data_sourcing/open_data.db
python3 Visuals/01_generate_estimator_comparison_data.py --input-csv src/estimator/cleaned_edmonton_realtor_cards.csv
```

## 2) Create charts from saved data

Run from repo root:

```bash
python3 Visuals/02_create_comparison_charts.py
```

This reads:

- `Visuals/property_estimator_comparison.csv`

And writes:

- `Visuals/chart_listed_vs_estimator_values.png`
- `Visuals/chart_neighborhood_diff_vs_range.png`
- `Visuals/neighborhood_summary.csv`

## Charts produced

1. `chart_listed_vs_estimator_values.png`
   - X axis: listed price
   - Y axis: estimator values (`low`, `final`, `high`) as different colors

2. `chart_neighborhood_diff_vs_range.png`
   - One point per neighborhood (average values)
   - X axis: average estimator total range (`high - low`)
   - Y axis: average difference (`listed price - estimator final`)
