'''
Simple interface for IMAP checking.
'''

import imaplib, time, re, email
from datetime import datetime
from pprint import pformat
from mail.emailobj import DecodedEmail
from mail import Email, AuthenticationError
from logging import getLogger; log = getLogger('imapcheck')
from util import autoassign, callsback, traceguard
import traceback

import ssl
from imaplib import IMAP4_SSL_PORT
import socket

class IMAP4_SSL_Fixed(imaplib.IMAP4_SSL):
    '''Fixed because SSL objects may return an empty string even with suppress_ragged_eofs=True.'''
    def open(self, host = '', port = IMAP4_SSL_PORT):
        """Setup connection to remote server on "host:port".
            (default: localhost:standard IMAP4 SSL port).
        This connection will be used by the routines:
            read, readline, send, shutdown.
        """
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sslobj = ssl.wrap_socket(self.sock, self.keyfile, self.certfile, suppress_ragged_eofs=False)

    def readline(self):
        """Read line from remote."""
        line = []
        while 1:
            char = self.sslobj.read(1)
            if not char:
                raise ssl.SSLError(ssl.SSL_ERROR_EOF)
            line.append(char)
            if char == "\n": return ''.join(line)

    def read(self, size):
        """Read 'size' bytes from remote."""
        # sslobj.read() sometimes returns < size bytes
        chunks = []
        read = 0
        while read < size:
            data = self.sslobj.read(min(size-read, 16384))
            if not data:
                raise ssl.SSLError(ssl.SSL_ERROR_EOF)
            read += len(data)
            chunks.append(data)

        return ''.join(chunks)

class IMAPCheck(object):

    def __init__(self, maxfetch = 25):
        self.maxfetch = maxfetch
        self.cache = {}
        self.srv = None

    def login(self, host, port, ssl, user, password):
        autoassign(self, locals())

    def update(self):
        if self.srv is not None:
            srv, self.srv = self.srv, None
            try:
                srv.logout()
            except ssl.SSLError, e:
                log.error('got SSLError during logout: %r', e)
            except Exception:
                traceback.print_exc()

        if self.ssl:
            cls = IMAP4_SSL_Fixed
        else:
            cls = imaplib.IMAP4

        srv = cls(self.host, self.port)

        try:
            srv.login(srv._checkquote(self.user.encode('ascii')), self.password)
        except (imaplib.IMAP4.error, imaplib.IMAP4_SSL.error):
            raise AuthenticationError


        srv.select()

        # retrieve UIDs for messages without \Seen or \Deleted flags
        res, lst = srv.uid('search', None, '(UNSEEN UNDELETED)')
        if res != 'OK':
            raise Exception('could not retrieve unseen messages from the server')

        uids  = ' '.join(lst).split(' ') if lst[0] else []
        log.info('%d unseen uids: %r', len(uids), uids)

        msg_sendtimes = {}
        unread_msgs = []

        # retrieve INTERNALDATEs for each message in that list
        if uids:
            res, lst = srv.uid('FETCH', ','.join(uids), '(INTERNALDATE FLAGS)')
            if res != 'OK':
                raise Exception('could not retrieve message dates from the server')

            for resp in lst:
                try:
                    # keep only responses to the fetch
                    dt, uid, flags = getDatetime(resp), getUid(resp), getFlags(resp)

                    log.info('%s %r', uid, flags)

                    if (dt is not None and uid is not None and
                        ('\\Seen' not in flags and '\\Deleted' not in flags)):
                        unread_msgs.append((dt, uid))
                        msg_sendtimes[uid] = dt
                except Exception:
                    traceback.print_exc()

        count = len(unread_msgs)

        # Newest messages first.
        unread_msgs.sort(reverse = True)

        # ask for a limited number of newest messages, excluding ones
        # we've already downloaded

        uids_to_fetch = []
        uids_already_fetched = []

        for dt, uid in unread_msgs[:self.maxfetch]:
            try:
                if uid not in self.cache:
                    uids_to_fetch += [uid]
                else:
                    uids_already_fetched += [uid]
            except Exception:
                traceback.print_exc()

        emailobjs = []

        from common import pref

        if uids_to_fetch:
            res, lst = srv.uid('fetch', ','.join(uids_to_fetch),
                               '(BODY.PEEK[]<0.%d>)' % pref('imaplib.max_fetch_bytes', default=5120, type=int))
            if res != 'OK':
                raise Exception('could not retrieve message contents from the server')

            #need a real parser here.
            #assert not (len(lst) % len(uids_to_fetch))
            #print len(lst), len(uids_to_fetch)

            # This mess is due to Exchange servers returning data where
            # UID comes after the message, which is valid, but mangled
            # by imaplib.py.
            lst2 = []
            currinfo = []
            currdata = None
            for resp in lst + [(None, None)]:
                if isinstance(resp, tuple):
                    if currdata:
                        lst2.append((currinfo, currdata))
                        currdata = None
                        currinfo = []
                    assert len(resp) == 2
                    currinfo.append(resp[0])
                    currdata = resp[1]
                else:
                    assert isinstance(resp, str)
                    currinfo.append(resp)

            for resp in lst2:
                try:
                    if isinstance(resp, tuple):
                        nfo, msg = resp

                        uid = getUid(nfo)
                        sndtime = msg_sendtimes[uid]
                        emailobj = emailFromString(uid, msg, sndtime)
                        self.cache[uid] = emailobj
                        emailobjs += [emailobj]
                except Exception:
                    traceback.print_exc()

        for uid in uids_already_fetched:
            emailobjs += [self.cache[uid]]


        log.info('untagged responses')
        log.info(pformat(srv.untagged_responses))
        srv.untagged_responses.clear()

        self.srv = srv
        return count, emailobjs

    #TODO: why isn't this handled more cleanly in EmailAccount??

    @callsback
    def markAsRead(self, msg, callback = None):
        try:
            self.srv.uid("STORE", msg.id, "+FLAGS.SILENT", r"(\SEEN)")
        except:
            import traceback
            traceback.print_exc()

            return callback.error()

        callback.success()

    @callsback
    def delete(self, msg, callback = None):
        try:
            self.srv.uid("STORE", msg.id, "+FLAGS.SILENT", r"(\DELETED \SEEN)")
        except:
            import traceback
            traceback.print_exc()

            return callback.error()

        callback.success()

#
# utility functions for parsing information out of server responses
#

def emailFromString(uid, s, sendtime_if_error):
    'Email RFC822 string -> Email object'

    return Email.fromEmailMessage(uid, DecodedEmail(email.message_from_string(s)),
                                  sendtime_if_error)


def getDatetime(s):
    'Returns a datetime object for an INTERNALDATE response.'

    timetuple = imaplib.Internaldate2tuple(s)

    if timetuple is not None:
        return datetime.fromtimestamp(time.mktime(timetuple))

_uidMatcher = re.compile(r'UID ([0-9]+)\D')
def getUid(s):
    "Given strings like '3 (UID 16407497 RFC822 {2410}' returns 16407497."
    if isinstance(s, basestring):
        vals = [s]
    else:
        vals = s
    for val in vals:
        match = _uidMatcher.search(val)
        if match:
            return match.group(1)
    else:
        log.error('coult not find uid in %r', s)

def getFlags(s):
    'Returns a tuple of flag strings.'

    return imaplib.ParseFlags(s)


if __name__ == '__main__':
    i = IMAPCheck()
    i.login('imap.aol.com', 143, False, 'digsby04', 'thisisnotapassword')
    print
    print 'DONE'
    print
    print repr(i.update())

