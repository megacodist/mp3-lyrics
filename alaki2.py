from json import loads
from pprint import pprint
import subprocess


def main() -> None:
    filename = input('Specify the multimedia file system path: ')
    args = [
        'ffprobe',
        '-hide_banner',
        '-loglevel',
        '0',
        '-print_format',
        'json',
        '-show_format',
        '-show_streams',
        filename]
    popen = subprocess.Popen(
        args=args,
        universal_newlines=True,
        encoding='utf-8',
        bufsize=1,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    jsonData = ''
    while True:
        output = popen.stdout.readline()
        if output:
            jsonData += output
        elif popen.poll() is not None:
            break
    jsonData = loads(
        jsonData,
        parse_float=float,
        parse_int=int)
    pprint(jsonData)


if __name__ == '__main__':
    main()
