from __future__ import with_statement
import re, sys, itertools
from util import threaded, traceguard, CallCounter, fmt_to_dict
from util.xml_tag import tag, post_xml
from uuid import UUID
from datetime import datetime
from email import message_from_string
from email.header import Header, decode_header
from base64 import b64decode

from common import pref

from logging import getLogger
log = getLogger('msn.oim')

import msn
import uuid
import util
from util.auxencodings import fuzzydecode
from util.Events import EventMixin, event

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
POST_URL = "https://rsi.hotmail.com/rsi/rsi.asmx"
NS  = "http://www.hotmail.msn.com/ws/2004/09/oim/rsi"
GET = NS + "/GetMessage"
DEL = NS + "/DeleteMessages"
META = NS + '/GetMetadata'

import msn.SOAP.services as SOAPServices

def soap(ns):
    env = tag((('soap',SOAP_NS), 'Envelope'), xmlns=ns)
    env += ('soap','Header'),
    env += ('soap','Body'),

    return env

def make_header(s):
    return str(Header(s, 'utf-8'))

class OIMMessages(list):
    def __init__(self, acct, t):
        log.info('OIMMessages created')

        self.acct = acct
        list.__init__(self)

        if t is None:
            # SOAPRequest the XML data and store it in messages
            messages = None
        else:
            messages = t.M

        self.msginit(messages)

    def msginit(self, meta):
        if meta is None:
            return self.request_meta()

        if not meta:
            return

        if type(meta) is tag:
            messages = [meta]
        else:
            messages = meta

        del self[:]

        for message in messages:
            with traceguard:
                self.append(OIM(self.acct, message))
        self.get_messages(pref('msn.oim.markasread',False), True)


    def get_messages(self, markread=False, delete=True):
        for oim in self:
            callback = lambda _oim=oim: (self.received(_oim), log.info_s('Received: %r', oim))
            oim.get_message(markread=markread, success=callback, error=self.get_message_error)

        if False: #delete:
            self.delete_messages()

    def get_message_error(self, e):
        log.info("Error getting message %r", e)
        try:
            log.info('\t%r', e.body.getvalue())
        except:
            pass

    def received(self, oim):
        log.info('Received OIM (%d/%d): %r', len(filter(None, [x.received for x in self])), len(self), oim)
        if all(x.received for x in self):
            log.info('Received all OIMs. Telling acct')
            self.acct.received_oims(list(sorted(self)))

    def delete_messages(self):
        rsi = self.acct.getService(SOAPServices.AppIDs.RSIService)
        rsi.DeleteMessages(message_ids = [oim.id for oim in self],
                           success = self.delete_success)

    def delete_success(self, response):

        fault = response._findOne('Fault')


        if response._find('DeleteMessagesResponse'):
            for oim in self:
                oim.deleted = True
            log.info('OIMs deleted from server')
        elif fault:
            log.info('OIMs were not deleted. Fault occurred: %r', fault._to_xml(pretty=False))

    def request_meta(self):
        rsi = self.acct.getService(SOAPServices.AppIDs.RSIService)
        rsi.GetMetadata(success = lambda response: self.msginit(response.MD.M))

