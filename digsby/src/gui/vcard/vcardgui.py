from util.primitives import Storage
from util.primitives.funcs import do
import gettext
gettext.install('digsby')
from gui.controls import *
import jabber

import wx

class Holder(object):
    pass

class vcardcontrols(CustomControls):
    class _VCardOrg(Holder):
        def __init__(self, controls, parent):
            self.parent = parent
            self.controls = controls
            self.namelabel, self.nametext  = self.controls.LabeledTextInput(_("Name"))
            self.unitlabel, self.unittext  = self.controls.LabeledTextInput(_("Unit"))
            self.elems = [self.namelabel, self.nametext, self.unitlabel, self.unittext]
        def GetValue(self):
            if any(getattr(self, attr+'text').Value for attr in ['name', 'unit']):
                org = jabber.vcard.VCardOrg('ORG', '')
                for attr in ['name', 'unit']:
                    val = getattr(self, attr+'text').Value
                    if val:
                        setattr(org, attr, val)
                return org
            else:
                return None
        def SetValue(self, org):
            for attr in ['name', 'unit']:
                getattr(self, attr+'text').Value = getattr(org, attr) or ''
        def clear(self):
            for attr in ['name', 'unit']:
                getattr(self, attr+'text').Value = ''
        Value = property(GetValue, SetValue)

    def VCardOrg(self):
        return self._VCardOrg(self, self.parent)

    class _VCardName(Holder):
        def __init__(self, controls, parent):
            assert False
            self.parent = parent
            self.controls = controls
            l = self.controls.LabeledTextInput
            d = dict(family  =(_("Last Name"),),
                 given    = (_("First Name"),),
                 middle   = (_("Middle Name"),),
                 prefix   = (_("Prefix"),),
                 suffix   = (_("Suffix"),))
            self.elems = []
            for i in d.iteritems():
                one, two = l(*i[1]); self.elems.append(one); self.elems.append(two)
                setattr(self, i[0]+'label', one); setattr(self, i[0]+'text', two);
        def GetValue(self):
            name = jabber.vcard.VCardName('N', '')
            for attr in ['family', 'given', 'middle', 'prefix', 'suffix']:
                setattr(name, attr, getattr(self, attr+'text').Value)
            return name
        def SetValue(self, name):
            for attr in ['family', 'given', 'middle', 'prefix', 'suffix']:
                getattr(self, attr+'text').Value = getattr(name, attr)
        Value = property(GetValue, SetValue)

    def VCardName(self):
        return self._VCardName(self, self.parent)

    class _VCardString(object):
        _class = jabber.vcard.VCardString
        def __init__(self, controls, parent, type_, label):
            self.parent = parent
            self.controls = controls
            self.type_ = type_
            if label is not None:
                l = self.controls.LabeledTextInput
                self.stringlabel, self.stringtext = l(label)
                self.elems = [self.stringlabel, self.stringtext]
            else:
                self.stringtext = self.controls.TextInput()
                self.elems = [self.stringtext]
        def GetValue(self):
            try:
                strng = self._class(self.type_, self.stringtext.Value)
                return strng
            except:
                return None
        def SetValue(self,strng):
            self.stringtext.Value = strng.value
        def clear(self):
            self.stringtext.Value = ''
        Value = property(GetValue, SetValue)

    class _VCardXString(_VCardString):
        _class = jabber.vcard.VCardXString

    def VCardString(self, type_, label):
        return self._VCardString(self, self.parent, type_, label)

    def VCardXString(self, type_, label):
        return self._VCardXString(self, self.parent, type_, label)

    class _VCardTel(Holder):
        def __init__(self, controls, parent):
            self.parent = parent
            self.controls = controls
            self.numberlabel, self.numbertext  = self.controls.LabeledTextInput(_("Number"))
            self.type = Storage()
            self.type.Value = []
#            self.unitlabel, self.unittext  = self.controls.LabeledTextInput("Unit")
            self.elems = [self.numberlabel, self.numbertext]
        def GetValue(self):
            if getattr(self, 'numbertext').Value:
                tel = jabber.vcard.VCardTel('TEL', '')
                val = getattr(self, 'numbertext').Value
                tel.number = val
                if self.type.Value:
                    tel.type = self.type.Value[:]
                return tel
            else:
                return None
        def SetValue(self, tel):
            self.type.Value = tel.type[:]
            self.numbertext.Value = tel.number
        def clear(self):
            self.type.Value = []
            self.numbertext.Value = ''
        Value = property(GetValue, SetValue)

    def VCardTel(self):
        return self._VCardTel(self, self.parent)

    class _VCardEmail(Holder):
        def __init__(self, controls, parent):
            self.parent = parent
            self.controls = controls
            self.addresslabel, self.addresstext  = self.controls.LabeledTextInput(_("Email"))
            self.type = Storage()
            self.type.Value = []
