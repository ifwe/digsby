'''

Manages a tree of skin objects used for drawing GUI elements

'''

from __future__ import with_statement

# options for skin loading

SKIN_FILENAME    = 'skin.yaml'    # base skin files must be named this
VARIANT_DIR      = 'Variants'     # variant skin files must appear in a subdirectory named this
SKIN_NAME_KEY    = 'name'         # skins can name themselves with this key
VARIANT_NAME_KEY = 'variant'      # variants can name themselves with this key

# skin elements at these keys will use the "alternating list" method
# instead of stacking skin elements

alternating_keys = ['buddiespanel.backgrounds.buddy',
                    'filetransfers.backgrounds.normal']

# factor to multiply font sizes by -- strings are "createdon_runningon"
# and are specified by FONT_MULTIPLY_KEY
FONT_MULTIPLY_KEY = 'FontPlatform'
FONT_MULTIPLY = {'windows_mac': 4.0/3.0,
                 'mac_windows': 3.0/4.0}



__metaclass__ = type
from operator import isMappingType
from util.primitives import Storage, traceguard, dictrecurse
S = Storage
from path import path
from copy import deepcopy
#import config
#import hooks
import syck
import sys, os, wx
from wx import GetTopLevelWindows, GetApp, MessageBox

from traceback import print_exc
from gui.toolbox import colorfor
from types import FunctionType
from util.merge import merge, merge_keys, tolower
from util.primitives import syck_error_message
from util.introspect import funcinfo

from gui.skin.skintransform import transform
from gui.skin import SkinException
from peak.util.plugins import Hook

from logging import getLogger; log = getLogger('skin'); info = log.info

import stdpaths


activeTree = None

# the only state
resource_paths = [path('res').abspath(),
                  path('res/skins/default').abspath()]

try:
    userdata = stdpaths.userdata
except AttributeError:
    log.warning('not including stdpaths.userdata in skin lookup paths')
else:
    resource_paths.append(userdata / 'skins')
    del userdata

def get(dottedpath, default = sentinel):
    global activeTree

    try:
        return lookup(activeTree, dottedpath.lower().split('.'))
    except (KeyError, TypeError):
        if default is sentinel:
            raise SkinException('not found: ' + dottedpath)
        else:
            return default
    except:
        print_exc()
        print >> sys.stderr, 'exception for "%s"' % dottedpath

def refresh_wx_tree():
    '''
    Calls "UpdateSkin" on every GUI control that has it, descending from top
    level windows down through their children.
    '''

    # UMenus aren't necessarily wx Children accessible
    # through the widget tree--skip them on the tree descent
    from gui.uberwidgets.umenu import UMenu
    skip = (UMenu, )

    for window in GetTopLevelWindows():
        with window.FrozenQuick():
            _updateskin(window, skip)

    # now update menus
    UMenu.CallAll(UMenu.UpdateSkin)


def _updateskin(window, skip):
    '''
    Calls window.UpdateSkin() unless isinstance(window, skip), and then
    does the same thing recursively on window's children.
    '''

    try:
        # don't incur the hasattr() cost for every GUI element.
        update = window.UpdateSkin
    except AttributeError:
        pass
    else:
        if not isinstance(window, skip):
            try: update()
            except: print_exc()

    for c in window.Children:
        _updateskin(c, skip)

def alternating(tree):
    'Makes some skin elements "alternating" lists.'

    from gui.skin.skinobjects import SkinList

    for k in alternating_keys:
        spath = k.split('.')
        try:
            val = lookup(tree, spath)
        except AttributeError:
            pass
        else:
            if isinstance(val, list):
                lookup(tree, spath[:-1])[spath[-1]] = SkinList(val)

def fontplatform(finaltree):
    from gui import skin
    from config import platformName

    platform_aliases = {'win': 'windows',
                        'mac': 'mac'}

    fontplatform = finaltree.get(FONT_MULTIPLY_KEY.lower(), None)

    fp = '%s_%s' % (fontplatform, platform_aliases.get(platformName))

    factor = FONT_MULTIPLY.get(fp, 1)
    log.info('new font multiply factor: %s -> %s', fp, factor)
    skin.font_multiply_factor = factor

pretransforms  = [fontplatform]
posttransforms = [alternating]

_loaded_fonts = set()

def skin_font_files(paths):
    fonts = []
    for p in paths:
        fontsdir = p.parent / 'fonts'
        if fontsdir.isdir():
            for ext in ('ttf', 'fon'):
                fonts.extend(fontsdir.files('*.' + ext))

    return [f.abspath().normpath() for f in fonts]

