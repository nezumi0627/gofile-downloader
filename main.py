import asyncio

import aiohttp

from gofile_dl.downloader import GoFileDownloader


async def main():
    async with aiohttp.ClientSession() as session:
        downloader = GoFileDownloader(session)
        await downloader.init()

        result = await downloader.download(
            "https://gofile.io/d/nqZAPr", output_dir="./downloads"
        )
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
