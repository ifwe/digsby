'''
Loads emoticons
'''

from __future__ import with_statement
from traceback import print_exc
from util import Storage as S, odict
from util.xml_tag import tag
from util.plistutil import plisttype_to_pytype
from collections import defaultdict
from PIL import Image
from os.path import getmtime
import re
from logging import getLogger; log = getLogger('emoticons')


DEFAULT_PACK = u'MSN Messenger'
def _default_emoticon_pack():
    import common
    return common.pref('appearance.conversations.emoticons.pack', type = unicode, default = DEFAULT_PACK)

class EmoticonPack(object):
    emoticon_loaders = []

    def __repr__(self):
        return '<%s %r from %r>' % (type(self).__name__, self.name, self.path)

    def __init__(self, path):
        self.path = path
        self.name = None
        self.emoticons = None
        self.bitmaps = None

    @classmethod
    def register_loader(cls, loader):
        cls.emoticon_loaders.append(loader)

    @classmethod
    def is_emoticon_dir(cls, path):
        loader = cls.get_loader(path)
        return loader is not None

    @classmethod
    def get_loader(cls, path):
        for loader in cls.emoticon_loaders:
            if loader.is_emoticon_dir(path):
                return loader

        return None

    def load(self):
        raise NotImplementedError

    def post_load(self):
        # build a regex matching every emoticon
        # sort items by length so longer smileys are matched first
        for key in list(self.emoticons.keys()):
            self.emoticons[key.encode('xml')] = self.emoticons[key]
        emotitems = sorted(self.emoticons.items(), key = lambda e: len(e[0]), reverse = True)

        smiley_regex   = '|'.join('(?:%s)' % re.escape(smiley) for (smiley, __emoticon) in emotitems)

        # whitespace before, after, or both

        # Facebook's smiley matcher is this: '(?:^|\\s|\'|"|\\.)(' + regexArr.join('|') + ')(?:\\s|\'|"|\\.|,|!|\\?|$)'
        # I'd imagine the var regexArr is exactly what we have in smiley_regex. seems like a simple translation to me...
        patterns = [r'(?:^|\s)(%s)(?:\s|$)']
                    #r'(?:^|\s+)(%s)',
                    #r'(%s)(?:\s+|$)']

        compiled_patterns = [re.compile(r % smiley_regex, re.MULTILINE) for r in patterns]

        self.patterns = compiled_patterns

@EmoticonPack.register_loader
class DigsbyEmoticonPack(EmoticonPack):
    @classmethod
    def is_emoticon_dir(cls, pth):
        emoticons_txt = pth / 'emoticons.txt'
        return emoticons_txt.isfile()

    def load(self):
        emoticons_txt = self.path / 'emoticons.txt'
        if not emoticons_txt.isfile():
            raise Exception("%r not found", emoticons_txt)

        title = self.path.name
        emoticons = {}
        bitmaps = odict()

        with file(emoticons_txt) as f:
            # the first nonblank line is the title
            for line in f:
                line = line.strip()
                if line:
                    title = line
                    break

            for line in f:
                line = line.strip()
                if not line:
                    continue

                content = line.split()
                image_filename, smileys = content[0], content[1:]

                imgpath = self.path / image_filename
                if imgpath.isfile():
                    for smiley in smileys:
                        emoticons[smiley.encode('xml')] = S(path = imgpath)
                        if not imgpath in bitmaps:
                            bitmaps[imgpath] = [smiley]
                        else:
                            bitmaps[imgpath].append(smiley)

        self.name = title
        self.emoticons = emoticons
        self.bitmaps = bitmaps

        self.post_load()

@EmoticonPack.register_loader
class PidginEmoticonPack(EmoticonPack):
    @classmethod
    def is_emoticon_dir(cls, pth):
        return (pth / 'theme').isfile()

    def load(self):
        theme = self.path / 'theme'
        if not theme.isfile():
            return None, None

        smileys = defaultdict(list)
        emoticons = {}
        bitmaps = odict()
        title = self.path.name

        with file(theme) as f:
            for line in f:
                if line.count('\t') > 0:
                    seq = filter(None, line.strip().split('\t'))
                    if len(seq) >= 2:
                        img, smiley = seq[:2]
                        imgpath = self.path / img
                        if imgpath.isfile():
                            emoticons[smiley.encode('xml')] = S(path = imgpath)

                            if not imgpath in bitmaps:
                                bitmaps[imgpath] = [smiley]
                            else:
                                bitmaps[imgpath].append(smiley)
                elif line.count('='):
                    key, val = line.split('=', 1)
                    if key.lower() == 'name':
                        title = val

        self.name = title
        self.emoticons = emoticons
        self.bitmaps = bitmaps

        self.post_load()

@EmoticonPack.register_loader
class AdiumPlistEmoticonPack(EmoticonPack):
    @classmethod
    def is_emoticon_dir(cls, pth):
        return (pth / 'Emoticons.plist').isfile()

    def load(self):
        emoticons_txt = self.path / 'Emoticons.plist'
        if not emoticons_txt.isfile():
            return None, None

        title = self.path.name
        with file(emoticons_txt) as f:
            plist = tag(f.read())
            toplevel = plist._children[0]
            converted = plisttype_to_pytype(toplevel)
            emoticons = odict()
            bitmaps = odict()

            for img_name, info in sorted(converted['Emoticons'].items()):
                smileys = info['Equivalents']
                imgpath = self.path / img_name
                if imgpath.isfile():
                    for smiley in smileys:
                        if not smiley:
                            continue # for badly formed plists with <string></string>

                        emoticons[smiley] = S(path = imgpath)
                        if not imgpath in bitmaps:
                            bitmaps[imgpath] = [smiley]
                        else:
                            bitmaps[imgpath].append(smiley)

        self.name = title
        self.emoticons = emoticons
        self.bitmaps = bitmaps

        self.post_load()

