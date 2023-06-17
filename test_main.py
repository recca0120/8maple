import glob
import io
import os
import re
from unittest.mock import MagicMock

import m3u8
import pytest
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest_mock import MockFixture

from main import Crawler, M3U8Downloader, Page, Downloader
from utils import read_file


def get_fixture(url: str):
    file = url[url.rfind('/') + 1:]
    directory = ''
    if 'bowang' in url:
        directory = 'bowang'

    if 'ffzy-online2' in url:
        directory = 'ffzy-online2'

    if 'yle888' in url:
        directory = 'yle888'

    if re.search(r'\.ts$', url) is not None:
        content = (url + "\n").encode('utf-8')
        if directory in ['yle888']:
            cipher = AES.new(read_file(os.path.join('fixtures', directory, 'key.key')), AES.MODE_CBC)
            content = cipher.encrypt(pad(content, AES.block_size))

        return content

    if directory == 'bowang' and file.find('126771-') != -1:
        return read_file(os.path.join('fixtures', directory, '126771-4-1.html'))

    if directory == 'ffzy-online2' and file == 'mixed.m3u8':
        return """#EXTM3U
            #EXT-X-VERSION:3
            #EXT-X-PLAYLIST-TYPE:VOD
            #EXT-X-MEDIA-SEQUENCE:0
            #EXT-X-TARGETDURATION:8
            #EXT-X-DISCONTINUITY
            #EXTINF:5.880867,
            d5f7e4b581e000000.ts
            """.encode('utf-8')

    if directory == 'yle888' and 'hls/index.m3u8' in url:
        return """ #EXTM3U
            #EXT-X-VERSION:3
            #EXT-X-TARGETDURATION:7
            #EXT-X-PLAYLIST-TYPE:VOD
            #EXT-X-MEDIA-SEQUENCE:0
            #EXT-X-KEY:METHOD=AES-128,URI="/20221207/Gqk5BD7f/1500kb/hls/key.key"
            #EXTINF:4.128,
            /20221207/Gqk5BD7f/1500kb/hls/1N6S6O1u.ts
            #EXTINF:3.127,
            /20221207/Gqk5BD7f/1500kb/hls/Q0HXvpgA.ts 
            """.encode('utf-8')

    file = os.path.join('fixtures', directory, file)
    if os.path.exists(file):
        return read_file(file)

    return b''


def mocked_requests_get(*args, **kwargs):
    mock = MagicMock()

    content = get_fixture(args[0])
    mock.headers = {'Accept-Ranges': 'bytes', 'Content-Length': len(content)}
    mock.content = content
    try:
        mock.text = content.decode('utf-8')
    except UnicodeDecodeError:
        mock.text = None

    if kwargs.get('stream') is True:
        mock.iter_content = MagicMock()
        mock.iter_content.return_value = io.BytesIO(content)

    return mock


def mocked_m3u8(*args, **kwargs):
    url: str = args[0]
    content = get_fixture(url)

    mock = m3u8.loads(content.decode('utf-8'))
    mock.base_uri = url

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


def test_m3u8_downloader_and_decrypt_content(mocker: MockFixture, my_fs):
    mocker.patch('requests.head', side_effect=mocked_requests_get)
    mocker.patch('requests.get', side_effect=mocked_requests_get)
    mocker.patch('m3u8.load', side_effect=mocked_m3u8)
    mocker.patch('ffmpeg.probe', return_value={'streams': [{'height': '960', 'width': '480'}]})

    root = 'video-test'
    name = "DB"
    no = 1
    url = 'https://bowang.su/play/126771-4-1.html'
    m3u8_ = 'https://new.yle888.vip/20221207/Gqk5BD7f/index.m3u8'

    page = Page(name, no, url, m3u8_)
    downloader = M3U8Downloader(root)
    downloader.download(page)


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
#     files = sorted(glob.glob(os.path.join('video/龍珠改/001/*.ts')))
#     print('')
#     for file in files:
#         print(get_video_properties(file)['width'])


@pytest.fixture
def my_fs(fs: FakeFilesystem):
    fs.add_real_directory('fixtures')

    yield fs
