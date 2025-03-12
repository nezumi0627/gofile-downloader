from typing import Any, Dict, Optional

import aiohttp

from .go_file_api_manager import GoFileAPIManager


class GofileAccountManager:
    """Gofile.ioのアカウント情報を管理するクラス"""

    def __init__(self, api_server: str = "api"):
        """初期化"""
        self.api_server = api_server
        self._accounts: Dict[str, Dict[str, Any]] = {}
        self._api_manager = GoFileAPIManager()

    async def fetch_account(self, token: str) -> Dict[str, Any]:
        """トークンに紐づくアカウント情報を取得

        Args:
            token (str): アクセストークン

        Returns:
            Dict[str, Any]: アカウント情報

        Example:
            {
                'ipTraffic30': 222760553104,
                'id': '4a3d5926-b94c-4d4c-948e-cd9dd5e466e3',
                'createTime': 1741770646,
                'email': 'guest5212037279@gofile.io',
                'tier': 'guest',
                'token': 'nH8oAZ2ibJg8SnBqoWpV2kSG6vaYCYa5',
                'rootFolder': '39e68f88-f314-4609-acdb-e3ef7b99c8f1',
                'statsCurrent': {
                    'folderCount': 1,
                    'fileCount': 0,
                    'storage': 0,
                    'trafficWebDownloaded': 12052872
                }
            }
        """
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.get(
                    f"https://{self.api_server}.gofile.io/accounts/website",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                response.raise_for_status()
                data = await response.json()
                return data.get("data", {})
        except aiohttp.ClientError as e:
            raise ValueError(f"Failed to fetch account: {e}") from e

    async def sync_account(self, token: str) -> Dict[str, Any]:
        """トークンに紐づくアカウント情報を取得して同期する"""
        account_data = await self.fetch_account(token)
        self._accounts[account_data["email"]] = account_data
        return account_data

    async def get_account_status(
        self, token: Optional[str] = None
    ) -> Dict[str, Any]:
        """アクティブなアカウント情報を取得"""
        if not self._accounts and not token:
            raise ValueError("No accounts available and no token provided.")

        if token:
            await self.sync_account(token)
            return await self.get_first_active_account()

        if not self._accounts:
            raise ValueError("No accounts available.")

        return await self.get_first_active_account()

    async def get_first_active_account(self) -> Dict[str, Any]:
        """最初のアクティブなアカウントを取得"""
        active_account = next(
            (
                account
                for account in self._accounts.values()
                if account.get("clientActive")
            ),
            None,
        )

        if not active_account:
            active_account = list(self._accounts.values())[0]
            active_account["clientActive"] = (
                True  # 最初のアカウントをアクティブにする
            )

        return active_account
