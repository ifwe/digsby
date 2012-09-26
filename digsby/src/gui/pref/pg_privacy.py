import wx
from gui.pref.prefcontrols import *

from gui.uberwidgets.PrefPanel import PrefCollection, PrefPanel

from util.primitives.error_handling import try_this
from util.primitives.funcs import get
from common import netcall, silence_notifications

from logging import getLogger; log = getLogger('pg_privacy')

wxMac = 'wxMac' in wx.PlatformInfo

def panel(panel, sizer, newgroup, exithooks):

    gprivops = PrefPanel(panel,
                         PrefCollection(Check('send_typing_notifications',  _('&Let others know that I am typing')),
                                        Check('www_auto_signin', _('&Automatically sign me into websites (e.g., Yahoo! Mail)')),
                                        layout = VSizer(),
                                        itemoptions = (0,BOTTOM,6)),
                         _('Global Privacy Options'),
                         prefix = 'privacy')


    privacy_panel = PrefPanel(panel)
    PageFactory(privacy_panel, exithooks)
    sizer.Add(gprivops, 0, EXPAND|BOTTOM,6)
    sizer.Add(privacy_panel, 1, EXPAND)

    return panel

def account_menuitem(a):
    return [a.statusicon.ResizedSmaller(16), a.serviceicon.Resized(16), a.name]

def account_stringitem(a):
    return '%s (%s)' % (a.name, a.protocol_info().name + (', connected' if a.connected else ''))

from config import platformName
def PageFactory(privacy_panel, exithooks):
    _panels = {}

    def update_panels():
        for account in profile.account_manager.accounts:
            if account not in _panels:
                try:
                    panel = _panels[account] = GetAccountPanelType(account)(account, exithooks, privacy_panel)
                except KeyError,e:
                    print 'Panel not defined for protocol %s,%r' % (account.protocol,e)
                    return

                if hasattr(panel, 'on_close'):
                    exithooks.append(panel.on_close)

    def accts_changed(*a, **k):
        wx.CallAfter(_gui_accts_changed)

    def _gui_accts_changed():
        update_panels()

        accounts = profile.account_manager.accounts
        if platformName != 'mac':
            items = [(_panels[a], account_menuitem(a)) for a in accounts]
            privacy_panel.SetContents(items)
            privacy_panel.combo.menu.Refresh()
        else:
            # TODO: wxMac -- images in wxComboBox?
            items = [(_panels[a], account_stringitem(a)) for a in accounts]
            privacy_panel.SetContents(items)

    _gui_accts_changed()
    obs_link = profile.account_manager.accounts.add_observer(accts_changed, obj = privacy_panel)

    def acct_changed(account, *a, **k):
        wx.CallAfter(_gui_acct_changed, account)

    def _gui_acct_changed(account):
        i = profile.account_manager.accounts.index(account)
        item = privacy_panel.MenuItems[i]
        item.content = account_menuitem(account)

        if wxMac:
            privacy_panel.combo.SetString(i, account_stringitem(account))
        else:
            privacy_panel.combo.menu.Refresh()
            privacy_panel.combo.Refresh()

    for account in profile.account_manager.accounts:
        account.add_observer(acct_changed, 'state', obj = privacy_panel)

    def remove_observers():
        accts = profile.account_manager.accounts
        accts.remove_observer(accts_changed)

        for account in accts:
            account.remove_observer(acct_changed,'state')

    exithooks.append(remove_observers)

    accs = profile.account_manager.accounts
    occs = profile.account_manager.connected_im_accounts

    if len(occs):
        privacy_panel.combo.SetSelection(accs.index(occs[0]))
        privacy_panel.ChangeShownContent()

def label_and_button(parent, text_label, button_lbl, button_cb):
    sizer = HSizer()
    label = wx.StaticText(parent, -1, text_label)
    button = wx.Button(parent, -1, label=button_lbl, style=wx.BU_EXACTFIT)
    button.Bind(wx.EVT_BUTTON, button_cb)

    sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
    sizer.AddSpacer(24)
    sizer.AddStretchSpacer()
    sizer.Add(button, 0, wx.ALIGN_RIGHT)

    return sizer

