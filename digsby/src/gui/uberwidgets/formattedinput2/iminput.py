'''
Additional logic for the input in the IM window
'''

from gui.uberwidgets.formattedinput2.fromattedinputevents import EVT_TEXT_FORMAT_CHANGED
from gui.uberwidgets.formattedinput2.fontutil import StyleToStorage
from gui.uberwidgets.spacerpanel import SpacerPanel
import wx
from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.formattedinput2.formattedinput import FormattedInput
from gui.uberwidgets.formattedinput2.formatprefsmixin import FormatPrefsMixin
from gui.uberwidgets.formattedinput2.splittereventsmixin import SplitterEventMixin
from common import prefprop



class IMInput(FormattedInput, FormatPrefsMixin, SplitterEventMixin):
    def __init__(self,
                 parent,
                 value     = '',
                 autosize = True,
                 formatOptions = None,
                 multiFormat = True,
                 showFormattingBar = True,
                 rtl = False,
                 skin = None,
                 entercallback = None,
                 validator = wx.DefaultValidator,):


        FormattedInput.__init__(self,
                                parent,
                                value = value,
                                autosize = autosize,
                                formatOptions = formatOptions,
                                multiFormat = multiFormat,
                                showFormattingBar = showFormattingBar,
                                rtl = rtl,
                                skin = skin,
                                validator = validator)

        self.LoadStyle('messaging.default_style')

        self.entercallback = entercallback


        self.tc.Bind(wx.EVT_KEY_DOWN, self.OnEnterKey)

        self.sendbutton = None
        if self.showSendButton:
            self.CreateSendButton()


    def ShowSendButton(self, show):
        sendbutton = self.sendbutton
        hasSendButton = sendbutton is not None

        if hasSendButton:
            self.spacer.Show(show)
            sendbutton.Show(show)
        elif show:
            self.CreateSendButton()

        self.Layout()

    def CreateSendButton(self):

        self.spacer = SpacerPanel(self, skinkey = 'inputspacer')
        self.inputsizer.Add(self.spacer, 0, wx.EXPAND)

        sendbutton = self.sendbutton = UberButton(self, label = _('Send'), skin='InputButton') #wx.Button(self, label = _('Send'))
        self.inputsizer.Add(sendbutton, 0, wx.EXPAND)
        sendbutton.Bind(wx.EVT_BUTTON, lambda e: self.entercallback(self))

    shiftToSend = prefprop("messaging.shift_to_send", False)
    showSendButton = prefprop("messaging.show_send_button", False)

    def OnEnterKey(self, event):
        """
            This detects key presses, runs entercallback if enter or return is pressed
            Any other key continues as normal, then refreshes the font and size info
        """
        keycode = event.KeyCode

        shiftToSend = self.shiftToSend
        hasModifiers = event.HasModifiers()
        shiftIsDown = event.Modifiers == wx.MOD_SHIFT

        if keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            # if there is a enter callback and no modifiers are down or if
            # shift should send and shift is down, call the callback
            if self.entercallback and \
                    (not (shiftToSend or hasModifiers or shiftIsDown) or \
                     (shiftToSend and shiftIsDown)):
                return self.entercallback(self)

        event.Skip()

