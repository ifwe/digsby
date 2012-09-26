'''
POP mail
'''

from mail.smtp import SMTPEmailAccount
from common import pref
from util import ResetTimer
from util.primitives.funcs import get
from logging import getLogger; log = getLogger('popmail'); info = log.info
from mail.emailobj import DecodedEmail
from mail.emailobj import Email
from traceback import print_exc
import email

from hashlib import sha1
from util.command_queue import CommandQueue, cmdqueue, callback_cmdqueue

class PopMail(SMTPEmailAccount):
    protocol = 'pop'
    default_timeout = 20

    opening_email_marks_as_read = False

    def __init__(self, **options):
        d = self.default
        self.popserver   = options.get('popserver', '')
        self.require_ssl = options.get('require_ssl', d('require_ssl'))
        self.popport     = options.get('popport', d('popport'))
        self.uidlworks   = None
        self.topworks    = True #assume it does until proven otherwise

        self.cmdq = CommandQueue(start_hooks=[self._connect], end_hooks=[self._quit])
        self.timeouttimer = ResetTimer(pref('pop.timeout',self.default_timeout), self.timeout_check)

        SMTPEmailAccount.__init__(self, **options)

    can_has_preview = True

    def timeout_check(self):
        log.info('Checking server connection for %r', self)
        if self.state in (self.Statuses.OFFLINE, self.Statuses.ONLINE):
            log.info('%s is not currently checking', self)
            return True

        if get(self, 'conn', False):
            try:
                self.conn.noop()
            except:
                self.on_error()
                log.error('%s\'s server connection has failed', self)
                return False
        else:
            log.error('%s has no conn attribute', self)
            self.on_error()
            return False

    def update(self):
        SMTPEmailAccount.update(self)
        log.info('starting timeout timer')
        self.timeouttimer.start()
        self.real_update(success = self.finish_update)

    def finish_update(self, updates):
        import time
        if self.state == self.Statuses.OFFLINE:
            log.error('finish_update exiting early, state is %s', self.state)
            return

        (updated_emails, updated_count) = updates
        log.info("%s got %d new messages %s", self, updated_count, time.ctime(time.time()))
        #self.change_state(self.Statuses.ONLINE)
        self._received_emails(updated_emails[:25], updated_count)
#        if self.state in (self.Statuses.CONNECTING, self.Statuses.CHECKING):
#            self.change_state(self.Statuses.ONLINE)
        self.error_count = 0
        log.info('stopping timeout timer')
        self.timeouttimer.stop()



    @callback_cmdqueue()
    def real_update(self):
        #self.change_state(self.Statuses.CHECKING)
        if self.state == self.Statuses.OFFLINE:
            return
        conn = self.conn
        num_emails, box_size = conn.stat()
        num_emails = int(num_emails)
        emails = []

        def retr(mid):
            if self.topworks:
                try:
                    return conn.top(mid, 100)
                except:
                    self.topworks = False
            return conn.retr(mid)

        uidl = conn.uidl()
        if uidl[0].startswith("+"):
            self.uidlworks = True
            msg_tups = [tuple(tup.split()) for tup in uidl[1]][-25:]

            for tup in msg_tups:
                try:
                    mailmsg = retr(tup[0])
                except Exception:
                    print_exc()
                else:
                    try:
                        email_id = tup[1]
                    except IndexError:
                        email_id = None #someone had '1  ' -> ('1',)  None seems to work fine.
                    emails.append(
                                  Email.fromEmailMessage(email_id,
                                   DecodedEmail(
                                    email.message_from_string(
                                     "\n".join(mailmsg[1])
                                  ))))
        else:
            self.uidlworks = False
            num_to_get = min(num_emails, 25)
            for i in xrange(num_to_get, max(num_to_get-25, -1), -1):
                try:
                    mailmsg = retr(str(i))
                except Exception:
                    print_exc()
                else:
                    emailstring = "\n".join(mailmsg[1])
                    de = DecodedEmail(email.message_from_string(emailstring))
                    emails.append(Email.fromEmailMessage(
                                  sha1(emailstring).hexdigest() + "SHA"+str(i)+"SHA", de))


        return emails, num_emails

        #self.change_state(self.Statuses.ONLINE)
#        import time
#        print num_emails, time.time()

    def _connect(self):
        if self.require_ssl:
            from poplib import POP3_SSL as pop
        else:
            from poplib import POP3 as pop

        try:
            conn = pop(self.popserver, self.popport)
        except Exception, e:
            log.error('There was an error connecting: %s', e)
            self.on_error()
            raise
        self.conn = conn
        log.info(conn.user(self.name))
        try:
            password = self._decryptedpw().encode('utf-8')
            log.info(conn.pass_(password))
        except Exception, e:
            log.error('Bad password: %s', e)
            self._auth_error_msg = e.message
            self.set_offline(self.Reasons.BAD_PASSWORD)
            self.timer.stop()
            raise
        return conn

    def _quit(self):
        try:
            self.conn.quit()
        except Exception, e:
            log.error('Error when disconnecting: %s', str(e))
            if self.state != self.Statuses.ONLINE:
                self.set_offline(self.Reasons.CONN_FAIL)

    @cmdqueue()
    def delete(self, msg):
        SMTPEmailAccount.delete(self, msg)
        conn = self.conn

        if self.uidlworks:
            uidl = conn.uidl()
            #check if response is ok
            mids = [mid for mid, uid in
                    [tuple(tup.split()) for tup in uidl[1]]
                    if uid == msg.id]
            if mids:
                mid = mids[0]
                conn.dele(mid)
        else:
            hash, msgid, _ = msg.id.split("SHA")
            newmsg = conn.retr(msgid)
            #check if response is ok
            newstring = "\n".join(newmsg[1])
            newhash = sha1(newstring).hexdigest()
            if hash == newhash:
                conn.dele(msgid)
            else:
                num_emails, box_size = conn.stat()
                num_emails = int(num_emails)
                for i in xrange(num_emails):
                    emailhash = sha1("\n".join(conn.retr(str(i))[1])).hexdigest()
                    if hash == emailhash:
                        conn.dele(msgid)
                        break

    def _get_options(self):
        opts = SMTPEmailAccount._get_options(self)
        opts.update(dict((a, getattr(self, a)) for a in
                'popserver popport require_ssl'.split()))
        return opts

