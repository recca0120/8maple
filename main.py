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
from bs4 import BeautifulSoup

from utils import progressbar, get_mediainfo

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
}


class Page:
    def __init__(self, no: int, url: str, m3u8_: str):
        self.no = no
        self.url = url
        self.m3u8 = m3u8_


class Crawler:

    def pages(self, url: str, start: Union[int, None] = None, end: Union[int, None] = None):
        parsed = urlparse(url)
        base_url = '%s://%s' % (parsed.scheme, parsed.netloc)

        response = requests.get(url, headers=headers)

        soup = BeautifulSoup(response.text, 'html.parser')

        for link in soup.select(".play-tab-list.active .module-play-list-link"):
            no = int(re.search(r'[\d\\.]+', link.text).group(0))
            if self.allowed(no, start, end):
                url = "%s%s" % (base_url, link['href'])
                yield Page(no, url, self.__get_m3u8(url))

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

        # for index, seg in enumerate(playlist.segments):
        #     self.__save_ts(directory, playlist.base_uri + seg.uri, index)

        with ThreadPoolExecutor(max_workers=20) as pool:
            for index, seg in enumerate(playlist.segments):
                pool.submit(self.__save_ts, directory, playlist.base_uri + seg.uri, index)

        progressbar(0, 1, 'merge: %s' % target)
        files = sorted(glob.glob(os.path.join(directory, '*.ts')))
        total = len(files)
        base_info = get_mediainfo(files[0])

        for index, file in enumerate(files):
            if self.is_same_video(file, base_info) is False:
                print('\r' + 'adv: %s' % file)
                # progressbar(index + 1, total, 'merge: %s' % target)
                continue

            with open(file, 'rb') as fr, open(target, 'ab') as fw:
                fw.write(fr.read())
            progressbar(index + 1, total, 'merge: %s' % target)

    @staticmethod
    def is_same_video(file: str, base_info: dict):
        info = get_mediainfo(file)
        if len(base_info) != len(info):
            return False

        props = ['width', 'height']
        for prop in props:
            if base_info[prop] != info[prop]:
                return False

        return True

    @staticmethod
    def __get_playlist(page):
        base = m3u8.load(page.m3u8)

        return m3u8.load(base.base_uri + base.playlists[0].uri)

    def __get_directory(self, page):
        if os.path.exists(self.__root) is False:
            os.mkdir(self.__root)

        directory = '%s/%s' % (self.__root, str(page.no).zfill(3))
        if os.path.exists(directory) is False:
            os.mkdir(directory)

        return directory

    @staticmethod
    def __save_ts(directory, url, index):
        message = 'download: %s/%s.ts'
        filename = os.path.join(directory, str(index).zfill(5) + '.ts')
        conn_timeout = 5
        read_timeout = 10
        timeouts = (conn_timeout, read_timeout)

        while True:
            try:
                response = requests.head(url, headers=headers, timeout=timeouts)
                response.raise_for_status()

                filesize = int(response.headers['Content-Length'])

                # if 'Content-disposition' in response.headers:
                #     value, params = cgi.parse_header(response.headers['Content-disposition'])
                #     filename = params['filename']
                # else:
                #     filename = url.split('/')[-1]

                start = os.path.getsize(filename) if os.path.exists(filename) else 0

                if start == filesize:
                    progressbar(start, filesize, message % (directory, str(index).zfill(5)))
                    # print('%s - %s: %0.f' % (directory, index, (start / filesize) * 100))
                    return

                end = int(filesize) - 1
                resume_headers = headers.copy()
                resume_headers['Range'] = "bytes={0}-{1}".format(start, end)

                response = requests.get(url, stream=True, headers=resume_headers, timeout=timeouts)
                response.raise_for_status()

                with open(filename, 'ab+') as f:
                    for chunk in response.iter_content(chunk_size=None):
                        f.write(chunk)
                        start = start + len(chunk)
                        progressbar(start, filesize, message % (directory, str(index).zfill(5)))
                return
            except Exception as e:
                print('\r' + 'retry: %s.mp4-%s: %s' % (directory, str(index).zfill(5), e))
                time.sleep(2)


class Downloader:
    def __init__(self, crawler: Crawler, m3u8_downloader: M3U8Downloader):
        self.crawler = crawler
        self.m3u8_downloader = m3u8_downloader

    def download(self, url: str, start: Union[int, None] = None, end: Union[int, None] = None):
        pages = self.crawler.pages(url, start, end)
        for page in pages:
            self.m3u8_downloader.download(page)


def main():
    downloader = Downloader(Crawler(), M3U8Downloader())
    downloader.download('https://bowang.su/play/126771-4-1.html')


if __name__ == '__main__':
    main()
