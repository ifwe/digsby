'''
Advanced tab in the preferences dialog.
'''
from __future__ import with_statement
import wx
from gui.pref.prefcontrols import *
from gui.uberwidgets.PrefPanel import PrefPanel,PrefCollection

from util.primitives.funcs import do
from util.primitives.mapping import lookup_table

def panel(panel, sizer, addgroup, exithooks):

    addgroup(_('IM Window'),      lambda p,*a:  Check('conversation_window.merge_metacontact_history', 'Merge Metacontact History')(p))

#    status_check = Check('fullscreen.set_status',     _('&Set status to:'))(panel)
#    status_input = wx.TextCtrl(panel, -1)
#
#    status_sz = wx.BoxSizer(wx.HORIZONTAL)
#    status_sz.AddMany([
#        (status_check, 0, wx.EXPAND),
#        (status_input, 1, wx.EXPAND)
#    ])
#
#    g.Add(status_sz, 0, wx.EXPAND | wx.ALL, 4)
#
#
#    addgroup(_('Proxy Settings'),
#        build_proxy_panel(panel)
#    )

    return panel

# ----

def get_protocols():
    # (Protocol nicename, Preference short name)

    return [('Global Settings',       'proxy'),
            ('AOL Instant Messenger', 'aim'),
            ('MSN Messenger',         'msn'),
            ('Yahoo! Messenger',      'yahoo'),
            ('ICQ',                   'icq'),
            ('Jabber',                'jabber'),
            ('Google Talk',           'gtalk')]

proxy_protocols = ['SOCKS4', 'SOCKS5', 'HTTP', 'HTTPS']

def build_proxy_panel(parent):
    s = VSizer()

    protos = get_protocols()
    choices = [a[0] for a in protos]

    # Choice for "Global Settings" and then all the protocols
    proto_choice = wx.Choice(parent, -1, choices = choices)
    proto_choice.SetSelection(0)

    # Checkbox which is either "Use Proxy Server" or "Use Global Settings"
    checkbox = wx.CheckBox(parent, -1, _('&Use Proxy Server'))

    # Proxy protocols (HTTP, HTTPS, ...)
    proxy_proto_choice = wx.Choice(parent, -1, choices = proxy_protocols)
    proxy_proto_choice.SetSelection(0)

    grid = wx.FlexGridSizer(0, 2, 5, 5)
    proxy_info = [
        ('host', _('Host')),
        ('port', _('Port')),
        ('username', _('Username')),
        ('password', _('Password'))
    ]

    # Shortcuts for preference names.
    prefbase     = lambda i: 'proxy.' if i == 0 else (protos[i][1] + '.proxy.')
    getcheckpref = lambda i: prefbase(i) + ('use_proxy' if i == 0 else 'use_global')
    gettextpref  = lambda i, name: prefbase(i) + name
    getprotopref = lambda i: prefbase(i) + 'protocol'

    fields = []
    for i, (name, trans) in enumerate(proxy_info):
        field = wx.TextCtrl(parent, -1, '', size=(300, -1),
                            style = wx.TE_PASSWORD if name == 'password' else wx.TE_LEFT)
        fields.append( (name, field) )

    proxy_info_fields = lookup_table(fields)

    def protocol_changed(e = None):
        '''Invoked when the choice box with "Global Settings" and all the other
        protocols changes.'''

        i = proto_choice.Selection

        checkstr = _('&Use Proxy Server') if i == 0 else _('&Use Global Settings')
        checkbox.Label = checkstr

        enabled = bool(get_pref(getcheckpref(i)))
        checkbox.SetValue(enabled)

        proxy_proto_choice.SetStringSelection(get_pref(getprotopref(i)))
        for i, (name, trans) in enumerate(proxy_info):
            proxy_info_fields[name].Value = get_pref(gettextpref(i, name))

        print i, enabled
        do(c.Window.Enable(enabled if i == 0 else not enabled) for c in grid.Children)

    def proxy_proto_changed(e):
        i = proto_choice.Selection
        mark_pref(getprotopref(i), proxy_proto_choice.StringSelection)

    def checkbox_changed(e):
        i   = proto_choice.Selection
        val = checkbox.Value

        do(c.Window.Enable(val if i == 0 else not val) for c in grid.Children)
        mark_pref(getcheckpref(i), val)

    def textfield_changed(e):
        tfield = e.EventObject
        name   = proxy_info_fields[tfield]

        mark_pref(gettextpref(proto_choice.Selection, name), tfield.Value)

    # Connect event functions
    proto_choice.BBind(CHOICE = protocol_changed)
    proxy_proto_choice.BBind(CHOICE = proxy_proto_changed)
    checkbox.BBind(CHECKBOX = checkbox_changed)

    # The grid of fields for protocol specific proxy options
    grid.Add(wx.StaticText(parent, -1, _('&Protocol:')), 0, wx.ALIGN_CENTER_VERTICAL)
    grid.Add(proxy_proto_choice)

    for name, label in proxy_info:
        grid.Add(wx.StaticText(parent, -1, label + ':'), 0, wx.ALIGN_CENTER_VERTICAL)
        textctrl = proxy_info_fields[name]
        textctrl.BBind(KILL_FOCUS = textfield_changed)
        grid.Add(textctrl)

    protocol_changed()

    s.Add( proto_choice, 0, wx.NORTH, 4 )
    s.Add( checkbox, 0, wx.NORTH, 8 )
    s.AddSpacer( 10 )
    s.Add( grid, 0, wx.WEST, 22 )
    return s
