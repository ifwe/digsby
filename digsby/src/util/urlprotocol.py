'''
URL protocol handling.

MyProtocol = {
    name = 'DigsbyPlugin'
    protocol = 'digsbyplugin'    # digsbyplugin://path/to/plugin
    icon = 'c:\\someicon.ico'
    command = 'c:\\Program Files\\Digsby\\Digsby.exe'
}

>> import urlprotocol
>> urlprotocol.register(MyProtocol)
>> assert urlprotocol.isRegistered(MyProtocol)
>> urlprotocol.unregister(MyProtocol)
'''

__all__ = 'isRegistered register unregister'.split()

import platform
from traceback import print_exc
from warnings import warn
platform = platform.system().lower()
platform = {'microsoft': 'windows',
            '4nt': 'windows',
            'darwin': 'darwin',
            'linux': 'linux',
            }.get(platform, 'windows')

def attrget(obj, attr):
    try: return obj[attr]
    except TypeError: return obj.name

def platform_call(name, *a, **k):
    funcname = name + '_' + platform

    try:
        func = globals()[funcname]
    except KeyError:
        warn('platform %s not implemented (%s)' % (platform, funcname))
    else:
        return func(*a, **k)

def isRegistered(urlprotocol, system = True):
    '''
    Returns if the URL protocol handler specified in urlprotocol is currently
    registered.
    '''

    return platform_call('isDefault', urlprotocol, system = system)

def get(protocol_name, system = True):
    return platform_call('get', protocol_name, system = system)

def register(urlprotocol, system = True):

    return platform_call('register', urlprotocol, system = system)

def unregister(protocol_or_name, system = True):
    name = protocol_or_name if isinstance(protocol_or_name, basestring) \
        else getattr(protocol_or_name, 'name', protocol_or_name['name'])

    return platform_call('unregister', name, system = system)

##
## Windows
##

def _init_windows():
    global reg
    import _winreg as reg

def get_windows(protocol_name, system = True):
    from auxencodings import fuzzydecode

    key = reg.OpenKey(basekey(system), '%s\\shell\\open\\command' % protocol_name)
    val = reg.EnumValue(key, 0)[1]

    # if what comes back is not already unicode, we have to guess :(
    if isinstance(val, str):
        val = fuzzydecode(reg.EnumValue(key, 0)[1], 'utf-16-be')

    return val

def urlkey(protocolname, system = False, write = False):
    try:
        if system:
            return reg.OpenKey(reg.HKEY_CLASSES_ROOT, '%s' % protocolname,
                               0, reg.KEY_ALL_ACCESS if write else reg.KEY_READ)
        else:
            return reg.OpenKey(reg.HKEY_CURRENT_USER, 'Software\\Classes\\%s' % protocolname,
                               0, reg.KEY_ALL_ACCESS if write else reg.KEY_READ)
    except reg.error:
        return None

def basekey(system = False):
    if system:
        return reg.OpenKey(reg.HKEY_CLASSES_ROOT, '')
    else:
        return reg.OpenKey(reg.HKEY_CURRENT_USER, 'Software\\Classes')

def keyToObj((obj, objtype)):
    if objtype in (reg.REG_NONE):
        return None
    elif objtype in (reg.REG_SZ, reg.REG_EXPAND_SZ, reg.REG_RESOURCE_LIST, reg.REG_LINK, reg.REG_BINARY, reg.REG_DWORD, reg.REG_DWORD_LITTLE_ENDIAN, reg.REG_DWORD_BIG_ENDIAN, reg.REG_MULTI_SZ):
        return obj
    raise NotImplementedError, "Registry type 0x%08X not supported" % (objtype,)

def register_microsoft(urlprotocol, system = True):
    protocol = attrget(urlprotocol, 'protocol')
    key = urlkey(protocol, system)

    if not key:
        reg.CreateKey(basekey(system), 'Software\\Classes\\%s' % protocol)



def isRegistered_microsoft(urlprotocol, system = True):
    name = attrget(urlprotocol, 'protocol')
    key = urlkey(name, system)

    # If there's no key at all, return False.
    if not key:
        return False


##
## Mac
##

## TODO: Determine best way to load default mail program from URL
def _init_darwin():
    pass

def _init_linux():
    pass

    #print keyToObj(reg.QueryValueEx(key, ''))


try:
    platform_call('_init')
except Exception:
    print_exc()

if __name__ == '__main__':
    print get('mailto')