def load_skinfonts(paths):
    import config
    if not config.platform == 'win':
        return

    from gui.native.win.winfonts import loadfont, unloadfont

    fonts = set(skin_font_files(paths))

    global _loaded_fonts

    if _loaded_fonts == fonts:
        return

    # unload old
    for fontfile in _loaded_fonts - fonts:
        with traceguard:
            res = unloadfont(fontfile, enumerable=True)
            log.debug('unloaded font %r: %r', fontfile, res)

    # load new
    for fontfile in fonts - _loaded_fonts:
        with traceguard:
            res = loadfont(fontfile, enumerable=True)
            log.debug('loading font %r: %r', fontfile, res)

    _loaded_fonts = fonts

    import wx.webview
    if hasattr(wx.webview.WebView, 'InvalidateFontCache'):
        log.debug('invalidating webkit font cache')
        wx.webview.WebView.InvalidateFontCache()

def set_active(skin, variant = None, update_gui = False, callback = None):
    'Changes the active skin.'
    log.info('set_active(%r, %r)', skin, variant)
    app  = GetApp()
    global activeTree

    # Search all resource_paths for skin
    skinname = skin
    for rp in resource_paths:
        skin = path(rp) / 'skins' / skinname
        skinpath = skin / SKIN_FILENAME
        if skinpath.isfile():
            break
    import hooks
    hooks.notify('skin.set.pre', skin, variant)

    # Find the variant file, if specified.
    if variant is not None:
        variant = skin / VARIANT_DIR / variant + '.yaml'

    default_path = resource_paths[0] / 'skins' / 'default' / SKIN_FILENAME

    paths = [default_path]
    insert_position = 1

    if os.path.basename(skin) == 'native':
        paths.append(resource_paths[0] / path('skins') / 'silverblue' / SKIN_FILENAME)

    if not skinpath.isfile():
        log.critical('cannot find %r (%r.isfile() == False, defaulting to silverblue', skin, skinpath)
        skin = resource_paths[0] / path('skins') / 'silverblue'
        skinpath = skin / SKIN_FILENAME
        variant = None

    if default_path.abspath() != skinpath.abspath():
        paths.append(skinpath)
    if variant is not None:
        if variant.isfile():
            paths.append(variant)
        else:
            log.warning('cannot find variant %r for skin %r', variant, skin)

    if not update_gui and hasattr(app, 'skin') and \
        app.skin.paths == paths:
        log.info('skin did not change, returning')

    with traceguard:
        load_skinfonts(paths)

    # load YAML from disk
    log.info('loading YAML from %d path(s):\n  %r', len(paths), '\n  '.join(paths))

    trees = get_skintrees(skin, paths, insert_position)

    # Ignore AppDefaults in all skins except default
    for tree in trees[1:]:
        tree.pop('appdefaults', None)

    # copy the default tree in case there is an exception later
    default_tree = deepcopy(trees[0])

    # merge keys from different trees into one (case insensitive)
    combined_tree = merge(*trees, **dict(keytransform = lambda k: getattr(k, 'lower', lambda k: k)()))

    # create a skin storage object (transformation below depends on this being
    # in the app)
    if not hasattr(app, 'skin'):
        app.skin = S()

    app.skin.update(path  = skinpath.parent, paths = get_image_load_paths(paths))

    for pretransform in pretransforms:
        pretransform(combined_tree)

    # do skin transformation, creating images, brushes, etc.
    try:
        finaltree = transform(combined_tree)
    except Exception, e:
        MessageBox('There was an error processing skin "%s":\n\n%s' % (skin, str(e)),
                   'Skin Error')

        # on an exception try loading the default tree
        print_exc()
        finaltree = transform(default_tree)

    for posttransform in posttransforms:
        posttransform(finaltree)

    # actually place the new skintree
    activeTree = finaltree
    app.skin.update(tree = finaltree)

    def done():
        # refresh the GUI if requested
        if update_gui:
            refresh_wx_tree()

        if callback is not None:
            with traceguard:
                callback()

        # HACK: collect garbage after a skin change
        import gc
        gc.collect()

    wx.CallAfter(done)
    return app.skin

def list_skins():
    'Returns paths to all available skin.yaml files.'

    resource_paths = sys.modules['gui.skin.skintree'].resource_paths
    skins = []

    for res in resource_paths:
        skinrootdir = res / 'skins'

        if skinrootdir.isdir():
            for skindir in skinrootdir.dirs():
                if skindir.name.startswith('.'): continue

                rootfile = skindir / SKIN_FILENAME

                if rootfile.isfile() and skindir.name != 'default':
                    skins.append(skindesc(rootfile))

    return skins

def get_skintrees(skin, paths, insert_position):
    '''
    Returns the separate mappings to be merged into one final skin later.

    paths is a list of skin YAML files.
    '''
    trees = []
    errors = []
    successful = False
    for f in paths:
        try:
            trees.append(load_skinfile(f))
        except Exception, e:
            errors.append(e)
            del e
        else:
            successful = True

    if not successful:
        MessageBox('There was an error loading skin "%s":\n\n%s' % (skin, '\n'.join(str(e) for e in errors)),
                   'Skin Error')

    # trees can also be supplied via Hook
    from gui.skin import SkinStorage
    to_skinstorage = dictrecurse(SkinStorage)

    for hook in Hook('digsby.skin.load.trees'):
        hook_trees = hook()

        if hook_trees is not None:
            # transform all mappings provided by plugins into SkinStorage
            # objects
            # TODO: why is dictrecurse not a deepcopy?
            trees[insert_position:insert_position] = (to_skinstorage(deepcopy(t)) for t in hook_trees)

    return trees


