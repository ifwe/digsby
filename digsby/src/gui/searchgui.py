'''
search gui
'''

import wx

import common.search as search
from common import setpref, profile, action

from gui.visuallisteditor import VisualListEditor, VisualListEditorList

def set_searches(engine_list, checked):
    engine_dicts = [e.dict(enabled=checked[n])
                    for n, e in enumerate(engine_list)]
    setpref('search.external', engine_dicts)

class SearchEditor(VisualListEditorList):
    'small drag and drop editor for enabling/rearranging searches'

    text_alignment = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL

    def get_icon(self, searchname):
        from gui import skin
        return skin.get('appdefaults.search.icons.' + searchname, None)

    def OnDrawItem(self, dc, rect, n):
        VisualListEditorList.OnDrawItem(self, dc, rect, n)
        icon = self.get_icon(self.GetItem(n).name)
        if icon is None:
            return

        # Draw search favicons on the right side of the list
        dc.DrawBitmap(icon, rect.Right - icon.Width - 32, rect.VCenter(icon), True)

class SearchEditDialog(VisualListEditor):
    text_alignment = wx.ALIGN_LEFT

    def __init__(self, parent):
        VisualListEditor.__init__(self, parent,
            list2sort    = search.searches,
            prettynames  = lambda search: search.gui_name,
            listcallback = set_searches,
            title        = _('Arrange Searches'),
            listclass    = SearchEditor,
            ischecked    = lambda search: search.enabled)

def edit(parent = None):
    search.link_prefs(profile.prefs)
    SearchEditDialog(parent).Show()

#
# buddylist classes
#
from common.actions import ActionMeta

class SearchEntryBase(object):
    __metaclass__ = ActionMeta

class SearchEntry(SearchEntryBase):
    'Corresponds to one web search entry on the buddylist.'

    def __init__(self, searchengine, searchstring):
        self.searchengine = searchengine
        self.searchstring = searchstring

        # this attribute is to make TreeList happy
        self.name = '%s: %s' % (searchengine.name, searchstring)

    # eq and hash do not include searchstring in their calculation, so that
    # selecting Google, for example, and then changing the query string, will
    # result in Google still being selected.

    def __eq__(self, other):
        return self is other or (self.searchengine == other.searchengine)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(''.join((self.__class__.__name__, self.searchengine.__repr__())))

    def activate(self):
        self.searchengine.search(self.searchstring)

    @property
    def menu_search_string(self):
        'used in the context menu for the "search" item'

        return _(u'Search {search_engine_name:s} for "{search_string:s}"').format(search_engine_name=self.searchengine.gui_name,
                                                                                  search_string=self.searchstring)

    def delete(self):
        from common.search import searches
        s = searches[:]

        for e in s:
            if self.searchengine == e:
                e.enabled = False

        setpref('search.external', [e.dict() for e in s])

class SearchOptionsEntry(SearchEntryBase):
    '''options... link at the end of searches'''

    inherited_actions = [SearchEntry]

    def __init__(self):
        # for treelist
        self.name = '__searchoptionsentry__'

    def __eq__(self, other):
        return self is other or isinstance(other, self.__class__)

    def __hash__(self):
        return hash(self.name)

    def activate(self):
        edit()

    @property
    def menu_search_string(self):
        return _('Options...')

    @action(lambda self: False)
    def delete(self):
        pass

class SearchWebGroup(list):
    'the special "Search Web" group on the buddylist'

    __metaclass__ = ActionMeta
    searchweb_name = _('Web Search')

    def edit(self):
        edit(wx.FindWindowByName('Buddy List'))

    def __init__(self):
        self.name = self.searchweb_name

    def __hash__(self):
        return hash(self.name)

    @property
    def display_string(self):
        return self.searchweb_name

def add_search_entries(view, search):
    '''
    adds search items to a buddylist tree
    '''

    from common.search import enabled_searches

    search_group = SearchWebGroup()

    # add an entry for each enabled search
    search_group.extend((SearchEntry(s, search) for s in enabled_searches()))

    # add an Options... link at the end.
    search_group.append(SearchOptionsEntry())

    view.append(search_group)

