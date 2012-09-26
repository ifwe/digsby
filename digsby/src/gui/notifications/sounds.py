from __future__ import with_statement
from gui import skin
import syck

class SoundsetException(Exception): pass

class Soundset(dict):
    pass

DESC_FILENAME = 'sounds.yaml'

from gui.notifications import underscores_to_dots

def fix_paths(d, soundset_dir):
    for k, v in d.iteritems():
        d[k] = (soundset_dir / v).abspath()

_soundset = None

def active_soundset():
    global _soundset

    if _soundset is not None:
        return _soundset

    _soundset = load_soundset('default')
    return _soundset

def load_soundset(name):
    set_name = set_dir = None

    for set_name, set_dir in list_soundsets():
        if set_name == name:
            found = True
            break
    else:
        found = False

    if set_dir and found:
        soundset_yaml = set_dir / DESC_FILENAME
    else:
        soundset_yaml = None

    if soundset_yaml is None or not soundset_yaml.isfile():
        raise SoundsetException('soundset %r is missing %r' % (name, DESC_FILENAME))

    # load from YAML file in res dir
    with file(soundset_yaml, 'r') as f:
        soundset = syck.load(f)

    if soundset is None:
        raise SoundsetException('soundset %r is empty' % name)

    # fix contact_signoff -> contact.signoff
    underscores_to_dots(soundset)

    # turn relative paths in YAML to actual paths
    fix_paths(soundset, set_dir)

    return Soundset(soundset)

def list_soundsets():
    import stdpaths
    paths = [
             stdpaths.userdata / 'sounds',
             stdpaths.config / 'sounds',
             skin.resourcedir() / 'sounds',
             ]

    soundsets = []
    for pth in paths:
        for dir in pth.dirs():
            if (dir / DESC_FILENAME).isfile():
                soundsets.append((dir.name, dir))

    return soundsets
