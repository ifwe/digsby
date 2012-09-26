import wx
import gui.uberwidgets as widgets
import gui.pref.prefcontrols as prefcontrols
import gui.pref.pg_privacy as pg_privacy
'''
 [ ] Only people on my contact list can see my status
 [ ] Only people on my contact list can send me messages

 When I'm offline, receive and store messages from:
   o Everyone
   o Only people on my contact list
   o No one
'''


class MSIMPrivacyPanel(pg_privacy.AcctPrivacyPanel):
    RB_OPTIONS = [
                  (_('Everyone'), 0),
                  (_('Only people on my contact list'), 1),
                  (_('No one'), 2),
                  ]

    def __init__(self, *a, **k):
        pg_privacy.AcctPrivacyPanel.__init__(self, *a, **k)
        self.build_panel()
        self.acct_changed()

        # HACK: makes the page layout properly. why is this necessary for this panel type but not other ones?
        wx.CallAfter(self.acct_changed)

    def acct_changed(self, *a):
        conn = self.acct.connection
        if conn is not None and conn.self_buddy is not None:
            self.status_priv_chk.Value = conn.self_buddy.ShowOnlyToList == 'True'
            priv_mode_s = conn.self_buddy.PrivacyMode
            try:
                priv_mode = int(priv_mode_s)
            except Exception:
                priv_mode = 0xA0001
            self.message_priv_chk.Value = bool(priv_mode & 1)
            offline_pref = conn.self_buddy.OfflineMessageMode
            try:
                offline_pref = int(offline_pref)
            except Exception:
                offline_pref = 0
            self.opts_rbs[offline_pref].Value = True
        pg_privacy.AcctPrivacyPanel.acct_changed(self)

    def build_panel(self):
        pg_privacy.AcctPrivacyPanel.build_panel(self)

        # ## Online Components

        sz = prefcontrols.VSizer()
        status_priv_chk = wx.CheckBox(self, -1, _('Only people on my contact list can see my status'))
        status_priv_chk.Bind(wx.EVT_CHECKBOX, self.status_priv_changed)
        self.status_priv_chk = status_priv_chk
        message_priv_chk = wx.CheckBox(self, -1, _('Only people on my contact list can send me messages'))
        message_priv_chk.Bind(wx.EVT_CHECKBOX, self.message_priv_changed)
        self.message_priv_chk = message_priv_chk
        self.opts_rbs = opts_rbs = []
        offline_radios = widgets.PrefPanel.PrefPanel(self,
                          widgets.PrefPanel.PrefCollection(
                                         wx.StaticText(self, -1, _('When I\'m offline, receive and store messages from:')),
                                         layout=prefcontrols.VSizer(),
                                         itemoptions=(0, wx.BOTTOM, 6),
                                         *pg_privacy.CheckVList(self, opts_rbs, self.RB_OPTIONS,
                                                                self.offline_changed)),

                          _('Offline Messages'))

        sz.Add(
               widgets.PrefPanel.PrefPanel(self,
                widgets.PrefPanel.PrefCollection(status_priv_chk,
                                                 message_priv_chk,
                                                 itemoptions=(0, wx.BOTTOM, 6),
                                                 layout=prefcontrols.VSizer()),
                _('Privacy')),
                0, wx.EXPAND | wx.ALL, 3
               )

        sz.Add(offline_radios, 0, wx.EXPAND | wx.ALL, 3)
        self.online_components = sz

    def status_priv_changed(self, e):
        conn = self.acct.connection
        if conn is None:
            return
        conn.edit_privacy_list(presence_vis=int(e.Checked))
        conn.set_userpref(ShowOnlyToList=str(bool(e.Checked)))

    def message_priv_changed(self, e):
        conn = self.acct.connection
        if conn is None:
            return
        conn.edit_privacy_list(contact_vis=int(e.Checked))
        conn.set_userpref(PrivacyMode=str(0xA0000 | int(e.Checked)))

    def offline_changed(self, who_can_send):
        conn = self.acct.connection
        if conn is None:
            return
        conn.set_userpref(OfflineMessageMode=str(who_can_send))
