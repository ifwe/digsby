'''

advanced prefs editor

'''

from __future__ import with_statement
from util import dictadd, boolify as bool_from_string, is_all
import wx.lib.mixins.listctrl
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from wx import VERTICAL, HORIZONTAL, TOP, BOTTOM, LEFT, RIGHT, EXPAND, ALL, ALIGN_CENTER, ALIGN_RIGHT, \
    FONTWEIGHT_BOLD, WXK_DOWN
from prefsdata import nice_name_types, nice_type_names
from common import profile, delpref

class PrefsViewer(wx.Panel):
    """
    View and edit preferences.

    Digsby's about:config.
    """

    columns = ('Preference Name', 'Status', 'Type', 'Value')

    def __init__(self, parent, prefs, defaults):
        wx.Panel.__init__(self, parent, -1)

        self.prefs = prefs
        self.defaults = defaults

        self.construct_gui()

        prefs.add_observer(self.pref_changed)
        parent.Bind(wx.EVT_CLOSE, self.on_frame_closed)

        self.sort = (0, False)  # sort by column zero, ascending
        self.on_filter_txt()

        # do some nitpicky platform specific cosmetic adjustments
        self.prefs_list.SetColumnWidth(0,-1)
        if wx.Platform != '__WXMAC__': offset = 20
        else: offset = 25
        self.prefs_list.SetColumnWidth(0,self.prefs_list.GetColumnWidth(0) + offset)

    def pref_changed(self, source, pref, old, new):
        wx.CallAfter(self.on_filter_txt)

    def on_frame_closed(self, e = None):
        if hasattr(profile, 'localprefs'):
            profile.localprefs['advanced_prefs.filter'] = self.filter_txt.Value
        self.prefs.remove_observer(self.pref_changed)
        if getattr(self, '_did_change_pref', False):
            profile.save('prefs')
        e.Skip(True)

    def filtered_prefs(self, substr=""):
        sum = dictadd(self.defaults, self.prefs)

        # find all keys not containing substr
        substr = substr.lower()
        remove_these_keys = [key for key in sum if key.lower().find(substr) == -1]

        # remove them
        for key in remove_these_keys:
            sum.pop(key)

        return sum

    def construct_gui(self):
        # create and setup the fiter text box
        if hasattr(profile, 'localprefs'):
            filter = profile.localprefs.get('advanced_prefs.filter', u'')
        else:
            filter = u''

        self.filter_txt = wx.TextCtrl(self, -1, filter)

        [self.filter_txt.Bind(e,m) for e,m in [
            (wx.EVT_TEXT,     self.on_filter_txt),
            (wx.EVT_KEY_DOWN, self.on_filter_text_key)
        ]]

        # create and setup the preferences list control
        self.prefs_list = PrefsListCtrl(self)
        for e, m in [(wx.EVT_LIST_ITEM_ACTIVATED, self.on_dclick),
                     (wx.EVT_LIST_COL_CLICK,      self.on_col_click),
                     (wx.EVT_RIGHT_UP,            self.on_right_up),
                     (wx.EVT_RIGHT_DOWN,          self.on_right_down)]:
            self.prefs_list.Bind(e, m)

        # insert columns
        for i in xrange(len(self.columns)):
            self.prefs_list.InsertColumn(i, self.columns[i])

        self.show_all = wx.Button(self, -1, "Sho&w All")
        self.show_all.Bind(wx.EVT_BUTTON, lambda e: self.filter_txt.SetValue('') if self.filter_txt.GetValue() != '' else None)

        self.add_new = wx.Button(self, -1, '&Add')
        self.add_new.Bind(wx.EVT_BUTTON, self.add_new_pref)

        self.push_now = wx.Button(self, -1, '&Push Now')
        self.push_now.Bind(wx.EVT_BUTTON, lambda e: profile.save('prefs'))

        # layout components
        hbox = wx.BoxSizer(HORIZONTAL)


        hbox.AddMany([(wx.StaticText(self, -1, "Filter:", style=ALIGN_CENTER), 0, TOP | LEFT | BOTTOM | ALIGN_CENTER, 8),
                     (self.filter_txt, 100, EXPAND | ALL, 8),
                     (self.show_all,   0,   TOP | BOTTOM, 8),
                     (self.add_new,    0,   TOP | BOTTOM | RIGHT, 8)])

        vbox = wx.BoxSizer(VERTICAL)
        vbox.AddMany([(hbox, 0, EXPAND),
                     (self.prefs_list, 1, EXPAND),
                     (self.push_now, 0, ALL | ALIGN_RIGHT, 8)])

        self.SetSizer(vbox)

        def foo(e):
            print e
        self.Bind(wx.EVT_BUTTON, foo)

    def add_new_pref(self, e):
        key = str(wx.GetTextFromUser('Please enter the name for the pref', 'Add pref', self.filter_txt.Value))
        if not key: return
        typ = str(wx.GetSingleChoice('Please choose the type for the pref', 'Add pref', nice_type_names.values()))
        if not typ: return
        typ = nice_name_types[typ]

        if typ is list:
            from gui.toolbox import edit_list
            ok, val = edit_list(self, [], 'Editing %s' % key)
            if not ok: return
        else:
            val = str(wx.GetTextFromUser('Please enter the value for the pref','Add pref'))
            val = bool_from_string(val) if typ is bool else typ(val)
            if val == '': return

        self.prefs[key] = val


    def on_filter_txt(self, e = None):
        """
        Called when the filter text changes.

        Updates the table to reflect the new filter.
        """
        self.update_list(self.filtered_prefs(self.filter_txt.Value))

    def get_default_string(self, key):
        "Returns 'default' or 'user-set' for the indicated preference."

        try:
            val = self.prefs[key]
        except KeyError:
            return 'default'
        else:
            return 'default' if val  == self.defaults.get(key, sentinel) else 'user-set'

    def update_list(self, prefs_dict, n = -1):
        '''
        Called everytime text is entered in the filter text control.

        Rebuilds and resorts the list.
        '''

        self.shown = []
        append = self.shown.append
        plist  = self.prefs_list
        sel    = plist.GetFirstSelected()
        getdefstr = self.get_default_string


        with plist.Frozen():
            plist.DeleteAllItems()

            SetStringItem = plist.SetStringItem

            for i, (key, value) in enumerate(prefs_dict.iteritems()):
                def_string = getdefstr(key)

                plist.InsertStringItem(i, key)
                SetStringItem(i, 1, def_string)
                SetStringItem(i, 2, nice_type_names[type(value)])
                SetStringItem(i, 3, str(value))
                plist.SetItemData(i, i)

                if def_string == 'user-set':
                    item = plist.GetItem(i)
                    f = item.Font
                    f.SetWeight(FONTWEIGHT_BOLD)
                    item.SetFont(f)
                    plist.SetItem(item)

                append((key, value))
                i += 1

            plist.SortItems(self.on_sort)
            # don't call EnsureVisible if we don't have a selection
            if sel != -1:
                plist.EnsureVisible(sel)

    def on_filter_text_key(self, e):
        """
        Catches down arrows from the filter box to allow jumping to the table
        via keyboard.
        """
        if e.KeyCode == WXK_DOWN:
            self.prefs_list.SetFocus()
        else:
            e.Skip(True)

    def on_col_click(self, e):
        c = e.GetColumn()

        if c == self.sort[0]: ascending = not self.sort[1]
        else: ascending = False

        self.sort = (c, ascending)
        self.prefs_list.SortItems(self.on_sort)

    def on_sort(self, one, two):
        one, two = self.shown[one], self.shown[two]

        column, ascending = self.sort

        _cmp = {0 : lambda x: x[0],
                1 : lambda x: self.get_default_string(x[0]),
                2 : lambda x: nice_type_names[type(x[1])],
                3 : lambda x: str(x[1])}.get(column, None)

        # XNOR!
        # equivalent to:
        # v = _cmp(one)<_cmp(two)
        # return v if ascending else not v
        return ascending == (_cmp(one) < _cmp(two))

    def on_dclick(self, e):
        key = e.GetText()
        from util.primitives.funcs import get
        mysentinel = Sentinel() #@UndefinedVariable
        defval = get(self.defaults, key, mysentinel)
        val    = self.prefs.setdefault(key, defval)

        preftype = defval.__class__ if defval is not mysentinel else val.__class__

        if issubclass(preftype, bool):
            val = not val

        elif isinstance(val, list):
            if is_all(val, (str, unicode))[0]:
                from gui.toolbox import edit_string_list
                ok, new_list = edit_string_list(self, val, 'Editing ' + key)
                if ok and new_list: val = new_list
                elif ok: val = defval
            elif is_all(val)[0]:
                from gui.toolbox import edit_list
                ok, new_list = edit_list(self, val, 'Editing ' + key)
                if ok and new_list: val = new_list
                elif ok: val = defval
            else:
                print is_all(val)
                raise AssertionError, key + \
                    ' is not a homogenous list :( tell Kevin to make this more gooder'

            if val == defval and defval is mysentinel:
                delpref(str(key))
                return

        elif isinstance(defval, (str,unicode,int,float)) or defval is mysentinel:
            t = type(val) if defval is mysentinel else type(defval)

            print 'editing pref of type',t

            diag = wx.TextEntryDialog(self, key, 'Enter %s' % nice_type_names[t], str(val))

            if diag.ShowModal() == wx.ID_OK:
                val = diag.GetValue()

                if t is bool:
                    val = bool_from_string(val)
                if val != '':
                    val = t(val)
                elif defval is not mysentinel:
                    val = defval
                else:
                    delpref(str(key))
                    return

        self.prefs[str(key)] = val
        self.on_filter_txt()
        self._did_change_pref = True

    def on_right_up(self, e):
        i = self.prefs_list.GetFirstSelected()

    def on_right_down(self, e):
        e.Skip(True)

