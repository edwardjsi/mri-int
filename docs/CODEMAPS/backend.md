# 🛸 Backend Architecture — MRI Codemap

**Last Updated:** 2026-04-05  
**Entry Points:** `scripts/mri_pipeline.py`, `api/main.py`

## Architecture Overview
[EOD Data: Yahoo/NSE/BSE] -> **Ingestion Engine** -> [PostgreSQL: daily_prices]
                                       |
                                       v
[Indicators: EMA/RS/Slope] <--- **Indicator Engine**
                                       |
                                       v
[Scores: 0-100 Weighted] <--- **Scoring Engine**
                                       |
                                       v
[Actionable Signals] <--- **Signal Generator** -> [Email: AWS SES]

---

## Key Modules
| Module | Purpose | Key Exports | 
|--------|---------|-------------|
| `src/ingestion_engine.py` | Multi-batch EOD fetching & normalization. | `load_stocks`, `sync_universe` |
| `src/indicator_engine.py` | Technical indicator computation (Pandas). | `compute_all_indicators` |
| `src/regime_engine.py` | Global Market Regime filter (0-100). | `calculate_regime_score` |
| `src/signal_generator.py` | 0-100 Weighted Trend Scoring. | `get_recommendations` |
| `src/db.py` | Hardened SQL interaction utilities. | `get_connection`, `insert_daily_prices` |

---

## 🛡️ Hardened Pipeline Features
- **SQLi Protection**: All queries are parameterized via `psycopg2.sql`.
- **Connection Integrity**: Strict context-manager ( `with` blocks) for all DB transactions.
- **Auto-Rescue**: Ingestion automatically triggers a 2-year backfill if history is <200 rows.

## Related Areas
- [Database Codemap](file:///home/edwar/mri-int/docs/CODEMAPS/database.md)
