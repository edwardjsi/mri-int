import time
import uuid
import logging
import os
import requests
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
    Adapter for managing Kite price alerts via the official Kite Connect Alerts API.
    Zero execution capabilities.
    """
    BASE_URL = "https://api.kite.trade/alerts"

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.api_key = os.getenv("KITE_API_KEY")
        if not self.api_key:
            raise ValueError("KITE_API_KEY is not configured in the environment.")
        self.access_token = None

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

    def _get_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise ValueError("Adapter not authenticated. Call authenticate() first.")
        return {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}"
        }

    def _map_condition(self, condition: str) -> str:
        valid_conditions = {">=", ">", "<=", "<", "=="}
        if condition not in valid_conditions:
            raise ValueError(f"Invalid CAI condition: '{condition}'. Must be one of {valid_conditions}")
        return condition

    def _handle_response(self, response) -> Any:
        try:
            data = response.json()
        except ValueError:
            raise RuntimeError("Zerodha API returned non-JSON response.")
            
        if response.status_code != 200 or data.get("status") != "success":
            err_msg = data.get("message", "Unknown API error")
            raise RuntimeError(f"Zerodha API Error: {err_msg}")
            
        return data

    def create_alert(self, symbol: str, condition: str, price: float, alert_name: str, alert_type: str = "simple") -> str:
        """Creates a price alert. Strictly hard-blocks type=ato."""
        if alert_type == "ato":
            raise ValueError("HARD BLOCK: type=ato is strictly forbidden in CAI V1. Only simple alerts are permitted.")
            
        mapped_condition = self._map_condition(condition)
        self.rate_limiter.wait(EndpointCategory.ALERT)
        
        payload = {
            "name": alert_name,
            "lhs_exchange": "NSE",
            "lhs_tradingsymbol": symbol,
            "lhs_attribute": "LastTradedPrice",
            "operator": mapped_condition,
            "rhs_type": "constant",
            "type": "simple",
            "rhs_constant": str(price)
        }
        
        resp = requests.post(self.BASE_URL, data=payload, headers=self._get_headers())
        data = self._handle_response(resp)
        
        uuid_created = data.get("data", {}).get("uuid")
        if not uuid_created:
            raise RuntimeError("Zerodha API did not return a UUID for the created alert.")
            
        logging.info(f"KiteAlertAdapter: Created alert '{alert_name}' (UUID: {uuid_created}) for {symbol}")
        return str(uuid_created)

    def retrieve_alert(self, alert_uuid: str) -> Optional[Dict[str, Any]]:
        self.rate_limiter.wait(EndpointCategory.ALERT)
        resp = requests.get(f"{self.BASE_URL}/{alert_uuid}", headers=self._get_headers())
        if resp.status_code == 404:
            return None
        data = self._handle_response(resp)
        return data.get("data")

    def get_all_alerts(self) -> List[Dict[str, Any]]:
        self.rate_limiter.wait(EndpointCategory.ALERT)
        resp = requests.get(self.BASE_URL, headers=self._get_headers())
        data = self._handle_response(resp)
        return data.get("data", [])

    def modify_alert(self, alert_uuid: str, new_condition: str, new_price: float, new_name: Optional[str] = None) -> bool:
        mapped_condition = self._map_condition(new_condition)
        self.rate_limiter.wait(EndpointCategory.ALERT)
        
        # We need to send all required fields for a PUT. 
        # Retrieve the existing alert first to get symbol/exchange.
        existing = self.retrieve_alert(alert_uuid)
        if not existing:
            return False
            
        payload = {
            "name": new_name or existing.get("name"),
            "lhs_exchange": existing.get("lhs_exchange", "NSE"),
            "lhs_tradingsymbol": existing.get("lhs_tradingsymbol"),
            "lhs_attribute": existing.get("lhs_attribute", "LastTradedPrice"),
            "operator": mapped_condition,
            "rhs_type": existing.get("rhs_type", "constant"),
            "type": existing.get("type", "simple"),
            "rhs_constant": str(new_price)
        }
        
        resp = requests.put(f"{self.BASE_URL}/{alert_uuid}", data=payload, headers=self._get_headers())
        self._handle_response(resp)
        logging.info(f"KiteAlertAdapter: Modified alert UUID: {alert_uuid}")
        return True

    def delete_alert(self, alert_uuid: str) -> bool:
        self.rate_limiter.wait(EndpointCategory.ALERT)
        resp = requests.delete(f"{self.BASE_URL}?uuid={alert_uuid}", headers=self._get_headers())
        if resp.status_code == 404:
            return False
        self._handle_response(resp)
        logging.info(f"KiteAlertAdapter: Deleted alert UUID: {alert_uuid}")
        return True
