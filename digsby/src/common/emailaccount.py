from __future__ import with_statement
from common import AccountBase, profile, netcall, pref, UpdateMixin, FromNetMixin
from util.observe import ObservableList
from common.actions import action
from common.notifications import fire
from urllib import quote
from util.net import UrlQuery
from traceback import print_exc
import os, shlex, locale
from subprocess import Popen
from os.path import expandvars
from logging import getLogger; log = getLogger('emailaccount'); info = log.info
from util import urlprotocol, try_this, get_func_name, call_later, callsback
from path import path
from prefs import localprefprop

import util

def localprefs_key(name):
    def get(acct):
        return '/'.join([acct.protocol, acct.username, name]).lower()

    return get

class EmailAccount(AccountBase, UpdateMixin, FromNetMixin):

    retry_time = 3
    error_max = 3

    def __init__(self, enabled = True, updateNow = True, **options):

        AccountBase.__init__(self, **options)
        UpdateMixin.__init__(self, **options)
        FromNetMixin.__init__(self, **options)

        self.emails = ObservableList()
        self.count = 0
        self.seen = set()
        self._dirty_error = True # The next error is new.

        log.info('Created EmailAccount: %r. Setting enabled to %r', self, enabled)

        self.enabled = enabled

    def timestamp_is_time(self, tstamp):
        return True

    #
    # local prefs
    #
    mailclient         = localprefprop(localprefs_key('mailclient'), None)
    custom_inbox_url   = localprefprop(localprefs_key('custom_inbox_url'), None)
    custom_compose_url = localprefprop(localprefs_key('custom_compose_url'), None)

    email_address = util.iproperty('get_email_address', 'set_email_address')

    @property
    def extra_header_func(self):
        return None # inviting disabled

        if self.protocol not in ('aolmail', 'ymail', 'gmail', 'hotmail'):
            return None
        import hooks
        d = {}
        for attr in ('protocol', 'name', 'password'):
            d[attr] = getattr(self, attr)
        return ("Invite Contacts", lambda *a, **k: hooks.notify('digsby.email.invite_clicked', **d))

    def get_email_address(self):
        from util import EmailAddress
        try:
            return str(EmailAddress(self.name, self.default_domain)).decode('ascii')
        except (AttributeError, ValueError):
            try:
                ret = self.name if '@' in self.name else self.name + '@' + self.default_domain
                if isinstance(ret, bytes):
                    return ret.decode('ascii')
                else:
                    return ret
            except Exception:
                # hopefully bad data has been caught before here.
                if isinstance(self.name, bytes):
                    return self.name.decode('ascii', 'replace')
                else:
                    return self.name

    def set_email_address(self, val):
        # Not supported
        pass

    @property
    def display_name(self):
        return try_this(lambda: getattr(self, pref('email.display_attr')), self.email_address)

    def on_error(self, task=None):
        '''
        Called when an error occurs. task is a callable that can be used to make another attempt
        at whatever caused the error (if error_count is less than max_error).
        '''
        self.error_count += 1

        log.error('%r\'s error count is now: %d',self, self.error_count)
        log.error('on_error called from %s', get_func_name(2))

        if self.error_count < pref('email.err_max_tolerance', self.error_max):
            if task is None:
                task = self.update_now
            log.error('error count is under, calling %r now', task)

            if not callable(task):
                # If it was an exception assume that update_now was called. (the account type
                # probably just hasn't been fixed yet
                task = self.update_now
            util.call_later(pref('email.err_retry_time', type=int, default=2), task)
        else:
            log.error('assuming the connection has died')
            self.set_offline(self.Reasons.CONN_FAIL)
            self.error_count = 0

        del self.emails[:]

    def bad_pw(self):
        log.info('%r: changing state to BAD_PASSWORD', self)
        self.set_offline(self.Reasons.BAD_PASSWORD)
        self.timer.stop()

    def no_mailbox(self):
        log.info('%r: changing state to NO_MAILBOX', self)
        self.set_offline(self.Reasons.NO_MAILBOX)
        self.timer.stop()

    def __repr__(self):
        r = AccountBase.__repr__(self)[:-1]
        r += ', '
        r += 'enabled' if self.enabled else 'disabled'
        return r + '>'

    @property
    def web_login(self):
        return (pref('privacy.www_auto_signin') and self.state in (self.Statuses.ONLINE, self.Statuses.CHECKING))

    def error_link(self):

        reason  = self.Reasons
        linkref = {
            reason.BAD_PASSWORD : ('Edit Account', lambda *a: profile.account_manager.edit(self,True)),
            reason.CONN_FAIL    : ('Retry',        lambda *a: self.update_now())
        }
        if self.offline_reason in linkref:
            name, callback = linkref[self.offline_reason]
            return name, callback
        else:
            return None

    def sort_emails(self, new=None):
        self.emails.sort()

        if new is not None:
            new.sort()

    def filter_new(self, new, old):
        if old:
            return [e for e in new if e <= old[-1]]
        elif self.seen:
            new_ids = set(e.id for e in new)
            keep = set()
            for email in self.emails:
                if email.id in new_ids:
                    keep.add(email.id)
                else:
                    break
            return [e for e in new if e.id in keep]
        else:
            return list(new)

    def _see_new(self, new_messages):
        new_seen = set()
        for email in new_messages:
            new_seen.add(email.id)
        self.seen.update(new_seen)

    def _get_new(self):
        new = []
        for email in self.emails:
            if email.id not in self.seen:
                new.append(email)
        return new

    def _received_emails(self, emails, inboxCount = None):
        '''
        Subclasses should call this method with any new emails received.

        @param emails: a sequence of Email objects
        '''
        old, self.emails[:] = self.emails[:], list(emails)

        new = self._get_new()
        for email in new:
            import plugin_manager.plugin_hub as plugin_hub
            plugin_hub.act('digsby.mail.newmessage.async', self, email)
        self._see_new(new)

        self.sort_emails(new)
        new = self.filter_new(new, old)
        del old

        info('%s - %s: %d new emails', self.__class__.__name__, self.name, len(new))

        if inboxCount is not None:
            self._setInboxCount(inboxCount)

        self.new = new
        if new:
            profile.when_active(self.fire_notification)

        self.error_count = 0
        self.change_state(self.Statuses.ONLINE)
        self._dirty_error = True # Next error will be new

    def fire_notification(self):
        if self.new:
            self._notify_emails(self.new)

    def popup_buttons(self, item):
        return []

    def _notify_emails(self, emails, always_show = None, allow_click = True):
        if self.enabled:
            fire('email.new', emails = emails,
                              onclick = self.OnClickEmail if allow_click else None,
                              always_show = always_show,
                              buttons = self.popup_buttons,
                              icon = self.icon)

    def _setInboxCount(self, inboxCount):
        self.setnotifyif('count', inboxCount)

    @action()
    @callsback
    def OnComposeEmail(self, to='', subject='', body='', cc='', bcc='', callback = None):
        import hooks; hooks.notify('digsby.statistics.email.compose')
        for name in ('to','subject', 'body', 'cc', 'bcc'):
            assert isinstance(vars()[name], basestring), (name, type(vars()[name]), vars()[name])

        if self.mailclient and try_this(lambda: self.mailclient.startswith('file:'), False):
            os.startfile(self.mailclient[5:])

        elif self.mailclient == 'sysdefault':
            kw = {}
            for name in ('subject', 'body', 'cc',  'bcc'):
                if vars()[name]:
                    kw[name] = vars()[name]

            query = UrlQuery('mailto:' + quote(to), **kw)
            log.info('OnComposeEmail is launching query: %s' % query)
            try:
                os.startfile(query)
            except WindowsError:
                # WindowsError: [Error 1155] No application is associated with the specified file for this operation: 'mailto:'
                mailclient_error()
                raise

        elif self.mailclient == '__urls__':
            url = self.custom_compose_url
            if url is not None: launch_browser(url)

        else:
            url = self.compose(to, subject, body, cc, bcc)
            if url:
                launch_browser(url)

        callback.success()

    @property
    def client_name(self):
        "Returns a string representing this email account's mail client."

        mc = self.mailclient

        if mc in (None, True, False):
            return self.protocol_info().name

        elif mc.startswith('file:'):
            return path(mc).basename().title()

        elif mc == 'sysdefault':
            #HACK: Use platform specific extensions to extract the actual
            #application name from the executable. for now, use ugly path
            #TLDR: needs the registry
            return ''

        elif mc == '__urls__':
            return ''

        else:
            log.warning('unknown mailclient attribute in %r: %s', self, mc)
            return _('Email Client')

    @action()
    def OnClickInboxURL(self, e = None):
        import hooks; hooks.notify('digsby.statistics.email.inbox_opened')
        if self.mailclient:
            url = self.start_client_email()
            if url is None:
                return
        else:
            url = self.inbox_url

        launch_browser(self.inbox_url)

    DefaultAction = OnClickHomeURL = OnClickInboxURL

    opening_email_marks_as_read = True

    def OnClickEmail(self, email):
        import hooks; hooks.notify('digsby.statistics.email.email_opened')
        if self.mailclient:
            self.start_client_email(email)
        else:
            url = self.urlForEmail(email)
            launch_browser(url)

        # For accounts where we are guaranteed to actually read the email
        # on click (i.e., ones that use webclients and have autologin on),
        # decrement the email count.
        if self.opening_email_marks_as_read:
            self._remove_email(email)

    @callsback
    def OnClickSend(self, to='', subject='', body='', cc='', bcc='', callback = None):
        '''
        Sends an email.
        '''
        getattr(self, 'send_email', self.OnComposeEmail)(to=to,
                    subject=subject, body=body, cc=cc, bcc=bcc, callback = callback)

    def start_client_email(self, email=None):
        log.info('mailclient: %s', self.mailclient)
        import os.path

        if self.mailclient == 'sysdefault':
            launch_sysdefault_email(email)

        elif self.mailclient == '__urls__':
            url = self.custom_inbox_url
            if url is not None: launch_browser(url)

        elif try_this(lambda:self.mailclient.startswith('file:'), False):
            filename = self.mailclient[5:]

            if os.path.exists(filename):
                os.startfile(filename)
            else:
                log.warning('cannot find %s', filename)

    def __len__(self):
        return self.count

    def __iter__(self):
        return iter(self.emails)

    can_has_preview = False

    @property
    def icon(self):
        from gui import skin
        from util import try_this
        return try_this(lambda: skin.get('serviceicons.%s' % self.protocol), None)

    @property
    def inbox_url(self):
        '''
        Return the url for the user's inbox to be opened in browser.
        This should adhere to the 'privacy.www_auto_signin' pref.
        '''
        raise NotImplementedError

    def observe_count(self,callback):
        self.add_gui_observer(callback, 'count')
        self.emails.add_gui_observer(callback)

    def unobserve_count(self, callback):
        self.remove_gui_observer(callback, 'count')
        self.emails.remove_gui_observer(callback)

    def observe_state(self, callback):
        self.add_gui_observer(callback, 'enabled')
        self.add_gui_observer(callback, 'state')

    def unobserve_state(self, callback):
        self.remove_gui_observer(callback, 'enabled')
        self.remove_gui_observer(callback, 'state')

    @property
    def header_funcs(self):
        return [('Inbox',self.OnClickInboxURL), ('Compose', self.OnComposeEmail)]

    def _get_options(self):
        opts = UpdateMixin.get_options(self)
        return opts

    def update_info(self, **info):
        flush_state = False
        with self.frozen():
            for k, v in info.iteritems():
                if k in ('password', 'username', 'server') and getattr(self, k, None) != v:
                    flush_state = True


                self.setnotifyif(k, v)

        # Tell the server.
        profile.update_account(self)

        if flush_state:
            log.info('Resetting state for %r', self)
            self._reset_state()

        self._dirty_error = True

    def _reset_state(self):
        return NotImplemented

    def update(self):
        # Protocols must override this method to check for new messages.
        if self.update == EmailAccount.update:
            log.warning('not implemented: %s.update', self.__class__.__name__)
            raise NotImplementedError

        if not self.enabled:
            return

        log.info('%s (%s) -- preparing for update. update called from: %s', self, self.state, get_func_name(2))

        if self.state == self.Statuses.OFFLINE:
            # First check -- either after creation or failing to connect for some reason
            self.change_state(self.Statuses.CONNECTING)
        elif self.state == self.Statuses.ONLINE:
            # A follow-up check.
            self.change_state(self.Statuses.CHECKING)
        elif self.state == self.Statuses.CONNECTING:
            # Already connecting -- if there have been errors this is just the Nth attempt.
            # if there are not errors, something is wrong! -- disconnect
            if not self.error_count:
                log.error('%s -- called update while connecting, and no errors! disconnecting...',self)
                self.set_offline(self.Reasons.CONN_FAIL)
        else:
            log.error('Unexpected state for update: %r', self.state)

    @action(lambda self: (self.state != self.Statuses.CHECKING))
    def update_now(self):
        'Invoked by the GUI.'

        netcall(self.update)
        self.timer.reset(self.updatefreq)


    @action()
    def tell_me_again(self):

        if self.emails:
            emails = self.emails
            allow_click = True
        else:
            from mail.emailobj import Email
            emails = [Email(id = -1, fromname = _('No unread mail'))]
            allow_click = False

        # Use "always_show" to always show a popup, regardless of whether the
        # user has popups enabled or not.
        self._notify_emails(emails,
                            always_show = ['Popup'],
                            allow_click = allow_click)

    @action()
    def auth(self):
        netcall(self.authenticate)

    def Connect(self):
        self.change_reason(self.Reasons.NONE)
        call_later(1.5, self.update)

    @action()
    def compose(self, to, subject, body, cc, bcc):
        '''
        Return a link for a browser that will bring the user to a compose window
        (or as close as possible, adhering to the 'privacy.www_auto_signin' pref).

        '''
        raise NotImplementedError

    def urlForEmail(self, email):
        '''
        Return a link to be opened by a browser that will show the user the email
        (or as close as possible, adhering to the 'privacy.www_auto_signin' pref).

        email -- the email OBJECT that we want the URL for.
        '''
        raise NotImplementedError

    @action()
    def open(self, email_message):
        '''

        '''
        if type(self) is EmailAccount:
            raise NotImplementedError

    def _remove_email(self, email_message):
        try:
            self.emails.remove(email_message)
        except ValueError:
            # already removed
            pass
        else:
            self.setnotifyif('count', self.count - 1)

    @action()
    def markAsRead(self, email_message):
        '''
        Mark the email object as read.
        '''
        import hooks; hooks.notify('digsby.statistics.email.mark_as_read')
        self._remove_email(email_message)

    @action()
    def delete(self, email_message):
        import hooks; hooks.notify('digsby.statistics.email.delete')
        self._remove_email(email_message)

    @action()
    def archive(self, email_message):
        import hooks; hooks.notify('digsby.statistics.email.archive')
        self._remove_email(email_message)

    @action()
    def reportSpam(self, email_message):
        import hooks; hooks.notify('digsby.statistics.email.spam')
        self._remove_email(email_message)