#            self.unitlabel, self.unittext  = self.controls.LabeledTextInput("Unit")
            self.elems = [self.addresslabel, self.addresstext]
        def GetValue(self):
            if getattr(self, 'addresstext').Value:
                email = jabber.vcard.VCardEmail('EMAIL', '')
                val = getattr(self, 'addresstext').Value
                email.address = val
                if self.type.Value:
                    email.type = self.type.Value[:]
                return email
            else:
                return None
        def SetValue(self, email):
            self.type.Value = email.type[:]
            self.addresstext.Value = email.address
        def clear(self):
            self.type.Value = []
            self.addresstext.Value = ''
        Value = property(GetValue, SetValue)

    def VCardEmail(self):
        return self._VCardEmail(self, self.parent)

    class _VCardAdr(Holder):
        def __init__(self, controls, parent):
            self.parent = parent
            self.controls = controls
            l = self.controls.LabeledTextInput
            self.poboxtext = Storage()
            self.poboxtext.Value = ''
            common_ = ('H',)
            d = [
                 ('street', _("Street")),
                 ('extadr', ""),
#                 ('pobox', "PO BOX"),
                 ('locality', _("City")),
                 ('region', _("State")),
                 ('pcode', _("Postal Code")),
                 ('ctry', _("Country"))]
            self.elems = []
            for i in d:
                one, two = l(i[1]); self.elems.append(one); self.elems.append(two)
                setattr(self, i[0]+'label', one); setattr(self, i[0]+'text', two);
#            self.type     = "list of etc."
        def GetValue(self):
            if any(getattr(self, attr+'text').Value for attr in
                   ['street', 'extadr', 'pobox', 'locality', 'region','pcode','ctry']):
                adr = jabber.vcard.VCardAdr('ADR', '')
                for attr in ['street', 'extadr', 'pobox', 'locality', 'region','pcode','ctry']:
                    val = getattr(self, attr+'text').Value
                    if val:
                        setattr(adr, attr, val)
                return adr
            else:
                return None
        def SetValue(self, adr):
            for attr in ['street', 'extadr', 'pobox', 'locality','region','pcode','ctry']:
                getattr(self, attr+'text').Value = getattr(adr, attr) or ''
        def clear(self):
            for attr in ['street', 'extadr', 'pobox', 'locality','region','pcode','ctry']:
                getattr(self, attr+'text').Value = ''
        Value = property(GetValue, SetValue)

    def VCardAdr(self):
        return self._VCardAdr(self, self.parent)

