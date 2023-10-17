import json
import re
from abc import ABC, abstractmethod
from typing import Union
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from client import Http


class Crawler(ABC):
    def __init__(self, http: Http = None):
        self._http = Http() if http is None else http

    @abstractmethod
    async def pages(self, name: str, url: str, start: Union[int, str, None] = None, end: Union[int, str, None] = None):
        pass

    async def _get_html(self, url):
        response = await self._http.get(url)

        return response.decode('utf-8')

    @staticmethod
    def _allowed(episode: int, start, end):
        if start is not None and start > episode:
            return False

        if end is not None and end < episode:
            return False

        return True

    @staticmethod
    def _get_m3u8(html: str) -> str:
        url = re.search(r'\"https:.+?\.m3u8\"', html).group(0)

        return json.loads('{"url": %s}' % url)['url']


class Bowang(Crawler):

    async def pages(self, name: str, url: str, start: Union[int, str, None] = None, end: Union[int, str, None] = None):
        parsed = urlparse(url)
        base_url = '%s://%s' % (parsed.scheme, parsed.netloc)

        soup = BeautifulSoup(await self._get_html(url), 'html.parser')
        for link in soup.select(".play-tab-list.active .module-play-list-link"):
            url = f'{base_url}{link["href"]}'
            _m3u8 = self._get_m3u8(await self._get_html(url))

            matched = re.search(r'第([\w\\.]+)集', link.text)
            episode = matched.group(1) if matched is not None else link.text.strip()

            try:
                episode = int(episode)
                if self._allowed(episode, start, end):
                    yield Page(name, episode, url, _m3u8)
            except ValueError:
                yield Page(name, episode, url, _m3u8)


class Gimy(Crawler):
    async def pages(self, name: str, url: str, start: Union[int, str, None] = None, end: Union[int, str, None] = None):
        parsed = urlparse(url)
        base_url = '%s://%s' % (parsed.scheme, parsed.netloc)

        path = parsed.path
        episode_prefix = (path[0:path.rfind('-')])

        soup = BeautifulSoup(await self._get_html(url), 'html.parser')
        for link in soup.select(f'.playlist[class*="activeplayer"] li a[href^="{episode_prefix}"]'):
            url = f'{base_url}{link["href"]}'
            _m3u8 = self._get_m3u8(await self._get_html(url))

            matched = re.search(r'第([\w\\.]+)集', link.text)
            episode = matched.group(1) if matched is not None else link.text.strip()

            try:
                episode = int(episode)
                if self._allowed(episode, start, end):
                    yield Page(name, episode, url, _m3u8)
            except ValueError:
                yield Page(name, episode, url, _m3u8)


class Page:
    def __init__(self, name, episode: Union[int, str], url: str, m3u8_url: str):
        self.name = name
        self.episode = self.parse_episode(episode)
        self.url = url
        self.m3u8 = m3u8_url

    @staticmethod
    def parse_episode(episode: Union[int, str]) -> str:
        try:
            return '%03d' % int(episode)
        except ValueError:
            return episode


class Factory(object):
    def __init__(self, http: Http = None):
        self.__http = Http() if http is None else http

    def create(self, url: str):
        crawlers = {
            'bowang': Bowang,
            'gimy': Gimy
        }

        return crawlers.get(self.parse_name(url))(self.__http)

    @staticmethod
    def parse_name(url: str):
        domain = urlparse(url).netloc
        if re.search(u'gimy', domain):
            return 'gimy'

        return 'bowang'
