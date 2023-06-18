import videoprops


class ANSI:
    header = '\033[95m'
    ok_blue = '\033[94m'
    debug = '\033[96m'
    success = '\033[92m'
    warning = '\033[93m'
    failed = '\033[91m'
    end = '\033[0m'
    bold = '\033[1m'
    underline = '\033[4m'


class Logger:

    @staticmethod
    def _color(color, message):
        print(f'\r{color}{message}{ANSI.end}')

    @staticmethod
    def info(message):
        print(f'\r{message}')

    def warning(self, message):
        self._color(ANSI.warning, message)

    def error(self, message):
        self._color(ANSI.failed, message)

    def success(self, message):
        self._color(ANSI.success, message)

    def debug(self, message):
        self._color(ANSI.debug, message)


def progressbar(size: int, total: int, title="Progress", color=None):
    color_start = ''
    color_end = ''

    if color is not None:
        color_start = color
        color_end = ANSI.end

    print('\r%s[%s]:[%s%s]%.2f%%%s' % (
        color_start,
        title,
        '█' * int(size * 20 / total),
        ' ' * (20 - int(size * 20 / total)),
        float(size / total * 100),
        color_end
    ), end='')
    # if size == total:
    #     print('')


def read_file(filename: str) -> bytes:
    with open(filename, 'rb') as f:
        content = f.read()
    return content


def save_file(filename: str, content: bytes):
    with open(filename, 'wb') as f:
        f.write(content)


def get_media_info(file: str) -> dict:
    return videoprops.get_video_properties(file)


def is_same_video(file: str, base_info: dict):
    info = get_media_info(file)
    if len(base_info) != len(info):
        return False

    props = ['width', 'height']
    for prop in props:
        if base_info.get(prop) != info.get(prop):
            return False

    return True
