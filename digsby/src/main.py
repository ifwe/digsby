'''

The Digsby wxApp, and startup and shutdown functionality.

'''
from __future__ import with_statement

import sys

import wx
import os.path, logging, platform
import traceback
from time import time
from path import path
from traceback import print_exc
from threading import currentThread

from config import platformName, newMenubar

from logging import getLogger
import hooks
log = getLogger(); info = log.info

import digsbysite

IDLE_CHECK_MS     = 2000
IDLE_CHECK_MOUSE_DISTANCE = 10

# on release builds, the name of the log file. see "get_logdir" for its location
LOG_FILENAME = 'digsby.log.csv'

LOG_SPEED_LIMIT = .4 * 1024 * 1024 # bytes/sec
LOG_SPEED_WINDOW = 10 # seconds

# hanging thread exit checker
USE_HANGING_THREAD_DAEMON = True
EXIT_TIMEOUT_SECS = 30

# only use single instance mode in release builds, or if
# --single is specified on the command line. additionally,
# --multi in a release build allows multiple instances to run
USE_SINGLE_INSTANCE = (not getattr(sys, 'DEV', False)) and '--multi' not in sys.argv or '--single' in sys.argv

APP_NAME = u'Digsby'

def init_threadpool():
    if getattr(wx, 'WXPY', False):
        from util.threads.bgthread import add_before_cb, add_after_cb
        add_before_cb(wx.SipNewThread)
        add_after_cb(wx.SipEndThread)

    from util.threads.threadpool import ThreadPool
    ThreadPool(5)

if USE_SINGLE_INSTANCE:
    from singleinstance import SingleInstanceApp
    DigsbyAppBase = SingleInstanceApp
else:
    DigsbyAppBase = wx.App

from gui.app.mainMenuEvents import MainMenuEventHandler