class AcctPrivacyPanel(wx.Panel):
    from common import profile
    def __init__(self, acct, on_exit, *a, **k):
        self.inited = False

        wx.Panel.__init__(self, *a, **k)
        self.acct = acct
        self.on_exit = on_exit

        self.on_exit += self.on_close

        self.acct.add_observer(self.acct_changed, 'state')
        self.acct_will_be_saved = False

        self.editors = {}

    def acct_changed(self, *a, **k):
        #TODO: plz unregister observers.
        if self:
            self.show_options(self.acct.is_connected)

    def build_panel(self):
        sz = VSizer()

        ### Offline components
        msg = SText(self, _("You must be signed in to modify privacy settings."))
        btn = wx.Button(self, -1, _('Sign in with "%s"') % self.acct.name, style=wx.BU_EXACTFIT)
        if platformName == 'mac':
            btn.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)
        btn.Bind(wx.EVT_BUTTON, lambda e: (btn.Enable(False), self.acct.connect()))
        self._btn = btn

        sz.Add(msg, 0, wx.EXPAND)
        sz.Add(btn, 0, wx.ALL, 4)
        sz.AddStretchSpacer()

        sz.Enable(False)
        sz.ShowItems(False)

        self.offline_components = sz

    def show_options(self, online):
        old = self.Sizer
        new = self.online_components if online else self.offline_components

        self.Freeze()

        if not new: return
        self.SetSizer(new, False)

        if old is not None and old is not new:
            old.Enable(False)
            old.ShowItems(False)

        self.Sizer.Enable(True)
        self.Sizer.ShowItems(True)

        self._btn.Enable(not (self.acct.connection and self.acct.connection.state))

        self.Thaw()

#        self.Fit()
        self.Layout()


    def mark_for_save(self):
        if not self.acct_will_be_saved:
            self.acct_will_be_saved = True
            self.on_exit += self.acct.update

    def on_close(self):
        for cls, ed in self.editors.items():
            self.kill_editor(ed)
            self.editors.pop(cls)

        self.acct.remove_observer(self.acct_changed, 'state')

    def editor_closed(self,cls,ed,e):
        self.kill_editor(ed)
        self.editors.pop(cls, None)

    def kill_editor(self, ed):
        ed.on_close()
        ed.Hide()
        ed.Destroy()

    def show_editor(self, cls):

        if cls not in self.editors:
            ed = self.editors[cls] = cls(self.acct.connection, self)
            ed.Bind(wx.EVT_CLOSE, lambda e: self.editor_closed(cls, ed, e))

        ed = self.editors[cls]

        if not ed.IsShown():
            ed.Show()

        ed.SetFocus()

class AcctListEditor(AutoCompleteListEditor):
    def __init__(self, protocol, *a, **k):
        self.protocol = protocol
        AutoCompleteListEditor.__init__(self, *a, **k)
        if 'wxMac' in wx.PlatformInfo:
            self.SetSize((400, 300))
            self.CenterOnParent()
        self.Title = self.make_title()

        from gui import skin
        ico = wx.IconFromBitmap(skin.get('serviceicons.%s' % self.protocol.service))
        self.SetIcon(ico)

        self.list.OnDelete = self.remove_item

    def make_title(self):
        return _('{title} ({username})').format(title = self.title, username = self.protocol.username)

    def __contains__(self, thing):
        if thing in self.protocol.buddies:
            buddy = self.protocol.buddies[thing]
        else:
            buddy = None

        parent = AutoCompleteListEditor.__contains__

        if parent(self, thing):
            return True
        elif buddy is not None and parent(self, buddy):
            return True

        return False

def CheckGridList(parent, check_list, choices, acct, checkcallback, buttoncallback):
    perm_pct = []

    for i,(_string, args) in enumerate(choices):
        style = 0 if i else wx.RB_GROUP
        rb = wx.RadioButton(parent, -1, label=_string, style=style)

        rb.Bind(wx.EVT_RADIOBUTTON, lambda e,a=args: checkcallback(a))

        check_list.append(rb)
        perm_pct.append((rb, (i, 0), (1, 1), ALIGN_CENTER_VERTICAL))

        if 'list' in args:
            try:
                cls = globals()['%s%sListEditor' % (acct.protocol.upper(), args[-1])]
            except KeyError:
                cls = globals()['%s%sListEditor' % (acct.protocol.capitalize(), args[-1])]

            btn = wx.Button(parent, -1, _('Edit'), style=wx.BU_EXACTFIT)
            if platformName == 'mac':
                btn.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)
            btn.Bind(wx.EVT_BUTTON, lambda e, _cls=cls: buttoncallback(_cls))

            perm_pct.append((btn,(i,1),(1,1),ALIGN_CENTER_VERTICAL))

    return perm_pct

