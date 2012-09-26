'''
Contact List tab for the preferences dialog.
'''

from __future__ import with_statement

import wx
import config
from gui.pref.prefcontrols import HSizer, VSizer, Check, mark_pref, get_pref, \
    SText, PrefGroup, Choice, Slider, FontFaceAndSize, EnabledGroup, OffsetGroup
from gui.uberwidgets.PrefPanel import PrefPanel, PrefCollection

from util.fsm import StateManager, StateMachine
from util.primitives.funcs import do
from util.primitives.mapping import dictreverse
from common import profile, pref

from wx import LEFT, EXPAND, TOP, RIGHT, BOTTOM, EVT_CHOICE, EVT_CHECKBOX
from peak.events import trellis
from util.lego.lattice.blocks import IValueListener
from pg_sandbox import LayoutModel
from gui.pref.pg_sandbox import PrefLink, Selection, TranslatableChoices
from contacts.sort_model import ChoiceModel, CheckModel

def panel(panel, sizer, addgroup, exithooks):
    two = PrefPanel(panel,
        sorting_sizer(panel, exithooks),_('Sorting and Groups'))

    autohide_panel = wx.Panel(panel)
    aps = autohide_panel.Sizer = HSizer()

    if config.platform == 'win':
        # Setting autohide has to modify taskbar settings, so focus jumps to
        # the buddylist. This meant you wouldn't immediately see the effect
        # of checking the box if the blist was already docked, though.
        #
        # Now 50ms after checking it, the checkbox gets focus again, and the
        # buddylist will then slide away.
        def on_autohide_check(v):
            if v: wx.CallLater(50, autohide.SetFocus)
    else:
        def on_autohide_check(v):
            pass

    autohide = Check('local.buddylist.dock.autohide',
                     _('Autohide when not in &focus'),
                     callback = on_autohide_check)(autohide_panel)

    aps.Add(autohide, 0, LEFT, 18)

    dock = Check('local.buddylist.dock.enabled', _('Automatically &dock when near edge of screen'),
                 callback = lambda v: autohide.Enable(v))(panel)
    autohide.Enable(dock.IsChecked())

    three = PrefPanel(  panel,
                        PrefCollection(
                            Check('buddylist.always_on_top',   _('&Keep on top of other applications')),
                            Check('buddylist.show_in_taskbar', _('Show in taskbar')),
                            dock,
                            autohide_panel,
                            layout = VSizer(),
                            itemoptions = (0, BOTTOM, 6)
                        ),
                        _('Window Options')
                     )


    # The autohide checkbox is slightly indented, and disabled when the "dock"
    # checkbox is unhecked.

    h = HSizer()
    h.Add(two,   1, EXPAND | RIGHT, 3)
    h.Add(three, 0, EXPAND | LEFT, 3)

    v = VSizer()
    v.Add(h, 0, EXPAND)

    from functools import partial
    four = PrefPanel(panel,
                     partial(contact_layout_panel, exithooks=exithooks),
                     _('Contact Layout'),
                     prefix = 'buddylist.layout')

    def AdvancedToggleCB(button):
        val = not pref('buddylist.layout.ez_layout',False)
        mark_pref('buddylist.layout.ez_layout', val)
        ezmode = val

        ez  = four.content.ez_panel
        adv = four.content.adv_panel

        four.content.Sizer.Clear()

        four.content.Show(False)
        if ezmode:
            adv.Destroy()
            adv = None
            easy_layout_panel(four.content, 'buddylist.layout')
        else:
            ez.Destroy()
            ez = None
            advanced_layout_panel(four.content, 'buddylist.layout', exithooks=exithooks)

        button.SetLabel(_('Advanced') if ezmode else _('Basic'))

        four.content.Layout()
        four.content.Show(True)
        panel.Layout()

    four.SetButton(_('Advanced') if four.content.ez_panel else _('Basic'), lambda button: wx.CallAfter(AdvancedToggleCB, button))


    v.Add(four, 0, EXPAND | TOP, 5)

    sizer.Add(v, 1, EXPAND)

    return panel

