import wx
import sys
from copy import deepcopy
from wx import StaticText, EXPAND, TOP, ALIGN_CENTER, VERTICAL, HORIZONTAL, \
    Color, ALIGN_CENTER_VERTICAL, CheckBox, Choice
from gettext import ngettext
from gui.uberwidgets.autoheightstatictext import AutoHeightStaticText

UPDATE_DESC_TEXT = _('Twitter allows for 150 requests per hour. Make sure to leave room for manual updates and other actions.')

# A choice appears for each of these update type
UPDATE_TYPES = [
    # protocolmeta key   gui string
    ('friends_timeline', _('Friends:')),
    ('replies',          _('Mentions:')),
    ('direct_messages',  _('Directs:')),
    ('search_updatefreq',_('Searches:')),
]

def adds_to_total(updatetype):
    return updatetype != 'search_updatefreq' # searches don't cost API calls

# Options you can pick for each update type.
UPDATE_CHOICES = [('1',  1),
                  ('2',  2),
                  ('3',  3),
                  ('4',  4),
                  ('5',  5),
                  ('10', 10),
                  ('15', 15),
                  ('20', 20),
                  ('30', 30)]

# append "minutes" to all the strings above
UPDATE_CHOICES = [(ngettext('{mins} minute', '{mins} minutes', n).format(mins=n), n) for s, n in UPDATE_CHOICES]

# add a Never option
UPDATE_CHOICES.append((_('Never'), 0))

UPDATE_GUI_STRINGS = [s for s, n in UPDATE_CHOICES]

UPDATE_VALUES = dict((n, i) for i, (s, n) in enumerate(UPDATE_CHOICES))

def color_for_total(total):
    'Returns a wx color for an update count per hour.'

    if total > 150:   return Color(0xFF, 0, 0)
    elif total > 125: return Color(0xFF, 0xA5, 0x00)
    else:            return Color(0, 0, 0)

def protocolinfo():
    from common.protocolmeta import protocols
    return protocols['twitter']

class TwitterAccountPanel(wx.Panel):
    '''
    Selects update frequencies for different Twitter update types.

    Shows in the account dialog when editing Twitter accounts.
    '''
    def __init__(self, parent, account):
        wx.Panel.__init__(self, parent)

        self.construct()
        self.layout()
        self.Bind(wx.EVT_CHOICE, self.SelectionChanged)

        # force an initial update
        self.set_values(account)
        self.SelectionChanged()

    @property
    def show_server_options(self):
        return getattr(sys, 'DEV', False)

    def set_values(self, account):
        # set initial values based on information from a Twitter Account
        defaults = deepcopy(protocolinfo().defaults)
        defaults.update(getattr(account, 'update_frequencies', {}))

        self.auto_throttle.Value = getattr(account, 'auto_throttle', defaults.get('auto_throttle'))

        for name, _ in UPDATE_TYPES:
            self.choices[name].Selection = UPDATE_VALUES.get(defaults.get(name), 4)

        if self.show_server_options:
            api_server = getattr(account, 'api_server', None)
            if api_server is not None:
                self.server.Value = api_server

    def construct(self):
        'Construct GUI components.'

        self.header = StaticText(self, -1, _('Update Frequency:'))
        self.header.SetBold()

        self.desc = AutoHeightStaticText(self, -1, UPDATE_DESC_TEXT)
        self.desc.MinSize = wx.Size(40, -1)

        self.update_texts = {} # "Tweets every"
        self.choices   = {} # "0 - 10 minutes"

        # Build StaticText, Choice for each update option.
        for i, (name, guistring) in enumerate(UPDATE_TYPES):
            self.update_texts[name] = StaticText(self, -1, guistring)
            self.choices[name] = Choice(self, choices = UPDATE_GUI_STRINGS)

        self.total = StaticText(self, style = ALIGN_CENTER)
        self.total.SetBold()

        self.auto_throttle = CheckBox(self, label=_('Auto-throttle when Twitter lowers the rate limit.'), name='auto_throttle')

        if self.show_server_options:
            self.server_text = StaticText(self, -1, _('Server'))
            self.server = wx.TextCtrl(self, -1)

    def info(self):
        """
        Returns a mapping for this dialog's info.

        This looks like
        {'friends_timeline': 4,
         'replies': 4,
         'directs': 4}
        """

        d = dict((name, UPDATE_CHOICES[self.choices[name].Selection][1])
                    for name, _gui in UPDATE_TYPES)
        d['auto_throttle'] = self.auto_throttle.Value
        if self.show_server_options:
            d['api_server'] = self.server.Value.strip() or None
        return d

    def layout(self):
        'Layout GUI components.'

        gb = wx.GridBagSizer(hgap = 3, vgap = 3)

        for i, (name, guistring) in enumerate(UPDATE_TYPES):
            gb.Add(self.update_texts[name], (i, 0), flag = ALIGN_CENTER_VERTICAL)
            gb.Add(self.choices[name], (i, 1))

        gb_h = wx.BoxSizer(HORIZONTAL)
        gb_h.Add(gb, 0, EXPAND)

        t_v = wx.BoxSizer(VERTICAL)
        t_v.AddStretchSpacer(1)
        t_v.Add(self.total, 0, EXPAND | ALIGN_CENTER)
        t_v.AddStretchSpacer(1)

        gb_h.Add(t_v, 1, EXPAND | ALIGN_CENTER)

        inner_sz = wx.BoxSizer(VERTICAL)

        if self.show_server_options:
            hsz = wx.BoxSizer(HORIZONTAL)
            hsz.Add(self.server_text, 0, EXPAND | wx.RIGHT, 7)
            hsz.Add(self.server, 1, EXPAND | wx.BOTTOM, 7)
            inner_sz.Add(hsz, 0, EXPAND)

        inner_sz.AddMany([
            (self.header, 0, EXPAND),
            (self.desc,   1, EXPAND | TOP, 5),
            (gb_h,        0, EXPAND | TOP, 7),
            (self.auto_throttle, 0, EXPAND | TOP, 7),
        ])

        sz = self.Sizer = wx.BoxSizer(VERTICAL)
        sz.Add(inner_sz, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 7)

        self.Fit()

    def SelectionChanged(self, e = None):
        'Invoked when the user changes an update frequence Choice control.'

        # sum up 60/minutes for each choice to find how many updates
        # per hour we will request.
        mins = [UPDATE_CHOICES[c.Selection][1] for name, c in self.choices.items()
                if adds_to_total(name)]
        total_updates = sum(((60./min) if min else 0) for min in mins)

        # the function color_for_total will use color to warn the user
        # if there is going to be too many updates.
        total_txt = self.total
        total_txt.SetLabel(_('{total_updates} / hour').format(total_updates=int(total_updates)))
        total_txt.ForegroundColour = color_for_total(total_updates)

        self.Layout()

