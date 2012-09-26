from common import pref, setpref
from gui import skin, toolbox
from logging import getLogger
from peak.util.addons import AddOn
from threading import RLock
import branding, hooks
import re
import warnings

def url_for_protocol(protocol):
    return "http://digsby.com/" + protocol

def re_url_for_protocol():
    return "http://digsby.com/\S*"

def url_append_for_protocol(protocol):
    url = branding.get('digsby.status.url.for_protocol', 'digsby_status', default=url_for_protocol(protocol), protocol=protocol)
    if protocol == 'yahoo':
        url = url + " " + url
    return url

def tag_status(message, protocol, status=None):
    if pref('digsby.status.promote_tag.enabled', default=True) and \
       (pref('digsby.status.promote_tag.upgrade_response', default=None) is not None):
        if protocol == 'msim':
            protocol = 'myspaceim'
        if not message and status:
            message = status
        return message + " - I use " + url_append_for_protocol(protocol)
    else:
        return message

def branding_re():
    return '( ((' + ')|('.join(hooks.each('digsby.status.url.for_protocol_re')) + ')))'

BASE_RE = lambda: r"- I use" + branding_re() + "+"
TAGLINE_RE = lambda: r"\s*" + BASE_RE()

SPECIAL_STATUSES = '''
Available
Away
Idle
Invisible
Offline
'''.split()

def remove_tag_text(msg, status=None):
    for st in SPECIAL_STATUSES + ([status] if status else []):
        msg = re.sub(st + ' ' + BASE_RE(), '', msg)
    msg = re.sub(TAGLINE_RE(), '', msg)
    return msg

class StatusTagDialog(toolbox.UpgradeDialog):
    faq_link_label = _('Learn More')
    faq_link_url   = 'http://wiki.digsby.com/doku.php?id=faq#q34'

    def __init__(self, parent, title, message):
        icon = skin.get('serviceicons.digsby', None)
        if icon is not None:
            icon = icon.Resized(32)

        super(StatusTagDialog, self).__init__(parent, title,
                                     message = message,
                                     icon = icon,
                                     ok_caption = _('Yes, Spread the Word!'),
                                     cancel_caption = _('No Thanks'),
                                     link = (self.faq_link_label, self.faq_link_url))

class StatusPrefUpgrader(AddOn):
    did_setup = False
    check_fired = False
    def __init__(self, subject):
        self.profile = subject
        self.lock    = RLock()
        super(StatusPrefUpgrader, self).__init__(subject)

    def setup(self):
        with self.lock:
            if self.did_setup:
                warnings.warn('reinitialized AddOn StatusPrefUpgrader')
                return
            self.did_setup = True
        hooks.Hook('digsby.accounts.released.async', 'status_tag').register(self.check_accounts)

    def check_accounts(self, *a, **k):
        with self.lock:
            if self.check_fired:
                return
            self.check_fired = True
        from util.threads.timeout_thread import Timer
        Timer(5, self.do_check_accounts, *a, **k).start()

    def do_check_accounts(self, *a, **k):
        with self.lock:
            if pref('digsby.status.promote_tag.upgrade_response', default=None) is not None:
                return
            if len(self.profile.all_accounts) == 0:
                setpref('digsby.status.promote_tag.upgrade_response', 'skipped_ok')
            else:
                import wx
                @wx.CallAfter
                def after():
                    from gui.toast.toast import popup
                    popup(header = _('Spread the Word!'),
                          icon   = skin.get('appdefaults.taskbaricon', None),
                          major  = None,
                          minor  = _("We've made it easier to spread the word about Digsby by adding a link to your IM status. You can disable this option in Preferences > Status."),
                          sticky = True,
                          max_lines=10,
                          onclose=self.response,
                          buttons=[(_('Close'), lambda *a, **k: None)])


    def response(self):
        with self.lock:
            setpref('digsby.status.promote_tag.upgrade_response', 'ok')
            setpref('digsby.status.promote_tag.enabled', True)

