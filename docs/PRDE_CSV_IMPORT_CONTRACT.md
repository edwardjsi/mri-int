# PRDE CSV Import Contract

## Purpose

PRDE needs trusted annual financial and ratio data before agent scoring can be useful. The MVP import path is a single CSV file loaded by:

```bash
python scripts/import_prde_financials.py path/to/prde_financials.csv
```

The importer is idempotent. Re-running the same file updates the same company/year rows.

Template:

```text
docs/prde_financials_template.csv
```

## Required Columns

| Column | Type | Notes |
| --- | --- | --- |
| ticker | text | Required. Stored uppercase. Should match MRI symbols where possible, for example `RELIANCE` or `TCS`. |
| fiscal_year | integer | Required. Four-digit fiscal year, for example `2024`. |
| revenue | number | Required for useful feature engineering. |
| ebitda | number | Required for operating leverage and margin features. |
| pat | number | Required for earnings acceleration. |
| roce | number | Required for capital efficiency scoring. |
| capex | number | Required for operating leverage/capital cycle analysis. |
| employee_cost | number | Required for fixed-cost leverage analysis. |
| total_assets | number | Required for asset turnover. |

## Optional Columns

| Column | Type | Notes |
| --- | --- | --- |
| name | text | Company display name. |
| country | text | Defaults to `IN`. |
| sector | text | Used later for peer/industry context. |
| industry | text | Used later for peer/industry context. |
| pe | number | Valuation gap agent input. |
| ev_ebitda | number | Valuation gap agent input. |
| pb | number | Balance sheet valuation context. |
| debt_equity | number | Risk agent input. |
| source | text | Data provenance, for example `manual_screener_export_2026_04`. |

## Number Formatting

Accepted:

```text
1234
1234.56
1,234.56
₹1,234.56
12.4%
```

Empty strings are treated as null.

## Example

```csv
ticker,name,country,sector,industry,fiscal_year,revenue,ebitda,pat,roce,capex,employee_cost,total_assets,pe,ev_ebitda,pb,debt_equity,source
TCS,Tata Consultancy Services,IN,IT,Software,2022,191754,57233,38327,54.2,3500,107522,140924,31.2,22.1,13.8,0.08,manual_seed
TCS,Tata Consultancy Services,IN,IT,Software,2023,225458,66637,42147,58.1,4200,126720,143987,29.5,20.6,12.1,0.07,manual_seed
TCS,Tata Consultancy Services,IN,IT,Software,2024,240893,71000,45908,61.5,4600,134000,153000,28.1,19.8,11.4,0.06,manual_seed
```

## Validation Rules

The importer rejects the file if:

- Required columns are missing.
- `ticker` is blank.
- `fiscal_year` is not a four-digit integer.
- A row has no usable financial values.

The importer warns, but does not reject, if:

- Fewer than 5 years exist for a ticker.
- Optional valuation ratios are missing.
- Company metadata is incomplete.

## MVP Guidance

Start with 10-20 companies and 5-10 years each. Do not run LLM agents until this import can be repeated cleanly and the row counts are stable.

After importing, verify database health:

```bash
python scripts/verify_prde_import.py --min-companies 10 --min-years 5
```
