from __future__ import with_statement
import os
import sys
import wx
import wx.py as py

from util import traceguard
from gui.toolbox import loadWindowPos, saveWindowPos
import gui.native.helpers

__all__ = ['PyCrustFrame']


if hasattr(sys, 'gettotalrefcount'):
    def get_total_refcount():
        return '-- totalrefs: %d' % sys.gettotalrefcount()
else:
    def get_total_refcount():
        return ''

class PyCrustFrame(wx.Frame):
    def __init__(self, parent = None, id_ = -1, title = 'Digsby Shell', standalone = False,
                 name = 'Digsby Shell'):
        wx.Frame.__init__(self, parent, id_)

        self.SetTitle(self.ShellTitle)

        self.Bind(wx.EVT_SHOW, self.on_show)
        self.title_timer = wx.PyTimer(lambda: self.SetTitle(self.ShellTitle))
        self.title_timer_interval = 500

        try:
            import digsbyprofile
            prefs = digsbyprofile.profile.prefs
        except ImportError:
            prefs = {}
        except AttributeError:
            prefs = {}

        py.editwindow.FACES['mono'] = prefs.get('debug.shell.font', 'Courier New')

        if prefs.get('debug.shell.minimal', True):
            crust = shell = py.shell.Shell(self)
        else:
            crust = py.crust.Crust(self, intro="Digsby Shell")
            shell = crust.shell

        wx.GetApp().shell_locals = shell.interp.locals

        import common.commandline
        shell.interp.locals.update(common.commandline.__dict__)

        self.input = shell

        # Load history from file
        if 'debug.shell.history.size' in prefs:
            maxsize = prefs['debug.shell.history.size']
            h = prefs['debug.shell.history.lines']
            h = h[:maxsize]
            prefs['debug.shell.history.lines'] = shell.history = h
        self.crust = crust
        self.Bind(wx.EVT_CLOSE, self.on_close)
        loadWindowPos(self)

        self.standalone = standalone

        with traceguard:
            from gui import skin
            self.SetFrameIcon(skin.get('AppDefaults.TaskbarIcon').Inverted)

    def FocusInput(self):
        self.input.SetFocus()

    def on_close(self, e = None):
        if self.IsShown():
            saveWindowPos(self)
        self.Show(False)

        if self.standalone:
            sys.exit()

    def on_show(self, shown):
        shown.Skip()

        if shown: self.title_timer.Start(self.title_timer_interval, False)
        else:     self.title_timer.Stop()

    if 'wxMSW' in wx.PlatformInfo:
        @property
        def ShellTitle(self):
            m = memory_info()
            ramusage = '%s' % nicebytecount(m.WorkingSetSize)
            if m.PrivateUsage:
                ramusage += '/%s' % nicebytecount(m.PrivateUsage)

            return ('Digsby Shell -- %s -- (gdi: %s, user: %s) -- pid: %s %s' %
                (ramusage,
                 count_gdi_objects(),
                 count_user_objects(),
                 os.getpid(),
                 get_total_refcount()))
    else:
        ShellTitle = 'Digsby Shell'

    def toggle_shown(self):
        if self.Visible:
            self.on_close()
        else:
            self.Show()
            if self.IsIconized():
                self.Iconize(False)
            self.Raise()

if 'wxMSW' in wx.PlatformInfo:
    from gui.native.win.process import memory_info, count_gdi_objects, count_user_objects
    from util import nicebytecount
    import gc
