from common import pref
import wx
import wx.lib.sized_controls as sc

from cgui import SimplePanel
from gui.uberwidgets.UberCombo import UberCombo
from gui.uberwidgets.simplemenu import SimpleMenuItem

from gui.textutil import default_font
from gui.validators import LengthLimit
from util.primitives.error_handling import traceguard
from util.primitives.funcs import do
from util.primitives.structures import oset

from common import profile
import common.protocolmeta as protocolmeta
from contacts.buddylistfilters import OfflineGroup

from wx import EXPAND, LEFT, VERTICAL, HORIZONTAL, ALIGN_LEFT, \
        ALIGN_CENTER_VERTICAL, FULL_REPAINT_ON_RESIZE


bgcolors = [
    wx.Color(238, 238, 238),
    wx.Color(255, 255, 255),
]

def namebyproto(p):
    return protocolmeta.protocols[p].username_desc+':'

def ShowAddContactDialog(g):
    AddContactDialog.MakeOrShow(g)

def groupaddcontact(menu, group):
    if not isinstance(group, OfflineGroup):
        menu.AddItem(_('Add Contact'), callback=lambda : ShowAddContactDialog(group.name))

class CheckablePanel(SimplePanel):
    def __init__(self,parent,name,associate,bitmap=None,checkcallback=None):
        SimplePanel.__init__(self,parent,FULL_REPAINT_ON_RESIZE)

        s = self.Sizer = wx.BoxSizer(HORIZONTAL)

        self.checkcallback = checkcallback
        checkbox = self.checkbox = wx.CheckBox(self,-1)
        checkbox.Bind(wx.EVT_CHECKBOX,self.OnCheck)

        self.MinSize = wx.Size(-1, 22)

        s.Add(checkbox,0,LEFT|ALIGN_CENTER_VERTICAL,3)

        self.name = name

        self.associate = associate

        self.bitmap = bitmap


        self.checkbox.Value=False
        self.checkcallback(self.associate, self.checkbox.Value)

        Bind = self.Bind
        Bind(wx.EVT_PAINT,self.OnPaint)
        Bind(wx.EVT_LEFT_UP, lambda e: self.Check(not self.checkbox.Value))


    def Check(self, value = True):
        self.checkbox.Value= value
        self.OnCheck()


    def OnCheck(self,event = None):

        if self.checkcallback:
            self.checkcallback(self.associate,self.checkbox.Value)

    def OnPaint(self,event):
        dc   = wx.AutoBufferedPaintDC(self)
        rect = wx.RectS(self.Size)

        n = self.Parent.Index(self)
        dc.Brush = wx.Brush(bgcolors[n % len(bgcolors)])
        dc.Pen = wx.TRANSPARENT_PEN #@UndefinedVariable

        dc.DrawRectangleRect(rect)

        x = self.checkbox.Rect.Right+3
        w = self.Rect.Width - x - 3
        textrect = wx.Rect(x,0,w,rect.Height)

        dc.Font = default_font()
        dc.DrawLabel(self.name,textrect,ALIGN_LEFT|ALIGN_CENTER_VERTICAL)

        bm = self.bitmap

        dc.DrawBitmap(bm,rect.width-(bm.Size.width+3),3)

class CheckableList(wx.ScrolledWindow):
    def __init__(self,parent,thelist = None,setchangedcallback = None):
        wx.ScrolledWindow.__init__(self,parent)

        self.Sizer = wx.BoxSizer(VERTICAL)

        self.BackgroundColour = wx.WHITE #@UndefinedVariable

        self.theset = set()
        self.setchangedcallback = setchangedcallback


        self.SetScrollRate(0,1)

        if thelist != None:
            self.SetList(thelist)

        self.Bind(wx.EVT_PAINT,self.OnPaint)

    def OnPaint(self,event):

        event.Skip()

        srect= wx.Rect(*self.Rect)
        srect.Inflate(1,1)
        pcdc = wx.ClientDC(self.Parent)
        pcdc.Brush = wx.TRANSPARENT_BRUSH #@UndefinedVariable

        pcdc.Pen   = wx.Pen(wx.Colour(213,213,213))

        pcdc.DrawRectangleRect(srect)


    def SetList(self,thelist):

        if not hasattr(self,'thelist'):
            self.thelist=[]

        if thelist == self.thelist:
            return

        oldset = set(self.thelist)
        newset = set(thelist)

        removeset = oldset - newset
        addset   = newset - oldset

        self.thelist = thelist
#        self.Sizer.Clear(True)

        def AddOrRemove(acct,add):

            theset = self.theset

            if add:
                theset.add(acct)
            elif acct in theset:
                theset.remove(acct)

            print theset

            self.setchangedcallback(theset)

        for sizeritem in self.Sizer.Children:

            if sizeritem.Window:
                chkitem = sizeritem.Window

                if chkitem.associate in removeset:
                    self.Sizer.Detach(chkitem)
                    chkitem.Destroy()

                self.theset -= removeset




        for item in addset:
            self.Sizer.Add(CheckablePanel(self,item.username,item,item.serviceicon.Resized(16),AddOrRemove),0,EXPAND)

        self.SetVirtualSize(self.Sizer.MinSize)
        self.Layout()
        self.Refresh()

        self.setchangedcallback(self.theset)

    def Index(self,item):
        try:
            return self.Children.index(item)
        except:
            return None

    def SelectAccount(self, account):
        for child in self.Children:
            if isinstance(child, CheckablePanel):
                if child.associate == account:
                    child.Check()
                else:
                    print "NOT THE SAME!"
                    print "Account:", type(account), account
                    print "Associate:", type(child.associate), child.associate