class DigsbyApp(DigsbyAppBase, MainMenuEventHandler):
    'The main Digsby wxApp.'

    def OnFatalException(self):
        '''
        Called when a fatal exception (divide by zero, null pointer dereference,
        access violation, etc) occurs.
        '''

        # prevent reentry or calling more than once
        if getattr(self, '_did_fatal_exception', False): return
        self._did_fatal_exception = True

        # Attempt to dump Python stack traces for each thread out to stderr
        try:
            from common.commandline import where_string
            print >> sys.stderr, where_string(duplicates = True)
            sys.stderr.flush()
        except Exception, e:
            print_exc()

    def __init__(self, plugins=None):
        self.plugins = plugins
        if USE_SINGLE_INSTANCE:
            DigsbyAppBase.__init__(self, appname = APP_NAME, redirect = False)
        else:
            DigsbyAppBase.__init__(self, redirect = False)

        # Add thread-safety checks to wx methods in dev mode. It's not comprehensive,
        # but it checks over 3000 methods, so it's a lot better than nothing :)
        if sys.DEV:
            import gui.app
            gui.app.addThreadChecksToClassRecursive(wx)
        MainMenuEventHandler.__init__(self)

        self.Bind(wx.EVT_ACTIVATE_APP, self.OnAppActivate)

        self.global_hotkeys = {}
        self.next_hotkey_id = 0

        self.PreShutdown = []


        self.SetStatusPrompt = SetStatusPrompt

    def OnAppActivate(self, event):
        '''
        Send out a notification with the current state, as there are at least three
        targets in various areas that need to respond to app activation events:

        - MenuListBox (to dismiss windowless menus)
        - Mac (and probably Linux) docking (for autohide)
        - Mac notifications (e.g. for dock bouncing)
        '''
        from wx.lib.pubsub import Publisher
        Publisher().sendMessage(('app', 'activestate', 'changed'), (event.Active))

    def Restart(self):
        oldval = getattr(self, 'restarting', False)

        self.restarting = True
        if not self.DigsbyCleanupAndQuit():
            self.restarting = oldval

    def AfterStartup(self):
        if getattr(self, '_afterstartup', False):
            return

        self._afterstartup = True

        log.info('AfterStartup')
        import wx
        import util.callbacks
        #do not confuse w/ wx.CallLater
        util.callbacks.register_call_later('MainThread', wx.CallAfter)

        import hooks
        hooks.notify('proxy.info_changed', util.GetProxyInfo())

        import urllib
        log.debug('system default proxy information: %r', urllib._getproxies())

        if 'wxMSW' in wx.PlatformInfo:
            self.setup_fullscreen()
            import gui.native.win.winutil as winutil
            winutil.disable_callback_filter()

        self.init_hotkeys()
        self.plugins = self.plugins if self.plugins is not None else init_plugins()

        # start the CPU monitor
        import wx
        if 'wxMSW' in wx.PlatformInfo and sys.opts.cpuwatch:
            from util.perfmon import CPUWatch
            self.cpu_watcher = CPUWatch()

    def OnInit(self):
        self.SetExitOnFrameDelete(False)
        log.info('SetExitOnFrameDelete(False)')

        set_app_info(self)

        if platformName == 'win':
            self.Bind(wx.EVT_POWER_SUSPENDED, self.OnSuspend)
            self.Bind(wx.EVT_POWER_RESUME,    self.OnResume)

        self.Bind(wx.EVT_MENU,            self.DigsbyCleanupAndQuit, id = wx.ID_EXIT)

        wx.IdleEvent.SetMode(wx.IDLE_PROCESS_SPECIFIED)
        wx.UpdateUIEvent.SetMode(wx.UPDATE_UI_PROCESS_SPECIFIED)

        wx.SystemOptions.SetOptionInt("mac.textcontrol-use-mlte", 1)
        wx.SystemOptions.SetOptionInt("mac.textcontrol-use-spell-checker", 1)

        self.setup_crash_reporting()

        if os.name != 'nt':
            init_stdpaths()

        import stdpaths
        sys.comtypes_dir = stdpaths.userlocaldata

        if platformName == 'win':
            # ensure comtypes interface generation happens in a user writable location
            log.info('set_comtypes_gendir()')
            set_comtypes_gendir()

        if not getattr(sys, 'DEV', False):
            try:
                self._get_release_type()
            except Exception, e:
                log.error('Error getting release type %r', e)

        try:
            self.init_branding()
        except Exception, e:
            log.error("Error getting brand type: %r", e)

        # Give the _MainThread class a getter for loopcount (which gets logged)
        if hasattr(self, 'MainLoopCount'):
            _MainThread = currentThread().__class__ # Thread subclass
            _MainThread.loopcount = property(lambda thread: self.MainLoopCount)

        import hooks
        hooks.register('proxy.info_changed', on_proxy_info_changed)
        import gui.toolbox as toolbox
        lsp = toolbox.local_settings_path()

        import metrics
        metrics.register_hooks()

        self.local_settings_exist_at_startup = lsp.isfile()

        # these hooks can prevent the app from starting
        start = True
        for hook in hooks.Hook("digsby.app.gui.pre"):
            if hook() is False:
                start = False
                break

        if start:
            force_autologin = getattr(getattr(sys, 'opts', None), 'measure') == 'startup' or None
            self.ShowSplash(force_autologin)
        else:
            wx.CallAfter(self.DigsbyCleanupAndQuit)

        return True

    def GetCmdLine(self):
        exe = sys.executable.decode(sys.getfilesystemencoding())

        if getattr(sys, 'frozen', False) in ('windows_exe', 'macosx_app'):
            args = sys.argv[1:] # slice off the executable name, since in Py2exe'd runs it's there.
        else:
            args = sys.argv[:]

        args = map(lambda x: x.decode(sys.getfilesystemencoding()), args)
        # We need to use the open command on Mac to ensure the new process is brought to the front
        # and that the old process is shut down.
        if sys.platform.startswith('darwin'):
            exe = exe.replace('/Contents/MacOS/python', '')
            return "open --new %s --args %s" % (exe, ' '.join(args))

        return u' '.join([exe] + args)

    def setup_crash_reporting(self, username = None):
        if not sys.opts.crashreporting:
            print >> sys.stderr, 'Crash reporting is disabled.'
            return

        crash_cmd = self.GetCmdLine()

        if username is not None:
            crash_cmd += ' --crashuser %s' % username

        # the app will fill in %s with the name of the generated dump file
        crash_cmd += ' --crashreport '
        if not sys.platform.startswith('darwin'):
            crash_cmd += '%s'

        sys.crashuniquekey = int(time()) # if this format changes, see diagnostic.py
        crash_cmd += ' --crashuniquekey %s' % sys.crashuniquekey

        # Process to be invoked upon crash
        if sys.opts.submit_crashdump:
            log.info("setting crash command to %s" % crash_cmd)
            self.SetCrashCommand(crash_cmd)

        if sys.opts.full_crashdump:
            # Send full crash dumps with process memory
            flag = (wx.CRASH_REPORT_LOCATION | wx.CRASH_REPORT_STACK |
                    wx.CRASH_REPORT_LOCALS | wx.CRASH_REPORT_GLOBALS)

            self.crash_report_flags = flag

        # Location of crash file can be specified on the command line.
        crashdump_dir = sys.opts.crashdump_dir
        if crashdump_dir:
            from os.path import isdir, abspath, join as pathjoin, normpath

            try:
                crashdump_dir = abspath(crashdump_dir)
                if not isdir(sys.opts.crashdump_dir):
                    os.makedirs(crashdump_dir)
            except Exception:
                print_exc()
            else:
                filename = 'Digsby_%s_%s.dmp' % (username or '', str(time()))
                filename = normpath(pathjoin(crashdump_dir, filename))
                wx.CrashReport.SetFileName(filename)
                print >> sys.stderr, 'Dumpfile: %r' % wx.CrashReport.GetFileName()

        # Indicate to WX that we'd like to catch C exceptions
        wx.HandleFatalExceptions()


    def OnSuspend(self, e):
        from common import profile
        p = profile()
        if p is not None:
            p.hibernate()

    def OnResume(self, e):
        from common import profile
        p = profile()
        if p is not None:
            p.unhibernate(20)

    def setup_fullscreen(self):
        from gui.native.helpers import FullscreenApp
        from gui.imwin import imhub
        from util.primitives.funcs import Delegate

        self.on_fullscreen = Delegate()
        self._fs_app_running = wx.PyTimer(lambda: self.on_fullscreen(FullscreenApp()))
        self._fs_app_running.Start(1000, False)

        # when returning from fullscreen, flush the IM window show delegate
        self.on_fullscreen += lambda val: wx.CallAfter(imhub.im_show.call_and_clear) if not val else None

    finish_init = False

    def ShowSplash(self, autologin_override = None, kicked=False):
        log = getLogger('splash')

        init_threadpool()

        self.OnBuddyListShown = []

        def splash_success(info):
            self.AfterStartup()
            import digsbyprofile
            digsbyprofile.initialized += self.FinishInit

            return digsbyprofile.signin(hooks.first('digsby.identity.active'))

        if 'wxMSW' in wx.PlatformInfo:
            preload_comctrls()

        self._show_splash(splash_success, autologin_override)

        if kicked:
            wx.CallAfter(wx.MessageBox, message = _('Your digsby password has been changed. '
                                                    'Please log back in with the new password.'),
                                        caption =  _('Password Changed'))
        self.finish_init = False
        return True

    def _show_splash(self, splash_success, autologin_override):
        from digsbysplash import LoginController
        login_controller = LoginController(splash_success, autologin_override=autologin_override)
        self._login_controller = login_controller

        opts = getattr(sys, 'opts', None)
        username, password = getattr(opts, 'username', ''), getattr(opts, 'password', '')

        # passing --username and --password on the commandline prefills the splash screen.
        if username: login_controller.set_username(username)
        if password: login_controller.set_password(password)
        if username and password:
            login_controller.signin()

        self.SetTopWindow(login_controller.window)
        wx.CallAfter(login_controller.ShowWindow)

    def SetupTaskbarIcon(self):
        # The icon
        assert(self.buddy_frame)

        from gui.trayicons import BuddyListTaskBarIcon
        ticon = self.tbicon = BuddyListTaskBarIcon()

    def OpenUrl(self, url):
        wx.LaunchDefaultBrowser(url)

    def FinishInit(self, on_gui_load=None):
        log.info('FinishInit enter')
        if self.finish_init:
            return
        self.finish_init = True

        wx.CallAfter(self._finish_init_gui, on_gui_load)

    def _finish_init_gui(self, on_gui_load=None):
        import digsbyprofile
        digsbyprofile.initialized -= self.FinishInit
        profile = digsbyprofile.profile
        login_controller = self._login_controller
        del self._login_controller

        if 'WX_WEBKIT_LOG' not in os.environ:
            os.environ['WX_WEBKIT_LOG'] = 'SQLDatabase'

        initialize_webkit()

        if login_controller.cancelling:
            log.info('splash screen is cancelled...returning profile.disconnect()')
            return profile.disconnect()

        log.info('wx.CallAfter(login_controller.DestroyWindow)')
        wx.CallAfter(login_controller.DestroyWindow)

        autologin = not wx.GetKeyState(wx.WXK_SHIFT)
        log.info('autologin for IM accounts: %r', autologin)

        from gui.imwin.imtabs import explodeAllWindows
        # link on/off preference
        # It would be nice if we could put this somewhere else,
        # like a sort of place for things that should happen during
        # "real" app load, i.e. post splash screen.
        profile.prefs.link('messaging.tabs.enabled',
                   lambda val: (wx.CallAfter(explodeAllWindows) if not val else None),
                   callnow = False,
                   obj = wx.GetApp())

        import gui.skin

        # preload fonts
        log.info('gui.textutil.default_font()')
        gui.textutil.default_font()
        def preload_fonts():
            log.info('preloading fonts')
            n = len(list(gui.textutil.GetFonts()))
            log.info('preloaded %d fonts', n)

        log.info('wx.CallAfter(preload_fonts)')
        wx.CallAfter(preload_fonts)

        # when skinning prefs change, update the skin

        import stdpaths
        import util
        log.info('setting resource paths')
        gui.skin.set_resource_paths([
                                     util.program_dir() / 'res', # Apparently this has to be first?
                                     stdpaths.userdata,
                                     stdpaths.config,
                                    ])

        changeskin = gui.skin.set_active

        def on_skin_load():
            log.info('on_skin_load callback called, calling PostSkin')
            self.PostSkin(autologin = autologin, success=on_gui_load)

        log.info('setting up crash reporting')
        self.setup_crash_reporting(username = profile.username)

        from common import pref
        def foo():
            log.info('calling gui.skin.set_active')
            if sys.platform.startswith('darwin'):
                changeskin('native', None,
                       callback = on_skin_load)
            else:
                changeskin(pref('appearance.skin'), pref('appearance.variant'),
                       callback = on_skin_load)
        log.info('wx.CallAfter(foo)')
        wx.CallAfter(foo)

    #@callsback
    def PostSkin(self, autologin=False, success=None):
        log.info('PostSkin enter, creating BuddyListFrame')

        initialize_jumplist()

        from gui.buddylist.buddylistframe import BuddyListFrame
        self.buddy_frame = BuddyListFrame(None, title = _('Buddy List'), name = 'Buddy List',
                                          style = wx.DEFAULT_FRAME_STYLE | wx.FRAME_NO_TASKBAR)

        # register the main menu events
        # TODO: Enable this for Win too once I confirm the automated tests pass
        # and do some testing myself.
        if newMenubar:
            self.register_handlers()

        log.info('BuddyListFrame created')

        # gui for saving snapshots
        if sys.opts.savesnapshots:
            wx.GetApp().AddGlobalHotkey((wx.MOD_CMD | wx.MOD_ALT, ord('S')), save_webkit_snapshot_gui)

        def muchlater():
            log.info('muchlater enter')
            self.idletimer = wx.PyTimer(self.not_idle)
            self.idletimer.Start(IDLE_CHECK_MS)

            def show_buddylist_frame():
                from common import pref
                if pref('buddylist.show_on_startup', type=bool, default=True):
                    self.buddy_frame.Show(True)

                from gui.toast.toasthelp import enable_help
                enable_help()

                self.SetTopWindow(self.buddy_frame)

                from util.primitives.funcs import Delegate
                log.info('calling and clearing OnBuddyListShown w/ %r', autologin)
                Delegate(self.OnBuddyListShown)(autologin = autologin)
                del self.OnBuddyListShown[:]

                # do RAM page out 1 minute after buddylist shows.
                def memevent():
                    from gui.native import memory_event
                    memory_event()

                self.memtimer = wx.CallLater(60 * 1000, memevent)

                if platformName == 'win':
                    from gui.native.win.process import page_out_ram
                    wx.CallLater(1000, page_out_ram)

            wx.CallAfter(show_buddylist_frame)

        wx.CallAfter(muchlater)
        log.info('setting up task bar icon')
        self.SetupTaskbarIcon()

    def MacOpenFile(self, filename):
        log.info('File dragged to dock icon: ' + filename)

    def toggle_prefs(self):
        import digsbyprofile
        if (not hasattr(digsbyprofile, 'profile')) or (digsbyprofile.profile is None):
            return wx.MessageBox(_('Please login first.'), _('Advanced Preferences'))

        from common import pref

        if not (__debug__ or sys.REVISION == 'dev' or pref('debug.advanced_prefs', False)):
            return

        profile = digsbyprofile.profile
        import prefs

        prefs.edit(profile.prefs, profile.defaultprefs, self.buddy_frame or None)

    def toggle_crust(self):
        'Pops up or hides the Python console.'

        from common import pref

        can_show_console = getattr(sys, 'DEV', False) or pref('debug.console', False)
        if not can_show_console:
            return
        self.make_crust()
        self.crust.toggle_shown()

        # keyboard focus goes to shell prompt
        if self.crust.IsShown():
            self.crust.FocusInput()

    def make_crust(self):
        if not hasattr(self, 'crust') or not self.crust:
            import gui.shell
            tlws = wx.GetTopLevelWindows()
            self.crust = gui.shell.PyCrustFrame(None)

            if tlws:
                parent = tlws[0]
                parent.crust = self.crust

    def toggle_sorting(self):
        from common import profile
        prefs = profile.prefs

        if prefs:
            if prefs.get('buddylist.allow_sorting_change', False):
                prefs['buddylist.sorting'] = not prefs.get('buddylist.sorting', True)

    def not_idle(self, e=None):
        from common import pref, profile
        import digsbyprofile as d

        if not profile.prefs: return self.idletimer.Start()

        set_idle_after = pref('messaging.idle_after', 20 * d.IDLE_UNIT, type=int)

        from gui.native.helpers import GetUserIdleTime
        t = GetUserIdleTime()

        min_idle = IDLE_CHECK_MS
        from peak.util.plugins import Hook
        for hook in Hook('digsby.app.idle'):
            try:
                next = int(hook(t))
            except Exception:
                traceback.print_exc()
            else:
                if next < min_idle and next > 0:
                    min_idle = next

        if t < (set_idle_after*1000):
            profile.reset_timers()
            profile.return_from_idle()

        self.idletimer.Start(min_idle)

    def OnSaved(self):
        log.info('profile.save SUCCESS, shutting down')
        return self.do_shutdown()

    def OnSaveError(self):
        log.warning("error saving blobs")
        return self.do_shutdown()

    def DigsbyCleanupAndQuit(self, e=None):
        from util.primitives.error_handling import traceguard
        from util.primitives.funcs import Delegate

        # first close the IM windows: they might veto the app closing.
        with traceguard:
            for win in wx.GetTopLevelWindows():
                from gui.imwin.imtabs import ImFrame
                if isinstance(win, ImFrame):
                    if not win.Close():
                        return False

        # prevent reentracy
        if getattr(self, 'shutting_down', False):
            return False

        self.shutting_down = True

        from peak.util.plugins import Hook
        for hook in Hook('digsby.app.exit'):
            hook()

        # Do stuff from OnExit, and then self.ExitMainLoop()
        # Keep OnExit empty-ish
        log.info('DigsbyCleanupAndQuit')

        log.info('shutting down single instance server')
        with traceguard:
            # stop the single instance server so that if we have an error on shutdown,
            # other instances will still run.
            if USE_SINGLE_INSTANCE:
                self.StopSingleInstanceServer()

        if USE_HANGING_THREAD_DAEMON and sys.opts.force_exit:
            from util import HangingThreadDaemon
            log.info('starting shutdown timer daemon')
            HangingThreadDaemon(wait = EXIT_TIMEOUT_SECS, sysexit = True).start()

        log.info('calling PreShutdown')
        Delegate(getattr(self, 'PreShutdown', []))()

        log.info('  saving and disconnecting profiles and accounts')

        # Hide the buddylist immediately.
        with traceguard:
            # FIXME: On Mac, we need to delete the TaskBarIcon before calling Close()
            # on TLWs, because for some odd reason wxTaskBarIcon uses a hidden wxTLW
            # instead of wxEvtHandler to catch and forward events. Unfortunately, we
            # can't keep a wxTLW from appearing in wx.GetTopLevelWindows(), but at the
            # same time, wxTaskBarIcon expects the wxTLW to still be alive when it
            # is destroyed. This change can be reverted once I've found a suitable
            # fix for the Mac problem. Phew. ;-)
            log.info("destroying main tray icon...")
            if getattr(self, 'tbicon', None) is not None:
                self.tbicon.Destroy()
                self.tbicon = None

            frame = getattr(self, 'buddy_frame', None)
            if frame:
                if frame.IsShown():
                    frame.on_close(exiting = True)

                # TODO: decouple account tray icons from the buddylist frame
                #       until then, this code needs to run.
                log.info('destroying %r', frame)
                frame.on_destroy()

            # Close all popups
            with traceguard:
                from gui import toast
                toast.cancel_all()

            # Close any remaining top level windows. This way EVT_CLOSE will always run
            # even if the window is never closed while the app is running. This way
            # we can always use on_close for window cleanup and persistence.
            for tlw in wx.GetTopLevelWindows():
                # TODO: allow veto by dialog if there are unread messages?
                tlw.Close(True) # force = True means EVT_CLOSE handlers cannot veto

        if sys.opts.quickexit:
            log.info('exiting forcefully')
            os._exit(1)

        from digsbyprofile import profile
        if profile and profile.connection:
            try:
                profile.save(success = self.OnSaved,
                             error   = self.OnSaveError)            # Save account info.
            except Exception:
                print_exc()
                self.OnSaveError()
        else:
            self.OnSaved()


        return True

    def OnExit(self, event = None):
        log.info('OnExit')
        log.info('  replacing wx.CallAfter')

        wx.CallAfter = lambda f, *a, **k: f(*a, **k)

    def do_shutdown(self):
        from util import traceguard
        log.info('do_shutdown')

        dbg = log.debug

        # stuff to do after profile is disconnected
        def _after_disconnect():
            log.info('joining with TimeoutThread')
            with traceguard:
                from util.threads import timeout_thread
                timeout_thread.join()
            log.info('joined with TimeoutThread')

            log.info('joining with AsyncoreThread')
            with traceguard:
                import AsyncoreThread
                AsyncoreThread.end_thread()
                AsyncoreThread.join()

            if __debug__ and getattr(sys, 'REVISION', None)  == 'dev':
                with traceguard:
                    if os.path.exists('logs/lastlogfile'):
                        with open('logs/lastlogfile', 'ab') as f:
                            f.write('yes\n')

            log.info('joining ThreadPool')
            from util.threads.threadpool import ThreadPool
            ThreadPool().joinAll()
            log.info('done joining ThreadPool')

            # Goodbye, cruel world!
            dbg('exit main loop...')
            self.ExitMainLoop()
            dbg('clean exit.')

        dbg('disconnecting profile')
        with traceguard:
            from common import profile
            if profile and hasattr(profile, 'disconnect'):
                profile.disconnect(success = _after_disconnect)
            else:
                _after_disconnect()

        if "wxMSW" in wx.PlatformInfo:
            dbg('calling CoUnInitialize')
            with traceguard:
                import atexit
                for f, a, k in atexit._exithandlers:
                    if f.__module__ == 'comtypes' and f.__name__ == 'shutdown':
                        atexit._exithandlers.remove((f, a, k))
                        f(*a, **k)
                        break

        # If we're restarting, spawn the process again
        if getattr(self, 'restarting', False):
            cmdline = self.GetCmdLine()
            if '--noautologin' not in cmdline:
                cmdline += ' --noautologin'

            if '--updated' in cmdline:
                cmdline = cmdline.replace('--updated', '')

            wx.Execute(cmdline)

    def init_hotkeys(self):
        from gui.input.inputmanager import input_manager as input
        from gui import skin

        # Add common shortcut contexts.
        input.AddGlobalContext(_('Global Shortcuts'), 'Global')

        # Debug actions only enabled for dev mode
        if getattr(sys, 'DEV', False):
            input.AddGlobalContext(_('Debug Global Shortcuts'), 'Debug')

        # setup actions starting with "TextControls"
        input.AddClassContext(_('Text Controls'),    'TextControls', wx.TextCtrl)

        # Load all keyboard shortcuts from res/keys.yaml and res/platformName/keys.yaml
        resdir = skin.resourcedir()
        KEYS_YAML = 'keys.yaml'

        yaml_sources = (resdir / KEYS_YAML, resdir / platformName / KEYS_YAML)
        for yaml in yaml_sources:
            if yaml.isfile():
                log.info('loading keyboard shortcuts from %r', yaml)
                input.LoadKeys(yaml)

        # Link some callbacks to actions.
        actions = [('TextControls.SelectAll',          lambda textctrl: textctrl.SetSelection(-1, -1)),
                   ('TextControls.DeletePreviousWord', 'gui.toolbox.DeleteWord'),
                   ('Global.DigsbyShell.ToggleShow',   lambda win: self.toggle_crust()),
                   ('Global.AdvancedPrefs.ToggleShow', lambda win: self.toggle_prefs()),
                   ('Global.Skin.Reload',              lambda win: skin.reload()),
                   ('BuddyList.Sorting.Toggle',        lambda win: self.toggle_sorting()),
                   ('Debug.XMLConsole',                'common.commandline.xmlconsole'),
                   ('Debug.JavaScriptConsole',         'gui.browser.jsconsole.show_console'),
                   ('Debug.ClearConsole',              'cgui.cls')]

        addcb = input.AddActionCallback
        for name, action_cb in actions:
            addcb(name, action_cb)

        input.BindWxEvents(self)

    def AddGlobalHotkey(self, keys, callback):
        '''
        >> wx.GetApp().AddGlobalHotkey('ctrl+alt+d', MyAwesomeCallback)
        '''

        # TODO: hook this into the input manager system in the above method

        id = self.next_hotkey_id
        self.next_hotkey_id += 1

        modifiers, key = keys

        self.buddy_frame.RegisterHotKey(id, modifiers, key)
        self.buddy_frame.Bind(wx.EVT_HOTKEY, callback, id = id)

        self.global_hotkeys[(modifiers, key, callback)] = id

    def RemoveGlobalHotkey(self, keys, callback):
        from gui.toolbox import keycodes
        modifiers, key = keycodes(keys)

        id = self.global_hotkeys.pop((modifiers, key, callback))
        self.buddy_frame.UnregisterHotKey(id)

    def init_branding(self):
        import stdpaths, util, syck
        brand_fname = 'brand.yaml'
        for fpath in ((stdpaths.userlocaldata / brand_fname), (util.program_dir() / brand_fname)):
            try:
                with open(fpath, 'rb') as f:
                    yaml = syck.load(f)
                    brand = yaml['brand']
            except Exception, e:
                log.debug("Didn't get a brand from %r: %r", fpath, e)

        log.info("Got brand: %r", brand)
        sys.BRAND = brand
        return brand

    #
    # taskbar icon methods:
    #

    def OnRaiseBuddyList(self, e = None):
        frame = self.buddy_list

        docker = frame.docker
        if docker.AutoHide and docker.docked:
            if docker.autohidden:
                docker.ComeBack()

            frame.Raise()
        elif not frame.IsActive():
            frame.Raise()


