'''

GUI for the IM window's email tab.

'''

import wx

from util.primitives.funcs import Delegate

from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.UberBar import UberBar
from gui.uberwidgets.skintextctrl import SkinTextCtrl
from gui.uberwidgets.cleartext import ClearText
from gui.textutil import default_font
from gui.validators import LengthLimit
from gui import skin
from cgui import SimplePanel

class ImWinEmailPanel(SimplePanel):
    def __init__(self, parent):
        SimplePanel.__init__(self, parent)

        self.OnEditEmail = Delegate()
        self.OnSendEmail = Delegate()


        self.gui_constructed = False

        self.UpdateSkin()

        self.construct_gui()

    def SetEmailClient(self, email_account):
        '''
        Changes the "Edit In..." button to show the name of an email client.

        If None, the button becomes disabled.
        '''


        client = email_account.client_name if email_account is not None else None

        if client is not None:
            self.send_button.Enable(True)
            self.openin.Enable(True)

            if client:
                label = _('Edit in {client}...').format(client=client)
            else:
                label = _('Edit...')

            self.openin.SetLabel(label)
        else:
            self.send_button.Enable(False)
            self.openin.Enable(False)
            self.openin.SetLabel(_('Edit...'))

    def UpdateSkin(self):

        g = skin.get
        self.buttonbarskin = g('SendBar.ToolBarSkin', None)
        self.subjectskin = g('EmailSubjectBar.ToolBarSkin',None)

        self.subjectfont = g('EmailSubjectBar.Fonts.SubjectLabel',lambda: default_font())
        self.subjectfc = g('EmailSubjectBar.FontColors.SubjectLabel', wx.BLACK)

        self.buttonbarfont = g('SendBar.Font', default_font)
        self.buttonnarfc = g('SendBar.FontColor', wx.BLACK)


        if self.gui_constructed:

            self.subject_bar.SetSkinKey(self.subjectskin)
            self.email_buttons.SetSkinKey(self.buttonbarskin)

            ept = self.email_progress_text
            ept.SetFont(self.buttonbarfont)
            ept.SetFontColor(self.buttonnarfc)

            sl = self.subject_label
            sl.SetFont(self.subjectfont)
            sl.SetFontColor(self.subjectfc)


    def construct_gui(self):
        self.Sizer = wx.BoxSizer(wx.VERTICAL)

        s = self.subject_bar = UberBar(self, skinkey = self.subjectskin)

        self.subject_input   = SkinTextCtrl(s, skinkey = ('EmailSubjectBar', 'SubjectField'),
                                               skinkey_bg = 'EmailSubjectBar.FieldBackgroundColor',
                                               validator=LengthLimit(1024),
                                               )
        self.subject_label   = ClearText(s, _('Subject:'), alignment = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.subject_label.Font = self.subjectfont
        self.subject_label.FontColor = self.subjectfc

        s.Add(self.subject_label)
        s.Add(self.subject_input,1)

        # construct email buttons panel
        email_buttons = self.email_buttons   = UberBar(self, skinkey=self.buttonbarskin)

        ept = self.email_progress_text = ClearText(email_buttons, '', alignment = wx.ALIGN_CENTER_VERTICAL)
        ept.SetFont(self.buttonbarfont)
        ept.SetFontColor(self.buttonnarfc)

        # email body text input
        self.email_input_area = wx.TextCtrl(self, style = wx.TE_MULTILINE,
                                            validator=LengthLimit(20480),
                                            )

        # "open in" and "send"
        self.openin            = UberButton(email_buttons, -1, _('Edit...'), onclick = self.OnEditEmail)
        self.send_button       = UberButton(email_buttons, -1, _('Send'),    onclick = self.OnSendClicked)

        # layout email buttons
        email_buttons.Add(ept)
        email_buttons.Add(wx.Size(1,1), 1)#StretchSpacer(1)
        email_buttons.Add(self.openin)
        email_buttons.Add(self.send_button)

        # Make sure Tab from the subject input goes to the body input.
        self.email_input_area.MoveAfterInTabOrder(self.subject_bar)

        s = self.Sizer
        s.AddMany([(self.subject_bar, 0, wx.EXPAND),
                   (self.email_input_area, 1, wx.EXPAND),
                   (self.email_buttons, 0, wx.EXPAND)])

        self.gui_constructed = True

    def OnSendClicked(self, e):
        self.OnSendEmail(e)

    def Clear(self):
        self.subject_input.Clear()
        self.email_input_area.Clear()

    def SetStatusMessage(self, msg):
        self.email_progress_text.SetLabel(msg)

    def EnableSendButton(self, enabled):
        self.send_button.Enable(enabled)

