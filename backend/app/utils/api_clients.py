import requests
from typing import Any, Dict, Optional


class ExternalAPIClient:
    """
    Thin HTTP wrapper used by all services that call external APIs.
    Provides consistent timeout handling, header management, and error propagation.
    All services should use this instead of calling requests directly.
    """

    def fetch_data(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10,
    ) -> Dict:
        """Performs a GET request and returns the parsed JSON body."""
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def post_data(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> Dict:
        """Performs a POST request with a JSON body and returns the parsed JSON."""
        resp = requests.post(url, json=json, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()


# Singleton instance for import
api_client = ExternalAPIClient()
