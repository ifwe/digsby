""" MSIM provides a mechanism to add 'top' friends or all friends to the IM buddy list. this module provides a
    prompt to ask the user what to do. """
import wx
import gui.skin as skin
import util.callbacks as callbacks


@callbacks.callsback
def AddBuddiesPrompt(callback=None):
    dlg = PromptDialog("\n" + _("Would you like to automatically add your MySpace friends to your MySpace IM contact list?") + "\n",
                   [(_('Add Top Friends'), 'top'),
                    (_('Add All Friends'), 'all'),
                    (_('No Thanks'), 'cancel'),
                    ],
                    title=_("Add Friends"),
                   )
    dlg.SetFrameIcon(skin.get('serviceicons.msim'))
    dlg.Show(callback=callback)


class PromptDialog(wx.Dialog):

    def __init__(self, body_text, options, parent=None, id=-1, title='', pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=wx.DEFAULT_DIALOG_STYLE, name=''):

        wx.Dialog.__init__(self, parent, id, title, pos, size, style, name)
        self.construct(body_text, options)
        self.Fit()

    def construct(self, body_text, options):
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.body_text = wx.StaticText(self, -1, body_text, style=wx.ALIGN_CENTRE)
        self.Sizer.Add(self.body_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)
        button_sz = wx.BoxSizer(wx.HORIZONTAL)
        button_sz.AddStretchSpacer()
        self._buttons = {}
        ok_text, ok_value = options.pop(0)
        cancel_text, cancel_value = options.pop(-1)
        self._buttons[wx.ID_OK] = ok_value
        self._buttons[wx.ID_CANCEL] = cancel_value
        ok_button = wx.Button(self, wx.ID_OK, ok_text)
        cancel_button = wx.Button(self, wx.ID_CANCEL, cancel_text)
        button_sz.Add(ok_button, 0, wx.ALL, border=4)
        for text, value in options:
            button_id = wx.NewId()
            self._buttons[button_id] = value
            button = wx.Button(self, button_id, text)
            button_sz.Add(button, 0, wx.ALL, border=4)
        button_sz.Add(cancel_button, 0, wx.ALL, border=4)
        button_sz.AddStretchSpacer()
        self.Sizer.Add(button_sz, 0, wx.EXPAND | wx.ALL, 4)
        self.Bind(wx.EVT_BUTTON, self._on_click)

    def _on_click(self, e):
        callback, self.callback = self.callback, None
        if callback is not None:
            callback.success(self._buttons[e.Id])
        self.Hide()
        self.Destroy()

    def Show(self, callback=None):
        self.callback = callback
        return wx.Dialog.Show(self)