# apply a filter to the console handler so that it doesn't duplicate
# stderr by displaying the stderr logger
class StdErrFilter(object):
    def filter(self, record):
        return record.name != 'stderr'


class MyStdErr(object):
    has_stderr = True
    def write(self, s):
        try:
            self.stderrlog.error(s.rstrip())
        except:
            pass

        if MyStdErr.has_stderr:
            try:
                sys.__stderr__.write(s)
            except:
                MyStdErr.has_stderr = False


    def flush(self):
        if MyStdErr.has_stderr:
            try:
                sys.__stderr__.flush()
            except:
                MyStdErr.has_stderr = False

def get_logdir():
    """Returns the location for Digsby's log file to be created. After creation
        the directory can be more easily found with `sys.LOGFILE_NAME.parent`
    """

    # On Vista: C:\Users\%USERNAME%\AppData\Local\Digsby\Logs
    # On XP:    C:\Documents and Settings\%USERNAME%\Local Settings\Application Data\Digsby\Logs
    # On Mac:   /Users/$USER/Library/Application Support/Digsby/Logs
    # (internationalizations may apply)
    import sys, stdpaths
    if getattr(sys, 'is_portable', False):
        return stdpaths.temp / 'Digsby Logs'
    else:
        return stdpaths.userlocaldata / 'Logs'

