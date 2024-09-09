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
    # asyncio.run(main('勇者鬥惡龍 達伊的大冒險 (2020)', 'https://bowang.su/play/48772-17-1.html'))
    # asyncio.run(main('七龍珠 (1986)', 'https://bowang.su/play/99548-2-1.html'))
    # asyncio.run(main('七龍珠Z (1989)', 'https://bowang.su/play/110515-3-1.html'))
    # asyncio.run(main('七龍珠改 (2009)', 'https://bowang.su/play/41562-10-1.html'))
    # asyncio.run(main('龍珠改魔人布歐篇', 'https://bowang.su/play/15655-2-1.html'))
    # asyncio.run(main('七龍珠GT (1996)', 'https://bowang.su/play/15450-6-1.html'))
    # asyncio.run(main('九龍珠 (1993)', 'https://bowang.su/play/103058-5-1.html'))
    # asyncio.run(main('城市獵人 (1987)', 'https://bowang.su/play/10496-3-1.html'))
    # asyncio.run(main('城市獵人 (1987)', 'https://bowang.su/play/10496-2-1.html'))
    # asyncio.run(main('烏龍派出所', 'https://bowang.su/play/77596-2-1.html'))
    # asyncio.run(main('少年駭客：外星勢力第一季', 'https://bowang.su/play/160840-1-1.html'))
    # asyncio.run(main('少年駭客：外星勢力第二季', 'https://bowang.su/play/110789-6-1.html'))
    # asyncio.run(main('少年駭客：外星勢力第三季', 'https://bowang.su/play/110790-6-1.html'))
    # asyncio.run(main('幽遊白書', 'https://bowang.su/play/34018-6-1.html'))
    # asyncio.run(main('銀魂', 'https://bowang.su/play/4971-9-1.html'))
    # asyncio.run(main('銀魂劇場版：新譯紅櫻篇', 'https://bowang.su/play/78405-5-1.html'))
    # asyncio.run(main('銀魂：最終篇', 'https://bowang.su/play/64374-9-1.html'))
    # asyncio.run(main('舞動青春', 'https://bowang.su/play/33280-8-1.html'))
    # asyncio.run(main('魔神英雄傳', 'https://gimy.im/play/66819-1-1.html'))
    # asyncio.run(main('魔神英雄傳2', 'https://bowang.su/play/77539-5-1.html'))
    # asyncio.run(main('魔神英雄傳2', 'https://bowang.su/play/77539-3-15.html', 15, 15))
    # asyncio.run(main('超魔神英雄傳', 'https://bowang.su/play/103759-2-1.html'))
    # asyncio.run(main('魔神英雄傳 七魂龍神丸', 'https://bowang.su/play/76760-11-1.html'))
    # asyncio.run(main('魔神英雄傳 七魂龍神丸-再會', 'https://bowang.su/play/128262-2-1.html'))
    # asyncio.run(main('俺物語', 'https://pttplay.co/play/30132-11-1.html'))
    asyncio.run(main('蠟筆小新：新次元！超能力大決戰(日語)', 'https://gimy.ai/eps/251174-7-1.html'))
