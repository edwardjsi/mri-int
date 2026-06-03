#!/bin/bash
# ============================================================
# MRI Morning Brief — Pre-Market HoF & Shadow Debut Alert
#
# Sends a concise morning email with Hall of Fame and Strategy
# Shadow debuts from the latest pipeline run. Does NOT re-run
# the pipeline — queries existing data only.
#
# Usage:
#   bash scripts/morning_brief.sh
#
# Cron (8:55 AM IST, Mon-Fri):
#   55 8 * * 1-5 cd /path/to/mri-int && bash scripts/morning_brief.sh >> logs/morning_brief.log 2>&1
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/morning_brief_$(date +%Y%m%d).log"

echo "=== MRI Morning Brief — $(date) ===" | tee -a "$LOG_FILE"

cd "$PROJECT_DIR"

# Use the same Python environment as the main pipeline
python -c "
from engine_core.email_service import send_morning_brief
count = send_morning_brief()
print(f'Sent morning brief to {count} clients')
" 2>&1 | tee -a "$LOG_FILE"

echo "=== Morning Brief Complete — $(date) ===" | tee -a "$LOG_FILE"
