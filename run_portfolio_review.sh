#!/bin/bash
# Portfolio Review Engine — CLI runner
# Usage:
#   ./run_portfolio_review.sh --stock RELIANCE
#   ./run_portfolio_review.sh --holdings '[{"symbol":"RELIANCE","quantity":10,"avg_cost":2500}]'
#   ./run_portfolio_review.sh --file my_portfolio.json
#   ./run_portfolio_review.sh   (runs demo with sample portfolio)

set -euo pipefail
cd "$(dirname "$0")"

echo "=== MRI Portfolio Review Engine ==="
python -m src.portfolio_review_engine "$@"