@EmoticonPack.register_loader
class AdiumFilesysEmoticonPack(EmoticonPack):
    @classmethod
    def is_emoticon_dir(cls, pth):
        return any(x.isdir() for x in pth.glob('*.emoticon'))

    def load(self):

        dirs = [x for x in self.path.glob('*.emoticon') if x.isdir()]
        emoticons = odict()
        bitmaps = odict()
        title = self.path.name
        for dir in dirs:
            imgpath = dir / 'Emoticon.gif'
            if not imgpath.isfile():
                continue

            smileys_path = (dir / 'TextEquivalents.txt')
            if not smileys_path.isfile():
                continue

            smileys = smileys_path.lines()

            for smiley in smileys:
                smiley = smiley.strip()
                if not smiley:
                    continue

                emoticons[smiley] = S(path = imgpath)

                if not imgpath in bitmaps:
                    bitmaps[imgpath] = [smiley]
                else:
                    bitmaps[imgpath].append(smiley)

        self.name = title
        self.emoticons = emoticons
        self.bitmaps = bitmaps

        self.post_load()

def get_emoticon_dirs():
    import stdpaths

    dirs = []
    emotidir = 'emoticons'
    for dir in (stdpaths.userdata, stdpaths.config, resdir()):
        pth = dir / emotidir
        try:
            if not pth.isdir():
                pth.makedirs()

        except Exception:
            print_exc()
        else:
            dirs.append(pth)

    return dirs

def load_emoticons(emoticon_pack = None):
    if emoticon_pack is None:
        emoticon_pack = _default_emoticon_pack()

    log.info('load_emoticons: %s', emoticon_pack)

    emoticons = None
    for emoticon_dir in get_emoticon_dirs():
        emoticon_packdir = emoticon_dir / emoticon_pack
        loader = EmoticonPack.get_loader(emoticon_packdir)
        if loader is not None:
            pack = loader(emoticon_packdir)
            pack.load()
            return pack

    log.info('emoticon pack %r could not be found', emoticon_pack)
    return None

_emoticons = sentinel
_emoticons_pack = sentinel

def first_non_none(seq):
    for i, elem in enumerate(seq):
        if elem is not None:
            return i

    raise AssertionError

def repl(emoticons):
    def _repl(m, e=emoticons):
        (x, y), (i, j) = m.span(), m.span(1)
        s    = m.string
        emot = e[s[i:j]]
        size = imgsize(emot.path)

        emottext = s[i:j].encode('xml')
        replacement = '<img src="%s" width="%d" height="%d" alt="%s" title="%s" />' % \
                      (emot.path.url(), size[0], size[1], emottext, emottext)

        return ''.join([s[x:i], replacement, s[j:y]])

    return _repl

def load_pack(emoticon_pack):
    if emoticon_pack is None:
        emoticon_pack = _default_emoticon_pack()

    if not isinstance(emoticon_pack, basestring):
        raise TypeError('emoticon_pack must be a string')

    global _emoticons, _emoticons_pack
    if _emoticons is sentinel or emoticon_pack != _emoticons_pack:
        _emoticons = load_emoticons(emoticon_pack)
        _emoticons_pack = emoticon_pack

    return _emoticons

def apply_emoticons(s, emoticon_pack = None):
    load_pack(emoticon_pack)

    if _emoticons is None:
        return s

    for p in _emoticons.patterns:
        s = p.sub(repl(_emoticons.emoticons), s)
        s = p.sub(repl(_emoticons.emoticons), s)

    return s

def get_emoticon_bitmaps(emoticon_pack = None):
    if emoticon_pack is None:
        emoticon_pack = _default_emoticon_pack()
    load_pack(emoticon_pack)
    return list(_emoticons.bitmaps.items())

def findsets():
    '''Returns path objects to all emoticon sets.'''

    sets = []
    for d in get_emoticon_dirs():
        for subdir in d.dirs():
            if EmoticonPack.is_emoticon_dir(subdir):
                pack = EmoticonPack.get_loader(subdir)(subdir)
                pack.load()
                sets.append(pack)
                log.info('discovered emoticon directory: %r', subdir)

    log.info('all found emoticon sets: %r', sets)
    return sets

def imgsize(p, _cache = {}):
    key = (p, getmtime(p))

    try:
        return _cache[key]
    except KeyError:
        size = Image.open(p).size
        return _cache.setdefault(key, size)

if __name__ == '__main__':
    from path import path
    def resdir(): return path('../../../res')
else:
    def resdir():
        from gui import skin
        return skin.resourcedir()

if __name__ == '__main__':
    print load_emoticons_pidgin(path('../../../res/emoticons/sa'))
    #global _emoticons
    #from pprint import pprint
    #print apply_emoticons('&gt;(')
    #pprint(_emoticons)

    #s='<html><body><a href="test">one <b>two</b> three</a></body></html>'
    #from util import soupify

    #soup = soupify(s)
    #print soup.find(text = None)

