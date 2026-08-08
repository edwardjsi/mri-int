from typing import Dict, Any, Tuple, Optional
from api.cai_state_machine import AlertState


class CAIEvaluators:
    """
    Evaluates semantic alert conditions against the current price and configuration.
    
    IMPORTANT: None of these evaluators mutate position state or generate orders.
    They purely return whether an alert should transition to REVIEW_REQUIRED.
    """

    @staticmethod
    def evaluate_pullback_zone(current_price: float, config: Dict[str, Any]) -> bool:
        """
        PULLBACK_ZONE_REACHED
        True if current price is within the pullback_lower_bound and pullback_upper_bound.
        """
        levels = config.get("levels", {})
        pb = levels.get("pullback_zone", {})
        lower = pb.get("lower_bound")
        upper = pb.get("upper_bound")
        
        if lower is None or upper is None:
            return False
            
        return lower <= current_price <= upper

    @staticmethod
    def evaluate_breakout_confirmation(current_price: float, config: Dict[str, Any]) -> bool:
        """
        BREAKOUT_CONFIRMATION
        True if current price exceeds the breakout confirmation level.
        (For Phase 2, we simulate this with a simple upper threshold if provided).
        """
        levels = config.get("levels", {})
        breakout_level = levels.get("breakout_level")
        
        if breakout_level is None:
            return False
            
        return current_price > breakout_level

    @staticmethod
    def evaluate_next_add_candidate(current_price: float, config: Dict[str, Any]) -> bool:
        """
        NEXT_ADD_CANDIDATE
        True if current price is within the next_add_level bounds.
        """
        levels = config.get("levels", {})
        add_lvl = levels.get("next_add_level", {})
        min_price = add_lvl.get("min_price")
        max_price = add_lvl.get("max_price")
        
        if min_price is None:
            return False
            
        if max_price is not None:
            return min_price <= current_price <= max_price
        return current_price >= min_price

    @staticmethod
    def evaluate_structure_break(current_price: float, config: Dict[str, Any]) -> bool:
        """
        STRUCTURE_BREAK
        True if current price drops below the structural_break_price.
        """
        levels = config.get("levels", {})
        structural_break = levels.get("structural_break_price")
        
        if structural_break is None:
            return False
            
        return current_price < structural_break

    @classmethod
    def evaluate_all(cls, current_price: float, config: Dict[str, Any]) -> Tuple[Optional[str], bool]:
        """
        Evaluates all conditions and returns the triggered semantic alert type, if any.
        Always returns (Alert_Type, True_if_triggered).
        Zero autonomous orders or position mutations occur here.
        """
        if cls.evaluate_structure_break(current_price, config):
            return "STRUCTURE_BREAK", True
        if cls.evaluate_pullback_zone(current_price, config):
            return "PULLBACK_ZONE_REACHED", True
        if cls.evaluate_next_add_candidate(current_price, config):
            return "NEXT_ADD_CANDIDATE", True
        if cls.evaluate_breakout_confirmation(current_price, config):
            return "BREAKOUT_CONFIRMATION", True
            
        return None, False
