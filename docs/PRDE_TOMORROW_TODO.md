# PRDE Tomorrow TODO

**Target Date:** 2026-04-26

## Goal

Load the first real PRDE financial seed data and prove the deterministic feature engine works end to end.

## 1. Create Seed CSV

- [ ] Create a working seed file:

```bash
mkdir -p data
cp docs/prde_financials_template.csv data/prde_financials_seed.csv
```

- [ ] Add 5-10 years of data for 10-20 companies.
- [ ] Prioritize Indian listed companies that already exist in MRI symbols.

Required fields:

```text
ticker,fiscal_year,revenue,ebitda,pat,roce,capex,employee_cost,total_assets
```

Useful optional fields:

```text
name,country,sector,industry,pe,ev_ebitda,pb,debt_equity,source
```

## 2. Validate CSV Without DB Writes

- [ ] Run:

```bash
python scripts/import_prde_financials.py data/prde_financials_seed.csv --dry-run
```

- [ ] Fix any missing columns, invalid years, or numeric formatting issues.
- [ ] Confirm dry-run shows expected row and company counts.

## 3. Import Into DB

- [ ] Run:

```bash
python scripts/import_prde_financials.py data/prde_financials_seed.csv
```

- [ ] Re-run the same import once to confirm idempotency.

## 4. Verify Import Health

- [ ] Run:

```bash
python scripts/verify_prde_import.py --min-companies 10 --min-years 5
```

- [ ] Confirm:
  - No duplicate financial company/year groups.
  - No duplicate ratio company/year groups.
  - No missing required financial values.
  - No unexpected short histories.

## 5. Generate PRDE Features

- [ ] Dry-run feature generation:

```bash
python engine_core/prde_feature_engine.py --limit 20 --dry-run
```

- [ ] Persist feature snapshots:

```bash
python engine_core/prde_feature_engine.py --limit 20
```

- [ ] Re-run feature generation and confirm unchanged companies reuse the same feature hash.

## 6. Update Docs

- [ ] Tick completed items in `docs/PRDE_IMPLEMENTATION_CHECKLIST.md`.
- [ ] Update `Progress.md`.
- [ ] Update `Sessions.md`.

## Stop Point

Do not start LLM agents tomorrow unless the seed import and deterministic feature snapshots pass cleanly.

Next coding phase after this TODO:

```text
Phase 3 - Deterministic PRDE Scoring Baseline
```
