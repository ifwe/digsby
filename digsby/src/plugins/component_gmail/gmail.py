'''
A Gmail account.

Uses the ATOM feed for inbox checking, and negotiates an authorization token
from the server for opening mail in a web browser.
'''

from __future__ import with_statement

import re
import time
import urllib2
import cookielib
import threading

from threading import Lock
from urllib import urlencode
from datetime import datetime
from traceback import print_exc

from util.net import UrlQuery, GetDefaultHandlers, WebFormData
from util.threads.timeout_thread import call_later
from util import threaded, scrape_clean, EmailAddress, Storage

from mail import Email
from common import pref
from common.emailaccount import EmailAccount
from logging import getLogger; log = getLogger('gmail'); info = log.info

class BadResponse(Exception):
    def __nonzero__(self):
        return False
class BadPassword(BadResponse):
    pass

class Gmail(EmailAccount):
    'Checks Gmail accounts.'

    protocol = 'gmail'

    baseAuthUrl  = 'https://www.google.com'
    authUrl  = '/accounts/ClientAuth'
    tokenUrl = '/accounts/IssueAuthToken'

    messageIdMatcher  = re.compile(r'message_id=([a-z0-9]+?)&')
    jsredirectMatcher = re.compile('location\.replace\("(.*)"\)')

    default_domain = 'gmail.com'

    def __init__(self, **k):
        EmailAccount.__init__(self, **k)
        self.internal_token = ''
        self.external_token = ''
        self.token_lock = threading.RLock()
        self.datatoken = ''
        self.updated_emails = None
        self.updated_count = None
        self.update_lock = Lock()
        self.emailaddress = EmailAddress(self.name, 'gmail.com')
        self._hosted = None
        self._multi = None

        if self.emailaddress.domain in ('gmail.com', 'googlemail.com'):
            self.baseMailUrl = '://mail.google.com/mail/'
        else:
            self.baseMailUrl = '://mail.google.com/a/' + self.emailaddress.domain + '/'

        self.browser_http = 'https'

        self.init_jar()

    can_has_preview = True

    def _reset_state(self):
        self.init_jar()
        self.internal_token = self.external_token = ''

    @property
    def browserBaseMailUrl(self):
        return self.browser_http + self.baseMailUrl

    @property
    def internalBaseMailUrl(self):
        return 'https' + self.baseMailUrl

    def init_jar(self):
        self.internal_jar = cookielib.CookieJar()
        self.internal_http_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.internal_jar), *GetDefaultHandlers())
        self.internal_http_opener.addheaders = \
        [("Content-type",  "application/x-www-form-urlencoded"),
         ("Cache-Control", "no-cache")]

        self.external_jar = cookielib.CookieJar()
        self.external_http_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.external_jar), *GetDefaultHandlers())
        self.external_http_opener.addheaders = \
        [("Content-type",  "application/x-www-form-urlencoded"),
         ("Cache-Control", "no-cache")]

    @property
    def inbox_url(self):
        return self._external_url(UrlQuery(self.browserBaseMailUrl))

    def urlForEmail(self, email):
        return self._external_url(UrlQuery(self.browserBaseMailUrl + "#all/" + str(email.id)))

    def popup_buttons(self, item):
        if not pref('email.popup_actions', default=False):
            return []

        try:
            return self._popup_buttons
        except AttributeError:
            def action(name):
                def cb(item):
                    from common import netcall
                    netcall(lambda: getattr(self, name)(item.email))
                cb.takes_popup_item = True
                cb.disables_button = True
                return cb

            self._popup_buttons = [(label, action(actionname))
                    for label, actionname in [
                        (_('Mark as Read'), 'markAsRead'),
                        (_('Archive'),      'archive'),
                    ]]

            return self._popup_buttons

    def markAsRead(self, email):
        EmailAccount.markAsRead(self, email)
        self._do_action('read', email)

    def archive(self, email):
        EmailAccount.archive(self, email)
        self._do_action('archive', email)

        if pref('gmail.markive', False):
            self.markAsRead(email)

    def delete(self, email):
        EmailAccount.delete(self, email)
        self._do_action('delete', email)

    def reportSpam(self, email):
        EmailAccount.reportSpam(self, email)
        self._do_action('spam', email)

    @threaded
    def _do_action(self, action, email, tries=0):
        try:
            self.gmail_at
        except KeyError:
            self.new_token()
            try:
                self.gmail_at
            except KeyError:
                if tries < 3:
                    log.debug_s('Action %r being retried', action)
                    return call_later(2, self._do_action, action, email, tries+1)
        url, params = self._actionUrl(action, email.id)
        response = self.webrequest(url, **params)
        log.debug_s('Action %r result: %r', action, response)

    def compose(self, to='', subject='', body='', cc='', bcc=''):
