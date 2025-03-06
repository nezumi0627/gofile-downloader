import os
import time
from datetime import datetime
from typing import Optional

from .go_file_api_manager import GoFileAPIManager
from .token_file_manager import TokenFileManager


class TokenManager:
    """GoFile API トークンを管理するクラス"""

    def __init__(
        self, token_file: str = os.getenv("TOKEN_FILE_PATH", "tokens.json")
    ) -> None:
        self.token_file_manager = TokenFileManager(token_file)
        self.api_manager = GoFileAPIManager()
        self.tokens = self.token_file_manager.load_tokens()

    async def get_valid_token(self) -> Optional[str]:
        """有効なトークンを取得（環境変数 or tokens.json）"""
        token = os.getenv("GF_TOKEN")
        if token and any(
            t["token"] == token and t["valid"] for t in self.tokens
        ):
            return token

        if self.tokens:
            return self.tokens[0]["token"]  # 最初のトークンを返す

        # トークンがない場合は新しいトークンを取得
        new_token = await self.api_manager.fetch_new_token()
        await self.token_file_manager.save_tokens(
            [{"token": new_token, "valid": True}]
        )
        return new_token

    async def get_or_create_token(self) -> str:
        """有効なトークンがない場合、新しいトークンを取得"""
        token = await self.get_valid_token()
        if token:
            return token
        return await self.create_new_token()

    async def create_new_token(self) -> str:
        """新しいトークンを生成して保存"""
        new_token = await self.api_manager.fetch_new_token()
        generated_at = time.time()
        self.tokens.append(
            {
                "token": new_token,
                "generated_at": generated_at,
                "generated_at_str": datetime.fromtimestamp(
                    generated_at
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "valid": True,
            }
        )
        await self.token_file_manager.save_tokens(self.tokens)
        os.environ["GF_TOKEN"] = new_token
        return new_token

    async def invalidate_token(self, token: str) -> None:
        """トークンを無効化"""
        for t in self.tokens:
            if t["token"] == token:
                t["valid"] = False
                break
        await self.token_file_manager.save_tokens(self.tokens)

    async def replace_token(self) -> str:
        """現在のトークンが無効な場合、新しいトークンを生成して利用する"""
        new_token = await self.create_new_token()
        os.environ["GF_TOKEN"] = new_token
        return new_token
