import os
import uuid
import hashlib
from traceback import print_exc
from config import platformName

def sysident(prepend = '', append = ''):
    '''
    Returns a system identifier specific to this machine.

    Value may have null bytes.
    '''

    keymat = None

    try:
        if platformName == 'win':
            keymat = _get_key_win()
    except Exception:
        print_exc()

    if keymat is None:
        try:
            keymat = _get_key_default()
        except Exception, e:
            print_exc()
            # jfc, what's goin on here?
            keymat = 'foo'

    return hashlib.sha1(prepend + keymat + append).digest()

def _get_key_win():
    'Gets a system identifier from the registry.'

    import _winreg
    KEY_WOW64_64KEY = 0x0100
    path = r'SOFTWARE\Microsoft\Windows NT\CurrentVersion'

    windows_info = None
    try:
        try:
            windows_info = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, path, 0, _winreg.KEY_READ | KEY_WOW64_64KEY)
        except Exception: #KEY_WOW64_64KEY not allowed on win 2000
            windows_info = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, path, 0, _winreg.KEY_READ)
        dpid = _winreg.QueryValueEx(windows_info, 'DigitalProductId')[0]
        id_  = _winreg.QueryValueEx(windows_info, 'InstallDate')[0]
    finally:
        if windows_info is not None:
            windows_info.Close()

    return ''.join(str(x) for x in (dpid, id_))

def _get_key_default():
    'Uses uuid to get a system identifier.'

    mac_address = uuid.getnode()

    # in accordance with the RFC, the UUID module may return a random
    # number if unable to discover the machine's MAC address. this doesn't
    # make for a very good key.
    if mac_address == uuid.getnode():
        return str(mac_address)
    else:
        # this value is dependent on the computer's hostname. a weak
        import platform
        return os.environ.get('processor_identifier', 'OMG WHERE AM I') + ''.join(platform.uname())

