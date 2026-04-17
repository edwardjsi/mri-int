# EMA-50 NULL Indicator Fix - Task List
**Date**: April 15, 2026  
**Priority**: CRITICAL  
**Reference**: Decision 080, `docs/CRITICAL_EMA_50_NULL_ISSUE_2026-04-15.md`

## 📋 Overview
This task list outlines the step-by-step plan to fix the EMA-50 NULL indicator issue that affects 94% of symbols and renders the platform's core quantitative logic unusable.

## 🎯 Success Criteria
1. **≥90% symbols have non-NULL EMA-50** after pipeline run
2. **Golden path test passes**: In BULL regime, ≥10 stocks score ≥ 75
3. **Pipeline blocks** when NULL rate > 20% (circuit breaker)
4. **Validation layer** verifies indicators are written correctly

## 📊 Phase 1: Diagnosis & Understanding (COMPLETE)

### Task 1.1: Document Critical Issue ✅
- [x] Create `docs/CRITICAL_EMA_50_NULL_ISSUE_2026-04-15.md`
- [x] Record Decision 080 in `Decisions.md`
- [x] Update `Progress.md` with current status

### Task 1.2: Create Diagnostic Script
- [x] Create `scripts/diagnose_ema_issue.py`
- [x] Script should:
  - [x] Connect to database using DATABASE_URL
  - [x] Measure exact NULL EMA-50 percentage
  - [x] Check data completeness for sample symbols
  - [x] Test indicator engine's detection logic
  - [x] Provide actionable recommendations

## 🛠️ Phase 2: Core Fix Implementation

### Task 2.1: Fix Indicator Engine Logic
- [x] Examine `engine_core/indicator_engine.py` for bugs
- [x] Fix symbol detection logic in `fetch_data()`
- [x] Fix update logic in `compute_indicators()`
- [x] Ensure ALL rows with NULL indicators get updated
- [x] Add verification that updates were written
- [x] Add post-update NULL-rate validation gate

### Task 2.2: Add Validation Layer
- [ ] Create `engine_core/validation.py` module
- [ ] Add `validate_indicators()` function
- [x] Check: NULL EMA-50 rate < 20%
- [x] Check: EMA values are reasonable (not all zeros)
- [x] Add circuit breaker: raise exception if validation fails

### Task 2.3: Create Golden Path Test
- [ ] Create `tests/test_golden_path.py`
- [ ] Test: In BULL regime, ≥10 stocks score ≥ 75
- [ ] Test: Score distribution has variance
- [ ] Test: Indicators are computed for all symbols
- [ ] Make test runnable standalone

## 🧪 Phase 3: Testing & Verification

### Task 3.1: Test on Subset of Symbols
- [ ] Select 50 symbols for initial test
- [ ] Run diagnostic script before fix
- [ ] Apply fix to indicator engine
- [ ] Run pipeline on subset
- [ ] Verify EMA-50 values are populated

### Task 3.2: Full Pipeline Test
- [ ] Run full pipeline on all symbols
- [ ] Monitor memory and performance
- [ ] Verify NULL rate < 10%
- [ ] Check scoring produces reasonable results

### Task 3.3: Integration Test
- [ ] Test end-to-end: ingestion → indicators → scoring → signals
- [ ] Verify signals would be generated in BULL regime
- [ ] Test circuit breaker triggers when NULL rate > 20%

## 🚀 Phase 4: Deployment & Monitoring

### Task 4.1: Update Pipeline Scripts
- [ ] Update `scripts/pipeline_cloud.sh` to include validation
- [ ] Add validation step after indicator engine
- [ ] Ensure pipeline fails fast if validation fails
- [ ] Update GitHub Actions workflow if needed

### Task 4.2: Create Recovery Script
- [ ] Create `scripts/recover_null_indicators.py`
- [ ] Script should force recompute of NULL indicators
- [ ] Handle partial failures gracefully
- [ ] Log recovery actions

### Task 4.3: Add Monitoring & Alerting
- [ ] Add NULL rate tracking to admin dashboard
- [ ] Set up alert for NULL rate > 30%
- [ ] Create daily data quality report
- [ ] Add to `scripts/db_freshness_check.py`

## 📈 Phase 5: Prevention & Architecture

### Task 5.1: Implement Write-Verify-Read Pattern
- [ ] Refactor all database writes to include verification
- [ ] Add retry logic for failed writes
- [ ] Log write failures with context

### Task 5.2: Create Data Quality SLA
- [ ] Document minimum data quality requirements
- [ ] EMA-50 NULL rate: < 10%
- [ ] Score variance: > 20 points standard deviation
- [ ] Signal generation: Possible in BULL regime

### Task 5.3: Update Documentation
- [ ] Update `Readme.md` with new validation requirements
- [ ] Add troubleshooting guide for NULL indicators
- [ ] Document recovery procedures

## ⏱️ Timeline & Dependencies

### Day 1 (April 15-16):
- Complete Phase 1 (Diagnosis)
- Start Phase 2 (Core Fix)
- Test on subset of symbols

### Day 2 (April 16):
- Complete Phase 2 & 3
- Deploy fix
- Verify with full pipeline run

### Day 3 (April 17):
- Complete Phase 4 & 5
- Update all documentation
- Create monitoring dashboard

## 🎪 Risk Mitigation

### Technical Risks:
1. **Fix causes performance issues**: Test on subset first
2. **Database connection limits**: Use connection pooling
3. **Memory issues with full recompute**: Process in batches

### Business Risks:
1. **Extended downtime**: Have recovery script ready
2. **Data loss**: Backup database before major changes
3. **Incorrect fix**: Validate thoroughly before deployment

## 👥 Responsibilities
- **Lead AI Engineer**: Design and implement fix
- **System Owner**: Validate fix and approve deployment
- **Future Maintainers**: Follow patterns established here

## 📚 References
- Decision 080: EMA-50 NULL Indicator Critical Issue
- `docs/CRITICAL_EMA_50_NULL_ISSUE_2026-04-15.md`
- `docs/pipeline_silent_failure_audit.md` (previous similar issue)
- Decision 077: Pipeline Silent Failure Audit (April 1, 2026)

---
*This task list will be updated as work progresses. Each task completion should be documented with evidence.*