def setChoiceString(choice, s):
    if not s in choice.GetStrings():
        choice.Append(s)

    choice.SetStringSelection(s)

wx.Choice.SetThisString = setChoiceString

class ChoiceModelSync(trellis.Component):
    view = trellis.attr()
    model = trellis.attr()
    listener = trellis.attr()

    @trellis.perform
    def update(self):
        try:
#            print 'syncing', self.model.enabled, self.model.selection, self.values[:]
            with self.view.Frozen():
                self.view.Enabled = self.model.enabled
                self.view.Items = [val[1] for val in self.model.values]
                self.view.SetSelection(self.model.selection)
                #hack a size(?) event, roughly equivalent to the C function
                # implementation of UpdateVisibleHeight()
                #forces the list to not have a scrollbar (at least when going
                # from 4 to 5 items)
                self.view.Size = self.view.Size
        except Exception:
            if not wx.IsDestroyed(self.view):
                raise

    @trellis.maintain
    def selection(self):
        self.listener.value = self.model.selection

class CheckModelSync(trellis.Component):
    view = trellis.attr()
    model = trellis.attr()
    listener = trellis.attr()

    @trellis.perform
    def update(self):
        try:
            with self.view.Frozen():
                self.view.Enabled = self.model.enabled
                self.view.Value = self.model.checked
        except Exception:
            if not wx.IsDestroyed(self.view):
                raise

    @trellis.maintain
    def state(self):
        self.listener.value = self.model.checked

class ModelChoiceSync(trellis.Component):
    listener = trellis.attr()
    model = trellis.attr()

    @trellis.maintain
    def selection(self):
        self.model.selection = self.listener.value

class ModelCheckSync(trellis.Component):
    listener = trellis.attr()
    model = trellis.attr()

    @trellis.maintain
    def state(self):
        self.model.checked = self.listener.value

class ChoiceSync(object):
    def __init__(self, model, view):
        self.model = model
        self.view = view
        #order matters, make the view sync to the model before we allow
        #the other direction
        self.listener = IValueListener(self.view)
        self.model_to_view = ChoiceModelSync(model = model, view = view, listener = self.listener)
        self.view_to_model = ModelChoiceSync(model = model, listener = self.listener)

class CheckSync(object):
    def __init__(self, model, view):
        self.model = model
        self.view = view
        #order matters, make the view sync to the model before we allow
        #the other direction
        self.listener = IValueListener(self.view)
        self.model_to_view = CheckModelSync(model = model, view = view, listener = self.listener)
        self.view_to_model = ModelCheckSync(model = model, listener = self.listener)

class SyncingChoice(wx.Choice):
    def __init__(self, model, *a, **k):
        super(SyncingChoice, self).__init__(*a, **k)
        self.sync = ChoiceSync(view = self, model = model)

    def release(self):
        del self.sync

class SyncingCheck(wx.CheckBox):
    def __init__(self, model, *a, **k):
        super(SyncingCheck, self).__init__(*a, **k)
        self.sync = CheckSync(view = self, model = model)

    def release(self):
        del self.sync

def yield_choices(models, *a, **k):
    for model in models:
        yield SyncingChoice(model, *a, **k)

def release_syncs(choices):
    for choice in choices:
        choice.release()

def sorting_sizer(panel, exithooks):
    p = wx.Panel(panel)
    sz = p.Sizer = VSizer()

    #get models
    sort_models = profile.blist.sort_models

    import gui.lattice #@UnusedImport: side effect registering interfaces
    choices = list(yield_choices(sort_models, p))
    exithooks.append(lambda:release_syncs(choices))

    labels = [_('Group by:'),
              _('Sort by:')] + \
             [_('Then by:')]*(len(sort_models)-2)

    to_add = [[(SText(p, label), 0, wx.ALIGN_CENTER_VERTICAL),
                   (choice, 1, EXPAND)]
                  for label,choice in zip(labels, choices)]

    s = wx.FlexGridSizer(len(sort_models), 2, 7,7)
    s.AddMany(sum(to_add,[]))
    s.AddGrowableCol(1,1)
    sz.Add(s, 0, EXPAND)

    return p

