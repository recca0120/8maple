import glob
import io
import os
import re
from unittest.mock import MagicMock

import m3u8
import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest_mock import MockFixture

from main import Crawler, M3U8Downloader, Page, Downloader


def read_file(filename: str) -> bytes:
    with open(filename, 'rb') as f:
        content = f.read()
    return content


def mocked_requests_get(*args, **kwargs):
    mock = MagicMock()
    url: str = args[0]
    file = url[url.rfind('/') + 1:-1]
    content = b''
    if file.find('126771-') != -1:
        content = read_file('fixtures/126771-4-1.htm')
    elif re.search(r'\.ts$', url) is not None:
        content = (url + "\n").encode('utf-8')

    mock.content = content
    mock.text = content.decode('utf-8')

    mock.headers = {
        'Accept-Ranges': 'bytes',
        'Content-Length': len(content),
    }

    if kwargs.get('stream') is True:
        mock.iter_content = MagicMock()
        mock.iter_content.return_value = io.BytesIO(content)

    return mock


def mocked_m3u8(*args, **kwargs):
    url: str = args[0]
    file = url[url.rfind('/') + 1:-1]
    if file == 'mixed.m3u':
        text = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-PLAYLIST-TYPE:VOD
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-TARGETDURATION:8
#EXT-X-DISCONTINUITY
#EXTINF:5.880867,
d5f7e4b581e000000.ts
"""
    else:
        text = read_file(os.path.join('fixtures', file)).decode('utf-8')

    mock = m3u8.loads(text)
    mock.base_uri = 'https://vip.ffzy-online2.com/20221231/3982_a82a6172'

    return mock


def test_crawler(mocker: MockFixture):
    mocker.patch('requests.get', side_effect=mocked_requests_get)

    name = "DB"
    url = 'https://bowang.su/play/126771-4-1.html'

    crawler = Crawler()
    pages = list(crawler.pages(name, url))

    assert 153 == len(pages)

    page = pages[0]
    assert name == page.name
    assert 1 == page.no
    assert 'https://bowang.su/play/126771-4-1.html' == page.url
    assert 'https://vip.ffzy-online2.com/20221231/3982_a82a6172/index.m3u8' == page.m3u8


def test_m3u8_downloader(mocker: MockFixture, my_fs):
    mocker.patch('requests.head', side_effect=mocked_requests_get)
    mocker.patch('requests.get', side_effect=mocked_requests_get)
    mocker.patch('m3u8.load', side_effect=mocked_m3u8)
    mocker.patch('ffmpeg.probe', return_value={'streams': [{'height': '960', 'width': '480'}]})

    root = 'video-test'
    name = "DB"
    no = 1
    url = 'https://bowang.su/play/126771-4-1.html'
    m3u8_ = 'https://vip.ffzy-online2.com/20221231/3982_a82a6172/index.m3u8'

    page = Page(name, no, url, m3u8_)

    downloader = M3U8Downloader(root)
    downloader.download(page)

    assert re.search(r'000\.ts', read_file('%s/%s/%s.mp4' % (root, page.name, str(page.no).zfill(3))).decode('utf-8'))


def test_downloader(mocker: MockFixture, my_fs):
    mocker.patch('requests.head', side_effect=mocked_requests_get)
    mocker.patch('requests.get', side_effect=mocked_requests_get)
    mocker.patch('m3u8.load', side_effect=mocked_m3u8)
    mocker.patch('ffmpeg.probe', return_value={'streams': [{'height': '960', 'width': '480'}]})

    root = 'video-test'
    name = "DB"
    url = 'https://bowang.su/play/126771-4-1.html'

    downloader = Downloader(Crawler(), M3U8Downloader(root))
    downloader.download(name, url)

    assert 153 == len(glob.glob(os.path.join(root, name, '*.mp4')))


# def test_mediainfo():
#     from utils import get_mediainfo
#
#     files = sorted(glob.glob(os.path.join('video/004/' '*.ts')))
#     print('')
#     for file in files:
#         info = get_mediainfo(file)
#         print(len(info))
#         print(info)
#         # if info['height'] == 1080:
#         #     print(info)


@pytest.fixture
def my_fs(fs: FakeFilesystem):
    fs.add_real_directory('fixtures')

    yield fs