class VCardGUI(dict):
    components={
        #"VERSION": (VCardString,"optional"),
        "FN": 'VCardString', #have, finished
        "N": 'store',
        "NICKNAME": 'VCardString', #have, finished
        "PHOTO": 'store',
        "BDAY": 'VCardString', #have, finished
        "ADR": 'VCardAdr', #have, finished
        "LABEL": 'store',
        "TEL": 'VCardTel',
        "EMAIL": 'VCardEmail',
        "JABBERID": 'store',
        "MAILER": 'store',
        "TZ": 'store',
        "GEO": 'store',
        "TITLE": 'VCardString', #have, finished
        "ROLE": 'VCardString', #have, finished
        "LOGO": 'store',
#        "AGENT": 'store',
        "ORG": 'VCardOrg', #have, finished
        "CATEGORIES": 'store',
        "NOTE": 'store',
        "PRODID": 'store',
        "REV": 'store',
        "SORT-STRING": 'store',
        "SOUND": 'store',
        "UID": 'store',
        "URL": 'VCardString', #have, finished
        "CLASS": 'store',
        "KEY": 'store',
        "DESC": 'VCardXString', #have, finished
    }
    def __init__(self, protocol=None, vcard=None):
        dict.__init__(self)
        self.protocol = protocol
        vc = vcard if vcard is not None else self.protocol.vcard
        self.init_gui()
        self.page1()
        self.page2()
        self.page3()
        self.page4()
        self.assign_vc(vc)
        f = self.frame
        f.Fit()
        f.MinSize = wx.Size(f.Size.x * 1.5, f.Size.y)
        f.Fit()
        from gui import skin
        if protocol is None:
            f.SetFrameIcon(skin.get('AppDefaults.TaskbarIcon'))
        else:
            f.SetFrameIcon(protocol.serviceicon)
        wx.CallAfter(f.Show)

    def init_gui(self):
        name = 'vCard Editor' if self.protocol is not None else 'vCard Viewer'
        title = (_('vCard Editor for {username}').format(username=self.protocol.username)) if self.protocol is not None else _('vCard Viewer')
        self.frame    = f = wx.Frame( None, -1, title = title, name = name)
        self.notebook =     wx.Notebook(f, -1)
        if self.protocol is not None:
            #add retrieve/set buttons
            f.Sizer = s = wx.BoxSizer(wx.VERTICAL)
            s.Add(self.notebook, 1, wx.EXPAND)

            p = wx.Panel(f)

            save     = wx.Button(p, wx.ID_SAVE, 'Save')
            retrieve = Button(p, _('Retreive'), self.on_retrieve)
            cancel   = wx.Button(p, wx.ID_CANCEL, 'Cancel')

            save.Bind(wx.EVT_BUTTON, lambda e: self.on_save())

            p.Sizer = h = wx.BoxSizer(wx.HORIZONTAL)
            h.AddStretchSpacer(1)
            do(h.Add(b, 0, wx.EXPAND | wx.ALL, 3) for b in [save, retrieve, cancel])

            s.Add(p, 0, wx.EXPAND)
        else:
            assert False
            #no buttons
            pass

    def on_save(self):
        print "onsave"
        self.protocol.save_vcard(self.retrieve_vcard())

    def on_retrieve(self):
        assert self.protocol is not None
        self.protocol.request_vcard('', success=self.handle_vc_stanza)

    def handle_vc_stanza(self, stanza):
        q = stanza.get_query()
        if not q: return
        self.assign_vc(jabber.VCard(q))

    def assign_vc(self, vc):
        for k,v in self.components.items():
            if v == 'store':
                self[k] = vc[k]
        self.assign_page1(vc)
        self.assign_page2(vc)
        self.assign_page3(vc)
        self.assign_page4(vc)

    def assign_lists(self, names, vc):
        for name in names:
            self["_" + name] = vc[name][1:]
            if vc[name]:
                self[name].Value = vc[name][0]
            else:
                self[name].clear()

    def retrieve_lists(self, names, vc):
        for name in names:
            if self[name].Value:
                vc.content[name] = [self[name].Value]
            vc.content[name][1:] = self["_" + name]

    def assign_page1(self, vc):
        if vc['FN'] is not None:
            self['FN'].Value = vc['FN']
        else:
            self['FN'].clear()
        self.assign_lists(('NICKNAME', 'BDAY', 'TEL', 'URL','EMAIL'), vc)

    def page1(self):
        p = wx.Panel(self.notebook)
        self.notebook.AddPage(p, _("General"))
        c = vcardcontrols(p)
        vcs = c.VCardString
        self['FN']       = vcs("FN", _("Full Name"))
        self["NICKNAME"] = vcs("NICKNAME", _("Nickname"))
        self["BDAY"]     = vcs("BDAY", _("Birthday"))
        self['TEL']      = c.VCardTel()
        self["URL"]      = vcs("URL", _("Homepage"))
        self['EMAIL']    = c.VCardEmail()

        s = FGridSizer(0, 2, *sum([self['FN'].elems,
               self["NICKNAME"].elems,
               self["BDAY"].elems,
               self['TEL'].elems,
               self["URL"].elems,
               self['EMAIL'].elems], []))
        s.AddGrowableCol(1)
        p.Sizer = s

    def assign_page2(self, vc):
        self.assign_lists(('ORG', 'TITLE', 'ROLE'), vc)

    def page2(self):
        p = wx.Panel(self.notebook)
        self.notebook.AddPage(p, _("Work"))
        c = vcardcontrols(p)
        vcs = c.VCardString

        self["ORG"]   = c.VCardOrg()
        self["TITLE"] = vcs("TITLE", _("Position"))
        self["ROLE"]  = vcs("ROLE", _("Role"))

        s = FGridSizer(0,2, *sum([self["ORG"].elems,
                    self["TITLE"].elems,
                    self["ROLE"].elems], []))
        s.AddGrowableCol(1)
        p.Sizer = s

    def assign_page3(self, vc):
        self.assign_lists(('ADR',), vc)

    def page3(self):
        p = wx.Panel(self.notebook)
        self.notebook.AddPage(p, _("Location"))
        c = vcardcontrols(p)
        self["ADR"] = c.VCardAdr()

        s = FGridSizer(0,2,*self["ADR"].elems)
        s.AddGrowableCol(1)
        p.Sizer = s

    def assign_page4(self, vc):
        self.assign_lists(('DESC',), vc)

    def page4(self):
        p = wx.Panel(self.notebook)
        self.notebook.AddPage(p, _("About"))
        c = vcardcontrols(p)
        self['DESC'] = c.VCardXString("DESC", None)

        s = FGridSizer(0,1,self['DESC'].stringtext)
        s.AddGrowableCol(0)
        s.AddGrowableRow(0)
        p.Sizer = s

    def retrieve_vcard(self):
        vc = jabber.vcard.VCard('')
        for k,v in self.components.items():
            if v == 'store':
                vc.content[k] = self[k]
        vc.content['FN'] = self['FN'].Value
        self.retrieve_lists(('NICKNAME', 'BDAY','TEL',
                             'URL','EMAIL','ORG',
                             'TITLE', 'ROLE','ADR','DESC'), vc)
        return vc

    def Prompt(self, callback):
        return True

#abilities:
#    liveupdate: func/false
#    getvalue
#    orientation
#    validator
