import glob
import io
import os
import re
from unittest.mock import MagicMock

import m3u8
import pytest
import requests
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
    mocker.patch('videoprops.get_video_properties', return_value={'height': '960', 'width': '480'})

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
    mocker.patch('videoprops.get_video_properties', return_value={'height': '960', 'width': '480'})

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
    mocker.patch('videoprops.get_video_properties', return_value={'height': '960', 'width': '480'})

    root = 'video-test'
    name = "DB"
    url = 'https://bowang.su/play/126771-4-1.html'

    downloader = Downloader(Crawler(), M3U8Downloader(root))
    downloader.download(name, url)

    assert 153 == len(glob.glob(os.path.join(root, name, '*.mp4')))


# def test_mediainfo():
#     from utils import get_media_info, is_same_video
#     target = '龍珠GT'
#     root = sorted(glob.glob(os.path.join('video', target, '*')))
#     print('')
#     for directory in root:
#         if os.path.isdir(directory):
#             files = sorted(glob.glob(os.path.join(directory, '*.ts')))
#             base_info = get_media_info(files[0])
#             for file in files:
#                 if is_same_video(file, base_info) is False:
#                     print(file)
def test_request():
    # response = requests.get('https://jx.bowang.su/aliplayer/?url=http://www.iqiyi.com/v_19rroof6rc.html', headers={
    #     # 'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Brave";v="114"',
    #     # 'sec-ch-ua-mobile': '?0',
    #     # 'sec-ch-ua-platform': 'macOS',
    #     # 'Upgrade-Insecure-Requests': '1',
    #     # 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    #     # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    #     # 'Sec-GPC': '1',
    #     # 'Accept-Language': 'zh-TW,zh;q=0.8',
    #     # 'Sec-Fetch-Site': 'same-site',
    #     # 'Sec-Fetch-Mode': 'navigate',
    #     # 'Sec-Fetch-Dest': 'iframe',
    #     'Referer': 'https://bowang.su/',
    # })
    # content = response.content.decode('utf-8')
    # print(content)
    # url = re.search(r'source:\s*"([^"]+)"', content).group(1)
    # response = requests.get(url, headers={
    #     'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Brave";v="114"',
    #     'sec-ch-ua-mobile': '?0',
    #     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    #     'sec-ch-ua-platform': '"macOS"',
    #     'Accept': '*/*',
    #     'Sec-GPC': '1',
    #     'Accept-Language': 'zh-TW,zh;q=0.8',
    #     'Origin': 'https://jx.bowang.su',
    #     'Sec-Fetch-Site': 'cross-site',
    #     'Sec-Fetch-Mode': 'cors',
    #     'Sec-Fetch-Dest': 'empty',
    #     'Accept-Encoding': 'gzip',
    # })
    # print(response.content.decode('utf-8'))
    url = 'https://static1.keepcdn.com/avatar/2023/06/06/03/58/1f971a7f979e1b32ae662bf0e494423e.png'
    print(requests.get(url).content)
    pass


@pytest.fixture
def my_fs(fs: FakeFilesystem):
    fs.add_real_directory('fixtures')

    yield fs
