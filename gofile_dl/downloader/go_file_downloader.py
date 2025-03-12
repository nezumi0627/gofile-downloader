# go_file_downloader.py

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from ..token.token_manager import TokenManager
from .file_downloader import FileDownloader
from .go_file_api import GoFileAPI


class GoFileDownloader:
    """GoFile.ioのコンテンツをダウンロードするメインクラス"""

    def __init__(
        self, session: aiohttp.ClientSession, token: Optional[str] = None
    ):
        self.session = session
        self.token = token
        self._api = None
        self._downloader = None
        self._token_manager = None

    async def init(self):
        """非同期の初期化処理"""
        if not self.token:
            self._token_manager = TokenManager()
            self.token = await self._token_manager.get_or_create_token()
        self._api = GoFileAPI(self.session, self.token)
        self._downloader = FileDownloader(self.session, self.token)

    def _normalize_url(self, url_or_id: str) -> str:
        """URLまたはIDからGoFileのIDを抽出"""
        if url_or_id.startswith(("http://", "https://")):
            match = re.search(r"gofile\.io/d/([a-zA-Z0-9]+)", url_or_id)
            if match:
                return match.group(1)
        if re.match(r"^[a-zA-Z0-9]+$", url_or_id):
            return url_or_id
        return f"Invalid URL or ID format: {url_or_id}"

    async def _extract_files(
        self, content_data: Dict[str, Any], parent_path: str = ""
    ) -> List[Dict[str, Any]]:
        """コンテンツデータからファイル情報を抽出"""
        files = []

        if content_data["type"] == "file":
            files.append(
                {
                    "name": os.path.join(parent_path, content_data["name"]),
                    "link": content_data["link"],
                    "size": content_data.get("size"),
                }
            )
        elif content_data["type"] == "folder":
            folder_path = os.path.join(parent_path, content_data["name"])
            for _, child in content_data.get("children", {}).items():
                if child["type"] == "folder":
                    folder_data = await self._api.fetch_content(child["id"])
                    if folder_data:
                        folder_files = await self._extract_files(
                            folder_data, folder_path
                        )
                        files.extend(folder_files)
                else:
                    files.append(
                        {
                            "name": os.path.join(folder_path, child["name"]),
                            "link": child["link"],
                            "size": child.get("size"),
                        }
                    )

        return files

    async def download(
        self,
        url_or_id: str,
        password: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """GoFileからファイルをダウンロード"""
        result = {
            "status": "success",
            "message": "",
            "files": [],
            "errors": [],
        }

        try:
            content_id = self._normalize_url(url_or_id)
            if "Invalid URL or ID format" in content_id:
                result["status"] = "error"
                result["message"] = content_id
                return result

            output_path = (
                Path(output_dir) if output_dir else Path("./downloads")
            )
            output_path.mkdir(parents=True, exist_ok=True)

            # ファイルIDのディレクトリを作成
            content_id_dir = output_path / content_id
            content_id_dir.mkdir(parents=True, exist_ok=True)

            # APIからコンテンツデータを取得
            content_data = await self._api.fetch_content(content_id, password)
            if isinstance(
                content_data, str
            ):  # APIからエラーメッセージを受け取った場合
                result["status"] = "error"
                result["message"] = content_data
                return result
            if not content_data:
                result["status"] = "error"
                result["message"] = "Failed to fetch content data"
                return result

            files_to_download = await self._extract_files(content_data)

            download_tasks = [
                self._downloader.download_file(
                    file_info["link"], content_id_dir / file_info["name"]
                )
                for file_info in files_to_download
            ]

            download_results = await asyncio.gather(*download_tasks)

            for file_info, success in zip(files_to_download, download_results):
                file_result = {
                    "filename": file_info["name"],
                    "path": str(content_id_dir / file_info["name"]),
                    "size": file_info.get("size"),
                    "success": success,
                }
                result["files"].append(file_result)
                if isinstance(success, str):  # エラーメッセージ
                    result["errors"].append(success)

            if result["errors"]:
                result["status"] = "partial"
                result["message"] = (
                    f"Downloaded {len(result['files'])} files, "
                    f"{len(result['errors'])} of which failed"
                )
            else:
                result["message"] = (
                    f"Successfully downloaded {len(result['files'])} files"
                )

        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Error during download: {str(e)}"
            result["errors"].append(f"Error during download: {str(e)}")

        return result
