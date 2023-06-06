import ffmpeg


def progressbar(size: int, total: int, title="Progress"):
    print('\r' + '[%s]:[%s%s]%.2f%%' % (
        title,
        '█' * int(size * 20 / total), ' ' * (20 - int(size * 20 / total)),
        float(size / total * 100)), end='')
    # if size == total:
    #     print('')


def get_mediainfo(filename: str) -> dict:
    return ffmpeg.probe(filename)["streams"][0]
    # out = subprocess.Popen(['mediainfo', filename],
    #                        shell=False,
    #                        stdout=subprocess.PIPE).stdout.read()
    # info = {}
    # groups = re.findall(r'([^\n:]+):([^\n]*)', out.decode('utf-8'))
    # for (key, value) in groups:
    #     info[key.strip().lower()] = value.strip()
    #
    # return info


def read_file(filename: str) -> bytes:
    with open(filename, 'rb') as f:
        content = f.read()
    return content


def save_file(filename: str, content: bytes):
    with open(filename, 'wb') as f:
        f.write(content)
