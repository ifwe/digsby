'''
Contact List tab for the preferences dialog.
'''

from common import pref, profile
from peak.events import trellis

class ChoiceModel(trellis.Component):
    values = trellis.attr([])
    selection = trellis.attr(0)
    enabled = trellis.attr(True)

class CheckModel(trellis.Component):
    checked = trellis.attr(False)
    enabled = trellis.attr(True)

class SortOptionWatcher(trellis.Component):
    model = trellis.attr(None)

    @trellis.perform
    def print_selection(self):
        if self.model is not None:
            print 'selected', self.model.selection

class OptionLink(trellis.Component):
    parent = trellis.attr()
    this   = trellis.attr()
    child  = trellis.attr()
    dependant = trellis.attr(True)
    name = trellis.attr()

    @trellis.maintain
    def selected_val(self):
        try:
            return self.this.values[self.this.selection]
        except Exception:
            pass

    @trellis.make
    def orig_values(self):
        return self.this.values[:]

    @trellis.maintain
    def available_options(self):
        newvals = [val for val in self.orig_values
                   if val not in self.parent_vals or val[0] == 'none']
        return newvals

    @trellis.maintain
    def parent_vals(self):
        c = self
        parent_vals = []
        while c.parent is not None:
            if c.parent.selected_val is not None:
                parent_vals.append(c.parent.selected_val)
            c = c.parent
        return parent_vals

    @trellis.maintain
    def enabled(self):
        if not self.dependant:
            return True
        if not self.parent:
            return True
        if not self.parent.enabled:
            return False
        if self.parent.selected_val is None or self.parent.selected_val[0] in ['none', 'name']:
            return False
        return True

    @trellis.maintain
    def keepenabled(self):
        self.this.enabled = self.enabled

    @trellis.maintain
    def sync_values(self):
        newvals = self.available_options
        if not self.enabled:
            self.this.selection = -1
            self.this.values = []
            return
        if self.this.selection > 0 and self.this.values and newvals:
            oldval = self.this.values[self.this.selection]
            if oldval in newvals:
                self.this.selection = newvals.index(oldval)
            else:
                self.this.selection = 0
        elif not newvals:
            self.this.selection = -1
        else:
            self.this.selection = 0
        self.this.values = newvals

def set_sort_values(*a):
    sortby = pref('buddylist.sortby')
    sorts = sortby.split()
    if not sortby.startswith('*'):
        sorts.insert(0, 'none')
    else:
        sorts[0] = sorts[0][1:]
    if len(a) > len(sorts):
        sorts.extend(['none'] * (len(a) - len(sorts)))
    for model, val in zip(a, sorts):
        try:
            model.selection = [v[0] for v in model.values].index(val)
        except ValueError:
            #in my case, 'log status' isn't allowed now.
            break

def get_sort_value(group_by, *sort_bys):
    out = []
    if group_by.selection >= 0:
        gb_val = group_by.values[group_by.selection][0]
        if gb_val != 'none':
            out.append('*' + gb_val)
    for sort_by in sort_bys:
        if sort_by.selection >= 0:
            sb_val = sort_by.values[sort_by.selection][0]
            if sb_val == 'none':
                break
            out.append(sb_val)
        else:
            break
    if len(out) < 2:
        out.extend(['none']*(2-len(out)))
    return ' '.join(out)

class SortByWatcher(trellis.Component):
    def __init__(self, sorts):
        trellis.Component.__init__(self)
        self.sorts = sorts

    @trellis.perform
    def output_pref(self):
        val = get_sort_value(*self.sorts)
        from gui.pref.prefcontrols import mark_pref
        mark_pref('buddylist.sortby', val)

GROUP_BY_CHOICES = [
                        ('none',    _('None (custom)')),
                        ('status',  _('Status')),
                        ('service', _('Service')),
                   ]
SORT_BY_CHOICES  = [
                        ('none',    _('None')),
                        ('log',     _('Log Size')),
                        ('name',    _('Name')),
                        ('status',  _('Status')),
                        ('service', _('Service')),
                    ]

def build_models(then_bys=1, obj=None):
    #build models
    models = [ChoiceModel(values = GROUP_BY_CHOICES[:])]
    models.extend([ChoiceModel(values = SORT_BY_CHOICES[:])
                   for _i in range(then_bys+1)])

    models[0].link = OptionLink(
                                this   = models[0],
                                child  = models[1],
                                name   = 'group_by')
    models[1].link = OptionLink(parent = models[0].link,
                                this   = models[1],
                                child  = models[2],
                                dependant = False,
                                name   = 'sort_by')
    for i in range(then_bys):
        this_idx = i + 2
        this = models[this_idx]
        if this_idx + 1 < len(models):
            chld = models[this_idx + 1]
        else:
            chld = None
        this.link =  OptionLink(parent = models[this_idx - 1].link,
                                this   = this,
                                child  = chld,
                                name   = 'then_by%d' % (i+1))

    #this needs to be inside a "maintain" rule hooked from prefs
    # should set the value of a maintain rule from prefs,
    # a rule based on itself, so it will push down on a change, then
    # return it's value which can be pushed to prefs in a perform rule, at
    # which point, nothing should change, so we can stop there.
    #read pref, set selections:
    set_sort_values(*models)

    def on_sortby_changed(src, attr, old, new):
        import wx
        wx.CallAfter(set_sort_values, *models)

    profile.prefs.add_observer(on_sortby_changed, 'buddylist.sortby',
                               obj = obj)
    return models

