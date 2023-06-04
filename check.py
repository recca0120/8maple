import glob
import os


def is_ts(file):
    with open(file, 'rb') as f:
        return b'G@\x11' in f.read(4)


def main():
    directories = sorted(filter(lambda _file: os.path.isdir(_file), glob.glob(os.path.join('video', '*'))))
    failed = []
    for directory in directories:
        files = sorted(glob.glob(os.path.join(directory, '*.ts')))
        failed = failed + list(filter(lambda _file: is_ts(_file) is False, files))
    print(failed)


if __name__ == '__main__':
    main()
