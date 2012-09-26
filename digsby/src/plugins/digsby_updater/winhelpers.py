import os
import sys
import shutil
import locale

import wx
import util
import stdpaths
import path

from ctypes import windll

import logging
log = logging.getLogger('AutoUpdate')

def platform_cleanup():
    return _remove_virtual_store()

def get_exe_name():
    # XXX: this is horrible, can't we have this in a nice clean attribute somewhere?
    return util.program_dir().relpathto(path.path(sys._real_exe.decode(locale.getpreferredencoding())))

def _remove_virtual_store():
    '''
    Since Vista, the operating system has provided a mechanism to allow apps to seamlessly write to "program files",
    even if UAC is on. However, the actual on-disk location is not in %PROGRAMFILES%. It's something called the "virtual
    store", and if a file exists in the virtual store, we can read it even if we're actually trying to read from program
    files. This can cause issues when updating if modules have been removed but still exist in the virtual store.

    This function returns a list of all files in the app's virtual store for the purposes of having the updater process
    delete them.
    '''
    if not os.name == 'nt':
        return []

    import gui.native.win.winutil as winutil
    if not winutil.is_vista():
        return []

    # remove c:\Users\%USER%\AppData\Local\VirtualStore\Program Files\Digsby
    # if it exists

    to_remove = []
    # TODO: remove app name here, get it from the app object or something
    for virtual_store in ((stdpaths.userlocaldata / 'VirtualStore' / 'Program Files' / 'Digsby'),
                          (stdpaths.userlocaldata / 'VirtualStore' / 'Program Files (x86)' / 'Digsby')):

        with util.traceguard:
            if virtual_store.isdir():
                to_remove.extend(virtual_store.walkfiles())

    return to_remove

def get_top_level_hwnd():
    '''
    When calling ShellExecute, we need a window handle to associate the new process with. Here, we attempt to find it
    by getting the first TopLevelWindow (should be the buddy list). In the event that the buddy list is not shown,
    we assume that the login window is still around somewhere, so we'll use that for the window handle.
    '''
    splash = wx.FindWindowByName('Digsby Login Window')

    if splash is None:
        topwins = wx.GetTopLevelWindows()
        if isinstance(topwins, list) and topwins:
            topwins = topwins[0]

        splash = topwins if topwins else None

    if splash is not None:
        return splash.Handle

def restart_and_update(tempdir):
    '''
    Registers _launch_updater as an atexit function, attempts to get the app to quit, and in the event the interpreter
    is still running in 7 seconds, calls _launch_updater anyway.

    Special care is also taken to make sure we're not still in the OnInit handler of the wxApp.
    '''
    import atexit
    atexit.register(_launch_updater, tempdir)
    force_restart_timer = util.Timer(7, _launch_updater, tempdir)
    app = wx.GetApp()
    # Don't call DigsbyCleanupAndQuit if we're not yet out of OnInit - the startup sequence will do it for us.
    if app.IsMainLoopRunning() and app.DigsbyCleanupAndQuit():
        force_restart_timer.start()

def _launch_updater(tempdir):
    '''
    Runs a small executable

    digsby_updater.exe supersecret SRC EXEC

    which will
    - copy digsby_updater.exe to a temp directory, since the file itself may need to be updated
    - attempt to kill any instances of digsby that are found
    - copy the contents of directory SRC into the current directory
    - remove the SRC directory
    - start the program named by EXEC and exit

    The updater needs to do this since DLLs are locked during program execution
    and can't be updated.
    '''
    ShellExecute = windll.shell32.ShellExecuteW

    POST_UPDATE_EXE = 'Digsby Updater.exe'
    UPDATE_EXE = 'Digsby PreUpdater.exe'

    tempdir = path.path(tempdir)

    # grab the path to the currently running executable
    exc = get_exe_name()

    for EXE in (POST_UPDATE_EXE, UPDATE_EXE): # Order matters - the last one needs to be "Digsby Update.exe" so that it is run at the end

        if sys.DEV:
            # if running the dev version, Python.exe is probably somewhere else
            # than the Digsby directory.
            updater = path.path('ext') / 'msw' / EXE
        else:
            # in the release build its at Digsby/lib/digsby_updater.exe
            updater = path.path(sys.executable.decode(locale.getpreferredencoding())).parent / 'lib' / EXE

        if not updater.isfile():
            raise AssertionError('could not find %s' % updater)

        # copy the executable to the temp directory, in case it needs to update itself
        updater.copy2(tempdir.parent)
        updater = tempdir.parent / updater.name

        if not updater.isfile():
            raise AssertionError('could not copy %s to %s' % updater.name, tempdir.parent)

        log.info('updater path is %r', updater)

    # invoke it
    hwnd = get_top_level_hwnd()

    log.info('top level window HWND is %s', hwnd)

    SW_SHOWNORMAL = 1
    SE_ERR_ACCESSDENIED = 5

    params = u'supersecret "%s" "%s"' % (tempdir.parent, exc)
    log.info('%s %s', updater, params)

    # we have to use ShellExecute instead of Popen, since we need to pass a HWND to get
    # vista's UAC to come to the foreground
    # see http://msdn2.microsoft.com/en-us/library/bb762153.aspx
    res = ShellExecute(hwnd, None, updater, params, None, SW_SHOWNORMAL)

    if res > 32:
        log.info('ShellExecute successful: %s', res)
        return

    if res == SE_ERR_ACCESSDENIED:
        log.info('access denied')
        # vista UAC: user clicked "cancel"?
    else:
        log.info('ShellExecute error: %s', res)

    # If we got to this point, the updater EXEs failed to run and we need to
    # clear the pending update so the program will start again next time.
    import updater
    updater._delete_updater_files()