def CheckVList(parent, check_list, choices, checkcallback):
    perm_pct = []

    for i,(_string, args) in enumerate(choices):
        style = 0 if i else wx.RB_GROUP
        rb = wx.RadioButton(parent, -1, label=_string, style=style)

        rb.Bind(wx.EVT_RADIOBUTTON, lambda e,a=args: checkcallback(a))
        rb._cb_args = args

        check_list.append(rb)
        perm_pct.append(rb)

    return perm_pct

class AIMPrivacyPanel(AcctPrivacyPanel):
    perm_choices = [
                    (_('Allow all users to contact me'),       (True,   'all')),
                    (_('Allow only users on my contact list'), (True,   'contacts')),
                    (_("Allow only users on 'Allow List'"),    (True,   'list', 'Allow')),
                    (_('Block all users'),                     (False,  'all')),
                    (_("Block only users on 'Block List'"),    (False,  'list', 'Block'))]

    opts_choices = [(_('Only my screen name'),                  (True,          )),
                    (_('Only that I have an account'),          (False,         )),
                    (_('Nothing about me'),                     (None,          ))]

    def __init__(self, *a, **k):
        AcctPrivacyPanel.__init__(self, *a, **k)

        self.build_panel()
        self._got_search = False
        self.acct_changed()


    def build_panel(self):
        AcctPrivacyPanel.build_panel(self)
        ### Online components

        acct = self.acct

        self.perm_rbs = perm_rbs = []


        def rb_callback(a):
            acct.connection.set_privacy(*a)
            silence_notifications(acct.connection)


        perms = PrefPanel(self,
                          PrefCollection(layout = wx.GridBagSizer(hgap = 6),
                                         *CheckGridList(self, perm_rbs,self.perm_choices,acct, rb_callback,self.show_editor)),
                          _('Permissions'))


        self.opts_rbs = opts_rbs = []

        opts = PrefPanel(self,
                          PrefCollection(
                                         wx.StaticText(self,-1,_('Allow users who know my email address to find:')),
                                         layout = VSizer(),
                                         itemoptions=(0,BOTTOM,6),
                                         *CheckVList(self, opts_rbs, self.opts_choices, lambda a: acct.connection.set_search_response(*a))),

                          _('Options'))

        sz = VSizer()
        sz.Add(perms,0,EXPAND)
        sz.Add(opts,0,EXPAND)
        sz.ShowItems(False)

        self.online_components = sz

    def set_radio(self, val):
        '''
        value coming in:
        disclosure: True = full
                    False= limited
                    None = none
        '''
        log.info('Got value for radio button: %r', val)
        for rb in self.opts_rbs:
            if rb._cb_args == (val,):
                rb.SetValue(True)

        self._got_search = True

    def acct_changed(self,*a, **k):
        #TODO: plz unregister me
        if not self: return

        try:
            val = ord(self.acct.connection.ssimanager.get_privacy_ssi().tlvs[0xca])
        except:
            try:
                val = self.acct.connection.ssimanager.get_privacy_ssi().tlvs[0xca].value
            except:
                val = -1

        # magic avert your eyes
        val = {-1: 0, 0: 0, 1: 0, 2: 3, 3: 2, 4: 4, 5: 1,}[val]
        self.perm_rbs[val].SetValue(True)

        conn = self.acct.connection

        if conn and conn.connected and not self._got_search:

            if conn._search_disclosure is not sentinel:
                self.set_radio(conn._search_disclosure)

            conn.get_search_response(success=lambda a: wx.CallAfter(self.set_radio,a))

        elif not conn or not conn.connected:
            self._got_search = False


        AcctPrivacyPanel.acct_changed(self, *a, **k)

_lowerstrip = lambda s: s.lower().replace(' ','')
class AIMListEditor(AcctListEditor):

    def validate(self, _str):
        return bool(_str)

    def get_matches(self, _str):
        _str = _lowerstrip(_str)
        return filter(lambda s: _lowerstrip(s).startswith(_str),
                      (x.name for x in self.protocol.buddies.values() if x not in self))

    def get_autovalues(self):
        return sorted((x.name for x in self.protocol.buddies.values() if x.name not in self), key=lambda s: _lowerstrip(s))