#        extra = dict() if not self.hosted else dict(fs='1', view='cm')
        extra = dict(fs='1', tf='1', view='cm')#, ui='1')# if not self.hosted else dict()
        su = subject

        for name in 'to su body cc bcc'.split():
            if vars()[name]:
                extra[name] = vars()[name]
        return self._external_url(UrlQuery(self.browserBaseMailUrl, **extra))

    def _external_url(self, url):
        if self.web_login:
            self.new_token(internal=False)
        if self.web_login and self.external_token:
            return UrlQuery('https://accounts.google.com/TokenAuth?',
                    **{'auth':self.external_token,
                       'service':'mail',
                       'continue':url,
                       'source':'googletalk'})
        else:
            return url

    def _actionUrl(self, action, message_id):
        action_names = dict(archive = 'rc_^i',
                            delete  = 'tr',
                            read    = 'rd',
                            spam    = 'sp',
                            star    = 'st')

        if not action in action_names.values():
            action = action_names[action]
        at = self.gmail_at
        url = UrlQuery(self.internalBaseMailUrl,
                       ik='',
                       search='all',
                       view='tl',
                       start='0')
        params = dict(act=action, at=at, vp='', msq='', ba='false',
                      t=message_id, fs='1')
        return url, params

    @threaded
    def send_email(self, to='', subject='', body='', cc='', bcc=''):
        log.info('sending a mail')
        data = dict(nvp_bu_send='Send')
        for name in 'to subject body cc bcc'.split():
            if vars()[name]:
                data[name] = vars()[name].encode('utf-8')

        if not hasattr(self, 'sendpath'):
            response = self.internal_http_opener.open(self.internalBaseMailUrl + '?ui=html')
            from urllib2 import urlparse
            respurl = urlparse.urlparse(response.geturl())
            try:
                response.close()
            except: pass
            del response
            self.sendpath = respurl.path
        url = 'https://mail.google.com' + self.sendpath
        try:
            at = self.gmail_at
        except KeyError:
            at = ''
        params = dict(at=at, v='b', pv='tl', s='s', fv='b', cpt='c', cs='c')
        if not self.hosted:
            params.update(fv='b', cpt='c', cs='c')
        else:
            params.update(cs='b', s='s')

        url = UrlQuery(url, params)

        response = self.webrequest(url, follow_js_redirects=True, **data)
        log.info('sent a mail')
        assert response and ('Your message has been sent.' in response)
        log.info('send mail success: %r', bool('Your message has been sent.' in response))
        return True

    def _get_notifier_data(self):
        return self.webrequest(url  = UrlQuery(self.internalBaseMailUrl, ui='pb'),
                               data = '')

    @property
    def hosted(self):
        if self._hosted is False:
            return False
        domain = self.emailaddress.domain
        return domain if domain not in ('gmail.com', 'googlemail.com') else None


    def authenticate(self, task=None):
        self.internal_token = token = self.new_token(internal=True)

        if not token:
            return False

        webreq_result = self.webrequest(UrlQuery('https://accounts.google.com/TokenAuth?',
                                                 **{'auth':token,
                                                    'service':'mail',
                                                    'continue':self.internalBaseMailUrl,
                                                    'source':'googletalk'}), internal=True)
        try:
            self.gmail_at
        except Exception:
            log.debug('gmail_at failed in authenticate')
        if webreq_result:
            self.new_token(False)
            return True
        else:
            return webreq_result

    def new_token(self, internal = True):
        password = self._decryptedpw()
        data = self.webrequest(self.baseAuthUrl + self.authUrl,
                               internal = internal,
                        data = WebFormData(
                          Email = self.name,
                          Passwd = password,
                          PersistentCookie='false',
                          accountType = 'HOSTED_OR_GOOGLE',
                          skipvpage='true'))
        if not data:
            return False

        if not data or data.find('Error=badauth') != - 1:
            log.warning('Invalid username or password: badauth token')
            self.bad_pw()
            return False
        d1 = dict(b.split('=') for b in data.split())
        d1.update(Session='true',skipvpage='true', service = 'gaia')
        token = self.webrequest(self.baseAuthUrl + self.tokenUrl, WebFormData(**d1))
        token = token.strip()
        if not internal:
            self.external_token = token

        return token

    @property
    def gmail_at(self):
        hosted = self.hosted
        if hosted:
            at_path = ('/a/' + hosted)
            try:
                return self.get_at_path(at_path)
            except KeyError:
                try:
                    try:
                        ret = self.get_at_path('/mail/u/0')
                    except KeyError:
                        ret = self.get_at_path('/mail')
                    else:
                        self._multi = True
                except KeyError:
                    raise
                else:
                    self._hosted = False
                    if self._multi:
                        self.baseMailUrl = '://mail.google.com/mail/u/0/'
                    else:
                        self.baseMailUrl = '://mail.google.com/mail/'
                    return ret
        if self._multi:
            return self.get_at_path('/mail/u/0')
        try:
            return self.get_at_path('/mail')
        except KeyError:
            try:
                ret = self.get_at_path('/mail/u/0')
            except Exception:
                raise
            else:
                self._multi = True
                return ret

    def get_at_path(self, path):
        return self.internal_jar._cookies['mail.google.com'][path]['GMAIL_AT'].value

    def update(self):
        log.info("update at %s", time.ctime(time.time()))
        EmailAccount.update(self)
        self.real_update(success = self.finish_update, error=self.on_error)

    def finish_update(self, updates):
