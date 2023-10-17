import asyncio
import glob
import os
from concurrent.futures import ThreadPoolExecutor

import m3u8
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad
from m3u8 import Segment
from requests import HTTPError

from client import Http
from crawlers import Page
from utils import Logger, progressbar, ANSI, get_media_info, is_same_video


def wrapper(coro):
    return asyncio.run(coro)


class Worker:
    def __init__(self, http: Http, logger: Logger, directory: str, cipher: AES = None):
        self.__http = http
        self.__logger = logger
        self.directory = directory
        self.cipher = cipher

    async def save_ts(self, segment: Segment, index: int, total: int):
        url = segment.absolute_uri
        filename = os.path.join(self.directory, ('%05d.ts' % index))

        prefix = 'download: %s.mp4 %05d/%05d'
        tries = 0
        while True:
            try:
                headers = await self.__http.head(url)
                filesize = int(headers['Content-Length'])
                start = os.path.getsize(filename) if os.path.exists(filename) else 0
                message = prefix % (self.directory, index, total)

                if start == filesize:
                    progressbar(start, filesize, message)
                    return

                response = await self.__http.get(url)
                with open(filename, 'wb') as f:
                    start = len(response)

                    if self.cipher is not None:
                        response = unpad(self.cipher.decrypt(response), AES.block_size)

                    f.write(response)
                    progressbar(start, filesize, message)
                return
            except (HTTPError, Exception) as e:
                if os.path.exists(filename):
                    os.unlink(filename)

                if tries >= 10:
                    message = 'failed: %s.mp4 %05d/%05d: %s' % (self.directory, index, total, e)
                    self.__logger.error(message)
                    return

                tries = tries + 1
                message = 'retry: %s.mp4 %05d/%05d: %s' % (self.directory, index, total, e)
                self.__logger.warning(message)
                await asyncio.sleep(10)


class M3U8Downloader:
    def __init__(self, root: str = None, http: Http = None, logger: Logger = None):
        self.__root = 'video' if root is None else root
        self.__http = Http() if http is None else http
        self.__logger = Logger() if logger is None else logger

    async def download(self, page: Page):
        directory = self.__get_directory(page)
        temp = os.path.join(os.path.dirname(directory), page.episode + '.tmp.mp4')
        target = os.path.join(os.path.dirname(directory), page.episode + '.mp4')

        if os.path.exists(target):
            self.__logger.success(f'merged: {target}')
            return

        progressbar(1, 2, 'm3u8: %s' % target)
        while True:
            try:
                playlist = await self.__get_playlist(page)
                break
            except (HTTPError, Exception) as e:
                self.__logger.warning(e)
                await asyncio.sleep(15)
        progressbar(2, 2, 'm3u8: %s' % target)

        cipher = await self.__get_cipher(playlist)
        total = len(playlist.segments)

        worker = Worker(http=self.__http, logger=self.__logger, directory=directory, cipher=cipher)
        if self.__is_files_equals(directory, total) is not True:
            with ThreadPoolExecutor(max_workers=10) as executor:
                for index, segment in enumerate(playlist.segments):
                    executor.submit(wrapper, worker.save_ts(segment, index, total))
        progressbar(0, 1, 'merge: %s' % target)

        files = self.find_ts(directory)
        file_total = len(files)
        if self.__is_files_equals(directory, total) is not True:
            message = 'failed not equals: %s %05d/%05d' % (target, file_total, total)
            progressbar(file_total, total, message, ANSI.failed)
            print('')
            return

        base_info = get_media_info(files[0])
        if os.path.exists(temp):
            os.unlink(temp)

        try:
            with open(temp, 'ab') as fw:
                for index, file in enumerate(files):
                    if is_same_video(file, base_info) is False:
                        self.__logger.debug(f'adv: {file}')
                        continue

                    with open(file, 'rb') as fr:
                        fw.write(fr.read())
                    progressbar(index + 1, file_total, 'merging: %s %05d/%05d' % (target, index + 1, file_total))

            os.rename(temp, target)
            self.__logger.success('merged: %s %05d/%05d' % (target, index + 1, file_total))
        except Exception as e:
            self.__logger.error('failed: %s %s' % (target, e))

    async def __get_cipher(self, playlist: m3u8.M3U8):
        encryption = playlist.keys[0]

        if encryption is None:
            return None

        response = await self.__http.get(encryption.absolute_uri)

        return AES.new(response, AES.MODE_CBC, encryption.iv)

    async def __get_playlist(self, page: Page):
        url = page.m3u8

        while True:
            response = await self.__http.get(url)
            parsed = m3u8.loads(response.decode('utf-8'), url)

            if len(parsed.segments) > 0:
                return parsed

            playlist = parsed.playlists[0]
            url = self.__get_m3u8_url(playlist.base_uri, playlist.uri)

    def __get_directory(self, page: Page):
        if os.path.exists(self.__root) is False:
            os.mkdir(self.__root)

        root = os.path.join(self.__root, page.name)
        if os.path.exists(root) is False:
            os.mkdir(root)

        directory = os.path.join(root, page.episode)
        if os.path.exists(directory) is False:
            os.mkdir(directory)

        return directory

    def __is_files_equals(self, directory, total):
        files = self.find_ts(directory)
        file_total = len(files)

        if file_total > total:
            for file in files:
                if os.path.exists(file):
                    os.unlink(file)
                    self.__logger.warning(f'{file} deleted')

        return file_total == total

    @staticmethod
    def find_ts(directory):
        return sorted(glob.glob(os.path.join(directory, '*.ts')))

    @staticmethod
    def __get_m3u8_url(base_uri, uri):
        segments = uri.split('/')
        segments.reverse()
        positions = map(lambda segment: base_uri.rfind(segment), segments)
        positions = filter(lambda _pos: _pos != -1, positions)
        for pos in positions:
            base_uri = base_uri[0:pos]

        return base_uri.rstrip('/') + '/' + uri.lstrip('/')