class AIMBlockListEditor(AIMListEditor):
    title = _('Block List')

    def get_values(self):
        return list(self.protocol.block_list)

#        return sorted(set(self.protocol.buddies[s.name]
#                          for s in self.protocol.ssimanager.find(type=3)), key=lambda x: _lowerstrip(x.name))

    def add_item(self, _str):
        _str = _str.encode('utf-8')
        b = self.protocol.buddies[_str]

        if b.name in self:
            return

        b.block(True)

        AIMListEditor.add_item(self,b.name)

    def remove_item(self, _str):
        b = self.protocol.buddies[_str]

        if b.name not in self:
            return

        b.block(False)


        AIMListEditor.remove_item(self, b.name)

class AIMAllowListEditor(AIMListEditor):
    title = 'Allow List'
    def get_values(self):
        return sorted(set(self.protocol.buddies[s.name].name
                          for s in self.protocol.ssimanager.find(type=2)), key=lambda x:_lowerstrip(x))

    def add_item(self, _str):
        _str = _str.encode('utf-8')
        b = self.protocol.buddies[_str]

        if b.name in self:
            return

        b.permit(True)

        AIMListEditor.add_item(self,b.name)

    def remove_item(self, _str):
        b = self.protocol.buddies[_str]

        if b.name not in self:
            return

        b.permit(False)

        AIMListEditor.remove_item(self,b.name)

class ICQBlockListEditor(AIMListEditor):
#class ICQInvisibleListEditor(AIMListEditor):
    title = _('Block List')
#    title = 'Invisible List'

    def get_values(self):
        return list(self.protocol.ignore_list)

    def add_item(self, _str):
        buddy = self.protocol.buddies[_str.encode('utf-8')]

        if _str in self or buddy in self:
            return

        self.protocol.block(buddy, success=lambda *a, **k:AIMListEditor.add_item(self,_str))

    def remove_item(self, _str):

        buddy = self.protocol.buddies[_str.encode('utf-8')]

        if _str not in self and buddy not in self:
            return

        self.protocol.block(buddy, False, success=lambda *a, **k:AIMListEditor.remove_item(self, _str))

class ICQVisibleListEditor(AIMAllowListEditor):
    title = _('Visible List')

class ICQInvisibleListEditor(AIMBlockListEditor):
#class ICQBlockListEditor(AIMBlockListEditor):
    title = _('Invisible List')
#    title = 'Block List'

    def add_item(self, _str):
        buddy = self.protocol.buddies[_str.encode('utf-8')]

        if _str in self or buddy in self:
            return

        self.protocol.ignore(buddy, success=lambda *a, **k:AIMListEditor.add_item(self,_str))

    def remove_item(self, _str):
        b = self.protocol.buddies[_str.encode('utf8')]

        if _str not in self and b not in self:
            return

        self.protocol.unignore(b, success=lambda *a, **k:AIMListEditor.remove_item(self, _str))

