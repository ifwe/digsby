from __future__ import with_statement
import re
from gui import skin
from common import pref
from path import path
from util import traceguard, memoize
from traceback import print_exc
from logging import getLogger; log = getLogger('msgstyles')

class MessageStyle(object):
    @property
    def should_always_show_timestamp(self):
        return getattr(self, '_ignore_show_tstamp_flag', False)

    def set_always_show_timestamp(self, val):
        self._ignore_show_tstamp_flag = val

    @property
    def header(self):
        try:
            return ''.join(header.text() for header in get_user_files("Header.html"))
        except Exception:
            print_exc()
            return ''

class MessageStyleException(Exception):
    pass


CONVO_THEME_DIR = 'MessageStyles'


msgStyleTypes = {}

def register_message_style_type(name, constructor):
    global msgStyleTypes

    msgStyleTypes[name] = constructor

def get_user_files(filename):
    import stdpaths
    dirs = []
    for user_themes_dir in (stdpaths.userdata / CONVO_THEME_DIR, stdpaths.config / CONVO_THEME_DIR):
        fname = user_themes_dir / filename
        if fname.isfile():
            dirs.append(fname)

    return dirs

def get_user_themes_dirs():
    import stdpaths
    dirs = []
    for user_themes_dir in (stdpaths.userdata / CONVO_THEME_DIR, stdpaths.config / CONVO_THEME_DIR):
        with traceguard:
            if not user_themes_dir.isdir():
                user_themes_dir.makedirs()
        dirs.append(user_themes_dir)

    return dirs

@memoize
def get_themes():
    p            = skin.resourcedir() / CONVO_THEME_DIR
    themes       = []
    userdirs     = get_user_themes_dirs()

    userthemes = []
    for dir in userdirs:
        userdir = dir.abspath()
        try:
            userthemes.extend(pth.abspath() for pth in (userdir.dirs() if userdir.isdir() else []))
        except Exception, e:
            print_exc()

    systemthemes = p.dirs()
    subdirs      = userthemes + systemthemes

    global msgStyleTypes

    for subdir in subdirs:
        ext = subdir.ext[1:]

        if ext in msgStyleTypes:
            with traceguard:
                themes.append(msgStyleTypes[ext](subdir.abspath()))

    return themes

def get_theme(name, variant = None):
    for theme in get_themes():
        if theme.theme_name == name:
            theme.variant = variant
            return theme

    raise MessageStyleException('theme "%s" not found' % name)

def get_theme_safe(name, variant = None):
    try:
        return get_theme(name, variant)
    except Exception:
        print_exc()

    from basicmsgstyle import BasicMessageStyle
    return BasicMessageStyle()



