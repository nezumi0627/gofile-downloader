import hashlib
import urllib.parse
from typing import Any, Dict, Optional

import aiohttp


class GoFileAPI:
    """GoFile API client"""

    BASE_URL = "https://api.gofile.io"
    CONTENT_URL = f"{BASE_URL}/contents"
    WT_VALUE = "4fd6sg89d7s6"
    CACHE = "true"
    SORT_FIELD = "createTime"
    SORT_DIRECTION = "1"

    def __init__(
        self, session: aiohttp.ClientSession, token: Optional[str] = None
    ):
        """Initialize the API client"""
        self._session = session
        self._token = token

    async def fetch_content(
        self, content_id: str, password: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch content data from API"""
        url = self._build_url(content_id, password)
        try:
            response = await self._session.get(url, headers=self._headers)
            response.raise_for_status()
        except aiohttp.ClientError as e:
            raise ValueError(f"Failed to fetch content: {e}") from e
        data = await response.json()
        if data["status"] != "ok":
            message = data.get("message", "Unknown error")
            raise ValueError(f"Failed to fetch content: {message}")
        return data["data"]

    def _build_url(
        self, content_id: str, password: Optional[str] = None
    ) -> str:
        """Build the URL for the API request"""
        params = {
            "wt": self.WT_VALUE,
            "cache": self.CACHE,
            "sortField": self.SORT_FIELD,
            "sortDirection": self.SORT_DIRECTION,
        }
        if password:
            # パスワードがSHA-256でない場合、SHA-256に変換
            password = self._convert_to_sha256(password)
            params["password"] = password
        return (
            f"{self.CONTENT_URL}/{content_id}?{urllib.parse.urlencode(params)}"
        )

    @property
    def _headers(self) -> Dict[str, str]:
        """Create headers for API requests"""
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _convert_to_sha256(self, password: str) -> str:
        """パスワードをSHA-256に変換"""
        return hashlib.sha256(password.encode()).hexdigest()
