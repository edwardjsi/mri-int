# Decision Ladder Resolutions Specification

**Algorithm ID:** `DL-2.1-RESOLUTIONS`
**Status:** Approved for Implementation

This document defines the **Product Philosophy and Investor Actions** that govern the Decision Ladder Engine. It dictates how the system evaluates the mathematical thresholds (defined in `DECISION_LADDER_THRESHOLDS.md`) into final states and actionable intelligence.

## 1. Product Philosophy
The Decision Ladder separates opportunity from risk:
1. **Opportunity Flow:** Upside deployment (`Next Add`).
2. **Risk Flow:** Downside escalation (`Hold` -> `Risk Alert` -> `Structure` -> `Technical Exit`).

**Core Tenet:** A stock should remain in `HOLD` for most of its life. The engine must *not* issue a Risk Alert during a normal market pullback. Risk Alert is strictly reserved for when a stock approaches the zone of possible structural failure.

**The Decision Ladder is asymmetric.**
The Opportunity Flow (Next Add) exists to deploy capital selectively. The Risk Flow exists to preserve capital. These flows are independent and must never be mathematically coupled.

---

## 2. Investor Action Matrix

| Engine State | Investor Action | Conceptual Meaning |
|--------------|-----------------|--------------------|
| **ADD** | Prepare/add the next tranche when conditions confirm. | Breakout confirmed. Upside expansion. |
| **HOLD** | Continue holding; ignore normal market noise. | Healthy trend. No immediate action needed. |
| **ALERT** | Stop adding. Increase monitoring. Review weekly evidence. | Approaching structural anchor. Prepare for failure. |
| **STRUCTURE** | Weekly structure is damaged. No further capital. | Primary trend support violated. Prepare exit plan. |
| **QUIT** | Exit the position according to the strategy. | Absolute thesis invalidation confirmed. |

---

## 3. State Resolution Hierarchy

The backend engine evaluates the mathematical thresholds against the `current_price` (Friday Weekly Close) in the following strict priority order. The highest priority condition that evaluates to TRUE becomes the active `decision_state`.

**Priority 1: TECHNICAL EXIT (QUIT)**
* `IF current_price < quit_level THEN decision_state = 'QUIT'`
* *Note: Quit is a confirmed EVENT indicating the structure has fundamentally broken below the noise buffer.*

**Priority 2: STRUCTURE**
* `IF current_price >= quit_level AND current_price < structure_level THEN decision_state = 'STRUCTURE'`

**Priority 3: RISK ALERT**
* `IF current_price >= structure_level AND current_price < alert_level THEN decision_state = 'ALERT'`

**Priority 4: ADD**
* `IF current_price >= add_level AND breakout_confirmed AND portfolio_eligible THEN decision_state = 'ADD'`
* *Note: Price crossing the Add line does not automatically mean buy. The MRI Breakout Engine and Portfolio Policy must independently confirm.*

**Priority 5: HOLD (Default)**
* `ELSE decision_state = 'HOLD'`

---

## 4. Threshold Provenance & Quality

The system must track the provenance of the calculation to foster investor trust and debuggability. 

### Provenance Tracking
The engine evaluates the `decision_quality` to indicate confidence in the ladder geometry:
* **HIGH:** Ladder derived from a high-quality `primary_swing_low`.
* **NORMAL:** Ladder derived normally from EMAs (fallback).
* **LOW:** Ladder mathematically derived but visually compressed (Stage 1 base) or missing data.

### Provenance Tracking (V2.1 Requirement)
Every calculated threshold must store its mathematical provenance. Example payload mapping:
```json
{
    "structure": 1728.37,
    "reason": "Primary weekly higher low",
    "derived_from": "PRIMARY_SWING_LOW"
}
```
