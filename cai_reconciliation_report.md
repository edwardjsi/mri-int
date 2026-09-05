# CAI Production Reconciliation Report

> [!WARNING]
> **Production Audit Status**
> This audit confirms that the current production database contains only a partial CAI portfolio. The local regression test explicitly operated on production, but analysis of the test script shows it only issued `DELETE` statements specifically for `HSCL`, `TCS`, and `RELIANCE`.

## 1. CAI Configurations
Querying `cai_alert_config_versions` for all managed portfolio symbols yields only the restored configurations:

| Symbol | Version | Status | Pullback | Breakout | Next ADD | Structure | Created / Updated |
|---|---|---|---|---|---|---|---|
| **HSCL** | 1 | `DRAFT` | ₹720–730 | ₹800 | ₹820 | ₹670 | 2026-08-08 13:40:03 UTC |
| **TCS** | 1 | `APPROVED`| ₹2000–2050 | ₹2100 | ₹2150 | ₹1950 | 2026-08-08 13:42:00 UTC |

* `IPCA`: **MISSING**
* `RATEGAIN`: **MISSING**

## 2. Portfolio Positions
Querying `cai_positions` where `status = 'ACTIVE'` yields:

| Symbol | Tranche | Status | Created At |
|---|---|---|---|
| **HSCL** | T0 | ACTIVE | 2026-08-08 13:41:13 UTC |
| **RELIANCE** | T0 | ACTIVE | 2026-08-08 13:41:13 UTC |
| **TCS** | T0 | ACTIVE | 2026-08-08 13:41:13 UTC |

* `IPCA`: **MISSING**
* `RATEGAIN`: **MISSING**

## 3. CAI Alert Mappings
Querying `cai_alert_mappings` joined against active positions yields:
**No records found (0 rows).**

* IPCA v8 UUID mappings: **MISSING**
* HSCL accidental mappings: **INTACT (None exist, which is correct for a DRAFT)**

## 4. Decision Ledger
Querying `cai_decision_ledger` for the last 24 hours yields:
**No records found (0 rows).**

No unexpected `DELETE`/`UPDATE` ledger events were generated. Zerodha mutation count remains exactly zero.

## 5. Zerodha Evidence
Since no UUIDs exist in the mappings table and the API health checks confirm zero mutation calls were historically executed from this deployment, there are no active CAI-owned simple alerts inside the broker associated with `HSCL` or the wiped symbols.

## 6. Full Portfolio Classification

| Symbol | State | Classification | Notes |
|---|---|---|---|
| **HSCL** | Correct | **INTACT** | Values manually restored and verified. |
| **TCS** | Mocked | **MISMATCHED** | Currently holds the mock APPROVED values from the test script restoration. |
| **RELIANCE** | Unconfigured | **INTACT** | Correctly has an active position with no configuration. |
| **IPCA** | Not in DB | **MISSING** | Missing from both `cai_positions` and `configs`. |
| **RATEGAIN**| Not in DB | **MISSING** | Missing from both `cai_positions` and `configs`. |

## Additional Safeguard Implemented

To prevent this from ever happening again, a strict database guard has been implemented and pushed to the repository:

1. **`tests/conftest.py`**: A session-scoped `autouse` fixture that aborts Pytest entirely if `DATABASE_URL` contains `neondb` or `ep-bold-mud` without an explicit `TEST_ALLOW_PROD_DB=1` override.
2. **`scripts/test_db_guard.py`**: A standalone guard utility injected into the head of all manual test scripts (like `test_cai_saturday_immutability.py`) to hard-exit before any `psycopg2` connection is established.