class OIM(object):

    time_re = re.compile('(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.(\d{3})(Z?)')
    def __init__(self, acct, m_tag):
        '''
        http://msnpiki.msnfanatic.com/index.php/MSNP13:Offline_IM

        * T: Unknown, but has so far only been set to 11.
        * S: Unknown, but has so far only been set to 6.
        * RT: The date/time stamp for when the message was received by the server.
                This stamp can be used to sort the message in the proper order,
                although you are recommended to use a different method instead
                which will be explained later.
        * RS: Unknown, but most likely is set to 1 if the message has been read
                before ("Read Set").
        * SZ: The size of the message, including headers
        * E: The e-mail address of the sender
        * I: This is the ID of the message, which should be used later on to retrieve
                the message. Note that the ID is a GUID in the form
                XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX. It was previously (the change
                was first noticed in March 2007) in the format of
                "MSGunix-timestamp.millseconds" (for example MSG1132093467.11) and
                the Message ID format could change again anytime.
        * F: Unknown, but has so far only been observed as either a GUID with a
                single 9 at the end, or as ".!!OIM" (in case you are already online
                when receiving the notification).
        * N: This field contains the friendlyname of the person, wrapped in a special
                encoding. This encoding is defined in RFC 2047, but to get you started
                there is a quick overview of the format below (see #Field_encoding).
                You are recommended however to implement a fully able e-mail parser to
                handle OIMs!
              o Note! When this field is found in a non-initial notification it will
                  contain a space in the data field. You must filter this space (trim
                  the string) in order to correctly decode this field!
        * SU: Unknown, has only been observed to contain one space.

        Example:
          <M>
            <T>11</T>
            <S>6</S>
            <RT>2007-05-14T15:52:53.377Z</RT>
            <RS>0</RS>
            <SZ>950</SZ>
            <E>x2ndshadow@hotmail.com</E>
            <I>08CBD8BE-9972-433C-A9DA-84A0A725ABFA</I>
            <F>00000000-0000-0000-0000-000000000009</F>
            <N>=?utf-8?B?QWFyb24=?=</N>
          </M>
        '''

        self.acct = acct
        self.size = int(str(m_tag.SZ))
        self.email = str(m_tag.E)

        self.name = u''

        for val, encoding in decode_header(m_tag.N.text.strip()):
            self.name += fuzzydecode(val, encoding)

        try:
            self.time = self.parse_time(str(m_tag.RT))
        except Exception:
            self.time = None
        self.id = UUID(str(m_tag.I))
        self.msg = ''
        self.deleted = False
        self._had_error = False
        self.received = False

        self.runid = None
        self.seqnum = 0

        log.info_s('%r created', self)

    @util.callbacks.callsback
    def get_message(self, markread=False, callback=None):
        rsi = self.acct.getService(SOAPServices.AppIDs.RSIService)
        rsi.GetMessage(client = self.acct, message_id = self.id, markread = markread,
                       success = lambda resp: (self.parse_msg(resp), callback.success()),
                       error = callback.error)

    def parse_msg(self, response):
        log.debug('Parsing this OIM: %r',response._to_xml(pretty=False))

        self._content = (response.Body.GetMessageResponse.GetMessageResult._cdata.strip()).encode('utf-8')

        fault = response._findOne('Fault')

        if fault:
            log.error('Error retrieving message (%r): %r', self, fault._to_xml(pretty=False))
            self._had_error = True
            return

        self._msgobj = message_from_string(self._content)
        oim_proxy = self._msgobj.get('X-OIMProxy', None)

        if oim_proxy == 'MOSMS': # MObile SMS
            self._parse_mobile_oim()

        payload = self._msgobj
        # rfc822 messages have a pretty bad API. We call get_payload(0) on it (to get the first part of a multipart message
        # as long as it continues to work. When we get a TypeError, it's because it tried call something on a string (the
        # real content) instead of a list (which is what there is when the message is_multipart()). By the end of this loop
        # payload will be the our rfc822 object that has the *real* message as it's payload.
        while True:
            try:
                payload = payload.get_payload(0)
            except TypeError:
                break

        msgtext = payload.get_payload()
        charset = payload.get_content_charset() or ''

        msgtext = msgtext.strip()
        msgtext = msgtext.decode('base64')
        msgtext = msgtext.decode('fuzzy %s' % charset)

        self.msg = msgtext

        self.received = True

        self.runid = self._msgobj.get('X-OIM-Run-Id', None)
        if self.runid is not None:
            self.runid = uuid.UUID(self.runid)

        try:
            self.seqnum = int(self._msgobj.get('X-OIM-Sequence-Num', '0'))
        except ValueError:
            self.seqnum = 0

        newtime = self._msgobj.get('X-OriginalArrivalTime', self.time)
        if isinstance(newtime, basestring):
            try:
                timestr = newtime.split(' (UTC) ')[0]
                # ex: '27 Feb 2008 23:20:21.0425'...cut off the last 2 digits since datetime doesnt support that resolution
                timestr = timestr[:-2]
                dt = datetime.strptime(timestr, '%d %b %Y %H:%M:%S.%f')

                self.time = dt
            except Exception:
                import traceback;traceback.print_exc()
                log.error('Error parsing time: %r', newtime)

        log.debug('\t\tMessage successfully parsed')
        return self.msg

    def _parse_mobile_oim(self):
        self.name = self.email = (self._msgobj.get('From', self.name)).strip('<>')

    def parse_time(self, timestr):
        yr, mo, da, hr, mi, se, ms, tz = self.time_re.search(timestr).groups()

        args = map(int, (yr,mo,da,hr,mi,se,ms))
        args[-1] = args[-1] * 1000

        if not tz:
            log.warning_s('no time zone for %r', self)

        return datetime(*args)

    def __repr__(self):
        return '<OfflineIM from %r (%s) sent at %s%s>' % (self.name, self.email, self.time,
                                                          ': %r'%(self.msg) if self.msg else '')

    def __cmp__(self, other):
        try:
            return cmp((self.time, self.runid, self.seqnum), (other.time, other.runid, other.seqnum))
        except Exception:
            return -1


