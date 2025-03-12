import asyncio

import aiohttp

from gofile_dl.downloader import GoFileDownloader
from gofile_dl.token import TokenManager
from gofile_dl.token.get_status import GofileAccountManager


async def main():
    async with aiohttp.ClientSession() as session:
        token_manager = TokenManager()
        account_manager = GofileAccountManager()
        token = await token_manager.get_or_create_token()
        status = await account_manager.get_account_status(token)
        print(status)
        downloader = GoFileDownloader(session, token)
        await downloader.init()

        result = await downloader.download(
            "https://gofile.io/d/0GqyBD",
            output_dir="./downloads",
            password="0627",
        )
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