def get_last_log_file_name():
    if __debug__:
        with open('logs/lastlogfile', 'r') as f:
            lines = [line for line in f]
            return lines[0][:-1]
    else:
        return os.path.join(get_logdir(), LOG_FILENAME)

def get_std_redirect_file(force_release=False):
    '''Return a logfile name for the system log.'''

    if __debug__ and not force_release:
        return os.path.abspath('logs/systemlog.txt')
    else:
        return str((path(get_logdir()) / 'systemlog.txt').abspath())

def setup_log_system(force_release=False):
    # don't popup dialogs for wxLogError calls--
    # go to stderr instead
    wx.Log.SetActiveTarget(wx.LogStderr())

    if sys.opts.no_log:
        return

    from path import path
    import cgui

    from fileutil import DisablingStream, DelayedStreamLimiter, LimitedFileSize
    sys.stdout, sys.stderr = DisablingStream(sys.__stdout__), MyStdErr()

    stderrlog = logging.getLogger('stderr')
    sys.stderr.stderrlog = stderrlog

    root = logging.Logger.root
    root.stream = sys.stderr
    root.setLevel(1)

    from csvlogging import gzipFileHandler, CloseFileHandler, CSVFormatter, CSV_HEADERS

    _log_debug = __debug__ and not force_release
    sys.STDERR_LOGFILE = stderr_log_redirect = get_std_redirect_file(force_release)

    if _log_debug:
        # In debug mode, log every time to a new file.

        # set up logging to file - see previous section for more details
        t = str(int(time()))

        fn = path('logs/digsby-%s.log.csv' % t)

        sys.LOGFILE_NAME = fn

        if not os.path.exists('logs'):
            os.mkdir('logs')


        f = open(fn, 'wb')
        f.write(CSV_HEADERS)

        if getattr(sys.opts, 'limit_log', True):
            f = DelayedStreamLimiter(f, limit=LOG_SPEED_LIMIT, window=LOG_SPEED_WINDOW)

        hdlr = CloseFileHandler(f)
        hdlr.setFormatter(CSVFormatter())
        root.addHandler(hdlr)

        # define a Handler which writes INFO messages or higher to the sys.stderr
        global full_loggers
        gzip_file = gzipFileHandler(t)
        gzip_file.setFormatter(CSVFormatter())
        try:
            delete = False
            with open('logs/lastlogfile', 'r') as f:
                lines = [line for line in f]
                delete = len(lines) == 2
            if delete:
                path(lines[0][:-1]).remove()
        except Exception, e:
            pass

        with open('logs/lastlogfile', 'wb') as f:
            f.write(fn+'\n')

        global current_log

        current_log = fn
        full_loggers = [gzip_file]

        # add the handler to the root logger
        logging.getLogger('').addHandler(gzip_file)
        sys.CSTDERR_FILE = None
    else:
        # In release mode, only store the previous log, overwriting it each time.
        logdir = path(get_logdir())

        if not logdir.isdir():
            logdir.makedirs()

        logfilebase = logfile = logdir / LOG_FILENAME
        N = 2

        while True:
            try:
                f = open(logfile, 'wb')
                break
            except:
                print_exc()
                logfile = logfilebase + ' (%d)' % N
                N += 1
                if N > 100: raise AssertionError
                f = open(logfile, 'wb')

        sys.LOGFILE_NAME = logfile

        cstderr = (logdir / 'cstderr.txt').abspath()
        cgui.redirectStderr(cstderr)
        sys.CSTDERR_FILE = cstderr

        f.write(CSV_HEADERS)
        f.close()

        hdlr = CloseFileHandler(DelayedStreamLimiter
                                (LimitedFileSize(sys.LOGFILE_NAME, 20*1024*1024, 10*1024*1024, initmode='ab'),
                                 limit=LOG_SPEED_LIMIT, window=LOG_SPEED_WINDOW))
        hdlr.setFormatter(CSVFormatter())

        # allow buffered logging via --log-buffer on the console
        capacity = getattr(sys.opts, 'log_buffer', 0)
        if capacity:
            from logging.handlers import MemoryHandler
            hdlr = MemoryHandler(capacity, target=hdlr)

        full_loggers = [hdlr]
        root.addHandler(hdlr)

    if hasattr(wx, 'SetLogFile'):
        if not wx.SetLogFile(stderr_log_redirect):
            print >> sys.stderr, "Could not redirect log file to %s" % stderr_log_redirect
        else:
            import datetime
            wx.LogMessage(datetime.datetime.now().isoformat())

    global logging_to_stdout
    if not _log_debug:
        logging.info('logger started - rev %s', sys.REVISION)
        logging_to_stdout = False
    else:
        # don't log to the console in release mode
        init_stdout()
        logging_to_stdout = True

    print >> sys.stderr, "testing stderr"
    print >> sys.stdout, "testing stdout"

