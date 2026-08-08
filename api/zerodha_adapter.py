import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from enum import Enum


class EndpointCategory(str, Enum):
    QUOTE = "QUOTE"
    HISTORICAL = "HISTORICAL"
    ALERT = "ALERT"
    OTHER = "OTHER"


class RateLimiter:
    """Configurable rate limiter based on official Zerodha limits."""
    LIMITS = {
        EndpointCategory.QUOTE: 1.0,        # 1 req/sec
        EndpointCategory.HISTORICAL: 3.0,   # 3 req/sec
        EndpointCategory.ALERT: 10.0,       # 10 req/sec (assuming similar to standard endpoints)
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


class KiteAlertAdapter:
    """
    Adapter strictly for managing simple Kite price alerts via the free Kite Connect Personal API.
    Zero execution capabilities.
    """
    def __init__(self):
        self.rate_limiter = RateLimiter()
        # Mocking the internal state of active alerts
        self._alerts: Dict[str, Dict[str, Any]] = {}

    def authenticate(self, client_id: str, conn) -> bool:
        """Authentication using Kite Connect Personal via securely stored DB token."""
        self.rate_limiter.wait(EndpointCategory.OTHER)
        token = self.fetch_token_from_db(client_id, conn)
        if not token:
            logging.error(f"Authentication failed: No token found for client {client_id}")
            return False
            
        self.access_token = token
        return True

    def fetch_token_from_db(self, client_id: str, conn) -> Optional[str]:
        cur = conn.cursor()
        cur.execute(
            "SELECT access_token FROM kite_credentials WHERE client_id = %s",
            (str(client_id),)
        )
        row = cur.fetchone()
        if not row:
            return None
        return row["access_token"] if isinstance(row, dict) else row[0]

    def create_alert(self, symbol: str, condition: str, price: float, alert_name: str, alert_type: str = "simple") -> str:
        """Creates a price alert. Strictly hard-blocks type=ato."""
        if alert_type == "ato":
            raise ValueError("HARD BLOCK: type=ato is strictly forbidden in CAI V1. Only simple alerts are permitted.")
            
        self.rate_limiter.wait(EndpointCategory.ALERT)
        alert_uuid = str(uuid.uuid4())
        
        self._alerts[alert_uuid] = {
            "uuid": alert_uuid,
            "symbol": symbol,
            "condition": condition,
            "price": price,
            "name": alert_name,
            "type": alert_type,
            "status": "ACTIVE"
        }
        logging.info(f"KiteAlertAdapter: Created alert '{alert_name}' (UUID: {alert_uuid}) for {symbol} ({condition} {price})")
        return alert_uuid

    def retrieve_alert(self, alert_uuid: str) -> Optional[Dict[str, Any]]:
        self.rate_limiter.wait(EndpointCategory.ALERT)
        return self._alerts.get(alert_uuid)

    def get_all_alerts(self) -> List[Dict[str, Any]]:
        self.rate_limiter.wait(EndpointCategory.ALERT)
        return list(self._alerts.values())

    def modify_alert(self, alert_uuid: str, new_condition: str, new_price: float) -> bool:
        self.rate_limiter.wait(EndpointCategory.ALERT)
        if alert_uuid in self._alerts:
            self._alerts[alert_uuid].update({
                "condition": new_condition,
                "price": new_price
            })
            logging.info(f"KiteAlertAdapter: Modified alert UUID: {alert_uuid}")
            return True
        return False

    def delete_alert(self, alert_uuid: str) -> bool:
        self.rate_limiter.wait(EndpointCategory.ALERT)
        if alert_uuid in self._alerts:
            del self._alerts[alert_uuid]
            logging.info(f"KiteAlertAdapter: Deleted alert UUID: {alert_uuid}")
            return True
        return False
