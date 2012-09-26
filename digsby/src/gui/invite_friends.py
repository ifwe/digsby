from .anylists import AnyRow
from .pref import prefcontrols
from .uberwidgets.PrefPanel import PrefPanel
from common import profile as p #@UnresolvedImport
from gui.anylists import AnyList
from util.observe import ObservableList
from util.callbacks import callsback
import wx

class StaticEmailRow(AnyRow):
    checkbox_border = 3
    row_height = 20
    image_offset = (6, 0)

    def __init__(self, *a, **k):
        AnyRow.__init__(self, *a, **k)

    def PopulateControls(self, account):
        self.checkbox.Value = True
        self.text = self.data[1]

    @property
    def image(self):
        return self.data[0]

    def on_right_up(self, *a, **k):
        pass


def f_f(a, b):
    def factory(*args):
        return a(b(*args))
    factory.__repr__ = \
    lambda: '''<factory composing %(a)r with %(b)s>''' % locals()
    return factory

pen_f = f_f(wx.Pen, wx.Color)
brush_f = f_f(wx.Brush, wx.Color)

def pen_f_f(*a):
    return lambda: pen_f(*a)

def brush_f_f(*a):
    return lambda: f_f(wx.Brush, wx.Color)(*a)

webmail_types = frozenset(('gmail', 'ymail', 'aolmail', 'hotmail'))

TIME_UNTIL_SPAM = 60 * 60 * 24 * 7

def do_user_initiated_check():
    make_invite_diag(background = False, success=dialog_closed_callback)

def do_background_check():
    from common import pref, setpref
    from time import time
    invite_times = pref('usertrack.invite.dialog.results', type=dict, default={})
    if invite_times:
        return
    if not any(e.protocol in webmail_types for e in p.emailaccounts[:]):
        return
    first_online = pref('usertrack.firstknownonline', type=int, default=-1)
    if not first_online > 0:
        setpref('usertrack.firstknownonline', int(time()))
        return
    elif int(time()) - first_online < 60 * 60 * 24 * 7:
        return
    else:
        make_invite_diag(background = True, success=dialog_closed_callback)

def dialog_closed_callback(result):
    from util import Storage as S
    from time import time
    from common import pref, setpref
    result = S(result)
    invite_times = pref('usertrack.invite.dialog.results', type=dict, default={})

    num_email_accts = len(p.emailaccounts)
    num_webmail_accts = len([e.protocol in webmail_types for e in p.emailaccounts[:]])

    track_data = dict(
         accts=len(result.accts),
         web_accts = num_webmail_accts,
         email_accts = num_email_accts,
         background=result.background,
         send=result.send
         )

    num_not_triggered = sum(t.get('background', False) for t in invite_times.values())
    if not result.background or num_not_triggered < 5:
        invite_times[int(time())] = track_data
        setpref('usertrack.invite.dialog.results', invite_times)

    if result.send:
        from pprint import pprint
        print 'would send:'
        pprint(result.accts)

@callsback
def make_invite_diag(background = False, callback = None):
    f = wx.Dialog(None)
    f.Sizer = wx.BoxSizer(wx.VERTICAL)

    p1 = InvitePanel(f)

    def handle_invite_done(e):
        #handle
        if e.EventType in wx.EVT_BUTTON:
            print 'send was hit'
            name, accts = p1.info()
            if not name:
                return wx.MessageBox('Please enter your name so that ...\n will know from whom the invites were sent.', 'Please enter your name.')
            callback.success(dict(name=name, accts=accts, background=background, send=True))
        elif e.EventType in wx.EVT_CLOSE:
            name, accts = p1.info()
            callback.success(dict(name=name, accts=accts, background=background, send=False))
        else:
            assert False
        f.Show(False)
        f.Destroy()

    f.Bind(wx.EVT_CLOSE, handle_invite_done)
    f.Bind(wx.EVT_BUTTON, handle_invite_done)

    f.Sizer.Add(p1, 1, wx.EXPAND)
    p1.Layout()
    f.Layout()
    f.Fit()
    f.SetMinSize(f.GetSize())
    f.Show()
    return f