#        if self.state == self.Statuses.OFFLINE:
#            log.error('finish_update exiting early, state is %s', self.state)
#            self.on_error(self.update)
#            return
        if updates is sentinel:
            log.warning('two updates were running at the same time')
            return

        try:
            (updated_emails, updated_count) = updates
        except (TypeError, ValueError):
            assert updates is None
            log.error('Update failed for %s, assuming auth error', self.name)
            if self.offline_reason != self.Reasons.BAD_PASSWORD:
                self.on_error(self.update)
            return
        log.info("%s got %d new messages %s", self, updated_count, time.ctime(time.time()))
        #self.change_state(self.Statuses.ONLINE)
        self._received_emails(updated_emails[:pref('gmail.max_messages', default=25, type=int)], updated_count)

    @threaded
    def real_update(self):
        #don't change to with, the idea is a non-blocking get on the lock
        if self.update_lock.acquire(False):
            try:
                if not self.internal_token:
                    info('no auth token yet, authenticating')
                    if not self.authenticate():
                        log.info('auth failed, returning None from real_update')
                        return None
                info('updating Gmail account %r at %s' % (self.name, time.ctime(time.time())))
                notifier_data = self._get_notifier_data()
                if isinstance(notifier_data, BadResponse):
                    log.critical('bad response for notifier_data: %r', notifier_data)
                    raise notifier_data

                try:
                    updated_emails, updated_count, _data = \
                            parse_datapacks(notifier_data)
                    updated_emails = chunks_to_emails(updated_emails)
                except Exception:
                    log.critical('could not transform notifier_data: %r', notifier_data)
                    raise
                return updated_emails, updated_count
            finally:
                self.update_lock.release()
        else:
            return sentinel

    def webrequest(self, url, data = '', follow_js_redirects = False, internal=True, **kwparams):
        http_opener = self.internal_http_opener if internal else self.external_http_opener
        try:
            response = http_opener.open(url, data + urlencode(kwparams.items()))

            resp = response.read()

            if follow_js_redirects:
                match = self.jsredirectMatcher.search(resp)

                if match:
                    # response may contain a Javascript location.replace="url" type
                    # redirect that is supposed to work on browsers. follow it!
                    new_url = match.groups()[0]
                    response = http_opener.open(self.baseAuthUrl + new_url)
                    resp = response.read()
            return resp
        except (urllib2.HTTPError, urllib2.URLError), e:
            if getattr(e, 'code', None) == 403:
                log.warning('Invalid username or password: HTTP code 403')
                self.bad_pw()
                return BadPassword()
            else:
                print_exc()
                import sys
                print >> sys.stderr, "url: %s" % url
        except Exception, e:
            print_exc()

            #self.on_error()#e)

        return BadResponse()

from util.primitives.bits import utf7_to_int as u7i

def chunk_datapack(data):
    assert data[0] == '\n' #first char is \n
    data = data[1:]
    num, numbytes = u7i(data) #next bit is utf7 number
#    print "numbytes", numbytes, repr(data[:numbytes])
    data = data[numbytes:] #take off the number
    return data[:num], data[num:] #return value, remainder

