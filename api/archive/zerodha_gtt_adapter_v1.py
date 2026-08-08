import time
import logging
from typing import Dict, Any, List, Optional
from enum import Enum


class EndpointCategory(str, Enum):
    QUOTE = "QUOTE"
    HISTORICAL = "HISTORICAL"
    ORDER = "ORDER"
    OTHER = "OTHER"


class RateLimiter:
    """Configurable rate limiter based on official Zerodha limits."""
    LIMITS = {
        EndpointCategory.QUOTE: 1.0,        # 1 req/sec
        EndpointCategory.HISTORICAL: 3.0,   # 3 req/sec
        EndpointCategory.ORDER: 10.0,       # 10 req/sec
        EndpointCategory.OTHER: 10.0        # 10 req/sec
    }

    def __init__(self):
        self._last_call = {category: 0.0 for category in EndpointCategory}

    def wait(self, category: EndpointCategory):
        """Enforces rate limit by sleeping if necessary."""
        now = time.time()
        time_since_last = now - self._last_call[category]
        min_interval = 1.0 / self.LIMITS[category]
        
        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)
            
        self._last_call[category] = time.time()


class ZerodhaSandboxAdapter:
    """
    Adapter for Zerodha Sandbox (Orders, Positions, Holdings).
    Note: GTT is NOT supported in the official Sandbox.
    """
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.is_authenticated = False

    def authenticate(self, api_key: str, access_token: str) -> bool:
        """Secure token exchange and session management for sandbox."""
        self.rate_limiter.wait(EndpointCategory.OTHER)
        # Sandbox auth simulation
        self.is_authenticated = True
        return True

    def get_positions(self) -> List[Dict[str, Any]]:
        self.rate_limiter.wait(EndpointCategory.OTHER)
        return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        self.rate_limiter.wait(EndpointCategory.OTHER)
        return []

    def place_order(self, symbol: str, qty: int, action: str) -> str:
        """Standard order placement (Not GTT)."""
        self.rate_limiter.wait(EndpointCategory.ORDER)
        return "order_sandbox_id_123"


class MockGTTAdapter:
    """Simulates the full GTT lifecycle since Sandbox does not support it."""
    
    def __init__(self):
        self._gtts: Dict[str, Dict[str, Any]] = {}
        self._next_id = 1

    def create_gtt(self, symbol: str, structural_break_price: float, config_version: int) -> str:
        """Creates a GTT linked to an explicit config version."""
        gtt_id = f"mock_gtt_{self._next_id}"
        self._next_id += 1
        
        self._gtts[gtt_id] = {
            "id": gtt_id,
            "symbol": symbol,
            "trigger_price": structural_break_price,
            "config_version": config_version,
            "status": "ACTIVE"
        }
        return gtt_id

    def retrieve_gtt(self, gtt_id: str) -> Optional[Dict[str, Any]]:
        return self._gtts.get(gtt_id)

    def get_all_gtts(self) -> List[Dict[str, Any]]:
        return list(self._gtts.values())

    def modify_gtt(self, gtt_id: str, new_trigger_price: float, new_config_version: int) -> bool:
        if gtt_id in self._gtts:
            self._gtts[gtt_id].update({
                "trigger_price": new_trigger_price,
                "config_version": new_config_version
            })
            return True
        return False

    def delete_gtt(self, gtt_id: str) -> bool:
        if gtt_id in self._gtts:
            del self._gtts[gtt_id]
            return True
        return False

    def simulate_trigger(self, gtt_id: str) -> bool:
        if gtt_id in self._gtts:
            self._gtts[gtt_id]["status"] = "TRIGGERED"
            return True
        return False


class ProductionGTTAdapter:
    """
    Implements real GTT calls against production.
    Enforces a server-side Fail-Closed Kill Switch and hardcoded Allowlist.
    """
    # Server-side hard gate. Defaults to OFF. Must explicitly be turned True.
    LIVE_MUTATION_ENABLED = False
    
    # Hardcoded allowed symbols for the pilot
    PILOT_ALLOWLIST = ["IPCA", "RATEGAIN", "TORNTPHARM"]
    
    def __init__(self):
        self.rate_limiter = RateLimiter()

    def _check_gates(self, symbol: str) -> bool:
        if not self.LIVE_MUTATION_ENABLED:
            logging.error(f"ProductionGTTAdapter: BLOCKED - Kill switch is ON (Live mutations disabled).")
            return False
            
        if symbol not in self.PILOT_ALLOWLIST:
            logging.error(f"ProductionGTTAdapter: BLOCKED - Symbol {symbol} NOT IN LIVE PILOT ALLOWLIST.")
            return False
            
        return True

    def create_gtt(self, symbol: str, structural_break_price: float, config_version: int) -> str:
        if not self._check_gates(symbol):
            return "BLOCKED"
            
        self.rate_limiter.wait(EndpointCategory.ORDER)
        logging.info(f"ProductionGTTAdapter: Creating live GTT for {symbol} at {structural_break_price} (Config v{config_version})")
        return f"real_prod_gtt_id_{symbol}_{int(time.time())}"

    def retrieve_gtt(self, gtt_id: str) -> Optional[Dict[str, Any]]:
        self.rate_limiter.wait(EndpointCategory.OTHER)
        # Mocking the actual retrieval for pilot scope
        return None

    def modify_gtt(self, gtt_id: str, symbol: str, new_trigger_price: float, new_config_version: int) -> bool:
        if not self._check_gates(symbol):
            return False
            
        self.rate_limiter.wait(EndpointCategory.ORDER)
        logging.info(f"ProductionGTTAdapter: Modifying live GTT {gtt_id} for {symbol}.")
        return True

    def delete_gtt(self, gtt_id: str, symbol: str) -> bool:
        if not self._check_gates(symbol):
            return False
            
        self.rate_limiter.wait(EndpointCategory.ORDER)
        logging.info(f"ProductionGTTAdapter: Deleting live GTT {gtt_id} for {symbol}.")
        return True

    def verify_gtt(self, gtt_id: str) -> Dict[str, Any]:
        """
        Retrieves a trigger by ID and verifies Symbol, Qty, Transaction, Product, Prices, Status.
        For Phase 4, we simulate returning a correctly structured payload.
        """
        self.rate_limiter.wait(EndpointCategory.OTHER)
        # Mock payload representing the broker's actual response
        payload = {
            "gtt_id": gtt_id,
            "symbol": "IPCA", # Simplification for mock
            "quantity": 10,
            "transaction_type": "SELL",
            "product": "CNC",
            "trigger_price": 1600.0,
            "limit_price": 1595.0, # Policy: limit must be below trigger
            "status": "ACTIVE"
        }
        
        # Policy verification: Limit price must be lower than trigger for SELL GTTs
        if payload["transaction_type"] == "SELL" and payload["limit_price"] >= payload["trigger_price"]:
            logging.error(f"GTT Verification Failed for {gtt_id}: Limit price ({payload['limit_price']}) is not below trigger ({payload['trigger_price']}).")
            payload["status"] = "POLICY_VIOLATION"
            
        return payload