class ICQPrivacyPanel(AcctPrivacyPanel):
    perm_choices = [(_('Allow all users to contact me'), 0, (False,)),
                    (_('Allow only users on my contact list'), 1, (True,)),
                    ]

    def __init__(self, *a, **k):
        AcctPrivacyPanel.__init__(self, *a, **k)
        self.build_panel()
        self.acct_changed()

    def build_panel(self):
        AcctPrivacyPanel.build_panel(self)

        block_unknowns = wx.CheckBox(self, -1, label=_('Allow only users on my buddy list to contact me'))
        req_auth = wx.CheckBox(self, -1,       label=_('Require authorization before users can add me to their contact list'))
        block_urls = wx.CheckBox(self, -1,     label=_('Block authorization requests with URLs in them'))
        web_status = wx.CheckBox(self, -1,     label=_('Allow others to view my online status from the web'))

        req_auth.Bind(wx.EVT_CHECKBOX, self.auth_changed)
        block_urls.Bind(wx.EVT_CHECKBOX, self.block_urls_changed)
        web_status.Bind(wx.EVT_CHECKBOX, self.webaware_changed)
        block_unknowns.Bind(wx.EVT_CHECKBOX, self.block_changed)

        lists = []

        for labelclass in ((_('Block List'), ICQBlockListEditor), (_('Visible List'), ICQVisibleListEditor), (_('Invisible List'), ICQInvisibleListEditor)):
            lists.append(Label(labelclass[0]))
            lists.append(Button(_('Edit'),lambda b, cls=labelclass[1]: self.show_editor(cls)))

        perms = PrefPanel(self,
                          PrefCollection(block_unknowns,
                                         req_auth,
                                         block_urls,
                                         web_status,
                                         PrefCollection(layout = wx.GridSizer(cols = 2, hgap = 6),
                                                        itemoptions = (0,BOTTOM|ALIGN_CENTER_VERTICAL,3),
                                                        *lists),
                                         layout = VSizer(),
                                         itemoptions = (0,BOTTOM|ALIGN_CENTER_VERTICAL,6)),
                          _('Permissions'))



        self._web_status = web_status
        self._req_auth = req_auth
        self._block_urls = block_urls
        self._block_unknowns = block_unknowns


        sz = VSizer()
        sz.Add(perms, 0, wx.EXPAND|wx.ALL)
        sz.Enable(False)
        sz.ShowItems(False)

        self.online_components = sz
        self.get_check_values()

    def webaware_changed(self, e):
        v = self._web_status.Value
        self.acct.webaware = v

        conn = self.acct.connection
        if conn is not None:
            conn.set_webaware(v)
            silence_notifications(conn)
        self.mark_for_save()

    def auth_changed(self, e):
        v = self._req_auth.Value
        self.acct.auth_required = v

        conn = self.acct.connection

        if conn is not None:
            conn.set_auth_required(v)
            silence_notifications(conn)

        self.mark_for_save()

    def acct_changed(self, *a, **k):
        if not self: return
        self.get_check_values()
        AcctPrivacyPanel.acct_changed(self, *a, **k)

    def block_urls_changed(self, e):
        self.acct.block_url_requests = bool(self._block_urls.Value)
        if self.acct.connection is not None:
            self.acct.connection.block_url_requests = self.acct.block_url_requests
        self.mark_for_save()

    def block_changed(self,e ):
        a = self.acct
        a.block_unknowns = bool(self._block_unknowns.Value)

        if a.connection is not None:
            a.connection.block_unknowns = a.block_unknowns
            silence_notifications(a.connection)
        self.mark_for_save()

    def get_check_values(self):
        #self._web_status.Value = try_this(lambda: self.acct.connection.webaware, False)
        self._web_status.Value = self.acct.webaware
        self._req_auth.Value = self.acct.auth_required
        self._block_unknowns.Value = self.acct.block_unknowns
        self._block_urls.Value = self.acct.block_url_requests

#        if c is not None:
#            c.get_icq_privacy(success=lambda x,y:(req_auth.SetValue(x),
#                                                  web_status.SetValue(y)))


class MSNListEditor(AcctListEditor):

    def get_matches(self, _str):
        return [b[0] for b in filter(lambda s: s[0].startswith(_str) or s[1].startswith(_str),
                                     ((x.name, x.friendly_name or '')
                                      for x in self.protocol.buddies.values()))]

    def get_autovalues(self):
        return sorted(x.name for x in self.protocol.buddies.values() if x not in self)

    def validate(self, _str):
        import util
        return util.is_email(_str)

class MSNBlockListEditor(MSNListEditor):
    title = _('Block List')
    def get_values(self):
        return sorted(x.name for x in self.protocol.block_list)

    def add_item(self, _str):
        netcall(lambda: self.protocol.add_to_block
                (_str, success=lambda *a: wx.CallAfter
                 (lambda: MSNListEditor.add_item(self,_str))))

    def remove_item(self, _str):
        netcall(lambda: self.protocol.rem_from_block
                (_str, success=lambda *a: (self.protocol.add_to_allow(_str), wx.CallAfter
                 (lambda: MSNListEditor.remove_item(self,_str)))))

class MSNAllowListEditor(MSNListEditor):
    title = _('Allow List')
    def get_values(self):
        return sorted(x.name for x in self.protocol.allow_list)

    def add_item(self, _str):
        netcall(lambda: self.protocol.add_to_allow
                (_str, success=lambda *a, **k: wx.CallAfter
                 (lambda: MSNListEditor.add_item(self,_str))))

    def remove_item(self, _str):
        netcall(lambda: self.protocol.rem_from_allow
                (_str, success=lambda *a, **k: wx.CallAfter
                 (lambda: MSNListEditor.remove_item(self,_str))))

