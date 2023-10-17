import asyncio
from typing import Union

from client import Http
from crawlers import Factory
from m3u8_downloader import M3U8Downloader


class Downloader:
    def __init__(self, factory: Factory, m3u8_downloader: M3U8Downloader):
        self.factory = factory
        self.m3u8_downloader = m3u8_downloader

    async def download(
            self,
            name: str,
            url: str,
            start: Union[int, str, None] = None,
            end: Union[int, str, None] = None
    ):
        crawler = self.factory.create(url)
        pages = crawler.pages(name, url, start, end)

        async for page in pages:
            await self.m3u8_downloader.download(page)


async def main(folder: str, url: str, start: Union[int, str, None] = None, end: Union[int, str, None] = None):
    client = Http()
    downloader = Downloader(Factory(client), M3U8Downloader('video', client))
    await downloader.download(folder, url, start, end)


if __name__ == '__main__':
    asyncio.run(main('九龍珠 (1993)', 'https://bowang.su/play/103058-5-1.html'))
