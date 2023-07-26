import json
import re
from typing import Union
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from client import Http


class Crawler:
    def __init__(self, http: Http = None):
        self.__http = Http() if http is None else http

    async def pages(self, name: str, url: str, start: Union[int, None] = None, end: Union[int, None] = None):
        parsed = urlparse(url)
        base_url = '%s://%s' % (parsed.scheme, parsed.netloc)

        response = await self.__http.get(url)
        soup = BeautifulSoup(response.decode('utf-8'), 'html.parser')

        for link in soup.select(".play-tab-list.active .module-play-list-link"):
            no = int(re.search(r'[\d\\.]+', link.text).group(0))
            if self.allowed(no, start, end):
                url = "%s%s" % (base_url, link['href'])
                yield Page(name, no, url, await self.__get_m3u8(url))

    @staticmethod
    def allowed(no: int, start, end):
        if start is not None and start > no:
            return False

        if end is not None and end < no:
            return False

        return True

    async def __get_m3u8(self, url: str) -> str:
        response = await self.__http.get(url)

        return json.loads("{%s}" % re.search(r'\"url\":\"https:.*\.m3u8\"', response.decode('utf-8')).group(0))['url']


class Page:
    def __init__(self, name, no: int, url: str, m3u8_: str):
        self.name = name
        self.no = no
        self.url = url
        self.m3u8 = m3u8_