class MSNPrivacyPanel(AcctPrivacyPanel):
    perm_choices = [
                    (_('Allow unknown users to contact me'), 0, ()),
                    (_("Allow only users on 'Allow List'"), 1, ()),
                    (_("Block only users on 'Block List'"), 2, ()),
                    ]

    def __init__(self, *a, **k):
        AcctPrivacyPanel.__init__(self, *a, **k)

#        conn = get(self.acct, 'connection', None)
#        if conn is not None:
#            conn.self_buddy.add_observer(self.privacy_changed,'allow_unknown_contacts')
#            self.observing_privacy = True
#        else:
#            self.observing_privacy = False

        self.observing_privacy = False

        self.build_panel()
        #self.bind_evts()

        self.acct_changed()


#    def bind_evts(self):
#        self.options.Bind(wx.EVT_RADIOBOX, self.opts_changed)
#
#    def opts_changed(self, e):
#        print e.GetString()

    def build_panel(self):
        AcctPrivacyPanel.build_panel(self)
        ### Online components

#        p_box = wx.StaticBox(self,-1, 'Permissions')
#        perm_sz = MakeEnabledSizer(wx.StaticBoxSizer)(p_box,wx.VERTICAL)

        check = wx.CheckBox(self, 1, label=_("Allow unknown users to contact me"))
        check.Bind(wx.EVT_CHECKBOX, self.chk_changed)

        self.check = check

        perms = PrefPanel(self,
                          PrefCollection(check,
                                         PrefCollection(Label(_('Allow List')),
                                                        Button(_('Edit'),lambda *a : self.show_editor(MSNAllowListEditor)),
                                                        Label(_('Block List')),
                                                        Button(_('Edit'),lambda *a : self.show_editor(MSNBlockListEditor)),

                                                        layout = wx.GridSizer(cols=2, hgap=6),
                                                        itemoptions = (0, ALIGN_CENTER_VERTICAL|BOTTOM, 6)),

                                         layout = VSizer(),
                                         itemoptions = (0,BOTTOM,6)),
                          _('Permissions'))


        sz = VSizer()
        sz.Add(perms, 0, wx.EXPAND | wx.ALL, 3)
        sz.ShowItems(False)

        self.online_components = sz
        self.mobile_changed()

        #perm_sz.Add(unknown)

    ### Options removed per ticket 1534

#        o_box = wx.StaticBox(self, -1, 'Options')
#        opts_sz = MakeEnabledSizer(wx.StaticBoxSizer)(o_box, wx.VERTICAL)
#        add_alert = wx.CheckBox(self, -1, 'Alert me when other people add me to their contact list')
#
#        from msn import protocol as msnp
#        mob_link_cfg = wx.HyperlinkCtrl(self, -1, 'Click here to configure mobile settings',
#                                        msnp.mobile_edit_url)
#        mob_link_set = wx.HyperlinkCtrl(self, -1, 'Mobile settings',
#                                        msnp.mobile_enable_url)
#
#        mob_allow_chk = wx.CheckBox(self, -1, 'Allow my contacts to message my mobile device (')
#        mob_allow_par = wx.StaticText(self, -1, ')')
#
#        self.mob_sz = mob_sz = {}
#        mob_sz[False] = offsz = HSizer()
#        mob_sz[True] = onsz = HSizer()
#
#        #offsz.AddSpacer(20)
#        offsz.Add(mob_link_cfg)
#        onsz.AddMany([mob_allow_chk, mob_link_set, mob_allow_par])
#
#        opts_sz.AddMany([add_alert, offsz, onsz])
#
#        add_alert.Bind(wx.EVT_CHECKBOX, self.add_checked)
#        mob_allow_chk.Bind(wx.EVT_CHECKBOX, self.mob_checked)


    def add_checked(self, e):
        val = e.EventObject.Value
        self.acct.connection.send_gtc('A' if val else 'N')

    def mob_checked(self, e):
        val = e.EventObject.Value
        self.acct.connection.send_prp('MOB', 'Y' if val else 'N')

    def chk_changed(self, e):
        c = self.acct.connection
        c.set_blist_privacy(allow_unknowns=bool(self.check.Value))
        silence_notifications(c)

    def privacy_changed(self, src, attr, old, new):
        self.check.Value = new

    def acct_changed(self, *a, **k):
        if wx.IsDestroyed(self):
            return log.warning('pg_privacy is getting notified but is destroyed. FIX ME')

        try:    val = int(self.acct.connection.allow_unknown_contacts)
        except: val = 0

        self.check.SetValue(val)
        AcctPrivacyPanel.acct_changed(self, *a, **k)

        conn = get(self.acct, 'connection',None)
        if self.observing_privacy and not conn:
            self.observing_privacy = False

        elif not self.observing_privacy and conn:
            conn.add_observer(self.privacy_changed,'allow_unknown_contacts')
            self.observing_privacy = True
        else:
            assert bool(self.observing_privacy) == bool(conn), (conn, self.observing_privacy)

    def mobile_changed(self, *args):

        # Returning from this method early as it is no longer used,
        # but might come back in the future
        # see ticket #1534
        return


        if not self:
            return log.critical('mobile_changed is an unregistered observer!')

        val = try_this(lambda: self.acct.connection.self_buddy.enable_mobile, False)

        assert type(val) is bool, (val, type(val))

        self.Freeze()

        self.online_components.Hide(self.mob_sz[not val], recursive=True)

        if self.acct.is_connected:  f = self.online_components.Show
        else:                       f = self.online_components.Hide
        f(self.mob_sz[val],recursive=True)

