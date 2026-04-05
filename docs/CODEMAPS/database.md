# 🗄️ Database Schema — MRI Codemap

**Last Updated:** 2026-04-05  
**Entry Point:** `src/db.py`, `api/schema.py`

## Architecture Overview
[daily_prices: BIGINT, TIMESTAMPTZ] -> **Tracking Engine** -> [index_prices: BIGINT, TIMESTAMPTZ]
                                       |
                                       v
[client_id: UUID, RLS: ENABLED] <--- **Multi-Tenant Isolation**
                                       |
                                       v
[Portfolio: client_portfolio] <--- **Equity Trace** -> [Equity: client_equity]

---

## Key Tables
| Table | Purpose | Primary Key | Key Columns | 
|--------|---------|-------------|-------------|
| `daily_prices` | 17+ years of EOD OHLCV data. | `BIGSERIAL` | `symbol`, `date`, `close`, `volume` |
| `index_prices` | Benchmark performance data. | `BIGSERIAL` | `symbol`, `date`, `close`, `volume` |
| `client_watchlist` | User-added watchlist symbols. | `UUID` | `client_id`, `symbol`, `created_at` |
| `client_portfolio` | User's live digital twin holdings. | `UUID` | `client_id`, `symbol`, `quantity`, `is_open` |
| `clients` | User management and capital. | `UUID` | `email`, `password_hash`, `initial_capital` |

---

## 🛡️ Security Features
- **Row Level Security (RLS)**: Enabled on all tables containing `client_id`.
- **Policy**: `USING (client_id::text = current_setting('app.current_client_id', true))`
- **64-bit Big Data Support**: `BIGSERIAL` primary keys handle billions of rows.
- **Timezone Native**: All timestamps are `TIMESTAMPTZ`.

## Related Areas
- [Backend Codemap](file:///home/edwar/mri-int/docs/CODEMAPS/backend.md)
