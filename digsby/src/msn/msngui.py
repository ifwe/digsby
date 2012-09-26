import util
import util.callbacks as callbacks
import wx
import gui.toolbox as toolbox
import gui.skin as skin

import logging
log = logging.getLogger("msn.gui")

class MSNGroupInviteDialog(toolbox.SimpleMessageDialog):

    def __init__(self, circle, inviter):
        icon = skin.get('serviceicons.msn', None)
        super(MSNGroupInviteDialog, self).__init__(wx.GetApp().TopWindow,
                                                   _("Group Invite"),
                                                   message = self.get_message(circle.NickName,
                                                                              inviter.account,
                                                                              inviter.invite_message),
                                                   icon = icon,
                                                   ok_caption = _('Yes'),
                                                   cancel_caption = _('No'))

    def get_message(self, circle_name, inviter_email, invite_message):
        if invite_message:
            invite_segment = '\n' + _('{inviter_email} says: "{invite_message}"').format(inviter_email = inviter_email, invite_message = invite_message)
        else:
            invite_segment = u""
        return _('{inviter_email} has invited you to join the group {circle_name}.{invite_segment}\nWould you like to join?').format(inviter_email = inviter_email, circle_name = circle_name, invite_segment = invite_segment)

class MSNCreateCircleDialog(wx.TextEntryDialog, toolbox.NonModalDialogMixin):
    def __init__(self):
        icon = skin.get('serviceicons.msn', None)
        toolbox.NonModalDialogMixin.__init__(self)
        wx.TextEntryDialog.__init__(self, wx.GetApp().TopWindow,
                                    caption = _('Create Group Chat'),
                                    message = _("Please enter a name for your group chat:"),
                                    style = wx.OK | wx.CANCEL | wx.CENTRE)

        self.icon = icon
        if icon is not None:
            self.SetFrameIcon(self.icon)

    def on_button(self, e):
        ok = e.Id == wx.ID_OK
        self.Hide()
        cb, self.cb = self.cb, None
        txt = self.FindWindowByName('text')
        if cb is not None:
            with util.traceguard:
                cb(ok, txt.Value)

        wx.CallAfter(self.Destroy)

def on_circle_invite(circle, inviter, cb):
    @wx.CallAfter
    def make_and_show_dialog():
        dlg = MSNGroupInviteDialog(circle, inviter)
        dlg.ShowWithCallback(cb)

@callbacks.callsback
def on_circle_create_prompt(callback = None):
    def cb(result, text):
        if result and text:
            callback.success(text)
        else:
            callback.error()

    @wx.CallAfter
    def make_and_show_dialog():
        dlg = MSNCreateCircleDialog()
        dlg.ShowWithCallback(cb)