class OIMExceptions:
    AuthFailed = 'AuthenticationFailed'

class OfflineSBAdapter(EventMixin):
    events = EventMixin.events | set ((
        'on_buddy_join',
        'on_buddy_leave',
        'on_buddy_timeout',
        'on_conn_success',
        'on_authenticate',
        'disconnect',
        'contact_alias',
        'needs_auth',
        'recv_error',
        'recv_text_msg',
        'send_text_msg',
        'typing_info',
        'recv_action',

        'recv_p2p_msg',
        'transport_error',
    ))

    POST_URL  = "https://ows.messenger.msn.com/OimWS/oim.asmx"
    #SOAP_ACT  = "http://messenger.msn.com/ws/2004/09/oim/Store"
    SOAP_ACT  = 'http://messenger.live.com/ws/2006/09/oim/Store2'
    OIM_NS    = ('oim',"http://messenger.msn.com/ws/2004/09/oim/")
    WSRM_NS   = ('wsrm',"http://schemas.xmlsoap.org/ws/2003/03/rm")
    WSUTIL_NS = ('wsutil',"http://schemas.xmlsoap.org/ws/2002/07/utility")

    # Don't switch this to util.net.user_agent()
    USER_AGENT= 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; Messenger (BETA) 8.0.0328)'
    CLIENT_STR = '8.1.0178'

    def __init__(self, client, buddy):
        EventMixin.__init__(self)

        self.lockkey = ''
        self.buildver = 'Digsby %r' % sys.REVISION
        self.run_id = str(uuid.uuid4()).upper()
        self.msgnum = 1
        self.client = client
        self.buddy = buddy
        self.version = self.client.version
        self._closed = False
        self._connected = False

    @property
    def appid(self):
        return self.client.appid

    @property
    def appcode(self):
        return self.client.appcode

    def get_token(self):
        #return self.client.get_token('messenger.msn.com')
        return self.client.get_token('messengersecure.live.com')

    def set_token(self, newtoken):
        #return self.client.set_token('messenger.msn.com', newtoken)
        return self.client.set_token('messengersecure.live.com', newtoken)

    token = property(get_token, set_token)

    @property
    def self_buddy(self):
        return self.client.self_buddy

    def invite(self, name):
        self.on_buddy_join(name)

    @event
    def on_buddy_join(self, name):
        "the buddy named 'name' has joined"

    def connected(self):
        return self._connected

    @util.callbacks.callsback
    def connect(self, callback):
        log.info('Connecting OfflineMessageSender')
        log.info('OfflineSBAdapter "connected"')
        self.event('on_conn_success', self)
        self._connected = True
        callback.success()

    @util.callbacks.callsback
    def send_message(self, fmsg, callback=None):
        text = fmsg.format_as('plaintext')

        log.info('OfflineSBAdapter send_message: %r', text)

        env = soap(self.OIM_NS[1])
        env.Header += tag('From',
                          memberName=self.self_buddy.name,
                          #friendlyName=make_header(self.self_buddy.remote_alias),
                          proxy='MSNMSGR',
                          msnpVer=self.version,
                          buildVer=self.CLIENT_STR)
        env.Header += tag('To',memberName=self.buddy.name)
        env.Header += tag('Ticket',
                          passport=self.token.encode('xml'),
                          appid=self.appid,
                          lockkey = self.lockkey,
                          )
        env.Header += (tag((self.WSRM_NS, 'Sequence'))
                       (tag((self.WSUTIL_NS, 'Identifier'), 'http://messenger.msn.com'),
                        tag('MessageNumber',self.msgnum))
                       )

        env.Body += tag('MessageType','text')
        env.Body += tag('Content',self._build_message(text))

        self.event('send_text_msg', text)

        def post_success(result):
            log.info('Post result: %r', result._to_xml(pretty=False))
            fault = result._findOne("Fault")
            if fault:
                if (OIMExceptions.AuthFailed in fault.faultcode._cdata.strip()):
                    # try authentication again...
                    self.authenticate(fault,
                                      success=lambda: self.send_message(fmsg, callback=callback),
                                      error  =lambda e,*a,**k: (callback.error(e), log.info('Error   from authenticate: %r, %r', a,k))
                                      )
                else:
                    log.info('Sending message failed: %r', result._to_xml(pretty=False))
                    callback.error(result)
            elif result.Header.SequenceAcknowledgment:
                log.info('Got SequenceAcknowledgment')
                self.msgnum += 1
                callback.success()
            else:
                log.info('Unknown response from posting OIM: %r', result._to_xml(pretty=False))

        def post_error(exception):
            log.info('Post exception: %r, %r, %r', type(exception), (exception._to_xml(pretty=False) if hasattr(exception, '_to_xml') else ''), vars(exception))
            callback.error(exception)

        self.post(env, success=post_success, error=post_error)

    @util.callbacks.callsback
    def authenticate(self, fault, callback=None):
        lockcode = fault.detail.LockKeyChallenge._cdata.strip()
        twnchal =  fault.detail.TweenerChallenge._cdata.strip()
        if not (lockcode or twnchal):
            #assert lockcode or twnchal, (lockcode, twnchal, t._to_xml())
            callback.error(fault)
            return

        log.info('OIM LockKey=%r, TweenerChallenge=%r', lockcode, twnchal)

        if twnchal:
            self.token = ''
        if lockcode:
            self.lockkey = ''

        # Don't do this 'til we have both lockkey and tweener ticket
        success = util.CallCounter(2, callback.success)

        if lockcode:
            log.info('Making lockkey from LockKeyChallenge')
            self.lockkey = self.client.ns._challenge_response(lockcode, self.appcode)
            success()
            #env.Header.Ticket['lockkey'] = self.lockkey
        else:
            # knock the callcounter down one anyway
            success()

        if twnchal:
            log.info('Requesting tweener authentication with TweenerChallenge')

            def set_ticket(tck):
                log.info('Got tweener ticket. Setting it on protocol and calling success()')
                self.token = tck.decode('xml')
                success()

            import mail.passport
            mail.passport.do_tweener_auth_3(self.client.username, self.client.password,
                                         (twnchal,), success = set_ticket, error=callback.error)
        else:
            # knock the callcounter down one anyway. this will definitely call callback.success if we get here.
            success()

    @util.callbacks.callsback
    def post(self, env, callback=None):
        post_xml(self.POST_URL, env,
                 callback=callback,
                 Accept='*/*',
                 SOAPAction=self.SOAP_ACT,
                 ContentType='text/xml; charset=utf-8',
                 **{'User-Agent':self.USER_AGENT})

    def _build_message(self, msg):
        return '\r\n'.join([
             'MIME-Version: 1.0',
             'Content-Type: text/plain; charset=UTF-8',
             'Content-Transfer-Encoding: base64',
             'X-OIM-Message-Type: OfflineMessage',
             'X-OIM-Run-Id: {%s}' % self.run_id,
             'X-OIM-Sequence-Num: %d' % self.msgnum,
             '',
             msg.encode('utf-8').encode('base64'),
             ])

    def leave(self):
        self._closed = True
        self._connected = False

# ------------------------------------------------------------------------------
