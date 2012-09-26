import sys
import wx

import ctypes
try:
    ctypes.windll.dwmapi
except Exception:
    pass
else:
    import gui.vista

# for side effects:
import digsbysite

import util
import stdpaths
from util.primitives.funcs import Delegate
from util.primitives.mapping import Storage

def discover_digsby_root():
    '''
    Finds the digsby root directory somewhere at or above the current
    working directory. Raises an Exception if it can't be found.
    '''

    import os.path
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

def _isdigsbyroot(p):
    print >> sys.stderr, "isdigsbyroot?", p
    return (p / 'res' / 'skins' / 'default').isdir()

class TestApp(wx.App):
    def __enter__(self):
        pass
    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            # don't start MainLoop is there's an exception
            self.MainLoop()

wxMSW = 'wxMSW' in wx.PlatformInfo

def testapp(pypath = None, appname = 'Digsby', skinname = 'default', prefs = None, username = 'megazord',
            on_message = lambda message: None,
            plugins = True, logging = True):
    'A test application framework for test __main__s.'


    if wxMSW: preload_comctrls()

    import gettext, os.path

    import options
    sys.opts, _args = options.parser.parse_args()
    import logextensions

    digsbysite.COLORIZE_EXCEPTIONS = sys.opts.console_color

    # Install gui elements
    gettext.install(appname, unicode=True)

    from bootstrap import install_N_
    install_N_()

    # Create the app
    app = TestApp()
    app.SetAppName(appname)

    # initialize stdpaths
    from stdpaths import init
    init()

    if wxMSW:
        import gui.native.win.winutil as winutil
        winutil.disable_callback_filter()

    from gui import skin
    from gui.toolbox import setuplogging
    if logging:
        import logging
        setuplogging(level=logging.INFO)


    # make wxLogError go to stderr, not popup dialogs
    wx.Log.SetActiveTarget(wx.LogStderr())

    app.PreShutdown = Delegate()

    if pypath is None:
        pypath = discover_digsby_root()

    sys.path.insert(0, pypath)

    skin.set_resource_paths([
                             util.program_dir() / 'res', # Apparently this has to be first?
                             stdpaths.userdata,
                             stdpaths.config,
                             ])

    if plugins:
        from main import init_plugins
        app.plugins = init_plugins()
    else:
        app.plugins = []


    skin.skininit(os.path.join(pypath, 'res'), skinname = skinname)

    from util.threads.threadpool import ThreadPool
    ThreadPool(5)

    from prefs.prefsdata import flatten
    import syck
    from util.observe import ObservableDict


    prefs_path = os.path.join(pypath, 'res', 'defaults.yaml')

    prefs = ObservableDict(prefs) if prefs is not None else ObservableDict()
    prefs.update({'appearance.skin': skinname,
                  'appearance.variant': None,
                  'debug.shell.font': shellfont()})
    import common
    common.set_active_prefs(prefs, {})

    from util.observe import ObservableDict

    sys.modules['digsbyprofile'] = Storage()
    import digsbyprofile
    from common.notifications import default_notifications
    p = digsbyprofile.profile = Storage(name     = username,
                                    username = username,
                                    prefs    = prefs,
                                    on_message = on_message,
                                    notifications = default_notifications)



    f = file(prefs_path)
    defaults = Storage(flatten(syck.load(f)))
    f.close()
    user = ObservableDict(defaults)
    user.update(prefs)

    from prefs.prefsdata import localprefs
    import prefs
    p.defaultprefs = prefs.defaultprefs()
    p.localprefs = localprefs()

    import common
    common.setfakeprefs(user)

    def toggle_prefs(user=user, defaults=defaults):
        import prefs
        prefs.edit(user, defaults, None)

    def toggle_crust(app=app):
        if not getattr(app, 'crust', None):
            import gui.shell
            wins =  wx.GetTopLevelWindows()
            parent = wins[0] if wins else None
            app.crust = gui.shell.PyCrustFrame(None)
            if parent is not None:
                parent.crust = app.crust
            app.crust.Bind(wx.EVT_CLOSE, lambda evt: app.Exit())
        app.crust.toggle_shown()

        # keyboard focus goes to shell prompt
        if app.crust.IsShown():
            app.crust.crust.SetFocus()

    def on_key(e):
        code = e.GetKeyCode()
        if code == wx.WXK_F11:
            toggle_prefs()
        elif code == wx.WXK_F12:
            toggle_crust()
        elif code == wx.WXK_F5:
            from gui import skin
            skin.reload()
        else:
            e.Skip()

    app.Bind(wx.EVT_KEY_DOWN, on_key)
    app.toggle_crust = toggle_crust

    from main import initialize_webkit, SetStatusPrompt
    initialize_webkit()
    app.SetStatusPrompt = SetStatusPrompt

    return app

if 'wxMSW' in wx.PlatformInfo:
    def preload_comctrls():
        # preload comctrls to prevent a TrackMouseEvent crash
        # http://trac.wxwidgets.org/ticket/9922
        from ctypes import windll
        windll.comctl32.InitCommonControls()

def shellfont():
    try:
        import ctypes
        ctypes.windll.dwmapi
    except:
        font = 'Courier New'
    else:
        font = 'Consolas'

    return font

