from lrc import Lrc, LrcErrors, LyricsItem


if __name__ == '__main__':
    lrc = Lrc(r'H:\mro.lrc')
    print(lrc)
    changed = lrc.changed
    changed = True
    print(lrc.changed)
    lrc['mmm'] = 'Me'
    print(lrc.changed)
    tags = lrc.unknownTags
    tags['111'] = '111'
    tags['222'] = '222'
    print(lrc)
    x = lrc.lyrics
    x.append(LyricsItem('fdgdfiigdhiggdgd'))
    print(lrc)