# services/api_client.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import os
import requests

DEFAULT_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_TIMEOUT = float(os.getenv("API_TIMEOUT", "10"))

@dataclass
class ApiClient:
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    _token: Optional[str] = None

    # ---- auth ----
    def login(self, email: str, password: str) -> Dict[str, Any]:
        url = f"{self.base_url}/auth/login"
        resp = requests.post(url, json={"email": email, "password": password}, timeout=self.timeout)
        if resp.status_code != 200:
            # FastAPI manda detail en errores
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise RuntimeError(f"Login failed: {detail}")
        data = resp.json()
        self._token = data.get("access_token")
        return data

    def get_me(self) -> Dict[str, Any]:
        self._ensure_token()
        url = f"{self.base_url}/me"
        resp = requests.get(url, headers=self._auth_header(), timeout=self.timeout)
        if resp.status_code != 200:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise RuntimeError(f"/me failed: {detail}")
        return resp.json()

    # ---- helpers ----
    def _auth_header(self) -> Dict[str, str]:
        self._ensure_token()
        return {"Authorization": f"Bearer {self._token}"}

    def _ensure_token(self):
        if not self._token:
            raise RuntimeError("No token. Haz login primero.")

    @property
    def token(self) -> Optional[str]:
        return self._token

    def logout(self):
        self._token = None