import re
env_re = re.compile('(%.*?%)')

def mailclient_error():
    # Show an error popup if there is no mail client at all.
    fire('error', title   = _('No System Email Client'),
                  msg     = _('No system email client is configured.'),
                  details = '')

def mailclient_launch_error(msg=None):
    if msg is None:
        msg = _('Could not start system mail client.')

    fire('error', title   = _('Error launching system mail client'),
                  msg     = msg,
                  details = '')

def envexpand(s):
    parts = env_re.split(s)
    out = []

    for part in parts:
        if part.startswith('%') and part.endswith('%'):
            part = '${' + part[1:-1] + '}'
        out.append(part)

    return expandvars(''.join(out))

def launch_sysdefault_email(email = None):
    '''
    Launch the system's default mail client.

    If email is not None, a new message with the email address specified will
    be opened.

    Return True if a program was launched.
    '''

    import wx
    if 'wxMSW' in wx.PlatformInfo:
        from gui.native.win.winutil import is_vista
        if is_vista(): return launch_sysdefault_email_vista(email)

    # ask the system what is used for "mailto://"
    #
    # example return value: u'"C:\\PROGRA~1\\MICROS~1\\Office12\\OUTLOOK.EXE" -c IPM.Note /m "%1"'
    #

    mailclient = urlprotocol.get('mailto')

    log.info('mail client is %r', mailclient)

    if not mailclient.strip():
        mailclient_error()
        return False

    # replace %ENVVARS%
    mailclient = envexpand(mailclient)


    # start the program!
    try:
        args = shlex.split(mailclient.encode(locale.getpreferredencoding()))

        # only grab the first part (hopefully the executable)
        args = args[:1]

        log.info('launching %r', args)

        if Popen(args):
            return True
    except Exception, e:
        print_exc()
        msg = e.message
    else:
        try:
            msg = _('Could not start system mail client %r.') % mailclient
        except Exception:
            msg = None
            print_exc()

        mailclient_launch_error(msg)