class ConsoleFormatter(logging.Formatter):
    def format(self, record):
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        exc = record.exc_text if record.exc_text else ''

        return \
        ''.join(['%-20s' % record.name,
                 record.threadName[:4],
                 '-',
                 '%-4s | ' % record.levelname[:4],
                 '%s' % record.getMessage(),
                 exc
                 ])

def redirect_c_stderr(stderr_log_redirect):
    '''
    when C libraries fprintf(stderr, ...), we lose it. redirect it to systemlog.txt
    '''
    STDERR = 2
    if platformName == 'win':
        try:
            import ctypes
            STD_ERROR_HANDLE = -12
            STDERR = ctypes.windll.kernel32.GetStdHandle(STD_ERROR_HANDLE)
            if STDERR == 0:
                se = os.open(stderr_log_redirect, os.O_WRONLY|os.O_APPEND|os.O_CREATE)
                if not ctypes.windll.kernel32.SetStdHandle(STD_ERROR_HANDLE, se):
                    raise ctypes.WinErr()
                return
        except Exception:
            print_exc()
            pass

    se = os.open(stderr_log_redirect, os.O_WRONLY|os.O_APPEND)
    os.dup2(se, STDERR)
    os.close(se)


def init_stdout():
    from fileutil import DelayedStreamLimiter
    console = None
    root = logging.Logger.root

    try:
        sys.stdout.write('Testing if sys.stdout is safe...\n')
    except:
        root.info('stdout disabled')
    else:
        root.info("stdout enabled")
        import logextensions
        console = logextensions.ColorStreamHandler(DelayedStreamLimiter(sys.stdout,limit=LOG_SPEED_LIMIT, window=LOG_SPEED_WINDOW))
        console.setLevel(1)

        # set a format which is simpler for console use
        console.setFormatter(ConsoleFormatter())

    if console is not None:
        logging.getLogger('').addHandler(console)

    if console is not None:
        console.addFilter(StdErrFilter())