async def main(page: Page):
    downloader = M3U8Downloader('video')
    await downloader.download(page)


if __name__ == '__main__':
    # asyncio.run(main(Page(
    #     '超級瑪利歐兄弟電影版',
    #     'HD',
    #     'https://www.movieffm.net/movies/the-super-mario-bros-movie/',
    #     'https://m3u.haiwaikan.com/xm3u8/a6c6f7d96df1f4e37d4a1935c5f6869be9a3c8f65e180b8efdb8e914efd2f2f09921f11e97d0da21.m3u8'
    # )))
    asyncio.run(main(Page(
        '蠟筆小新：超級美味！B級美食大逃亡！',
        'HD',
        'https://www.movieffm.net/movies/crayon-shin-chan-very-tasty-b-class-gourmet-survival/',
        'https://m3u.haiwaikan.com/xm3u8/b2201b3b741640f809883aeb5a39202a4fd20978a1c37b312bd76d95a4e74a9c9921f11e97d0da21.m3u8'
    )))
    asyncio.run(main(Page(
        '小小兵2：格魯的崛起',
        'HD',
        'https://www.movieffm.net/movies/minions-the-rise-of-gru/',
        'https://m3u.haiwaikan.com/xm3u8/9fb6165cdf6ae4de2036cb59494c2df986cc0a5b8b470a7dd2a259a9243a4c699921f11e97d0da21.m3u8'
    )))
    # asyncio.run(main(Page(
    #     '名偵探柯南：萬聖節的新娘',
    #     'HD',
    #     'https://www.movieffm.net/movies/detective-conan-the-bride-of-halloween/',
    #     'https://m3u.haiwaikan.com/xm3u8/33a33393dae7bac77d0103f8547b11756f2ae344bd66ab8b55ce3663262ad22f9921f11e97d0da21.m3u8'
    # )))
    asyncio.run(main(Page(
        '名偵探柯南：大怪獸哥梅拉VS假面超人',
        'HD',
        'https://www.movieffm.net/movies/detective-conan-kaiju-gomera-vs-kamen-yaiba/',
        'https://m3u.haiwaikan.com/xm3u8/33a33393dae7bac77d0103f8547b11756f2ae344bd66ab8b55ce3663262ad22f9921f11e97d0da21.m3u8'
    )))
    asyncio.run(main(Page(
        '航海王劇場版：紅髮歌姬',
        'HD',
        'https://www.movieffm.net/movies/236834/',
        'https://m3u.haiwaikan.com/xm3u8/0c9882d9f0de154092ab8b5b0ab7a91eb87d76639ec8057467ca5495bf3fb8319921f11e97d0da21.m3u8'
    )))
    asyncio.run(main(Page(
        '侏羅紀世界3：統霸天下',
        'HD',
        'https://www.movieffm.net/movies/jurassic-world-dominion/',
        'https://m3u.haiwaikan.com/xm3u8/c91ea86dd6e862709b72ded369ca08932c26a5bc16fe80b904137d812a2de7449921f11e97d0da21.m3u8'
    )))
    asyncio.run(main(Page(
        '貓和老鼠：雪人國大冒險',
        'HD',
        'https://www.movieffm.net/movies/tom-and-jerry-snowmans-land/',
        'https://m3u.haiwaikan.com/xm3u8/9ae02a45330b0b1e5d259964e26236fdd9fd521266dea1758044f0c5f5d07d4e9921f11e97d0da21.m3u8'
    )))
