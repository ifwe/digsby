'''
Add or remove a program from a user's startup sequence.

>>> import startup
>>> startup.enable('c:\\Program Files\\Digsby\\digsby.exe', 'Digsby', 'extra', 'args')

Implemented for Windows and Mac OS X.
'''

import platform, os.path
from logging import getLogger, StreamHandler
log = getLogger('startup')
log.addHandler(StreamHandler())

# Darwin, Windows, ...
_myplatform = platform.platform(terse = True).split('-')[0]

def enable(program_path, nice_name, *args):
    'Causes a program to load on startup.'

    func_name = 'enable_' + _myplatform
    program_name = nice_name or app_name(program_path)

    globals()[func_name](program_path, program_name, *args)
    log.info('%s will launch on startup', program_name)

def disable(program_name):
    'Disable a program loading on startup.'

    func_name = 'disable_' + _myplatform
    globals()[func_name](program_name)

    log.info('%s removed from startup', program_name)

def is_enabled(program_name):
    return globals()['is_enabled_' + _myplatform]()




def app_name(program_path):
    'c:\Program Files\Digsby\digsby.exe -> digsby'

    return os.path.split(program_path)[-1].split('.')[0]

#
# Mac >= 10.4
#

def enable_Darwin(program_path, program_name, *args):
    username, home = os.environ.get('USER'), os.environ.get('HOME')
    folderpath = home + "/Library/LaunchAgents"
    plistpath = home + "/Library/LaunchAgents/%(program_name)s.plist" % locals()

    if not os.path.isdir(folderpath):
        os.mkdir(folderpath)
    if not os.path.isfile(plistpath):
        # On 10.4, startup items are just XML files in the right place.
        contents = \
'''<?xml mersion="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTDPLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>%(program_name)s</string>
        <key>OnDemand</key>
        <true/>
        <key>ProgramArguments</key>
            <array>
                <string>%(program_path)s</string>
''' % locals()
        # Add an entry for each additional arg
        contents += ''.join('<string>%s</string>' % arg for arg in args) + \
'''
            </array>
        <key>RunAtLoad</key>
        <true/>
        <key>ServiceDescription</key>
        <string>This plist launches a the specified program at login.</string>
        <key>UserName</key>
        <string>%(username)s</string>
    </dict>
</plist>
''' % locals()

        f = open(plistpath, 'w')
        f.writelines(contents)
        f.close()
    else:
        log.warning('There is already a startup item')

def disable_Darwin(program_name):
   home = os.environ.get("HOME")
   plistpath = home + "/Library/LaunchAgents/%(program_name)s.plist"

   if os.path.isfile(plistpath):
       os.remove(plistpath)
   else:
       log.warning('There was no plist file to remove!')

def is_enabled_Darwin(program_name):
    home = os.environ.get("HOME")
    path = home + "/Library/LaunchAgents/%s.plist" % program_name
    return os.path.isfile(path)

#
# Windows
#

def _startup_regkey():
    import _winreg

    return _winreg.OpenKeyEx(_winreg.HKEY_CURRENT_USER, #@UndefinedVariable
              "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",0,
              _winreg.KEY_ALL_ACCESS) #@UndefinedVariable


def enable_Windows(program_path, program_name, *args):
    import _winreg

    key = _startup_regkey()
    regval = program_path + ' ' + ' '.join(args)
    _winreg.SetValueEx(key, program_name, 0, _winreg.REG_SZ, regval)
    _winreg.CloseKey(key)

def disable_Windows(program_name):
    '''
        This function will delete the value programname from
        SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run in the registry
    '''
    import _winreg

    key = _startup_regkey()
    try:
        _winreg.DeleteValue(key, program_name)
    except WindowsError:
        log.warning('startup.disable could not delete registry key')
    _winreg.CloseKey(key)

def is_enabled_Windows(program_name):
    import _winreg

    key = _startup_regkey()
    try:
        _winreg.QueryValueEx(key, program_name)
        return True
    except WindowsError:
        return False