def setup_gettext(plugins):

    # allow !_ construction for translatable strings in YAML
    import syck
    syck.Loader.construct__ = lambda self, node: _(node.value)
    syck.Loader.construct_N_ = lambda self, node: N_(node.value)

    lang =  getattr(getattr(sys, 'opts', None), 'lang', None)
    if lang and lang.strip():
        set_language(lang, plugins)
    else:
        set_language(None)

def get_v(plugin):
    try:
        return plugin.info.get('bzr_revno')
    except Exception:
        traceback.print_exc()
        return -1

def set_language(language, plugins=None):
    import babel.support as support
    DOMAIN = 'digsby'
    if plugins is None:
        plugins = []
    matches = []
    for plugin in plugins:
        try:
            if plugin.info.get('type') == 'lang' and \
               plugin.info.get('domain')== 'digsby' and \
               plugin.info.get('language') == language:
                matches.append(plugin)
        except Exception:
            traceback.print_exc()
    matches.sort(key = get_v, reverse = True)
    for match in matches:
        cat = match.get_catalog()
        translation = support.Translations.load(cat, domain=DOMAIN)
    else:
        import gettext
        translation = gettext.NullTranslations()
    translation.install(unicode=True, names='<standard>')
    return

    # TODO: do we need to set wxLocale? how do we do it if there is not
    # a language code for it?

    thisdir = os.path.dirname(__file__)
    catalogpath = os.path.normpath(os.path.abspath(os.path.join(thisdir, '../locale')))
    wx.Locale.AddCatalogLookupPathPrefix(catalogpath)
    l = wx.Locale(wx.LANGUAGE_SPANISH_DOMINICAN_REPUBLIC)
    l.AddCatalog(DOMAIN)
    assert l.IsOk()

startup_begin = 0

def check_dependencies():
    try:
        import tlslite
    except ImportError:
        pass
    else:
        print >> sys.stderr, 'WARNING! tlslite is on PYTHONPATH, and will cause SSL problems. Please remove it: %r' % tlslite.__file__


def set_update_tag():
    tag = sys.opts.updatetag
    import syck
    if tag is not None:
        import stdpaths
        try:
            with open(stdpaths.userlocaldata / 'tag.yaml', 'w') as f:
                syck.dump({'tag':tag}, f)
        except Exception:
            pass

def init_stdpaths():
    # initialize util.stdpaths variables
    import stdpaths
    stdpaths.init()

APP_ID = u'com.dotSyntax.Digsby'
# append DEV if in devmode
if getattr(sys, 'DEV', False):
    APP_ID += '_DEV_%s' % time()

def set_app_id():
    import ctypes
    try:
        SetAppID = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
    except AttributeError:
        return

    SetAppID(APP_ID)

