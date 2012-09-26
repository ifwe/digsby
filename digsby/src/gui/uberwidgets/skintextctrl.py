import wx


#TODO: Make an UberWidget?
class SkinTextCtrl(wx.TextCtrl):
    '''
    Only used for email subject line
    Should be deprecated and replaced
    '''
    def __init__(self, parent, **k):

        self.skinkey    = k.pop('skinkey', None)
        self.skinkey_bg = k.pop('skinkey_bg', None)

        wx.TextCtrl.__init__(self, parent, **k)
        self.UpdateSkin()

    def UpdateSkin(self):
        from gui import skin
        if self.skinkey is not None:
            loc, key = self.skinkey

            font  = skin.get('%s.Fonts.%s'      % (loc, key), lambda: self.Font)
            color = skin.get('%s.FontColors.%s' % (loc, key), lambda: self.BackgroundColour)


            self.SetForegroundColour(color)

            # ignore bold/italics/underline, since this is a text control
            f = self.Font
            f.SetFaceName(font.FaceName)
            f.SetPointSize(font.PointSize)
            self.Font = f

        if self.skinkey_bg is not None:
            self.SetBackgroundColour(skin.get(self.skinkey_bg, lambda: self.BackgroundColour))
