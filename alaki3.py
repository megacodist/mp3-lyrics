"""Swapping artists for albums in ID3 tags of MP3 files in a directory.
"""
from pathlib import Path

from mutagen.id3 import ID3, TALB, TPE1

def main() -> None:
    folder = input("Enter the folder: ")
    # Listing all MP3 files in the folder...
    mp3s = Path(folder).glob('*.mp3')
    for file in mp3s:
        id3 = ID3(file)
        # Retrieving albums...
        try:
            albums: list[str] = list(id3['TALB'])
        except KeyError:
            albums = []
        # Retrieving artists...
        try:
            artists: list[str] = list(id3['TPE1'])
        except KeyError:
            artists = []
        # Setting new artists...
        id3.delall('TPE1')
        if albums:
            id3.add(TPE1(encoding=3, text=albums))
        # Setting new albums...
        id3.delall('TALB')
        if artists:
            id3.add(TALB(encoding=3, text=artists))

        id3.update_to_v24()
        id3.save()

if __name__ == '__main__':
    main()