def main():
    global startup_begin
    startup_begin = time()

    add_dev_plugins_path()

    plugins = None
    if os.name == 'nt': # init stdpaths early on windows.
        init_stdpaths()

    from bootstrap import install_N_
    install_N_()
    plugins = init_plugins()
    setup_gettext(plugins)
    set_app_id()

    import sys
    if getattr(sys, 'DEV', False):
        digsbysite.SHOW_TRACEBACK_DIALOG = getattr(sys.opts, 'traceback_dialog', True)

    # Digsby spawns itself with --crashreport if it crashes.
    if sys.opts.crashreport:
        # Remove this hack when we figure out manifests for dev mode
        if 'wxMSW' in wx.PlatformInfo:
            preload_comctrls()
        sys.util_allowed = True
        return send_crash_report()

    if sys.opts.profile:
        sys.util_allowed = True
        from util import set_profilers_enabled
        set_profilers_enabled(True)

    import hooks
    if hooks.any('digsby.app.init.pre'):
        return
    digsby_app = DigsbyApp(plugins)
    hooks.notify('digsby.app.init.post')


    wx.ConfigBase.Set(wx.FileConfig())

    setup_log_system(force_release=getattr(sys.opts, 'release_logging', False))
    log_system_info()

    set_update_tag()

    if sys.opts.profile:
        from util import use_profiler, all_profilers

        if sys.opts.profile > 1:
            # this option causes profiling information to be logged every thirty seconds
            from util import RepeatTimer

            def get_reports():
                print '\n\n'.join(p.report() for p in all_profilers().itervalues())

            digsby_app._profile_timer = RepeatTimer(30, get_reports)
            digsby_app._profile_timer.start()

        return use_profiler(currentThread(), digsby_app.MainLoop)
    else:
        return digsby_app.MainLoop()

def send_crash_report():
    '''Prompts the user to send a crash report, then sends it.'''

    a = wx.PySimpleApp()
    from traceback import format_exc

    set_app_info(a)
    from crashgui import CrashDialog

    if os.name != 'nt':
        init_stdpaths()

    msg = _('There was an error submitting your crash report.')

    try:
        diag = CrashDialog()
        diag.CenterOnScreen()
        diag.RequestUserAttention()
        if wx.ID_OK == diag.ShowModal():
            import util.diagnostic as d
            last_log = get_last_log_file_name()
            diagobj = d.load_crash(sys.opts.crashreport, last_log,
                                   username = sys.opts.crashuser,
                                   description = diag.Description)
            if diagobj.succeeded:
                msg = _('Crash report submitted successfully.')
        else:
            return
    except Exception:
        print_exc()

    if False: # disabled until we can handle the single instance checker still running
        msg += '\n\n' + _('Would you like to restart Digsby now?')

        if wx.YES == wx.MessageBox(msg, _('Crash Report'), style = wx.YES_NO | wx.YES_DEFAULT):
            cmd = sys.executable.decode(sys.getfilesystemencoding())

            if not getattr(sys, 'frozen', False) == 'windows_exe':
                cmd += ' ' + sys.argv[0] # the script name

            wx.Execute(cmd)

def log_system_info():
    'Logs basic info about WX, Python, and the system at startup.'

    import locale, stdpaths
    from time import clock

    global startup_begin
    startup_time = (clock()) * 1000

    opts_copy = dict(sys.opts.__dict__)
    opts_copy.pop('password', None)
    info = log.info
    info('Digsby rev %s', sys.REVISION)
    info('sys.opts: %r', opts_copy)
    info("started up in %s ms", startup_time)
    info(' '.join(wx.PlatformInfo) + ' wx v' + '.'.join(str(c) for c in wx.VERSION))
    info('Platform: %r', ' '.join(platform.uname()).strip())
    info('Python ' + sys.version)
    info('locale: ' + str(locale.getdefaultlocale()))
    info('user local data dir: %r', stdpaths.userlocaldata)
    info('__debug__ is %r', __debug__)

def set_app_info(app):
    app.SetAppName(APP_NAME)
    app.SetVendorName(u'dotSyntax')
    app.SetAppName(APP_NAME)
    app.SetClassName(APP_NAME)

if 'wxMSW' in wx.PlatformInfo:
    def preload_comctrls():
        # preload comctrls to prevent a TrackMouseEvent crash
        # http://trac.wxwidgets.org/ticket/9922
        from ctypes import windll
        windll.comctl32.InitCommonControls()

    def set_comtypes_gendir():
        'Ensure sure any COM interface generation happens in a user writable location.'
        info = log.info

        info('in set_comtypes_gendir')
        import stdpaths
        cache_root = stdpaths.userlocaldata / 'cache'
        info('in set_comtypes_gendir 2')

        info('importing comtypes')
        import comtypes
        info('comtypes.initialize()')
        comtypes.initialize()

        info('in set_comtypes_gendir 3')
        import comtypes.client
        info('in set_comtypes_gendir 4')

        gendir = cache_root / 'comtypes_generated'
        info('in set_comtypes_gendir 5')
        info('gendir %r', gendir)

        if not gendir.isdir():
            info('creating comtypes gendir at %r', gendir)
            gendir.makedirs()
            info('created comtypes gendir at %r', gendir)

        info('setting gen_dir')
        comtypes.client.gen_dir = unicode(gendir).encode(sys.getfilesystemencoding())
        info('comtypes gen_dir is now %r', comtypes.client.gen_dir)

        # monkeypatch comtypes on dev to ensure no double deletes happen. (known bug?)
        # http://thread.gmane.org/gmane.comp.python.comtypes.user/476
        from comtypes import _compointer_base
        _cpbDel = _compointer_base.__del__
        def newCpbDel(self):
            deleted = getattr(self, '_deleted', False)
            assert not deleted, "compointer already deleted"
            if not deleted:
                _cpbDel(self)
            self._deleted = True
        newCpbDel.__name__ = "__del__"
        _compointer_base.__del__ = newCpbDel
        del _compointer_base

def webkit_database_dir():
    from util.cacheable import get_cache_root
    database_dir = get_cache_root(user=True) / 'html5storage'
    return database_dir

def copytree(src, dest):
    if dest.isdir():
        dest.rmtree()
    src.copytree(dest)

webkit_initialized = False

def is_webkit_initialized():
    return webkit_initialized