#        self.mob_sz[not val].Show(False, recursive=True)
#        self.mob_sz[val].Show(True, recursive=True)

        self.Thaw()
        self.Fit()
        self.Layout()

    def on_close(self):
        if self.observing_privacy:
            self.acct.connection.remove_observer(self.privacy_changed,'allow_unknown_contacts')
            self.observing_privacy = False

class YahooBlockListEditor(AcctListEditor):
    title = _('Block List')

    def get_matches(self, _str):
        return filter(lambda s: s.startswith(_str),(x.name for x in self.protocol.buddies.values()))

    def get_autovalues(self):
        return sorted(x.name for x in self.protocol.buddies.values() if not x.blocked)

    def validate(self, _str):
        return True

    def get_values(self):
        return sorted(x.name for x in self.protocol.buddies.values() if x.blocked)

    def add_item(self, _str):


        def on_success():
            print 'blocked buddy, adding to list'
            wx.CallAfter(AcctListEditor.add_item, self,_str)

        def on_error():
            wx.MessageBox(_('Could not block {item:s}').format(item=_str))

        def do_block():
            print 'removed buddy, now blocking'
            self.protocol.block_buddy(_str, success = on_success, error = on_error)

        if _str in self.protocol.buddies:
            if wx.YES == wx.MessageBox\
                (_('{item:s} is on your buddylist. Do you want to remove {item:s}'
                 ' from your buddylist and block the user?').format(item=_str),
                 _('Confirm Block and Remove'), wx.YES_NO):

                self.protocol.remove_buddy(_str, success = do_block, error = do_block)
        else:
            do_block()

    def remove_item(self, _str):
        self.protocol.unblock_buddy(_str, success = \
             lambda *a, **k: wx.CallAfter(AcctListEditor.remove_item, self,_str))

class YahooPrivacyPanel(AcctPrivacyPanel):
    perm_choices = [
                    (_('Allow only users on my contact list'), (True, 'contacts')),
                    (_("Block only users on 'Block List'"),    (False,    'list', 'Block'))]

    def __init__(self, *a, **k):
        AcctPrivacyPanel.__init__(self, *a, **k)
        self.build_panel()
        self.acct_changed()

    def build_panel(self):
        AcctPrivacyPanel.build_panel(self)

        self.rbs = rbs = []

        perms = PrefPanel(self,
                          PrefCollection(layout = wx.GridBagSizer(hgap = 6),
                                         *CheckGridList(self, rbs,self.perm_choices,self.acct, self.rb_changed,self.show_editor)),
                          _('Permissions'))

        sz = VSizer()
        sz.Add(perms,0,EXPAND)
        sz.ShowItems(False)

        self.online_components = sz

    def acct_changed(self, *a, **k):
        if not self: return
        self.rbs[not self.acct.block_unknowns].Value = True
        AcctPrivacyPanel.acct_changed(self, *a, **k)

    def rb_changed(self, args):
        (block_unknowns, who) = args[:2]
        self.mark_for_save()
        silence_notifications(self.acct.connection)
        self.acct.connection.block_unknowns = self.acct.block_unknowns = block_unknowns