no_connections_label = _('No Connections')
class AddContactDialog(sc.SizedDialog):
    def __init__(self, parent=None, group='', onservice='', newname = '', onaccount = None):
        sc.SizedDialog.__init__(self, parent, -1, _('Add Contact'), size = (314, 250),
                           style = wx.DEFAULT_DIALOG_STYLE | wx.FRAME_FLOAT_ON_PARENT | wx.RESIZE_BORDER)
        #S = self.Sizer = wx.BoxSizer(VERTICAL)

        p = self.panel = self.GetContentsPane() #wx.Panel(self)

        p.SetSizerType("form")

        self.SetButtonSizer(self.CreateButtonSizer(wx.OK | wx.CANCEL))

        okbutton = self.okbutton = self.FindWindowById(wx.ID_OK, self) #wx.Button(p, wx.ID_OK, _('Add'))
        okbutton.SetLabel(_('Add'))
        okbutton.SetDefault()
        okbutton.Enabled = False
        cancelbutton = self.FindWindowById(wx.ID_CANCEL, self) #wx.Button(p,wx.ID_CANCEL, _('Cancel'))

#=================================================================

        protoitems = self.MakeProtocolItems()
        groupitems = self.MakeGroupItems()

        Text = lambda s: wx.StaticText(p, -1, s)

#=========================================================================================================
        R_CENTER= dict(halign='right', valign='center')
        Text(_('Contact Type:')).SetSizerProps(**R_CENTER)
        protocombo = self.protocombo = UberCombo(p, no_connections_label, False, None, skinkey='AppDefaults.PrefCombo')
        protocombo.SetSizerProps(expand=True)

        namelabel = self.namelabel = Text(_('Screen Name:'))
        namelabel.SetSizerProps(**R_CENTER)

        name = self.namefield = wx.TextCtrl(p, validator=LengthLimit(255), value=newname)
        name.SetFocus()
        name.Bind(wx.EVT_TEXT,self.OnNameChange)
        name.SetSizerProps(expand=True)

        Text(_('Alias:')).SetSizerProps(**R_CENTER)
        alias = self.aliasfield = wx.TextCtrl(p, validator=LengthLimit(255))
        alias.SetSizerProps(expand=True)

        Text(_('In Group:')).SetSizerProps(**R_CENTER)
        groupcombo = self.groupcombo = UberCombo(p, group, True, None, skinkey='AppDefaults.PrefCombo')
        groupcombo.display.txtfld.Bind(wx.EVT_TEXT,self.OnNameChange)
        groupcombo.SetSizerProps(expand=True)

        Text(_('On Accounts:')).SetSizerProps(halign='right', valign='top')
        checklist = self.accountchecks = CheckableList(p, setchangedcallback = self.OnCheckedSetChange)
        checklist.MinSize = (-1, 66)
        checklist.SetSizerProps(expand=True, proportion=1)

#==========================================================================================================
        defserv = 0
        if onservice:
            for item in protoitems:
                if item.id == onservice:
                    defserv = protoitems.index(item)
                    break

        protocombo.SetItems(protoitems, defserv)
        groupcombo.SetItems(groupitems, 0 if group == '' else None)

