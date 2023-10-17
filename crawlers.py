import json
import re
from typing import Union
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from client import Http


class BowangCrawler:
    def __init__(self, http: Http = None):
        self.__http = Http() if http is None else http

    async def pages(self, name: str, url: str, start: Union[int, str, None] = None, end: Union[int, str, None] = None):
        parsed = urlparse(url)
        base_url = '%s://%s' % (parsed.scheme, parsed.netloc)

        response = await self.__http.get(url)
        soup = BeautifulSoup(response.decode('utf-8'), 'html.parser')

        for link in soup.select(".play-tab-list.active .module-play-list-link"):
            matched = re.search(r'[\d\\.]+', link.text)

            if matched is None:
                url = "%s%s" % (base_url, link['href'])
                yield Page(name, link.text.strip(), url, await self.__get_m3u8(url))
            else:
                no = float(matched.group(0))
                if self.allowed(no, start, end):
                    url = "%s%s" % (base_url, link['href'])
                    yield Page(name, no, url, await self.__get_m3u8(url))

    @staticmethod
    def allowed(episode: float, start, end):
        if start is not None and start > episode:
            return False

        if end is not None and end < episode:
            return False

        return True

    async def __get_m3u8(self, url: str) -> str:
        response = await self.__http.get(url)

        return json.loads("{%s}" % re.search(r'\"url\":\"https:.*\.m3u8\"', response.decode('utf-8')).group(0))['url']


class Page:
    def __init__(self, name, episode: Union[float, str], url: str, m3u8_url: str):
        self.name = name
        self.episode = self.parse_episode(episode)
        self.url = url
        self.m3u8 = m3u8_url

    @staticmethod
    def parse_episode(episode: Union[float, str]) -> Union[float, str]:
        try:
            episode = int(episode)
            return '%03d' % episode
        except ValueError:
            return episode


class Factory(object):
    def __init__(self, http: Http = None):
        self.__http = Http() if http is None else http

    def create(self, url: str):
        crawlers = {'bowang': BowangCrawler}

        return crawlers.get(self.parse_name(url))(self.__http)

    @staticmethod
    def parse_name(url: str):
        # domain = urlparse(url).netloc
        # if re.search(u'bowang', domain):
        #     return 'bowang'
        return 'bowang'
