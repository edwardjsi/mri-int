#!/bin/bash
source venv/bin/activate
set -a
source .env
set +a

if [ -z "$UPSTOX_ACCESS_TOKEN" ]; then
    echo "Error: UPSTOX_ACCESS_TOKEN not found in .env"
    exit 1
fi

TOKEN_START="${UPSTOX_ACCESS_TOKEN:0:15}"
TOKEN_END="${UPSTOX_ACCESS_TOKEN: -5}"
MASKED_TOKEN="${TOKEN_START}...[REDACTED]...${TOKEN_END}"

echo "============================================================"
echo " VERBOSE cURL DIAGNOSTIC FOR UPSTOX SUPPORT"
echo "============================================================"

# Run the curl command and capture stderr and stdout
OUTPUT=$(curl -v -X GET "https://api.upstox.com/v3/historical-candle/NSE_EQ%7CINE002A01018/days/1/2026-08-15/2026-08-01" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer ${UPSTOX_ACCESS_TOKEN}" 2>&1)

# Mask the token in the output before displaying
echo "$OUTPUT" | sed "s/${UPSTOX_ACCESS_TOKEN}/${MASKED_TOKEN}/g"

echo ""
echo "============================================================"
