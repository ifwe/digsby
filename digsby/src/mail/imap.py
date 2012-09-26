'''
IMAP mail
'''
import re
import traceback
from mail import AuthenticationError
from mail.smtp import SMTPEmailAccount

from util import ResetTimer
from util.primitives.funcs import get
from util.command_queue import CommandQueue, callback_cmdqueue, cmdqueue
from common import pref

from logging import getLogger; log = getLogger('imap'); info = log.info

class IMAPMail(SMTPEmailAccount):
    protocol = 'imap'

    max_fetch = 25 # will only fetch contents for the last max_fetch messages

    default_port     = 143
    default_ssl_port = 993
    default_timeout  = 20

    opening_email_marks_as_read = False

    def __init__(self, **options):
        d = self.default
        log.info("imap options: %r", options)
        self.imapserver   = options.get('imapserver')
        self.require_ssl  = options.get('require_ssl', d('require_ssl'))
        self.imapport     = options.get('imapport', d('default_ssl_port') if
                                                    self.require_ssl else
                                                    d('imapport'))

        self.timeouttimer = ResetTimer(pref('imap.timeout', self.default_timeout),
                                       self.timeout_check)

        from mail.imapcheck import IMAPCheck
        self.imap = IMAPCheck(self.max_fetch)
        self.cmdq = CommandQueue([], [], 30, 1)
        #print 'IMAPMail:', repr(options['name']), repr(options['password'])
        SMTPEmailAccount.__init__(self, **options)

    can_has_preview = True

    def update(self):
        SMTPEmailAccount.update(self)
        info('starting timeout timer')
        self.timeouttimer.start()

        self.real_update(success = self.finish_update,
                         error   = self.on_error)

    def finish_update(self, result):
        self.error_count = 0

        if isinstance(result, tuple):
            count, emails = result
            self._received_emails(emails, count)
        else:
            log.warning('finish_update expects a tuple, got a %s: %r', type(result), result)

        info('stopping timeout timer')
        self.timeouttimer.stop()

    @callback_cmdqueue()
    def real_update(self):
        password = self._decryptedpw()
        if isinstance(password, unicode):
            password = password.encode('utf-8')

        self.imap.login(self.imapserver, self.imapport, self.require_ssl,
                        self.name, password)

        if self.state == self.Statuses.OFFLINE:
            if self.offline_reason == self.Reasons.NONE:
                return
            else:
                raise Exception

        try:
            result = self.imap.update()
        except AuthenticationError, e:
            traceback.print_exc()
            return self.bad_pw()

        return result

    def timeout_check(self):
        info('Checking server connection for %r', self)
        if self.state in (self.Statuses.OFFLINE, self.Statuses.ONLINE):
            info('%s is not currently checking', self)
            return True

        if get(self, 'imap', False):
            try:
                return self.imap.srv.check()
            except:
                self.on_error()
                log.error('%s\'s server connection has failed', self)

        else:
            log.error('%s has no imap attribute', self)
            self.on_error()

        return False


    def _get_options(self):
        opts = SMTPEmailAccount._get_options(self)
        opts.update(dict((a, getattr(self, a)) for a in
                        'imapserver imapport require_ssl'.split()))
        d = self.protocol_info()['defaults']
        if opts['require_ssl'] and opts['imapport'] == d['default_ssl_port']:
            opts.pop('imapport')
        return opts

    def copy(self, msg, new_mailbox):
        self.imap.srv.uid("COPY", msg.id, new_mailbox)

    @cmdqueue()
    def move(self, msg, new_mailbox):
        self.copy(msg, new_mailbox)
        self.imap.delete(msg, error = lambda: self.on_error(lambda: self.move(msg,new_mailbox)))

    def markAsRead(self, msg):
        SMTPEmailAccount.markAsRead(self, msg)
        self._markAsRead(msg)

    @cmdqueue()
    def _markAsRead(self, msg):
        self.imap.markAsRead(msg, error = lambda: self.on_error(lambda: self.markAsRead(msg)))

    def delete(self, msg):
        SMTPEmailAccount.delete(self, msg)
        self._delete(msg)

    @cmdqueue()
    def _delete(self, msg):
        SMTPEmailAccount.delete(self, msg)
        self.imap.delete(msg, error = lambda:self.on_error(lambda:self.delete(msg)))

_uidMatcher = re.compile(r'UID ([0-9]+?) ')
def getUid(s):
    '''
    Given strings like '3 (UID 16407497 RFC822 {2410}' returns 16407497.
    '''

    match = _uidMatcher.search(s)
    if match: return match.group(1)
    else: raise ValueError('no uid found')

if __name__ == '__main__':
    from tests.testapp import testapp
    from pprint import pprint

    acct = IMAPMail('digsby04', 'notreallythepassword',
                    imapserver = 'imap.aim.com',
                    imapport = 143,
                    require_ssl = False)
    print acct._connect()
    print acct.real_update()

    import wx
    a = testapp('../..')
    f = wx.Frame(None, -1, 'IMAP Test')
    f.Sizer = s = wx.BoxSizer(wx.VERTICAL)

    b = wx.Button(f, -1, 'noop', style = wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
    b.Bind(wx.EVT_BUTTON, lambda e: acct.server.noop())

    b2 = wx.Button(f, -1, 'recent')
    b2.Bind(wx.EVT_BUTTON, lambda e: pprint(acct.server.recent()))

    b3 = wx.Button(f, -1, 'update')
    b3.Bind(wx.EVT_BUTTON, lambda e: pprint(acct.real_update(), f.SetTitle(str(acct.updated_count))))

    s.AddMany([b, b2, b3])

    f.Show()
    f.imap = acct
    a.MainLoop()
