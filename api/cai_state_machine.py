from enum import Enum
from typing import Dict, Any, Optional, Tuple


class AlertState(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    TRIGGERED = "TRIGGERED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEWED = "REVIEWED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class PositionTranche(str, Enum):
    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T5 = "T5"
    FULL = "FULL"
    EXITED = "EXITED"


class TrancheProgressionEngine:
    """Manages Position state progression."""

    TRANCHE_ORDER = {
        PositionTranche.T0: 0,
        PositionTranche.T1: 1,
        PositionTranche.T2: 2,
        PositionTranche.T3: 3,
        PositionTranche.T4: 4,
        PositionTranche.T5: 5,
        PositionTranche.FULL: 6,
        PositionTranche.EXITED: 7
    }

    @classmethod
    def process_human_decision(cls, current_tranche: PositionTranche, decision: str, target_tranche: Optional[PositionTranche] = None) -> PositionTranche:
        """
        Calculates the new tranche based on a human decision.
        Decisions: ADD, WAIT, HOLD, EXIT
        """
        if decision == "EXIT":
            return PositionTranche.EXITED
        elif decision in ["WAIT", "HOLD"]:
            return current_tranche
        elif decision == "ADD":
            if target_tranche and cls.TRANCHE_ORDER[target_tranche] > cls.TRANCHE_ORDER[current_tranche]:
                return target_tranche
            # Default progression if no target provided
            curr_idx = cls.TRANCHE_ORDER[current_tranche]
            if curr_idx < cls.TRANCHE_ORDER[PositionTranche.FULL]:
                # Advance to next tranche
                for t, idx in cls.TRANCHE_ORDER.items():
                    if idx == curr_idx + 1:
                        return t
        
        return current_tranche


class AlertLifecycleEngine:
    """Manages the state transitions of an Alert."""

    @staticmethod
    def evaluate_transition(current_state: AlertState, event: str) -> AlertState:
        """
        Enforces valid state transitions.
        Events: ACTIVATE, TRIGGER, REQUIRE_REVIEW, HUMAN_REVIEW, RESOLVE, DISMISS
        """
        transitions = {
            AlertState.CREATED: {"ACTIVATE": AlertState.ACTIVE},
            AlertState.ACTIVE: {"TRIGGER": AlertState.TRIGGERED},
            AlertState.TRIGGERED: {"REQUIRE_REVIEW": AlertState.REVIEW_REQUIRED},
            AlertState.REVIEW_REQUIRED: {"HUMAN_REVIEW": AlertState.REVIEWED},
            AlertState.REVIEWED: {"RESOLVE": AlertState.RESOLVED, "DISMISS": AlertState.DISMISSED}
        }
        
        if current_state in transitions and event in transitions[current_state]:
            return transitions[current_state][event]
        
        # Invalid transition
        raise ValueError(f"Invalid transition from {current_state} via {event}")