#    def webtoggle(self, e):
#        print 'web pref toggled'

class JabberPrivacyPanel(AcctPrivacyPanel):
    def __init__(self, *a, **k):
        AcctPrivacyPanel.__init__(self, *a, **k)
        self.build_panel()
        self.inited = True
        self.acct_changed()

    def build_panel(self):
        AcctPrivacyPanel.build_panel(self)

        sz = VSizer()

        allow_chk = wx.CheckBox(self, -1, _('Allow only users on my buddy list to contact me'))
        allow_chk.Bind(wx.EVT_CHECKBOX, self.allow_changed)
        self.allow_chk = allow_chk


        hide_os_chk = wx.CheckBox(self, -1, _('Hide operating system from other users'))
        hide_os_chk.Bind(wx.EVT_CHECKBOX, self.cb_changed)
        self.hide_os_chk = hide_os_chk

        perms = PrefPanel(self,
                          PrefCollection(allow_chk,
                                         hide_os_chk,
                                         layout = VSizer(),
                                         itemoptions = (0,BOTTOM,6)),
                          _('Permissions'))

        sz.Add(perms, 0, wx.EXPAND| wx.ALL)

        sz.ShowItems(False)

        self.online_components = sz

    def allow_changed(self, e):
        self.mark_for_save()
        self.acct.connection.block_unknowns = self.acct.block_unknowns = bool(self.allow_chk.Value)

    def cb_changed(self, e):
        self.mark_for_save()
        self.acct.connection.hide_os = self.acct.hide_os = bool(self.hide_os_chk.Value)

    def acct_changed(self, *a, **k):
        if not self or not self.inited: return
        self.hide_os_chk.Value = self.acct.hide_os
        self.allow_chk.Value = self.acct.block_unknowns

        AcctPrivacyPanel.acct_changed(self, *a, **k)

class EmptyPrivacyPanel(AcctPrivacyPanel):
    def __init__(self, *a, **k):
        AcctPrivacyPanel.__init__(self, *a, **k)
        self.build_panel()
        self.inited = True
        self.acct_changed()

    def build_panel(self):
        AcctPrivacyPanel.build_panel(self)

        sz = VSizer()

        ### Online components
        msg = SText(self, "Nothing to see here. If you do see this, this is either a special dev-only account, or something is broken.")

        sz.Add(msg, 0, wx.EXPAND)
        sz.AddStretchSpacer()

        sz.Enable(False)
        sz.ShowItems(False)

        self.online_components = sz

class FBPrivacyPanel(AcctPrivacyPanel):
    def __init__(self, *a, **k):
        AcctPrivacyPanel.__init__(self, *a, **k)
        self.build_panel()
        self.inited = True
        self.acct_changed()

    def build_panel(self):
        sz = VSizer()

        ### Online components
        msg = wx.HyperlinkCtrl(self, -1, "http://www.facebook.com/privacy/",
                               "http://www.facebook.com/privacy/")

        sz.Add(msg, 0, wx.EXPAND)
        sz.AddStretchSpacer()

        sz.Enable(True)
        sz.ShowItems(True)

        self.online_components = self.offline_components = sz
        self.SetSizer(sz)

    def show_options(self, online):
        pass
#        self.Freeze()
#        self.Thaw()
#        self.Layout()

class GTalkPrivacyPanel(JabberPrivacyPanel):
    pass

acct_to_panel = dict(aim   = AIMPrivacyPanel,
                     icq   = ICQPrivacyPanel,
                     msn   = MSNPrivacyPanel,
                     yahoo = YahooPrivacyPanel,
                     jabber= JabberPrivacyPanel,
                     gtalk = GTalkPrivacyPanel,
                     fbchat= FBPrivacyPanel)

def GetAccountPanelType(account):
    log.info('getting privacy panel for %r', account)
    proto_class = account.protocol_class()
    if hasattr(proto_class, 'get_privacy_panel_class'):
        return proto_class.get_privacy_panel_class()
    else:
        return acct_to_panel.get(account.protocol, EmptyPrivacyPanel)
