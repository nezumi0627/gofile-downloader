import os
import time
from datetime import datetime
from typing import Optional

from .get_status import GofileAccountManager
from .go_file_api_manager import GoFileAPIManager
from .token_file_manager import TokenFileManager


class TokenManager:
    """GoFile API トークンを管理するクラス"""

    def __init__(
        self, token_file: str = os.getenv("TOKEN_FILE_PATH", "tokens.json")
    ) -> None:
        """初期化: トークンファイル、API管理、アカウント管理の準備"""
        self.token_file_manager = TokenFileManager(token_file)
        self.api_manager = GoFileAPIManager()
        self.account_manager = GofileAccountManager()
        self.tokens = self.token_file_manager.load_tokens()

    async def get_valid_token(self) -> Optional[str]:
        """有効なトークンを取得（環境変数またはtokens.json）"""
        # 環境変数GF_TOKENが設定されている場合、それを確認
        token = os.getenv("GF_TOKEN")
        if token and any(
            t["token"] == token and t["valid"] for t in self.tokens
        ):
            return token

        # tokens.jsonにトークンが存在すれば、最初のトークンを返す
        if self.tokens:
            return self.tokens[0]["token"]

        # トークンがない場合は新しいトークンを取得
        new_token = await self.api_manager.fetch_new_token()
        await self.token_file_manager.save_tokens(
            [{"token": new_token, "valid": True, "account": {}}]
        )
        return new_token

    async def get_or_create_token(self) -> str:
        """有効なトークンがない場合、新しいトークンを取得"""
        token = await self.get_valid_token()
        return token if token else await self.create_new_token()

    async def create_new_token(self) -> str:
        """新しいトークンを生成し、アカウント情報を追加して保存"""
        new_token = await self.api_manager.fetch_new_token()
        generated_at = time.time()

        # アカウント情報を同期し、状態を追加
        account_data = await self.account_manager.sync_account(new_token)
        account_data["status"] = "active"  # アカウントのステータスを追加

        # トークン情報とアカウントデータをトークンリストに追加
        token_data = {
            "token": new_token,
            "generated_at": generated_at,
            "generated_at_str": datetime.fromtimestamp(generated_at).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "valid": True,
            "account": account_data,
        }
        self.tokens.append(token_data)

        # トークンファイルに保存
        await self.token_file_manager.save_tokens(self.tokens)

        # 環境変数に新しいトークンを設定
        os.environ["GF_TOKEN"] = new_token

        return new_token

    async def invalidate_token(self, token: str) -> None:
        """指定したトークンを無効化"""
        for t in self.tokens:
            if t["token"] == token:
                t["valid"] = False
                t["account"]["status"] = "invalid"  # ステータスを無効に更新
                break
        await self.token_file_manager.save_tokens(self.tokens)

    async def replace_token(self) -> str:
        """現在のトークンが無効な場合、新しいトークンを生成して利用する"""
        new_token = await self.create_new_token()
        os.environ["GF_TOKEN"] = new_token
        return new_token
