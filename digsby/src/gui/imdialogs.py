import wx
import wx.lib.sized_controls as sc

from gui.uberwidgets.UberCombo import UberCombo
from gui.uberwidgets.simplemenu import SimpleMenuItem
from gui.imwin import begin_conversation

from gui.toolbox import persist_window_pos
from gui.validators import LengthLimit

from common import profile
from util.primitives.structures import oset

def ShowNewIMDialog():
    NewIMDialog.MakeOrShow()

class NewIMDialog(sc.SizedDialog):
    def __init__(self):
        sc.SizedDialog.__init__(self, None, -1, _('New IM'),
                           style = wx.DEFAULT_DIALOG_STYLE | wx.FRAME_FLOAT_ON_PARENT)

        self.Name = 'New IM Dialog'

        p = self.GetContentsPane()
        p.SetSizerType("form")

        R_CENTER= dict(halign='right', valign='center')

        Text = lambda t: wx.StaticText(p, -1, t)
        Text(_('To')).SetSizerProps(**R_CENTER)

        toctrl = self.toctrl = wx.TextCtrl(p,style = wx.TE_PROCESS_ENTER, validator=LengthLimit(255))
        toctrl.Bind(wx.EVT_KEY_DOWN,self.OnKeyDown)
        toctrl.SetSizerProps(expand=True)

        Text(_('From')).SetSizerProps(**R_CENTER)
        fromcombo = self.fromcombo = UberCombo(p, None, skinkey='AppDefaults.PrefCombo')
        fromcombo.SetItems(self.UpdateAccountItems(),0)
        fromcombo.SetSizerProps(expand=True)

        self.SetButtonSizer(self.CreateButtonSizer(wx.OK | wx.CANCEL))
        sendbutton = self.sendbutton = self.FindWindowById(wx.ID_OK, self)
        sendbutton.SetLabel(_('IM'))
        sendbutton.Enable(False)
        sendbutton.Bind(wx.EVT_BUTTON,self.OnAccept)

        profile.account_manager.connected_accounts.add_observer(self.WhenOnlineAcctsChange)

        Bind = self.Bind
        Bind(wx.EVT_CLOSE,self.OnClose)
        Bind(wx.EVT_KEY_DOWN,self.OnKeyDown)

        persist_window_pos(self, defaultPos = 'center', position_only = True)

        self.Fit()
        self.SetSize((300, self.BestSize.height))


    def WhenOnlineAcctsChange(self,*a):
        fromcombo = self.fromcombo

        fromcombo.SetItems(self.UpdateAccountItems())

        if not fromcombo.Value in fromcombo:
            if len(fromcombo):
                fromcombo.SetSelection(0)
            else:
                fromcombo.Value = _('No Connections')

        self.UpdateButtonState()

    def UpdateAccountItems(self):

        if not hasattr(self,'acctitems'):
            self.acctitems = oset()

        acctitems = self.acctitems

        accounts = oset(profile.account_manager.connected_accounts)
        accts    = set(item.id for item in acctitems)

        newaccts = accounts - accts
        oldaccts = accts - accounts

        for item in set(acctitems):
            if item.id in oldaccts:
                acctitems.remove(item)

        for account in newaccts:
            if account.allow_contact_add:
                acctitems.add(SimpleMenuItem([account.serviceicon.Resized(16),account.username],id = account))


        return list(acctitems)

    def OnKeyDown(self, event):
        ctrl = event.ControlDown()
        key  = event.GetKeyCode()

        if ctrl and key==wx.WXK_DOWN:
            self.fromcombo.SelectNextItem(True)
        elif ctrl and key==wx.WXK_UP:
            self.fromcombo.SelectPrevItem(True)
        elif key==wx.WXK_ESCAPE:
            self.Close()
        elif key==wx.WXK_RETURN and (bool(self.toctrl.Value) and len(self.fromcombo)):
            self.OnAccept()
        else:
            event.Skip()

        self.UpdateButtonState()

    def UpdateButtonState(self):
        wx.CallAfter(lambda: self.sendbutton.Enable(bool(self.toctrl.Value) and len(self.fromcombo)))

    def OnAccept(self, event = None):
        self.Hide()

        proto = self.fromcombo.Value.id.connection
        begin_conversation(proto.get_buddy(self.toctrl.Value), forceproto = True)

        self.Close()


    def OnClose(self,event):
        profile.account_manager.connected_accounts.remove_observer(self.WhenOnlineAcctsChange)

        self.Show(False)

        type(self).new_im_instance = None

        self.Destroy()


    @classmethod
    def MakeOrShow(cls):

        if not hasattr(cls,'new_im_instance'):
            cls.new_im_instance = None

        if cls.new_im_instance:
            cls.new_im_instance.Show(True)
        else:
            cls.new_im_instance = NewIMDialog()
            cls.new_im_instance.Show(True)

        cls.new_im_instance.ReallyRaise()
