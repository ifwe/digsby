#__LICENSE_GOES_HERE__

import gui.native
import path
import subprocess

__all__ = ['start']

PROCNAME = u'windows-x86-skypekit.exe'

#HAX: replace with real process management, ports, etc.
def start(protocol = None):
    if PROCNAME not in gui.native.process.process_list():
        # don't show a console window for the skype process.
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        subprocess.Popen(path.path(__file__).dirname() /
                         'res' / PROCNAME, startupinfo=startupinfo)
    return 8963
