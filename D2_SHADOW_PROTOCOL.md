# D2 Shadow Validation Protocol

## 1. Core Principle
The purpose of this tracking experiment is purely observational. **No part of this experiment may modify live CAI production execution or capital allocation.**

## 2. Frozen Classifier
The Day-0 archetype classifier is permanently frozen. It uses the exact medians, IQR, and centroids from the original Early+Middle training set used in the final Track B validation. 
* It must never be retrained, optimized, or recalibrated.
* Classification occurs once per entry on Day-0 and is permanently locked for that trade.

## 3. Entry & Tranche Events (Identical Mirror)
The shadow tracker does not simulate entries. It observes actual CAI/MOSI entries.
* Both the "Actual" and "Conditional" exits must evaluate performance starting from the exact same entry timestamp and executed price.
* Further tranche additions in production apply symmetrically to the conditional shadow position (up to the point where one of the two strategies exits).

## 4. Exit Definitions
### Actual Production Exit
Defined as whatever exit triggered the actual closure of the production trade (Stop Gap, Intraday Stop, or Daily Structural Stop).

### Counterfactual Conditional Exit
Defined as:
* **Momentum Archetype:** Uses the same Daily Structural Exit as production.
* **Deep-Base Archetype:** Uses the Weekly Structural Exit (only evaluated on Fridays against the W-anchor).
* *Note:* Both archetypes still obey the emergency Stop Gap and Intraday Stops just as production does. The conditional exit cannot generate an actual market order.

## 5. Event Censoring & Opportunity Cost
* **Completed Trades:** Separated from currently open trades. A trade is only completed when *both* the actual and conditional exits have fired (or the stock remains open in both).
* **Capital Leakage:** We track hypothetical cash that *would* have remained deployed in the conditional strategy when the actual portfolio exited early.
* **Missed Opportunities:** Whenever the conditional strategy retains a position longer than production, the capital is considered "locked". If the production portfolio uses that freed capital to take a new CAI trade, that new trade is logged as a "Missed Opportunity" for the conditional strategy.

## 6. Ledger Integrity
The `d2_shadow_ledger.csv` must be append-only and deterministic. Rerunning the tracker over historical days must not duplicate entries or rewrite previously recorded classifications. Every counterfactual exit must be explicitly labelled `COUNTERFACTUAL_ONLY`.

## 7. Pass / Fail Criteria
After sufficient live observations, the experiment will be evaluated on two levels:
1. **Trade Level:** Did the Weekly Structural Exit generate higher P&L for Deep-Base setups compared to the Daily exit?
2. **Portfolio Level:** Did the retained Deep-Base trades produce more P&L than the alternative CAI trades taken by the production portfolio using the freed capital?

*If both levels are positive, the Conditional Exit rule will be approved for production.*