#===========================================================================================================

        def onproto(*a):
            self.UpdateAccounts()
            name.SetFocus()

        protocombo.SetCallbacks(value = onproto)
        self.UpdateAccounts()

        if onaccount is not None:
            checklist.SelectAccount(onaccount)

        def NoEmptyGroup(*a):
            if groupcombo.Value == '':
                groupcombo.SetSelection(0)
                if groupcombo.Value == '':
                    groupcombo.Value = pref('buddylist.fakeroot_name', default='Contacts')
        groupcombo.SetCallbacks(value = NoEmptyGroup)

        self.Fit()
        self.Size = (314, self.Size.y)
        self.MinSize = self.Size

        okbutton.Bind(wx.EVT_BUTTON, self.OnOk)
        cancelbutton.Bind(wx.EVT_BUTTON, lambda e: self.Close())

        Bind = self.Bind
        Bind(wx.EVT_CLOSE,self.OnClose)

        profile.account_manager.connected_accounts.add_observer(self.WhenOnlineAcctsChange)
        profile.blist.add_observer(self.WhenGroupsChange, 'view')

        import hooks; hooks.notify('digsby.statistics.ui.dialogs.add_contact.created')

    def UpdateAccounts(self,*a):
        v = self.protocombo.Value

        accts = set()

        if not isinstance(v,basestring):
            proto = v.id.lower()
            self.namelabel.SetLabel(namebyproto(proto))


            accounts = profile.account_manager.connected_accounts

            for account in accounts:
                accpro = protocolmeta.SERVICE_MAP[account.protocol]
                if  proto in accpro:
                    accts.add(account)

        accts = list(accts)
        self.accountchecks.SetList(accts)

        if len(accts) == 1:
            self.accountchecks.SelectAccount(accts[0])

        wx.CallAfter(self.panel.Layout)


    def OnNameChange(self,event):
        self.okbutton.Enabled = bool(self.accountchecks.theset and self.namefield.Value and (self.groupcombo.Value or self.groupcombo.display.txtfld.Value))
        event.Skip()

    def OnCheckedSetChange(self,theset):
        self.okbutton.Enabled = bool(theset and self.namefield.Value and (self.groupcombo.Value or self.groupcombo.display.txtfld.Value))

    def WhenOnlineAcctsChange(self,*a):
        protocombo = self.protocombo

        protocombo.SetItems(self.MakeProtocolItems())

        if not protocombo.Value in protocombo:
            if len(protocombo):
                protocombo.SetSelection(0)
            else:
                protocombo.Value = no_connections_label
        else:
            self.UpdateAccounts()

    def WhenGroupsChange(self,*a):

        self.groupcombo.SetItems(self.MakeGroupItems())



    def OnOk(self,event):

        self.Show(False)

        import hooks; hooks.notify('digsby.statistics.contact_added')
        proto    = self.protocombo.Value.id
        name     = self.namefield.Value
        group    = self.groupcombo.Value if isinstance(self.groupcombo.Value,basestring) else self.groupcombo.Value.GetContentAsString()
        alias    = self.aliasfield.Value
        accounts = self.accountchecks.theset


        import hub
        from common import profile
        meta = False
        x = None
        for account in accounts:
            with traceguard:
                account.connection.add_new_buddy(name, group, proto, alias)
                x = (name, account.connection.service)
                if x in profile.blist.metacontacts.buddies_to_metas:
                    meta = True

        if meta:
            id = list(profile.blist.metacontacts.buddies_to_metas[x])[0].id
            m = profile.blist.metacontacts[id]
            alias = m.alias
            group = list(m.groups)[0][-1]
            hub.get_instance().user_message(
            "That buddy is already part of metacontact \"" + alias +
            "\" in group \"" + group + "\"")

        self.Close()

    def OnClose(self,event):
        profile.account_manager.connected_accounts.remove_observer(self.WhenOnlineAcctsChange)
        profile.blist.remove_observer(self.WhenGroupsChange, 'view')

        self.Show(False)

        type(self).current_instance = None

        self.Destroy()

    def MakeProtocolItems(self):
        set = oset
        if not hasattr(self,'protoitems'):
            self.protoitems = set()

        protoitems = self.protoitems

        oldprotocols = set(p.id for p in protoitems)

#==============================================================================

        accounts = profile.account_manager.connected_accounts
        protocols  = set()
        protocols2 = set()
        do(protocols.add(account.protocol) for account in accounts)

        for proto in protocols:
            try:
                protocols2.update(protocolmeta.SERVICE_MAP[proto])
            except:
                pass

        protocols = protocols2

#==============================================================================

        for account in accounts:
            if not account.allow_contact_add:
                protocols.discard(account.protocol)

        removeprotos = oldprotocols - protocols

        addprotos = protocols - oldprotocols

#==============================================================================

        for item in set(protoitems):
            if item.id in removeprotos:
                protoitems.remove(item)

        for protocol in addprotos:
            skinval = skin.get('serviceicons.%s'%protocol, None)
            if skinval is not None:
                skinval = skinval.Resized(16)
            protoval = protocolmeta.protocols.get(protocol, None)
            protoval = protoval.name if protoval is not None else protocol
            protoitems.add(SimpleMenuItem([skinval, protoval],id = protocol))

        return list(protoitems)

    def MakeGroupItems(self):
        accounts = profile.account_manager.connected_accounts
        groups = set()
        groups.add(pref('buddylist.fakeroot_name', default='Contacts'))
        do(groups.update(account.connection.get_groups())
           for account in accounts if getattr(account, 'connection', None) is not None)

        return [SimpleMenuItem(group) for group in list(sorted(groups,key = lambda g: g.lower()))]


    @classmethod
    def MakeOrShow(cls,group='', service = '', name = '', account = None):

        if not hasattr(cls,'current_instance'):
            cls.current_instance = None

        if cls.current_instance:
            cls.current_instance.Show(True)
            cls.current_instance.Raise()
        else:
            cls.current_instance = AddContactDialog(None, group, service, name, account)
            cls.current_instance.Show(True)

        import hooks; hooks.notify('digsby.statistics.ui.dialogs.add_contact.shown')

#==========================================================================

from gui import skin

class FakeAccount(object):
    def __init__(self,username,serviceicon):
        self.username = username
        self.serviceicon = serviceicon


if __name__ == '__main__':
    from tests.testapp import testapp
    app = testapp('../../')

    f=AddContactDialog()
    f.Show(True)

    app.MainLoop()
