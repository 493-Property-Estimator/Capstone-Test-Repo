#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p coverage/python coverage/frontend coverage/combined

PY_COV_OUT="coverage/python/coverage.txt"
FE_COV_OUT="coverage/frontend/coverage.txt"
COMBINED_OUT="coverage/combined/coverage.txt"

echo "== Python tests + coverage ==" | tee "$PY_COV_OUT"
python3 -m pytest \
  tests src/frontend/tests src/backend/tests scripts/Tests src/estimator/Tests src/data_sourcing/Tests \
  --cov=scripts --cov=src --cov-branch \
  --cov-fail-under=100 \
  --cov-report=term-missing \
  --cov-report=xml:coverage/python/coverage.xml \
  --cov-report=html:coverage/python/html \
  | tee -a "$PY_COV_OUT"

echo "" | tee "$FE_COV_OUT" >/dev/null
echo "== Frontend (node --test) + coverage ==" | tee "$FE_COV_OUT"
npm run test:frontend:coverage | tee -a "$FE_COV_OUT"

{
  echo "Combined coverage report"
  echo "========================"
  echo ""
  echo "---"
  echo ""
  echo "# Python (pytest-cov)"
  echo ""
  cat "$PY_COV_OUT"
  echo ""
  echo "---"
  echo ""
  echo "# Frontend (node --test --experimental-test-coverage)"
  echo ""
  cat "$FE_COV_OUT"
} > "$COMBINED_OUT"

echo ""
echo "Wrote:"
echo "  - $PY_COV_OUT"
echo "  - $FE_COV_OUT"
echo "  - $COMBINED_OUT"
echo "  - coverage/python/html/index.html"
echo "  - coverage/python/coverage.xml"