def launch_sysdefault_email_vista(email = None):
    import _winreg as reg

    try:
        #
        # there are more hops to the mail client on Vista. see
        #
        # http://msdn2.microsoft.com/en-us/library/bb776873.aspx#registration
        #
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, r'Software\Clients\mail', 0, reg.KEY_READ)
        client_name, t = reg.QueryValueEx(key, None)
        log.info('canonical name for mail client: %r', client_name)

        mc_key_name = 'SOFTWARE\Clients\Mail\%s\shell\open\command'
        mc_key = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, mc_key_name % client_name, 0, reg.KEY_READ)
        program, t = reg.QueryValueEx(mc_key, None)
        log.info('mail client shell launch string: %r', program)
    except Exception, e:
        print_exc()
        return mailclient_error()

    # shlex doesn't like unicode
    if isinstance(program, unicode):
        import sys
        program = program.encode(sys.getfilesystemencoding())

    try:
        # expand environment variables like %ProgramFiles%
        program = envexpand(program)

        import subprocess, shlex
        args = shlex.split(program)
        log.info('launching vista mail client: %r', args)
        subprocess.Popen(args)
        return True
    except Exception, e:
        print_exc()
        mailclient_launch_error()

def launch_browser(url):
    import wx; wx.LaunchDefaultBrowser(url)

if __name__ == '__main__':
    launch_sysdefault_email_vista()
