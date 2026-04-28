# MRI Data Quality Service Level Agreement (SLA)

## 🎯 Purpose
To ensure that the Market Regime Intelligence (MRI) platform serves accurate, timely, and complete quantitative indicators to all clients. This SLA defines the minimum standards for data integrity and the automated measures to enforce them.

## 📊 Key Performance Indicators (KPIs)

| Metric | Target | Critical Threshold (Circuit Breaker) |
|--------|--------|--------------------------------------|
| **Indicator Coverage** | > 99% non-NULL | < 80% (Pipeline Halts) |
| **Market Freshness** | 0 days drift | > 2 days (Alert Triggered) |
| **Price Integrity** | 0 anomalous spikes | > 50% single-day move (Audit Rejected) |
| **Score Variance** | Standard deviation > 15 | All scores identical (Validation Failure) |

---

## 🛡️ Enforcement Mechanisms

### 1. The Circuit Breaker (Pipeline Halt)
The `indicator_engine.py` includes a post-update validation gate. If more than **20%** of symbols in the latest date have NULL indicators, the pipeline will raise a `IndicatorComputationError` and halt. This prevents stale or corrupted signals from reaching clients.

### 2. The Write-Verify-Read Pattern
Every bulk update to the database is followed by a **sample verification**:
- After writing indicators, the engine randomly samples 50 updated rows.
- If the verification rate is below **90%**, the transaction is rolled back and an alert is sent.

### 3. Drift Detection (Health Monitor)
The `scripts/pipeline_health_monitor.py` runs as the final step of every pipeline run. It compares the max dates across:
- `daily_prices`
- `stock_scores`
- `market_regime`
- `market_index_prices`

If any table lags behind by more than **2 days**, an SES alert is dispatched to the admin team.

---

## 🔧 Recovery Procedures

If the SLA is breached, the following "Force Repair" actions should be taken:

1.  **Manual Ingestion**: Run `python engine_core/ingestion_engine.py` for the missing symbols.
2.  **Indicator Recompute**: Run `python engine_core/indicator_engine.py --all` to force-populate NULL values.
3.  **Regime Sync**: Run `python engine_core/regime_engine.py` to bridge trend gaps.

---

## 📝 Governance
This SLA is maintained by the Lead AI Engineer and enforced via automated checks in `.github/workflows/FINAL_FIX.yml`.
