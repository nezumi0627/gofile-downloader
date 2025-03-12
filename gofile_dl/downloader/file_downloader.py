import asyncio
from pathlib import Path

import aiofiles
import aiohttp
from tqdm import tqdm


class FileDownloader:
    """GoFile.ioからファイルをダウンロードするクラス"""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str,
        chunk_size: int = 1024 * 1024,
        max_concurrent_requests: int = 10,
    ):
        self.session = session
        self.token = token
        self._chunk_size = chunk_size
        self._max_concurrent_requests = max_concurrent_requests

    @property
    def chunk_size(self) -> int:
        """ファイルダウンロードのチャンクサイズ"""
        return self._chunk_size

    async def download_file(self, url: str, file_path: Path) -> bool:
        """単一ファイルをダウンロード"""
        response = await self._download_file_session(url, self.token)
        if response.status != 200:
            raise ValueError(
                f"Failed to download file: HTTP {response.status}"
            )
        await self._write_file(response, file_path)
        return True

    async def download_files(self, urls: list, file_paths: list) -> bool:
        """複数ファイルを並列でダウンロード"""
        tasks = []
        for url, file_path in zip(urls, file_paths):
            tasks.append(self.download_file(url, file_path))

        # 並列ダウンロードを制御するため、最大同時リクエスト数を設定
        semaphore = asyncio.Semaphore(self._max_concurrent_requests)

        async def download_with_semaphore(url, file_path):
            async with semaphore:
                return await self.download_file(url, file_path)

        await asyncio.gather(
            *(
                download_with_semaphore(url, file_path)
                for url, file_path in zip(urls, file_paths)
            )
        )
        return True

    async def _download_file_session(
        self, url: str, token: str
    ) -> aiohttp.ClientResponse:
        """ファイルダウンロードのためのHTTPセッションを生成"""
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0",
            "Accept-Encoding": "gzip, deflate, br",
        }
        return await self.session.get(url, headers=headers)

    async def _write_file(
        self, response: aiohttp.ClientResponse, file_path: Path
    ) -> None:
        """ファイルを書き込み"""
        tmp_file = file_path.with_suffix(f"{file_path.suffix}.part")
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with aiofiles.open(tmp_file, "wb") as f:
                total_size = int(response.headers.get("Content-Length", "0"))
                downloaded = 0

                # tqdmのpositionを0にして進捗バーを固定表示
                with tqdm(
                    total=total_size,
                    desc=f"Downloading {file_path.name}",
                    unit="B",
                    unit_scale=True,
                    bar_format=(
                        "{desc} {percentage:3.0f}%|{bar}|\n"
                        " {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
                    ),
                    position=0,  # ここで位置を固定
                    leave=True,
                    dynamic_ncols=True,
                ) as pbar:
                    async for chunk in response.content.iter_chunked(
                        self.chunk_size
                    ):
                        await f.write(chunk)
                        downloaded += len(chunk)
                        pbar.update(len(chunk))

            tmp_file.rename(file_path)

        except Exception as e:
            if tmp_file.exists():
                tmp_file.unlink()
            raise e