def get_chunk(data):
    type_, numbytes = u7i(data)
    data = data[numbytes:]
    if type_ == 184: #number of participants, value is next number
        value, length_ = u7i(data)
    elif type_ == 152: #to me/me only, mailing list
        value, length_ = u7i(data)
    else:
        length_, numbytes = u7i(data) #else, assume it has a length + value
        data = data[numbytes:] #remove length number
#    if type_ == 146:
#        length_ += 3
    return type_, data[:length_], data[length_:] #return type, value, remainder

def get_mid_date(data):
    orig_length = len(data)
    length_, numbytes = u7i(data) #length of chunk
    expected_length = (orig_length - length_) - numbytes
    data = data[numbytes:]
    msgid, numbytes = u7i(data) #msgid is first number
    data = data[numbytes:]
    _unknown, numbytes = u7i(data) #mystery byte
    data = data[numbytes:]
    time_in_ms, numbytes = u7i(data) #next is time in milliseconds
    data = data[numbytes:]
#    print "len is", len(data), "expected", expected_length
    assert len(data) == expected_length
    return msgid, time_in_ms, data #msgid, time, remainder

from collections import defaultdict
def parse_chunk(chunk):
    retval = defaultdict(list)
    mid, time_in_ms, data = get_mid_date(chunk)
    retval["mid"] = mid
    retval["time"] = time_in_ms
    while data:
        t, v, data = get_chunk(data)
        if t == 146: #email
            v = parse_from(v)
        elif t in (152, 184): #personal level, conversation size
#            print repr(v)
            v = u7i(v)[0]
        retval[t].append(v)
    return retval

def chunks_to_emails(dictionaries):
    def safe_transform(x):
        try:
            return dict_to_email(x)
        except Exception, e:
            log.error('Could not transform this dictionary into an email: %r', x)
            raise e

    return filter(bool, map(safe_transform, dictionaries))

def parse_datapacks(data):
    retval = []
    while data[0] == '\n': #while the next thing is a message
        chunk, data = chunk_datapack(data) #get a chunk
        retval.append(parse_chunk(chunk))
    num_messages = 0
    type_, numbytes = u7i(data) #the thing after the last msg is usually num msgs
    data = data[numbytes:]
    if type_ == 136: #num_messages
        num_messages, numbytes = u7i(data)
        data = data[numbytes:]
    return retval, num_messages, data

def parse_from(from_):
    retval = {}
    assert from_[0] == "\n" #first byte is \n
    from_ = from_[1:]
    retval['mystery_bytes1'], from_ = from_.split("\n", 1) #something, and then \n
#    retval['mystery_bytes1'] = ord(retval['mystery_bytes1']) #seems to be a number
    length_, numbytes = u7i(from_) #length of address
    from_ = from_[numbytes:]
    retval['email_addr'], from_ = from_[:length_], from_[length_:] #address is next
    type_, numbytes = u7i(from_)
    if type_ == 0x12: #text version of from, i.e. the name
        from_ = from_[numbytes:]
        length_, numbytes = u7i(from_)
        from_ = from_[numbytes:]
        retval['from_text'], from_ = from_[:length_], from_[length_:]
    retval['remainder_bytes'] = from_
    return retval

# email text comes in as UTF-8, and
# scrape_clean replaces HTML/unicode entities with their correct characters
decode = lambda s: scrape_clean(s.decode('utf-8'))


class GMAIL(object):
    '''Constants used to identify parts of messages.'''
    LABELS = 130
    AUTHOR = 146
    PERSONAL_LEVEL = 152
    SUBJECT = 162
    SNIPPET = 170
    ATTACHMENTS = 178
    NUM_MSGS_IN_THREAD = 184

def dict_to_email(d):
    msgid = d['mid']
    author_email = d[GMAIL.AUTHOR][-1]['email_addr']

    author_name = decode(d[GMAIL.AUTHOR][-1].get('from_text', ''))
    subject     = decode(d[GMAIL.SUBJECT][-1])
    snippet     = decode(d[GMAIL.SNIPPET][-1])
    attachments = [Storage(name = a) for a in d[GMAIL.ATTACHMENTS]]
    labels      = [decode(l) for l in d[GMAIL.LABELS] if not l.startswith('^')]

    return Email(id = ('%x' % msgid),
                 fromname    = author_name,
                 fromemail   = author_email,
                 sendtime    = datetime.fromtimestamp(d["time"]//1000),
                 subject     = subject,
                 content     = snippet,
                 attachments = attachments,
                 labels      = labels)