def initialize_webkit():
    assert wx.IsMainThread()

    # This allows wxWebKit to valid ssl certs
    import gui.skin
    ssl_cert_bundle = os.path.join(gui.skin.resourcedir(), 'ca-bundle.crt')
    assert os.path.exists(ssl_cert_bundle)

    if not isinstance(ssl_cert_bundle, bytes):
        ssl_cert_bundle = ssl_cert_bundle.encode('filesys')

    try:
        os.environ['CURL_CA_BUNDLE_PATH'] = ssl_cert_bundle
    except Exception:
        import traceback; traceback.print_exc()

    try:
        try:
            import webview
        except ImportError:
            import wx.webview as webview
    except Exception:
        print >> sys.stderr, "Warning: error preloading webkit"
    else:
        webview.WebView.InitializeThreading()
        WebView = webview.WebView

        _original_runscript = WebView.RunScript

        # Make RunScript asynchronous if we're already in a RunScript call
        # further down the stack.
        #
        # We haven't actually proven that WebKit doesn't tolerate reentrant
        # RunScript calls, but many WebKit crashers do have that in common.
        def RunScript(webview, *a, **k):
            if getattr(webview, '_in_run_script', False):
                wx.CallAfter(RunScript, webview, *a, **k)
                return

            webview._in_run_script = True
            try:
                return _original_runscript(webview, *a, **k)
            finally:
                webview._in_run_script = False

        WebView.RunScript = RunScript

        # limit webkit cache size
        if hasattr(webview.WebView, 'SetCachePolicy'):
            WEBKIT_CACHE_CAPACITY = 4 * 1024 * 1024
            log.info('setting webkit cache capacity to %d', WEBKIT_CACHE_CAPACITY)
            cachePolicy = WebView.GetCachePolicy()
            cachePolicy.MaxDeadCapacity = cachePolicy.Capcity = WEBKIT_CACHE_CAPACITY
            WebView.SetCachePolicy(cachePolicy)

        # snapshots
        database_dir = webkit_database_dir()
        if sys.opts.dbsnapshot:
            log.info('loading webkit snapshot %r', sys.opts.dbsnapshot)

            snapshot = database_dir.parent / sys.opts.dbsnapshot
            if not snapshot.isdir():
                print >> sys.stderr, 'Snapshot does not exist: %r' % snapshot
                sys.exit(-1)

            database_dir = snapshot + '_running'
            copytree(snapshot, database_dir)

        # set location of WebKit HTML5 databases
        if hasattr(WebView, 'SetDatabaseDirectory'):
            WebView.SetDatabaseDirectory(database_dir)

        global webkit_initialized
        webkit_initialized = True

def save_webkit_snapshot_gui(_arg):
    from gui.toolbox import GetTextFromUser
    name = GetTextFromUser('Enter a snapshot name:', 'Save database snapshot')
    if name.strip():
        save_webkit_snapshot(name)

def save_webkit_snapshot(name):
    p = path(wx.webview.WebView.GetDatabaseDirectory())
    dest = p.parent / name
    log.info('saving webkit snapshot %r to %r', name, dest)
    copytree(p, dest)

def dev_plugins_path():
    if not getattr(sys, 'DEV', False):
        return None

    try:
        p = path(__file__.decode(sys.getfilesystemencoding())).parent.parent / u'devplugins' # TODO: don't use __file__
    except Exception:
        traceback.print_exc()
        return None
    else:
        return p

def add_dev_plugins_path():
    devplugins = dev_plugins_path()
    if devplugins is not None:
        devplugins = str(devplugins)
        if devplugins not in sys.path:
            sys.path.append(devplugins)

def init_plugins():
    if not sys.opts.load_plugins:
        return []

    import plugin_manager, common

    paths = []
    try:
        PLUGINS_PATH = path(__file__.decode(sys.getfilesystemencoding())).parent / u'plugins' # TODO: don't use __file__
    except Exception:
        traceback.print_exc()
        PLUGINS_PATH = None
    else:
        paths.append(PLUGINS_PATH)

    DEV_PLUGINS_PATH = dev_plugins_path()
    if DEV_PLUGINS_PATH is not None:
        paths.append(DEV_PLUGINS_PATH)

    for pth in paths:
        pth = str(pth)
        if pth not in sys.path:
            sys.path.append(pth)

    import features
    paths.extend(features.find_feature_dirs())

    sys.path.extend(map(str, paths)) # 'paths' contains path.path objects, str(p) calls p.encode('filesys')

    plugins = []
    for pth in paths:
        try:
            if pth is not None:
                plugins.extend(plugin_manager.scan(pth))
        except Exception:
            traceback.print_exc()

    try:
        import common.protocolmeta
        common.protocolmeta.proto_update_types()
    except Exception:
        traceback.print_exc()

    return plugins

did_create_webview = False

def set_did_create_webview():
    global did_create_webview
    if not did_create_webview:
        did_create_webview = True
        import hooks, util
        hooks.notify('proxy.info_changed', util.GetProxyInfo())

def on_proxy_info_changed(proxy_info):
    import wx.webview as webview, socks

    # Tell socks module about proxy info
    socks.setdefaultproxy(**proxy_info)

    if not did_create_webview:
        # HACK: for a yet-to-be-determined reason, calling SetProxyInfo
        # before constructing a WebView breaks curl. did_create_webview
        # is set to True by the infobox construction code.
        return

    if not proxy_info:
        # empty dict means no proxy
        webview.WebView.SetProxyInfo()
        return

    # Tell WebKit (which does its own HTTP requests) about the proxy settings.
    proxy_types = {socks.PROXY_TYPE_SOCKS4: webview.Socks4,
                   socks.PROXY_TYPE_SOCKS5: webview.Socks5,
                   socks.PROXY_TYPE_HTTP:   webview.HTTP}

    proxy_type = proxy_types.get(proxy_info['proxytype'], webview.HTTP)

    webview.WebView.SetProxyInfo(
        proxy_info['addr'] or '',
        proxy_info['port'] or 0,
        proxy_type,
        proxy_info['username'] or '',
        proxy_info['password'] or '')

def SetStatusPrompt(accounts = None, initial_text = u'', **k):
    import gui.social_status_dialog as ssd
    from common import profile
    gsc = ssd.GlobalStatusController.GetInstance(profile(), accounts, initial_text, **k)
    gsc.ShowDialog()
    gsc.SetFocus()

def ExitDigsby():
    wx.GetApp().DigsbyCleanupAndQuit()

def initialize_metrics():
    import metrics
    metrics.register_hooks()

def initialize_jumplist():
    import cgui
    if not cgui.isWin7OrHigher():
        return

    try:
        from gui.native.win.jumplist import set_app_jumplist
        set_app_jumplist()
    except Exception:
        print_exc()

if __name__ == '__main__':
    raise AssertionError('run Digsby.py')

