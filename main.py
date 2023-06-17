import glob
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Union
from urllib.parse import urlparse

import m3u8
import requests
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad
from bs4 import BeautifulSoup
from m3u8 import Segment
from requests import HTTPError
from videoprops import get_video_properties

from utils import progressbar

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
}


class Page:
    def __init__(self, name, no: int, url: str, m3u8_: str):
        self.name = name
        self.no = no
        self.url = url
        self.m3u8 = m3u8_


class Crawler:

    def pages(self, name: str, url: str, start: Union[int, None] = None, end: Union[int, None] = None):
        parsed = urlparse(url)
        base_url = '%s://%s' % (parsed.scheme, parsed.netloc)

        response = requests.get(url, headers=headers)

        soup = BeautifulSoup(response.text, 'html.parser')

        for link in soup.select(".play-tab-list.active .module-play-list-link"):
            no = int(re.search(r'[\d\\.]+', link.text).group(0))
            if self.allowed(no, start, end):
                url = "%s%s" % (base_url, link['href'])
                yield Page(name, no, url, self.__get_m3u8(url))

    @staticmethod
    def allowed(no: int, start, end):
        if start is not None and start > no:
            return False

        if end is not None and end < no:
            return False

        return True

    @staticmethod
    def __get_m3u8(url: str) -> str:
        response = requests.get(url, headers=headers)

        return json.loads("{%s}" % re.search(r'\"url\":\"https:.*\.m3u8\"', response.text).group(0))['url']


class M3U8Downloader:
    timeouts = (5, 10)

    def __init__(self, root: str = None):
        self.__root = 'video' if root is None else root

    def download(self, page: Page):
        directory = self.__get_directory(page)
        target = os.path.join(os.path.dirname(directory), str(page.no).zfill(3) + '.mp4')

        if os.path.exists(target):
            progressbar(1, 1, 'merged: %s' % target)
            return

        progressbar(1, 2, 'm3u8: %s' % target)
        playlist = self.__get_playlist(page)
        progressbar(2, 2, 'm3u8: %s' % target)

        cipher = self.__get_cipher(playlist)

        # for index, segment in enumerate(playlist.segments):
        #     self.__save_ts(directory, segment, index, cipher)

        with ThreadPoolExecutor(max_workers=20) as pool:
            for index, segment in enumerate(playlist.segments):
                pool.submit(self.__save_ts, directory, segment, index, cipher)

        progressbar(0, 1, 'merge: %s' % target)
        files = sorted(glob.glob(os.path.join(directory, '*.ts')))
        total = len(files)
        base_info = get_video_properties(files[0])

        for index, file in enumerate(files):
            if self.__is_same_video(file, base_info) is False:
                print('\r' + 'adv: %s' % file)
                # progressbar(index + 1, total, 'merge: %s' % target)
                continue

            with open(file, 'rb') as fr, open(target, 'ab') as fw:
                fw.write(fr.read())
            progressbar(index + 1, total, 'merge: %s' % target)

    def __get_cipher(self, playlist):
        encryption = playlist.keys[0]

        if encryption is None:
            return None

        return AES.new(self.__http_get(encryption.absolute_uri).content, AES.MODE_CBC, encryption.iv)

    def __get_playlist(self, page):
        url = page.m3u8

        while True:
            m3u8_ = m3u8.loads(self.__http_get(url).content.decode('utf-8'), url)

            if len(m3u8_.segments) > 0:
                return m3u8_

            playlist = m3u8_.playlists[0]
            url = self.__get_m3u8_url(playlist.base_uri, playlist.uri)

    def __get_directory(self, page):
        if os.path.exists(self.__root) is False:
            os.mkdir(self.__root)

        root = os.path.join(self.__root, page.name)
        if os.path.exists(root) is False:
            os.mkdir(root)

        directory = os.path.join(root, str(page.no).zfill(3))
        if os.path.exists(directory) is False:
            os.mkdir(directory)

        return directory

    def __save_ts(self, directory: str, segment: Segment, index: int, cipher=None):
        url = segment.absolute_uri
        message = 'download: %s/%s.ts'
        filename = os.path.join(directory, str(index).zfill(5) + '.ts')

        while True:
            try:
                response = self.__http_head(url)

                filesize = int(response.headers['Content-Length'])
                start = os.path.getsize(filename) if os.path.exists(filename) else 0

                if start == filesize:
                    progressbar(start, filesize, message % (directory, str(index).zfill(5)))
                    return

                response = self.__http_get(url)
                content = response.content

                with open(filename, 'wb') as f:
                    start = len(content)
                    content = content if cipher is None else unpad(cipher.decrypt(content), AES.block_size)
                    f.write(content)
                    progressbar(start, filesize, message % (directory, str(index).zfill(5)))
                return
            except HTTPError as e:
                print('\r' + 'retry: %s.mp4-%s: %s' % (directory, str(index).zfill(5), e))
                time.sleep(2)

    def __http_get(self, url: str):
        response = requests.get(url, headers=headers, timeout=self.timeouts)
        response.raise_for_status()

        return response

    def __http_head(self, url):
        response = requests.head(url, headers=headers, timeout=self.timeouts)
        response.raise_for_status()

        return response

    @staticmethod
    def __is_same_video(file: str, base_info: dict):
        info = get_video_properties(file)
        if len(base_info) != len(info):
            return False

        props = ['width', 'height']
        for prop in props:
            if base_info.get(prop) != info.get(prop):
                return False

        return True

    @staticmethod
    def __get_m3u8_url(base_uri, uri):
        segments = uri.split('/')
        segments.reverse()
        positions = map(lambda segment: base_uri.rfind(segment), segments)
        positions = filter(lambda pos: pos != -1, positions)
        for pos in positions:
            base_uri = base_uri[0:pos]

        return base_uri.rstrip('/') + '/' + uri.lstrip('/')


class Downloader:
    def __init__(self, crawler: Crawler, m3u8_downloader: M3U8Downloader):
        self.crawler = crawler
        self.m3u8_downloader = m3u8_downloader

    def download(self, name: str, url: str, start: Union[int, None] = None, end: Union[int, None] = None):
        pages = self.crawler.pages(name, url, start, end)
        for page in pages:
            self.m3u8_downloader.download(page)


def main():
    downloader = Downloader(Crawler(), M3U8Downloader())
    downloader.download('龍珠GT', 'https://bowang.su/play/15450-10-1.html')


if __name__ == '__main__':
    main()
