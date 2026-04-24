# MRI Admin Repair Guide (2026-04-24)

This guide explains the data recovery and integrity features available in the MRI Admin Dashboard. These tools are designed to handle data gaps, indicator inconsistencies, and structural changes in Yahoo Finance.

---

## 1. Macro Healing: "Force Repair"

### When to use:
- The "Indicator Coverage" metric is below 100%.
- The "Data Integrity" card shows a **WARNING**.
- You notice several stocks marked with ⚠️ icons in the Global Explorer.

### What it does:
Initiates a background task that scans the entire database for symbols needing repair (NULLs, RS gaps, or stale indicators). It recomputes all technical indicators (EMA, RSI, RS, etc.) using existing historical price data in the database.

### Impact:
- **Low Risk**: It only updates indicator columns; it does not touch or delete raw price history.
- **Async**: Runs in the background; metrics will update on the next dashboard refresh (usually within 1-5 minutes).

---

## 2. Surgical Healing: "🔄 Reset"

### When to use:
- A specific stock's price history appears corrupt or has major gaps.
- Yahoo Finance has changed its ticker structure or split history for a specific symbol.
- "Force Repair" did not fix the ⚠️ icon for a specific stock (indicating the underlying price data is the problem).

### What it does:
This is a "Nuke & Re-ingest" command. It **DELETES** all local records (prices and scores) for that specific symbol. This forces the ingestion engine to treat it as a brand-new stock and fetch its entire history fresh from Yahoo Finance.

### Impact:
- **Moderate Risk**: Permanent deletion of local history for that symbol before re-fetching.
- **Recovery Time**: The stock will temporarily disappear or show as empty until the next background ingestion cycle completes.

---

## 3. Data Integrity Metrics

| Metric | Meaning |
| :--- | :--- |
| **Indicator Coverage** | Percentage of symbols that have successfully computed 50/200 EMAs. |
| **Market Freshness** | Date of the latest price point vs. the latest stock score. |
| **RS Gaps** | Count of stocks where Relative Strength is 0.0 or NULL (Merge failures). |
| **Stale Indicators** | Count of stocks where EMAs haven't moved despite market volume (Pipeline stalls). |
