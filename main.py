import glob
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import m3u8
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
}


class Page:
    def __init__(self, no: int, url: str, m3u8_: str):
        self.no = no
        self.url = url
        self.m3u8 = m3u8_


class Crawler:

    def pages(self):
        base_url = 'https://bowang.su'
        response = requests.get(f'{base_url}/play/126771-4-1.html', headers=headers)

        soup = BeautifulSoup(response.text, 'html.parser')

        for link in soup.select(".play-tab-list.active .module-play-list-link"):
            no = int(re.search(r'[\d\\.]+', link.text).group(0))
            url = "%s%s" % (base_url, link['href'])
            yield Page(no, url, self.__get_m3u8(url))

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
            progressbar(1, 1, '%s' % target)
            return

        playlist = self.__get_playlist(page)

        with ThreadPoolExecutor(max_workers=20) as pool:
            for index, seg in enumerate(playlist.segments):
                pool.submit(self.__save_ts, directory, playlist.base_uri + seg.uri, index)

        files = sorted(glob.glob(os.path.join(directory, '*.ts')))
        total = len(files)

        for index, file in enumerate(files):
            with open(file, 'rb') as fr, open(target, 'ab') as fw:
                fw.write(fr.read())
            progressbar(index + 1, total, 'merge: %s' % target)

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
        filename = os.path.join(directory, str(index).zfill(5) + '.ts')
        while True:
            try:
                response = requests.head(url, headers=headers)
                response.raise_for_status()

                filesize = int(response.headers['Content-Length'])

                # if 'Content-disposition' in response.headers:
                #     value, params = cgi.parse_header(response.headers['Content-disposition'])
                #     filename = params['filename']
                # else:
                #     filename = url.split('/')[-1]

                start = os.path.getsize(filename) if os.path.exists(filename) else 0

                if start == filesize:
                    progressbar(start, filesize, '%s/%s.ts' % (directory, str(index).zfill(5)))
                    # print('%s - %s: %0.f' % (directory, index, (start / filesize) * 100))
                    return

                end = int(filesize) - 1
                resume_headers = headers.copy()
                resume_headers['Range'] = "bytes={0}-{1}".format(start, end)

                response = requests.get(url, stream=True, headers=resume_headers)
                response.raise_for_status()

                with open(filename, 'ab+') as f:
                    for chunk in response.iter_content(chunk_size=None):
                        f.write(chunk)
                        start = start + len(chunk)
                        progressbar(start, filesize, '%s/%s.ts' % (directory, str(index).zfill(5)))
                return
            except Exception as e:
                print('\r' + 'retry %s.mp4-%s: %s' % (directory, str(index).zfill(5), e))
                time.sleep(5)


class Downloader:
    def __init__(self, crawler: Crawler, m3u8_downloader: M3U8Downloader):
        self.crawler = crawler
        self.m3u8_downloader = m3u8_downloader

    def download(self):
        for page in self.crawler.pages():
            self.m3u8_downloader.download(page)


def progressbar(size: int, total: int, title="Progress"):
    print('\r' + '[%s]:[%s%s]%.2f%%' % (
        title,
        '█' * int(size * 20 / total), ' ' * (20 - int(size * 20 / total)),
        float(size / total * 100)), end='')


def main():
    downloader = Downloader(Crawler(), M3U8Downloader())
    downloader.download()


if __name__ == '__main__':
    main()
