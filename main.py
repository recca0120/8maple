import asyncio
import glob
import os
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Union

import m3u8
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad
from m3u8 import Segment
from requests import HTTPError

from client import Http
from crawlers import Crawler, Page
from utils import progressbar, is_same_video, get_media_info, Logger, ANSI


def wrapper(coro):
    return asyncio.run(coro)


class M3U8Downloader:
    def __init__(self, root: str = None, http: Http = None, logger: Logger = None):
        self.__root = 'video' if root is None else root
        self.__http = Http() if http is None else http
        self.__logger = Logger() if logger is None else logger

    async def download(self, page: Page):
        directory = self.__get_directory(page)
        temp = os.path.join(os.path.dirname(directory), str(page.no).zfill(3) + '.tmp.mp4')
        target = os.path.join(os.path.dirname(directory), str(page.no).zfill(3) + '.mp4')

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
        if self.__is_files_equals(directory, total) is not True:
            with ThreadPoolExecutor(max_workers=10) as executor:
                for index, segment in enumerate(playlist.segments):
                    executor.submit(wrapper, self.__save_ts(directory, segment, index, total, cipher))
        progressbar(0, 1, 'merge: %s' % target)

        files = self.find_ts(directory)
        file_total = len(files)
        if self.__is_files_equals(directory, total) is not True:
            progressbar(
                file_total,
                total,
                'failed not equals: %s %05d/%05d' % (target, file_total, total),
                ANSI.failed
            )
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
            m3u8_ = m3u8.loads(response.decode('utf-8'), url)

            if len(m3u8_.segments) > 0:
                return m3u8_

            playlist = m3u8_.playlists[0]
            url = self.__get_m3u8_url(playlist.base_uri, playlist.uri)

    def __get_directory(self, page: Page):
        if os.path.exists(self.__root) is False:
            os.mkdir(self.__root)

        root = os.path.join(self.__root, page.name)
        if os.path.exists(root) is False:
            os.mkdir(root)

        directory = os.path.join(root, str(page.no).zfill(3))
        if os.path.exists(directory) is False:
            os.mkdir(directory)

        return directory

    async def __save_ts(self, directory: str, segment: Segment, index: int, total: int, cipher: AES = None):
        url = segment.absolute_uri
        filename = os.path.join(directory, ('%05d.ts' % index))

        prefix = 'download: %s.mp4 %05d/%05d'
        tries = 0
        while True:
            try:
                headers = await self.__http.head(url)
                filesize = int(headers['Content-Length'])
                start = os.path.getsize(filename) if os.path.exists(filename) else 0
                message = prefix % (directory, index, total)

                if start == filesize:
                    progressbar(start, filesize, message)
                    return

                response = await self.__http.get(url)
                with open(filename, 'wb') as f:
                    start = len(response)
                    response = response if cipher is None else unpad(cipher.decrypt(response), AES.block_size)
                    f.write(response)
                    progressbar(start, filesize, message)
                return
            except (HTTPError, Exception) as e:
                if os.path.exists(filename):
                    os.unlink(filename)

                if tries >= 10:
                    message = 'failed: %s.mp4 %05d/%05d: %s' % (directory, index, total, e)
                    self.__logger.error(message)
                    return

                tries = tries + 1
                message = 'retry: %s.mp4 %05d/%05d: %s' % (directory, index, total, e)
                self.__logger.warning(message)
                await asyncio.sleep(10)

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


class Downloader:
    def __init__(self, crawler: Crawler, m3u8_downloader: M3U8Downloader):
        self.crawler = crawler
        self.m3u8_downloader = m3u8_downloader

    async def download(self, name: str, url: str, start: Union[int, None] = None, end: Union[int, None] = None):
        pages = self.crawler.pages(name, url, start, end)

        async for page in pages:
            await self.m3u8_downloader.download(page)


async def main(folder: str, url: str, start: Union[int, None] = None, end: Union[int, None] = None):
    client = Http()
    downloader = Downloader(Crawler(client), M3U8Downloader('video', client))
    await downloader.download(folder, url, start, end)


if __name__ == '__main__':
    asyncio.run(main('九龍珠 (1993)', 'https://bowang.su/play/103058-5-1.html'))