def contact_layout_panel(panel,pre,exithooks):
    container_panel = wx.Panel(panel)
    container_panel.Sizer = VSizer()
    container_panel.ez_panel = None
    container_panel.adv_panel = None

    prefix = 'buddylist.layout.'

    service      = get_pref(prefix+'service_icon_pos')
    se_enabled   = get_pref(prefix+'show_service_icon')
    status       = get_pref(prefix+'status_icon_pos')
    st_enabled   = get_pref(prefix+'show_status_icon')
    icon         = get_pref(prefix+'buddy_icon_pos')
    icon_enabled = get_pref(prefix+'show_buddy_icon')

    #heal some conflicting states
    if not icon_enabled:
        if status.startswith('b'):  status = icon
        if service.startswith('b'): service = icon
    #service will be shown farther left if they're the same, so fix status first
    #technically, these next two would be ok as long as they're both enabled,
    #but let's get them to a consistent state ASAP
    if status.startswith('f') and service != status[1:]: status = status[1:]
    if service.startswith('f') and status != service[1:]: service = service[1:]
    #other states may be conflicting, but do not cause problems, only those where
    #the BUMP/VACUUM rules come into play need to be fixed

    container_panel.layout_model = LayoutModel(
                               service      = service,
                               se_enabled   = se_enabled,
                               status       = status,
                               st_enabled   = st_enabled,
                               icon         = icon,
                               icon_enabled = icon_enabled,
                               )
    Cells = trellis.Cells
    #hook up helper models
    cells = Cells(container_panel.layout_model)

    #Trellis will keep the rest alive
    container_panel.links = dict(
        service_icon_pos  = PrefLink(prefname=prefix+'service_icon_pos',  value = cells['service']),
        show_service_icon = PrefLink(prefname=prefix+'show_service_icon', value = cells['se_enabled']),
        status_icon_pos   = PrefLink(prefname=prefix+'status_icon_pos',   value = cells['status']),
        show_status_icon  = PrefLink(prefname=prefix+'show_status_icon',  value = cells['st_enabled']),
        buddy_icon_pos    = PrefLink(prefname=prefix+'buddy_icon_pos',    value = cells['icon']),
        show_buddy_icon   = PrefLink(prefname=prefix+'show_buddy_icon',   value = cells['icon_enabled']),
    )

    if pref('buddylist.layout.ez_layout', True):
        easy_layout_panel(container_panel,pre)
    else:
        advanced_layout_panel(container_panel,pre,exithooks)
    return container_panel

def easy_layout_panel(container_panel,pre):
    cp_sizer = container_panel.Sizer

    from gui.pref.noobcontactlayoutpanel import NoobContactLayoutPanel
    ez_panel = container_panel.ez_panel = NoobContactLayoutPanel(container_panel)

    cp_sizer.Add(ez_panel, 0, EXPAND)


def advanced_layout_panel(container_panel, pre, exithooks):
    cp_sizer = container_panel.Sizer
    adv_panel = container_panel.adv_panel = wx.Panel(container_panel)

    adv_panel.Sizer = VSizer()

    v =  VSizer()
#========================================================================================
#HAX: This should be done differently
#========================================================================================
    cb = wx.CheckBox(adv_panel, -1, '')
    adv_panel.Sizer.Add(v, 0, wx.ALIGN_CENTER_HORIZONTAL | RIGHT, cb.Size.width * 1.5)
    cb.Destroy()
#========================================================================================
    old_spacing, PrefGroup.SPACING = PrefGroup.SPACING, 0
