# Forensic Debate & STEE Alert Hardening

## Overview
This document tracks the hardening and verification of the AI Forensic Debate and Momentum Swing Trading Execution Engine (STEE) notification pipelines. These systems are critical for providing real-capital accountability and qualitative depth to the MRI signals.

## 🛠️ Verification Checklist

### 1. Engine Stability
- **OpenAI Client Conflict**: Resolved the `proxies` vs `proxy` argument mismatch between `openai` and `httpx` in `engine_qualitative/debate.py` by using a custom `httpx.Client`.
- **Numeric Hardening**: Fixed `ValueError` in `scripts/quality_alerts.py` by wrapping `float()` conversions in `try/except` blocks. Non-numeric data (e.g., "N/A") no longer crashes the alerting pipeline.

### 2. Pipeline Orchestration
- **Dispatch Audit**: Confirmed `scripts/pipeline_cloud.sh` (Step 6) correctly invokes the `email_service.py` main block.
- **STEE Integration**: Verified that `send_stee_signal_emails()` is triggered daily, ensuring swing trade alerts reach active clients.

### 3. Data Integrity
- **Symbol Normalization**: Confirmed consistent stripping of `.NS` and `.BO` suffixes across all fundamental and qualitative modules. This ensures successful joins between technical `stock_scores` and fundamental `quality_verdicts`.
- **Affected Modules**:
    - `api/fundamental.py`
    - `engine_qualitative/debate.py`
    - `engine_fundamental/collector.py`
    - `engine_fundamental/pipeline.py`

## 📋 Implementation Plan

### Phase 1: Post-Fix Verification (Completed)
- [x] Code audit for `debate.py`
- [x] Hardening `quality_alerts.py`
- [x] Grep audit for symbol suffix consistency

### Phase 2: End-to-End Functional Test
- [ ] **Trigger**: Manually initiate a Forensic Debate from the Stock Details modal.
- [ ] **Monitor**: Check logs for GPT-4o-mini response latency and formatting.
- [ ] **Delivery**: Verify SES email receipt for the debate report.

### Phase 3: Dataset Integrity Audit (Completed)
- [x] **Join Audit**: Run `scripts/audit_fundamental_joins.py` (Completed May 05). Confirmed no suffix mismatches (`.NS`/`.BO`) are blocking technical-fundamental joins. Identified 399 symbols (mostly BSE codes) missing fundamental data.
