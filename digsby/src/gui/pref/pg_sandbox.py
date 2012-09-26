from gui.pref.prefcontrols import VSizer, get_pref
from wx import EXPAND
import wx
from contacts.sort_model import ChoiceModel, CheckModel
from peak.events import trellis

class TranslatableChoices(trellis.Component):
    keys = trellis.attr()
    translations = trellis.attr()

    @trellis.maintain
    def values(self):
        return [(k,self.translations[k]) for k in self.keys]

class PrefLink(trellis.Component):
    prefname = trellis.attr()
    value = trellis.attr()

    @trellis.make
    def init_value(self):
        def on_value_changed(src, attr, old, new):
            import wx
            @wx.CallAfter
            def update():
                self.value = new
        from common import profile
        profile.prefs.add_observer(on_value_changed, self.prefname,
                                   obj = self)
        return self.value

    def go(self):
        return self.go or self.value != self.init_value
    go = trellis.maintain(go, initially=False)

    @trellis.perform
    def output_pref(self):
        if self.go:
            from gui.pref.prefcontrols import mark_pref
            if get_pref(self.prefname) != self.value:
                mark_pref(self.prefname, self.value)

def panel(panel, sizer, addgroup, exithooks):
    from gui.pref.pg_contact_list import SyncingCheck, SyncingChoice
    p = wx.Panel(panel)
    sz = p.Sizer = VSizer()

    s = wx.FlexGridSizer(6, 1, 7,7)
    prefix = 'buddylist.layout.'
    Cells = trellis.Cells

    layout_model = LayoutModel(
                               service      = get_pref(prefix+'service_icon_pos'),
                               se_enabled   = get_pref(prefix+'show_service_icon'),
                               status       = get_pref(prefix+'status_icon_pos'),
                               st_enabled   = get_pref(prefix+'show_status_icon'),
                               icon         = get_pref(prefix+'buddy_icon_pos'),
                               icon_enabled = get_pref(prefix+'show_buddy_icon'),
                               )
    #hook up helper models
    cells = Cells(layout_model)

    service_icon_pos  = PrefLink(prefname=prefix+'service_icon_pos',  value = cells['service'])
    show_service_icon = PrefLink(prefname=prefix+'show_service_icon', value = cells['se_enabled'])
    status_icon_pos   = PrefLink(prefname=prefix+'status_icon_pos',   value = cells['status'])
    show_status_icon  = PrefLink(prefname=prefix+'show_status_icon',  value = cells['st_enabled'])
    buddy_icon_pos    = PrefLink(prefname=prefix+'buddy_icon_pos',    value = cells['icon'])
    show_buddy_icon   = PrefLink(prefname=prefix+'show_buddy_icon',   value = cells['icon_enabled'])

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

    #Trellis will keep the rest alive
    s.links = [layout_model, service_icon_pos, show_service_icon, status_icon_pos, show_status_icon, buddy_icon_pos, show_buddy_icon]

    service_check   = SyncingCheck(service_enabled, p)
    service_choice  = SyncingChoice(service_model, p)
    status_check    = SyncingCheck(status_enabled, p)
    status_choice   = SyncingChoice(status_model, p)
    icon_check      = SyncingCheck(icon_enabled, p)
    icon_choice     = SyncingChoice(icon_model, p)

    s.Add(service_check)
    s.Add(service_choice)
    s.Add(status_check)
    s.Add(status_choice)
    s.Add(icon_check)
    s.Add(icon_choice)

    s.AddGrowableCol(1,1)
    sz.Add(s, 0, EXPAND)

    sizer.Add(p)

    return panel

BUMP = {'left':'fleft',
        'fleft':'left',
        'right':'fright',
        'fright':'right',
        'bleft':'bright',
        'bright':'bleft'}

VACUUM = {'fleft':'left',
          'fright':'right'}

