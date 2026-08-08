from typing import Dict, Any, Tuple, List


def is_valid_tranche_progression(current: str, target: str) -> bool:
    """Ensure target tranche is downstream of current tranche."""
    order = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5, "FULL": 6, "EXITED": 7}
    if current not in order or target not in order:
        return False
    return order[target] > order[current]


def validate_alert_configuration(config_payload: Dict[str, Any], current_tranche: str) -> Tuple[bool, List[str]]:
    """
    Validates ONLY intrinsic mathematical properties.
    The weekly review is the sole authority on level relationships.
    """
    errors = []
    levels = config_payload.get('levels', {})
    
    # 1. Non-negative prices
    if levels.get('structural_break_price', 0) <= 0:
        errors.append("Structural break price must be greater than 0.")
        
    # 2. Pullback bounds intrinsic integrity
    pb = levels.get('pullback_zone', {})
    if pb.get('lower_bound', 0) <= 0 or pb.get('upper_bound', 0) <= 0:
        errors.append("Pullback bounds must be greater than 0.")
    elif pb.get('lower_bound') >= pb.get('upper_bound'):
        errors.append("Pullback lower_bound must be strictly less than upper_bound.")
        
    # 3. Next ADD zone intrinsic integrity
    add_lvl = levels.get('next_add_level', {})
    if add_lvl.get('min_price', 0) <= 0:
        errors.append("Next ADD min_price must be greater than 0.")
    if add_lvl.get('max_price') is not None and add_lvl.get('min_price') >= add_lvl.get('max_price'):
        errors.append("Next ADD min_price must be strictly less than max_price.")
        
    # 4. Tranche progression integrity
    target_tranche = add_lvl.get('target_tranche')
    if target_tranche and not is_valid_tranche_progression(current_tranche, target_tranche):
        errors.append(f"Target tranche {target_tranche} must be downstream of current tranche {current_tranche}.")
        
    return len(errors) == 0, errors