class PrefsFrame(wx.Frame):
    def __init__(self, prefs, defaults, parent=None, id=-1, title="Advanced Preferences", name = 'Advanced Preferences'):
        wx.Frame.__init__(self, parent, id, title,
                          style = wx.DEFAULT_FRAME_STYLE & ~(wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX))

        self.prefs_viewer = PrefsViewer(self, prefs, defaults)

        from gui.toolbox import persist_window_pos, snap_pref
        persist_window_pos(self, unique_id = 'PrefsFrame',
                           defaultPos = wx.Point(100, 100),
                           defaultSize = wx.Size(600, 500),
                           position_only = True)
        snap_pref(self)

class PrefsListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
    list_style = wx.LC_REPORT | wx.SUNKEN_BORDER | wx.LC_SINGLE_SEL

    def __init__(self, parent, id=-1, style = None):
        wx.ListCtrl.__init__(self, parent, id, style=style or self.list_style)
        ListCtrlAutoWidthMixin.__init__(self)


def edit(prefs, defaults, parent=None):
    'Toggles the advanced preference frame.'

    for win in wx.GetTopLevelWindows():
        if isinstance(win, PrefsFrame):
            return win.Close()

    f = PrefsFrame(parent=parent, prefs=prefs, defaults=defaults)
    wx.CallAfter(f.Show)