class LayoutModel(trellis.Component):
    icon_enabled = trellis.attr(True)
    se_enabled = trellis.attr(True)
    st_enabled = trellis.attr(True)
    icon = trellis.attr('left')

    @trellis.maintain
    def monitor_icon(self):
        ie = self.icon_enabled
        st = self.status
        se = self.service
        i = self.icon
        if not ie:
            if i == 'left': pos = ['fleft', 'left', 'bleft', 'bright']
            else:           pos = ['bleft', 'bright', 'right', 'fright']

            from_  = [None, None, None, None]
            if self.st_enabled and st in pos: from_[pos.index(st)] = 'status'
            if self.se_enabled and se in pos: from_[pos.index(se)] = 'service'
            to = filter(None, from_)
            out = [None, None]
            if i == 'left':
                if to:     out[-len(to):] = to
                if out[0]: setattr(self, out[0], 'fleft')
                if out[1]: setattr(self, out[1], 'left')
            else:
                if to:     out[:len(to)] = to
                if out[0]: setattr(self, out[0], 'right')
                if out[1]: setattr(self, out[1], 'fright')

    @trellis.maintain
    def service(self):
        se = self.service
        st = self.status
        if se == st and se in BUMP:
            return BUMP[se]
        if se in VACUUM and st != VACUUM[se]:
            return VACUUM[se]
        return se

    @trellis.maintain
    def status(self):
        st = self.status
        se = self.service
        if st == se and st in BUMP:
            return BUMP[st]
        if st in VACUUM and se != VACUUM[st]:
            return VACUUM[st]
        return st

    @trellis.maintain
    def status_choices(self):
        return self._choices(other=self.service, other_enabled=self.se_enabled)

    @trellis.maintain
    def service_choices(self):
        return self._choices(other=self.status, other_enabled=self.st_enabled)

    def _choices(self, other, other_enabled):
        out = []
        if other_enabled and other in ('left', 'fleft'):
            out.append('fleft')
        out.append('left')
        if self.icon_enabled:
            out.extend(['bleft', 'bright'])
        out.append('right')
        if other_enabled and other in ('right', 'fright'):
            out.append('fright')
        return out

    @trellis.maintain
    def monitor_enabled(self):
        if not self.st_enabled and self.se_enabled:
            se = self.service
            if se in VACUUM:
                self.service = VACUUM[se]
                if VACUUM[se] in BUMP:
                    self.status = BUMP[VACUUM[se]]
        if not self.se_enabled and self.st_enabled:
            st = self.status
            if st in VACUUM:
                self.status = VACUUM[st]
                if VACUUM[st] in BUMP:
                    self.service = BUMP[VACUUM[st]]

class Selection(trellis.Component):
    value = trellis.attr()
    choices = trellis.attr()
    selection = trellis.attr(None)
    enabled = trellis.attr()

    @trellis.maintain
    def last_set_selection(self):
        if self.selection is None:
#            print '--initialize', self.current_selection
            self.selection = self.current_selection
            return self.current_selection
        if self.current_selection == self.selection:
#            print '--match ext', self.selection
            return self.current_selection
        if self.current_selection == self.last_set_selection:
#            print '--match int'
            if self.selection >= 0:
#                print '--set int',self.selection
                self.current_selection = self.selection
                self.set_value(self.selection)
                return self.selection
        if self.selection == self.last_set_selection:
#            print '--set ext', self.current_selection
            self.selection = self.current_selection
            return self.current_selection
#        print '--returning', self.current_selection
        return self.current_selection

    @trellis.maintain
    def current_selection(self):
        if not self.enabled:
            return -1
        if self.value in self.choices:
            return self.choices.index(self.value)
        return -1

    def set_value(self, pos):
        self.value = self.choices[pos]

if __name__ == '__main__':
    class watch(trellis.Component):
        w= trellis.attr()
        @trellis.perform
        def foo(self):
            print 'service:', self.w.service
            print 'status:', self.w.status
            print 'service_choices:', self.w.service_choices
            print 'status_choices:', self.w.status_choices
    f = LayoutModel(service='fleft', status='fleft', se_enabled=True)
    cells = trellis.Cells(f)
    se = Selection(value = cells['service'], choices=cells['service_choices'])
    st = Selection(value = cells['status'], choices=cells['status_choices'])
    w = watch(w=f)
#    f.icon_enabled = True
#
#    f.service = 'bleft'
#    f.status = 'right'
#    f.icon = 'right'
#
#    print '#'*80
#    print se.selection
#    se.selection = 0
#    f.service = 'right'
#    print se.selection
#    st.selection=3
#    print se.selection