def get_image_load_paths(paths):
    'Returns a list of paths from which skin images can be loaded.'

    image_load_paths = [p.parent for p in paths]

    for pathhook in Hook('digsby.skin.load.skinpaths'):
        hook_paths = pathhook()
        if hook_paths is not None:
            image_load_paths.extend(hook_paths)

    return image_load_paths

def quick_name_lookup(p, **names):
    '''
    Given a path object to a skin YAML file, and "name keys", returns the values of those keys.

    The names must be on the highest level of key-value pairs.

    Returns a mapping of {names: values}
    '''

    #TODO: do we even need to parse the file here?

    names = dict((name.lower(), key) for key, name in names.iteritems())
    vals = {}

    with p.open('r') as f:
        s = syck.load(f)
        for k, name in getattr(s, 'iteritems', lambda: s)():
            try:
                k = k.lower()
            except AttributeError:
                pass
            else:
                if k in names and isinstance(name, basestring):
                    vals[k] = name
                    if len(vals) == len(names):
                        break
    return vals

def skindesc(rootfile):
    'Returns a Storage for each skin found.'

    rootfile = path(rootfile)
    aliases  = quick_name_lookup(rootfile, skin_alias = SKIN_NAME_KEY, novariant_alias = VARIANT_NAME_KEY)
    variants = []

    # search the skin directory
    vardir = rootfile.parent / VARIANT_DIR
    if vardir.isdir():
        for variant in vardir.files('*.yaml'):  # res/skins/myskin/variant3.yaml
            if variant != rootfile:
                valias = quick_name_lookup(variant, variant_alias = VARIANT_NAME_KEY).get('variant_alias', variant.namebase)
                assert isinstance(valias, basestring)
                variants.append(S(path = variant,
                                  alias = valias))

    return S(name     = rootfile.parent.name,
             alias    = aliases.get(SKIN_NAME_KEY, rootfile.parent.name),
             novariant_alias = aliases.get(VARIANT_NAME_KEY, _('(none)')),
             base     = rootfile,
             variants = variants)


def lookup(root, pathseq):
    'Search a dictionary using a dotted path.'

    elem = root
    for p in pathseq:
        elem = elem[p]

    return elem


def load_skinfile(filepath):
    if not filepath.isfile():
        raise ValueError('file %s does not exist' % filepath)

    return globals()['load_%s' % filepath.ext[1:]](filepath)

def load_yaml(str_or_path):
    from gui.skin import SkinStorage

    bytes, fpath = getcontent(str_or_path)
    if isinstance(bytes, unicode):
        bytes = bytes.encode('utf-8')

    if not bytes:
        raise SkinException('no bytes in ' + str_or_path)

    content = load_yaml_content(bytes)

    try:
        root = syck.load(content)
    except syck.error, e:
        raise SkinException(syck_error_message(e, fpath))

    return merge_keys(root, maptype=SkinStorage)

def load_yaml_content(bytes, included_paths = None):
    if included_paths is None:
        included_paths = []

    # process includes
    lines = []
    for line in bytes.split('\n'):
        if line.lower().startswith('include:'):
            include_path = line[line.index(':') + 1:].strip()
            line = load_yaml_include(include_path, included_paths)

        lines.append(line)

    return '\n'.join(lines)

def load_yaml_include(incpath, included_paths):
    '''
    Returns bytes for an include.

    incpath         include path to another YAML file

    included_paths  a sequence of all already included (absolute) paths that
                    will be added to by this function
    '''

    incpath = path(incpath).abspath()

    if not incpath in included_paths:
        bytes = load_yaml_content(incpath.bytes(), included_paths)
        included_paths += [incpath]
        return bytes
    else:
        # including a file twice is a no-op
        return ''

from util.data_importer import zipopen
from contextlib import closing
def getcontent(str_or_path):
    try:
        if str_or_path.isfile():
            return str_or_path.bytes(), str_or_path
        with closing(zipopen(str_or_path)) as f:
            return f.read(), str_or_path
    except AttributeError:
        return str_or_path, '<String Input>'


if __name__ == '__main__':
    s = '''common:
- &mycolor red

menu:
  color: *mycolor

common:
- &mycolor blue'''

    print load_yaml(s)


if __name__ == '_AFDASF':

    import wx
    a = wx.PySimpleApp()

    sys.modules['gui.skin.skintree'].resource_paths = [path('../../../res')]
    skins = list_skins()

    if not skins: sys.exit()

    set_active(skins[1])

    with file('test.yaml', 'w') as f:
        f.write('''\
button:
    color: red''')

    s = '''
include: test.yaml
include: test.yaml

Button:
    font: Arial

button:
    Font: Comic Sans MS
'''

    #assert load_yaml(s) == {'button': {'font': 'Comic Sans MS'}}
