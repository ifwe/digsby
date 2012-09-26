'''
An addon that controls the about dialog.

The about dialog is a window that can be opened from the help menu of the main
buddy list frame. The main content of the window is in HTML, displayed in a
webkit window.

When opened, or when the digsby logo is clicked, an update check is initiated.
While the check is being performed a spinner is displayed.
When it completes, and there's an update available, the update is initiated in
the background. Clicking the link will open the file transfer dialog which shows
the update progress. If there's no update available, that'll be displayed and
the user can initiate another update if they want.

This is all accomplished with some neato hook magic. I believe this is the first
GUI component of the app that qualifies as a plugin :)
'''
import wx
import sys
import os
import util
import path
import hooks
import common
import gui.browser.webkit as webkit
import rpc.jsonrpc as jsonrpc

import protocols
import peak.util.addons as addons

import gui.infobox.interfaces as gui_interfaces
import gui.infobox.providers as gui_providers

import logging
log = logging.getLogger('aboutdlg')

class AboutAddon(addons.AddOn):
    def setup(self, *a):
        self.dlg = None

    def Show(self):
        self.maybe_make_dialog()
        self.dlg.Show()
        self.dlg.js("get_update_status();")

    def maybe_make_dialog(self):
        if self.dlg is None:
            self.dlg = AboutDialog(None)

    def update_check_result(self, update_required):
        if self.dlg is not None:
            self.dlg.update_check_result(update_required)

class AboutDialog(wx.Dialog, jsonrpc.RPCClient):

    _rpc_handlers = {
                     'check_for_updates' : 'check_for_updates',
                     'get_update_status' : 'get_update_status',
                     'show_filetransfer_window': 'show_filetransfer_window',
                     }

    def __init__(self, parent, *a, **k):
        wx.Dialog.__init__(self, parent, *a, **k)
        jsonrpc.RPCClient.__init__(self)
        self.SetTitle(_("About Digsby"))
        self._update_check_rpc_id = None
        self.construct()
        self.bind_events()

    def construct(self):

        self.webview = webkit.WebKitWindow(self)
        self.webview.WebSettings.SetAllowUniversalAccessFromFileURLs(True)
        self.webview.SetSize((191, 264))
        self.refresh_content()

        self.bridge = jsonrpc.JSPythonBridge(self.webview)
        self.bridge.on_call += lambda x: self.json(x, self.webview)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.webview, 1, wx.EXPAND | wx.ALL)

        self.Fit()

    def bind_events(self):
        pass

    def refresh_content(self):
        acp = AboutContentProvider()
        self.webview.SetHTML(acp.get_html())

    def _default_rpc(self, rpc, webview, id, *a, **k):
        log.info("jscall: %r, %r, %r, %r, %r", rpc, webview, id, a, k)

    def check_for_updates(self, rpc, webview, id):
        if self._update_check_rpc_id is not None:
            return self.Derror(self.webview, id, message="checking")

        self._update_check_rpc_id = id
        log.info("Requesting update check from about dialog")
        hooks.notify('digsby.updater.check')

    def get_update_status(self, rpc, webview, id):
        for hook in hooks.Hook("digsby.updater.status"):
            res = hook()
            if res:
                self.Dsuccess(webview, id, status = res)
                break
        else:
            self.Dsuccess(webview, id, status = 'idle')

    def update_check_result(self, update_required):
        if self._update_check_rpc_id is None:
            return

        id, self._update_check_rpc_id = self._update_check_rpc_id, None

        self.Dsuccess(self.webview, id, update_required = update_required)

    def show_filetransfer_window(self, rpc, webview, id, *a):
        import gui.filetransfer as ft
        wx.CallAfter(ft.FileTransferDialog.Display)

        self.Dsuccess(webview, id)
        self.Show(False)

    def js(self, s):
        self.webview.RunScript(s)

class AboutContentProvider(gui_providers.InfoboxProviderBase):
    javascript_libs = [
                       'jquery',
                       'json',
                       'utils',
                       ]

    def get_app_context(self, ctxt_class):
        return ctxt_class(path.path(__file__).parent.parent, 'digsby_about')

    def get_context(self):
        ctxt = super(AboutContentProvider, self).get_context()
        ctxt.update(
            tag = sys.TAG,
            revision = sys.REVISION,
        )
        return ctxt

def help_menu_items(*a):
    return [(_("&About Digsby"), show_dialog)]

def get_addon():
    p = common.profile()
    if p is not None:
        return AboutAddon(p)
    else:
        return None

def show_dialog(*a):
    a = get_addon()
    if a is not None:
        a.Show()

def on_update_check_complete(update_required, *a):
    a = get_addon()
    if a is not None:
        a.update_check_result(update_required)

if __name__=='__main__':

    from tests.testapp import testapp
    a = testapp('..\\..\\', username = 'mike')

    AboutDialog(None).Show()
    a.MainLoop()