class InvitePanel(wx.Panel):

    def __init__(self, *a, **k):
        if k.get('name') is not None:
            k['name'] = 'Invite Panel'

        wx.Panel.__init__(self, *a, **k)

        accounts = [e for e in p.emailaccounts[:] if e.protocol in ('gmail', 'ymail', 'aolmail', 'hotmail')]

        data = []
        for acct in accounts:
            if acct.icon is not None:
                ico = acct.icon.Resized(16)
            else:
                ico = None
            data.append(
                        (
                         ico,
                         acct.display_name,
                         acct.protocol,
                         acct.name,
                         acct._decryptedpw()
                         )
                        )
        self.data = data
        self.Construct()
        self.Fonts()
        self.Layout()

    def Construct(self):
        parent = self

        self.line1 = wx.StaticText(parent, label="We hope you've enjoyed using Digsby.", style=wx.TE_CENTER)
        self.line2 = wx.StaticText(parent, label="Please show your support and invite your friends.", style=wx.TE_CENTER)

        self.separator = wx.StaticLine(parent)

        self.name_label = wx.StaticText(parent, label='Full Name: ')
        self.name_text  = wx.TextCtrl(parent)

        self.acct_list = AnyList(
                                 parent,
                                 ObservableList(self.data),
                                 row_control     = StaticEmailRow,
                                 multiselect     = False,
                                 edit_buttons    = None,
                                 draggable_items = False,
                                 style           = 0,
                                 velocity        = None
                                )
        self.acct_list.SetMinSize(wx.Size(-1, (16+10) * 4))

        self.acct_panel = PrefPanel(parent, self.acct_list, 'Account')
        self.acct_panel._bg_brush = lambda: wx.Brush (wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE))
        self.acct_panel._fg_pen   = lambda: wx.Pen   (wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW))

        self.send_button = wx.Button(parent, wx.ID_OK, label='Send Invite!')
        self.send_button.MoveAfterInTabOrder(self.name_text)

    def info(self):
        # iter(AnyList) is bad news
        acct_list = self.acct_list
        acct_list = [acct_list[i] for i in xrange(len(acct_list))]
        return self.name_text.Value, [acct.data[2:] for acct in acct_list if acct.checkbox.Get3StateValue() == wx.CHK_CHECKED]

    def Fonts(self):
        #===============================================================================================================
        # top 2 lines
        #===============================================================================================================
        fnt1 = self.line1.Font

        fnt1.SetPointSize(fnt1.GetPointSize() + 4)
        fnt1.SetWeight(wx.FONTWEIGHT_BOLD)

        self.line1.Font = fnt1
        self.line2.Font = fnt1

        #===============================================================================================================
        #===============================================================================================================
        fnt2 = self.name_label.Font
        fnt2.SetPointSize(fnt2.GetPointSize() + 2)
        self.name_label.Font = fnt2

    def Layout(self):
        self.Sizer = s1 = prefcontrols.VSizer()

        #===============================================================================================================
        # top 2 lines
        #===============================================================================================================
        s1.Add(self.line1,    0, wx.EXPAND | wx.ALL, 5)
        s1.Add(self.line2,    0, wx.EXPAND | wx.ALL & ~wx.TOP, 5)
        s1.Add(self.separator,0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        #===============================================================================================================
        # Full Name: ---------------
        #===============================================================================================================
        s2 = prefcontrols.HSizer()

        s2.AddSpacer(6)
        s2.Add(self.name_label, 0, wx.EXPAND)
        s2.Add(self.name_text,  3, wx.EXPAND)
        s2.AddSpacer(6)

        s1.Add(s2,              0, wx.EXPAND | wx.ALL, 9)

        #===============================================================================================================
        # panel full of checkboxes
        #===============================================================================================================
        s1.Add(self.acct_panel, 1, wx.EXPAND | wx.ALL & ~wx.TOP, 15)

        #===============================================================================================================
        # Send Invites! (click)
        #===============================================================================================================
        s3 = prefcontrols.HSizer()

        s3.AddStretchSpacer     (20)
        s3.Add(self.send_button, 60, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL & ~wx.TOP, 3)
        s3.AddStretchSpacer     (20)

        s1.Add(s3, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND | wx.BOTTOM, 6)