#===============================================================================================================
    s = adv_panel.Sizer
    prefix = 'buddylist.layout.'
    Cells = trellis.Cells
    cells = Cells(container_panel.layout_model)

    se_selection = Selection(value   = cells['service'],
                             choices = cells['service_choices'],
                             enabled = cells['se_enabled'])
    st_selection = Selection(value   = cells['status'],
                             choices = cells['status_choices'],
                             enabled = cells['st_enabled'])
    bi_selection = Selection(value   = cells['icon'],
                             choices = ['left','right'],
                             enabled = cells['icon_enabled'])
    #adapt for GUI models
    translated = dict(fleft  = _('Far Left'),
                      left   = _('Left'),
                      bleft  = _('Badge (Lower Left)'),
                      bright = _('Badge (Lower Right)'),
                      right  = _('Right'),
                      fright = _('Far Right'))
    se_choices = TranslatableChoices(keys=cells['service_choices'], translations = translated)
    st_choices = TranslatableChoices(keys=cells['status_choices'], translations = translated)
    bi_choices = TranslatableChoices(keys=['left','right'], translations = translated)

    #share a bunch of cells
    service_model   = ChoiceModel(values = Cells(se_choices)['values'],
                                  selection = Cells(se_selection)['selection'],
                                  enabled = cells['se_enabled'])
    service_enabled = CheckModel( checked = Cells(service_model)['enabled'])
    status_model    = ChoiceModel(values = Cells(st_choices)['values'],
                                  selection = Cells(st_selection)['selection'],
                                  enabled = cells['st_enabled'])
    status_enabled  = CheckModel( checked = status_model.__cells__['enabled'])
    icon_model      = ChoiceModel(values = Cells(bi_choices)['values'],
                                  selection = Cells(bi_selection)['selection'],
                                  enabled = cells['icon_enabled'])
    icon_enabled    = CheckModel( checked = Cells(icon_model)['enabled'])

    service_check   = SyncingCheck(service_enabled,  adv_panel, label = _('Show service icon on:'))
    service_choice  = SyncingChoice(service_model, adv_panel)
    status_check    = SyncingCheck(status_enabled, adv_panel, label = _('Show status icon on:'))
    status_choice   = SyncingChoice(status_model, adv_panel)
    icon_check      = SyncingCheck(icon_enabled, adv_panel, label =  _('Show buddy icon on the:'))
    icon_choice     = SyncingChoice(icon_model, adv_panel)

    need_del = [locals()[cat + '_' + typ] for cat in ['service', 'status', 'icon']
                                          for typ in ['check', 'choice']]
    exithooks.append(lambda:release_syncs(need_del))

    # Slider returns sizer, control
    bicon_slide, s = Slider('buddy_icon_size',
                            _('Buddy icon size:'),
                            start = 12, stop = 65, step = 4,
                            value = get_pref('buddylist.layout.buddy_icon_size'),
                            fireonslide = True)(adv_panel,pre)

    buddypadding_slider, s2 = Slider('padding',
                                    _('Buddy padding:'),
                                    start = 0, stop = 12, step = 1,
                                    value = get_pref('buddylist.layout.padding'),
                                    fireonslide = True)(adv_panel, pre)

    v.Add(FontFaceAndSize('name_font', _('Contact name:'))(adv_panel, pre), 0, EXPAND)
    extra_info = EnabledGroup(('', pre),
                              Check('buddylist.layout.show_extra', _('&Show extra info:')),
                              Choice('buddylist.layout.extra_info',
                                     (('status', _('Status')),
                                      ('idle',   _('Idle Time')),
                                      ('both',   _('Idle Time + Status')))),

                                      FontFaceAndSize('extra_font'))(adv_panel)
    bsizer  = VSizer()
    sssizer = VSizer()

    bsizer.AddMany([(extra_info, 0, EXPAND),
                    (OffsetGroup(('', pre), icon_check, icon_choice, bicon_slide )(adv_panel), 0, EXPAND)])

    sssizer.AddMany([
        (OffsetGroup(('', pre), status_check, status_choice)(adv_panel), 0, EXPAND),
        (OffsetGroup(('', pre), service_check, service_choice)(adv_panel), 0, EXPAND | TOP, 7),
        (buddypadding_slider, 0, EXPAND | TOP, 22),
    ])

    h = HSizer()
    h.AddMany([(bsizer, 1),
               (sssizer, 0, LEFT, 48)])
    v.Add(h, 1, EXPAND)

#    cb(None)

    PrefGroup.SPACING = old_spacing

    cp_sizer.Add(adv_panel, 0, EXPAND)
