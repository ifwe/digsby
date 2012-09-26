from __future__ import with_statement
import os.path, sys
import util
from util import dictadd, is_all
from util.observe import observable_dict

import syck
from logging import getLogger; log = getLogger('PrefsData')
info = log.info; warning = log.warning

def flatten(mapping, parent_name=""):
    """
    Flattens a mapping tree so that all leaf nodes appears as tuples in a list
    containing a path and a value, like:

    >>> flatten({'a': 5, 'b': {'c': 6, 'd': 7}})
    [('a', 5), ('b.c', 6), ('b.d', 7)]
    """

    if not mapping: return []

    result_list = []
    for key, value in mapping.iteritems():
        path = parent_name + key
#        print path

        if isinstance(value, dict) or hasattr(key, 'iteritems'):
            result_list.extend( flatten(value, path + '.') )
        else:
            result_list.append( (path, value) )

    return result_list

def inflate(mappings_list, root=None, dict_factory=dict):
    """
    Expands a list of tuples containing paths and values into a mapping tree.

    >>> inflate([('some.long.path.name','value')])
    {'some': {'long': {'path': {'name': 'value'}}}}
    """
    root_map = root or dict_factory()

    for path, value in mappings_list:
        path = path.split('.')

        # traverse the dotted path, creating new dictionaries as needed
        parent = root_map
        for name in path:
            #if path.index(name) == len(path) - 1:
            if path[-1] == name:
                # this is the last name in the path - set the value!
                parent[name] = value
            else:
                # this is not a leaf, so create an empty dictionary if there
                # isn't one there already
                parent.setdefault(name, dict_factory())
            parent = parent[name]

    return root_map

nice_type_names = {
    unicode: 'unicode',
    str:  "str",
    bool: "boolean",
    int:  "integer",
    list: "list",
    float: "float",
    dict: 'dict',
    type(None):'none',
}

from util import dictreverse
nice_name_types = dictreverse(nice_type_names)

__localprefs = None

class localprefprop(object):
    '''
    Property stored as a local pref.

    "key" can be a string key or a callable with one argument--the object
    the property is being called on--that returns a string key used for lookup
    and storage in the local prefs dictionary.
    '''
    def __init__(self, key, default):
        if isinstance(key, basestring):
            key = lambda s: key

        assert callable(key)
        self.key     = key
        self.default = default

    def __get__(self, obj, objtype=None):
        try:
            return localprefs()[self.key(obj)]
        except KeyError:
            return self.default

    def __set__(self, obj, val):
        localprefs()[self.key(obj)] = val

def defaultprefs():
    '''
    Returns the default prefs as a Storage object
    '''
    import prefs
    import stdpaths
    import config

    the_prefs = util.Storage()

    resdir = os.path.join(util.program_dir(), 'res')
    filenames = [
                 os.path.join(resdir, 'defaults.yaml'),
                 os.path.join(resdir, config.platformName, 'defaults.yaml'),
                 stdpaths.config / 'prefs.yaml',
                 stdpaths.userdata / 'prefs.yaml',
                 ]

    for filename in filenames:
        info('loading prefs from %r', filename)

        try:
            with open(filename, 'rb') as f:
                prefdict = syck.load(f)
        except Exception, e:
            log.info('Error loading prefs from %r: %r', filename, e)
            continue

        if not isinstance(prefdict, dict):
            continue

        if not sys.DEV:
            prefdict.pop('debug', None)

        prefdict = prefs.flatten(prefdict)
        the_prefs.update(prefdict)

    return the_prefs

def localprefs():
    # Returns a dictionary of local prefs for the CURRENT ACTIVE profile. If you still have a reference
    # to the return value of this function when the CURRENT ACTIVE profile changes you may mess things up.

    global __localprefs

    import common
    if __localprefs is not None and __localprefs.name == common.profile.name:
        return __localprefs

    from gui.toolbox import local_settings
    from util.observe import ObservableDict as SavingDictBase
    ls = local_settings()

    _section = lambda: 'localprefs %s' % common.profile.name

    section = _section()
    if not ls.has_section(section):
        ls.add_section(section)

    class SavingDict(SavingDictBase):
        import localdefaults
        name = common.profile.name

        def __init__(self, save_func, *a, **k):
            self.save = save_func
            SavingDictBase.__init__(self, *a, **k)

        def __setitem__(self, key, val):
            set_func = getattr(self.localdefaults, 'set_%s' % key.replace('.', '_'), None)
            if set_func is not None:
                log.info('calling localpref setter function: %r', set_func)
                val = set_func(val)

            SavingDictBase.__setitem__(self, key, val)
            self.save(self)

        def __delitem__(self, key):
            SavingDictBase.__delitem__(self, key)
            self.save(self)

        def __getitem__(self, key):
            try:
                return SavingDictBase.__getitem__(self, key)
            except KeyError, e:
                try:
                    v = getattr(self.localdefaults, key.replace('.', '_'))
                except AttributeError:
                    try:
                        get_func = getattr(self.localdefaults, 'get_%s' % key.replace('.', '_'))
#                        log.info('calling localpref getter function: %r', get_func)
                        v = get_func()
                    except AttributeError:
                        raise e

                return v() if callable(v) else v

    def save(d):
        defaults = type(d)(save)
        d = d.copy()
        for k in d.keys():
            try:
                if d[k] == defaults[k]:
                    d.pop(k)
            except (KeyError, AttributeError) as _e:
                pass
        ls._sections[_section()] = d
        ls.save()

    __localprefs = SavingDict(save, ls.iteritems(section))

    return __localprefs
