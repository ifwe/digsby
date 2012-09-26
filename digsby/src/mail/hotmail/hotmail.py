'''
Hotmail.py

Provides functionality for logging into hotmail, retrieving messages
and common operations such as mark as read, delete, mark as spam, etc.
'''
from __future__ import with_statement

import logging, traceback, time, re, random, datetime
import cookielib, urlparse, urllib2, cgi
import uuid
import hmac, hashlib
import base64

import lxml.html as HTML
import util, util.httptools, util.xml_tag
import util.net as net
import util.callbacks as callbacks
import util.primitives.bits as bits
import common

import mail
import mail.passport

from contextlib import closing

WebScraper = util.httptools.WebScraperBase

def LXMLPARSE(s, base_url):
    return HTML.fromstring(s, base_url)

import ajax


def LaunchDefaultBrowserLater(url):
    import wx # XXX: gtfo plz
    log.warning('Opening the following URL in browser: %s', url)
    wx.CallAfter(wx.LaunchDefaultBrowser, url)

def ntok():
    return str(random.randint(0, 0x7fffffff))

class NotInbox(Exception):
    'This exception is raised when the page loaded from the inbox URL is not the inbox'

numregex = re.compile(r'(\d+)')

log = logging.getLogger('hotmail')

folderids = util.LowerStorage(dict(zip('inbox trash sent drafts junk'.split(), range(1,6))))
folderids.deleted = folderids.trash

class HotmailUUID(uuid.UUID):
    pass

class Hotmail(common.emailaccount.EmailAccount, WebScraper):
    '''
    Hotmail object. Contains all functionality of hotmail account
    '''

    MAX_REDIRECTS = 5

    domain = 'live.com'

    nicename = 'Hotmail'
    protocol = 'hotmail'
    livemail = True

    default_domain = 'hotmail.com'

    AUTH_URL = 'https://login.live.com/ppsecure/sha1auth.srf?lc=1033'
    PP_AUTH_VERSION = None
    LAST_KNOWN_PP_AUTH_VERSION = '1100'

    def __init__(self, *args, **kwargs):
        self.urls = {
                'inbox': lambda : 'https://mail.live.com/?rru=inbox',
                'prelogin' : lambda : 'http://login.live.com',
                }

        WebScraper.__init__(self)
        common.emailaccount.EmailAccount.__init__(self, *args, **kwargs)
        self.name = self.email_address

        self._reset_state()

        self.folders = []

        self.inbox = ajax.MailFolder(self)
        self.base_url = 'https://mail.live.com/default.aspx'

        self.HM = None

    def timestamp_is_time(self, tstamp):
        return not self.livemail

    def init_http(self):
        WebScraper.init_http(self)
        self.set_cookie('lr', '1', domain = '.live.com', path = '/')
        self.http.addheaders = [('User-Agent',
                                 net.user_agent()),
                                 ('Referer', 'https://mail.live.com/default.aspx?'
                                  'FolderID=00000000-0000-0000-0000-000000000001&'
                                  'InboxSortAscending=False&InboxSortBy=Date&n=' + ntok()),
                                 ]


    def build_request_default(self, name, **req_options):
        req = req_options.get('_request', None)
        if req is not None:
            if name == req.get_full_url():
                return req

        return super(type(self), self).build_request_default(name, **req_options)

    def open(self, req, *a, **k):
        return self.request(req.get_full_url(), _request = req, *a, **k)

    @util.callsback
    def _goto_hotmail_url(self, relative_url, data=None, callback=None):
        '''
        relative_url = '/cgi-bin/HoTMaiL' or '/cgi-bin/compose?mailto=1&to=email@domain.com'
        '''

        if data is not None:
            data = (relative_url, data)
            new_relative_url = '/cgi-bin/HoTMaiL'
        else:
            new_relative_url = relative_url

        def sso_success(s,t):
            log.info('sso_success: %r, %r', s, t)
            callback.success()
            self._open_url_2(hotmail_token(s, t, rru = new_relative_url), data)

        callback.error += lambda e : self._open_url_err(relative_url, e)
        SSO_Auth(self.username, self._decryptedpw(), pp_auth_version = self.PP_AUTH_VERSION,
                 success=sso_success,
                 error  =callback.error,
                 )

    def _open_url_err(self, url, err):
        log.error('Error (%r) opening url %s', err, url)

    def _open_url_2(self, token, data):

        url = self.AUTH_URL + '&'+ token

        if data is None:
            LaunchDefaultBrowserLater(url)
        else:
            self.post_data(url, *data)

    def check_for_redirect(self, data):
        try:
            return self.inbox_re.search(data).groups()[0]
        except Exception:
            return None

    def post_data(self, login_url, post_url, data):
        with closing(self.http.open(login_url)) as resp:
            redirect = resp.content

        assert 'window.location.replace' in redirect

        redirect_url = self.check_for_redirect(redirect)
        if redirect_url is None:
            raise Exception("Expected redirect url, but it wasn't there. Data = %r", redirect)

        with closing(self.http.open(redirect_url)):
            pass

        with closing(self.http.open(util.httpjoin(redirect_url, post_url), data)):
            pass

    def _get_mailclient(self):
        return common.pref('privacy.www_auto_signin', False)

    def _set_mailclient(self, val):
        '''
        Not supported.
        '''
        return

    mailclient = property(_get_mailclient, _set_mailclient)

    def start_client_email(self, email = None, use_client = True):

        if email is None:
            url = self.inbox.login_link()
        elif isinstance(email, basestring):
            url = email
        else:
            if self.mailclient:
                url = email.login_link()
            else:
                url = email.link

        if url and url.startswith("http"):
            LaunchDefaultBrowserLater(url)
            return None

        if url == '':
            url = self.inbox.login_link()

        if use_client and self.mailclient:
            self._goto_hotmail_url(url, error = lambda *a: self.start_client_email(url, use_client = False))
            return None
        else:

            url = 'https://mail.live.com/default.aspx?n=123456789'
            LaunchDefaultBrowserLater(url)

        return url

    @property
    def inbox_url(self):
        '''
        Returns the URL for this email account's inbox
        '''
        try:
            return self.inbox.link
        except AttributeError:
            return 'https://mail.live.com/default.aspx?n=' + ntok()

    @property
    def logged_in(self):
        if bool(self.get_cookie('MSPAuth', default = False, domain = '.live.com')):
            return True
        elif bool(self.get_cookie('PPAuth', default = False, domain = '.login.live.com')):
            return True
        else:
            return False

    def build_request_loginpage(self, *a):

        if _is_login_domain_exception(self.username):
            url = 'https://msnia.login.live.com/pp%s/login.srf'
        else:
            url = 'https://login.live.com/pp%s/login.srf'
        url %= self.PP_AUTH_VERSION
        return self.RequestFactory(util.UrlQuery(url, vv = self.PP_AUTH_VERSION, svc='mail', bk=int(time.time())))

    def handle_success_loginpage(self, _name, resp):
        doc = resp.document
        if doc is None:
            raise NotInbox()
        if int(self.PP_AUTH_VERSION) < 900:

            form = None
            for form in doc.forms:
                if form.get('name') == 'f1': # it would be great if this had a real name, like "login" or something.
                    break

            if form is None:
                self.handle_error(_name, Exception('No login form found'))
                log.error("Document: %r", HTML.tostring(doc))
                return

            form.fields['login'] = self.username
            form.fields['passwd'] = self._decryptedpw()

            self._login_form = form
        else:
            data =  HTML.tostring(doc)
            log.error("Document: %r", data)
            ppft_html = eval(util.get_between(data, "sFTTag:", ",") or 'None')
            ppft_token = HTML.fromstring(ppft_html).attrib['value']
            bk = str(int(time.time()))
            action_url = net.UrlQuery('https://login.live.com/ppsecure/post.srf',
                                      **{'bk': bk,
                                         'cbcxt': 'mai',
                                         'ct': bk,
                                         'id': '64855',
                                         'lc': '1033',
                                         'mkt': 'en-us',
                                         'rpsnv': '11',
                                         'rver': '6.1.6206.0',
                                         'snsc': '1',
                                         'wa': 'wsignin1.0',
                                         'wp': 'MBI',
                                         'wreply': 'https://mail.live.com/default.aspx'})

            if _is_login_domain_exception(self.username):
                action_url = action_url.replace('login.live.com', 'msnia.login.live.com')
            self._login_form = util.Storage(form_values = lambda:
                                            dict(login = self.username,
                                                 passwd = self._decryptedpw(),
                                                 type = '11',
                                                 LoginOptions = '2',
                                                 NewUser='1',
                                                 MEST='',
                                                 PPSX='Passp',
                                                 PPFT= ppft_token,
                                                 idsbho = '1',
                                                 PwdPad = '',
                                                 sso = '',
                                                 i1 = '1',
                                                 i2 = '1',
                                                 i3 = '161605',
                                                 i4 = '',
                                                 i12 = '1',
                                                 ),
                                            action = action_url)

        log.info('Got loginform for %r, submitting', self)
        self.request('sendauth')

    def handle_error_loginpage(self, _name, e):
        del self.PP_AUTH_VERSION
        log.error('Error getting loginpage')
        self._login_form = None
        self.handle_error_default(_name, e)
        self.set_offline(self.Reasons.CONN_FAIL)

    def build_request_sendauth(self, *a):
        if getattr(self, '_login_form', None) is None:
            return None

        form, self._login_form = self._login_form, None
        return self.RequestFactory(form.action, data = form.form_values()) # method? urllib2.Request doesn't accept a method override

    def handle_success_sendauth(self, _name, resp):
        if self.logged_in:
            on_login, self._on_login = getattr(self, '_on_login', None), None
            if on_login is not None:
                on_login()
        else:
            self.set_offline(self.Reasons.BAD_PASSWORD)

    def authenticate(self, task=None):
        '''
        Log in to the email account represented by this object with the given username and password.

        '''
        self.change_state(self.Statuses.AUTHENTICATING)

        if task is None:
            task = self.update

        if not self.logged_in:
            log.info('beginning authentication for %s', self.name)
            self._on_login = task
            if self.PP_AUTH_VERSION is None:
                self.request('prelogin', error = lambda *a: self.bad_pw())
            else:
                self.request('loginpage', error   = lambda *a: self.bad_pw())

        else:
            task()

    def find_pp_auth(self, resp):
        doc = HTML.fromstring(resp.read())
        base = doc.base
        if base is not None:
            urlparts = net.UrlQuery.parse(base)
            base_path = urlparts.get('path')
            match = re.match('/pp(\d+).*', base_path)
            if match and match.group(1):
                return match.group(1)

        return self.LAST_KNOWN_PP_AUTH_VERSION

    def handle_success_prelogin(self, _name, resp):
        self.PP_AUTH_VERSION = self.find_pp_auth(resp)
        log.debug('Got PPAuth version: %r', self.PP_AUTH_VERSION)

        self.request('loginpage',
                     error   = lambda *a: self.bad_pw())

    def check_message_at_login(self, resp):
        doc = resp.document

        form = doc.find('.//form[@id="MessageAtLoginForm"]')
        if form is not None:
            self._loginmsg_form = form
            self.request('loginmsg')
            return True
        else:
            return False

    def build_request_loginmsg(self, *a):
        if getattr(self, '_loginmsg_form', None) is None:
            return None

        form, self._loginmsg_form = self._loginmsg_form, None
        return self.RequestFactory(form.action, data = form.form_values()) # method? urllib2.Request doesn't accept a method override

    def handle_success_loginmsg(self, _name, resp):
        log.info('Got success response for loginmsg, requesting inbox')
        self.request('inbox')

    def handle_error_loginmsg(self, *args):
        log.info('Got error response for loginmsg, requesting inbox anyway (args=%r)', args)
        self.request('inbox')

    def check_success_inbox(self, _name, resp):
        doc = resp.document
        log.debug("Inbox page src: %r", HTML.tostring(doc, pretty_print = True))
        iframe = doc.find('.//iframe[@id="UIFrame"]')
        if iframe is not None:
            iframe_url = iframe.get('src', '').decode('xml')
            if iframe_url == '' or iframe_url.startswith("javascript"):
                self.urls['inbox'] = 'https://mail.live.com/?rru=inbox'
                log.info("using default url for inbox: %r", self.urls['inbox'])
                return True
            else:
                log.info('Found iframe. src = %r', iframe_url)
                self.urls['inbox'] = iframe_url
                return True
        else:
            return False

    def handle_success_inbox(self, _name, resp):

        if self.check_message_at_login(resp):
            return

        data = resp.content
        redirect_url = self.check_for_redirect(data)
        if redirect_url is not None:
            log.info("Detected redirect in inbox: %r", redirect_url)

        if self.check_success_inbox(_name, resp):
            self.clear_waiting('inbox')
            self.request('inbox')
            return

        got_page_info = False
        got_app_info = False

        self.base_url = resp.geturl()
        doc = resp.document

        for script in doc.findall('.//script'):
            if not script.text:
                continue
            if not got_app_info:
                app_info_raw = util.get_between(script.text, 'App =', ';')
                if app_info_raw is not None:
                    got_app_info = True

            if not got_page_info:
                page_info_raw = util.get_between(script.text, 'Page =', ';')
                if page_info_raw not in (None, ' {}'):
                    got_page_info = True

            if got_app_info and got_page_info:
                break
        else:
            raise NotInbox("Could not find app info or page info. Here's status, headers, raw data: (%r, %r, %r)",
                            resp.code, str(resp.headers), resp.content)

        try:
            app_info = jsdict_to_python(app_info_raw)
        except Exception:
            raise NotInbox("Error parsing app info. Here's raw data: (%r, %r)",
                            app_info_raw, resp.content)
        try:
            page_info = jsdict_to_python(page_info_raw)
        except Exception:
            raise NotInbox("Error parsing page info. Here's raw data: (%r, %r)",
                            page_info_raw, resp.content)

        log.info('Got app & page info: App = %r, Page = %r', app_info, page_info)

        self._app_info = app_info
        self._cfg_info = page_info
        cfg_info = page_info.get('fppCfg', {})
        trash_id = app_info.get('config', {}).get('sysFldrs', {}).get('trashFid', None)
        if trash_id is not None:
            self._trash_id = uuid.UUID(trash_id)
        else:
            self._trash_id = uuid.UUID(int=folderids.trash)

        network = ajax.Network_Type(ajax.FPPConfig(self), self, cfg_info)
        self.HM = ajax.HM_Type(network, urlparse.urlparse(self.base_url).hostname, app_info)

        log.info("Hotmail site version: %r", self.HM.build)
        if self.HM.build > max(sum((x.keys() for x in ajax._versioned_classes.values()), [])):
            if not getattr(self, 'warned_newbuild', False):
                self.warned_newbuild = True
                try:
                    raise Exception("New hotmail build detected: %r" % self.HM.build)
                except:
                    import traceback; traceback.print_exc()

        self._process_folderlist(doc)

        folders = self.folders

        inboxid = uuid.UUID(int=folderids.inbox)
        self.inbox = ([f for f in folders if f.id == inboxid] or [None])[0]
        self.trash = ([f for f in folders if f.id == self._trash_id] or [None])[0]

        self.GetInboxData(folders = True, messages = True, success = self._process_ajax_inbox)

    def _process_folderlist(self, doc):
        folderlist = doc.find('.//*[@id="folderList"]')
        if folderlist is None:
            raise NotInbox('Couldnt find folderList in %r', HTML.tostring(doc))
        self.folders = [self.HM.GetFppTypeConstructor('LivemailFolder').from_doc(x, self) for x in folderlist.findall('.//*[@count]')]

    def _process_messagelist(self, doc):
        self.inbox.process_one_page(doc)

    def _process_ajax_inbox(self, result):

        folderlist_doc = HTML.fromstring("<div>" + result.FolderListHtml.value + "</div>")
        self._process_folderlist(folderlist_doc)

        messagelist_doc = HTML.fromstring(result.MessageListHtml.value)
        self._process_messagelist(messagelist_doc)

        self.on_good_inbox() # clear bad inbox counter

        if self.state == self.Statuses.OFFLINE:
            log.error('finish_update exiting early, state is %s', self.state)
            return

        self._received_emails(self.inbox[:25], len(self.inbox))
        self.setnotifyif('count', self.inbox.count)
        self.change_state(self.Statuses.ONLINE)

    def preprocess_resp_inbox(self, name, resp, **req_options):
        if not isinstance(resp, NotInbox):
            resp = self.preprocess_resp_default(name, resp, **req_options)
            redirect_url = self.check_for_redirect(resp.content)
            if redirect_url is not None:
                return Redirect(redirect_url)

        return resp

    def handle_error_inbox(self, _name, e):
        self._login_form = None

        def fatal_error():
            self.handle_error_default(_name, e)
            self.set_offline(self.Reasons.CONN_FAIL)

        try:
            raise e
        except NotInbox:
            self.on_bad_inbox(e)
            if self._inbox_request_error_count < 3:
                self.request('inbox')
            else:
                fatal_error()
        except:
            self.on_good_inbox() # it's not really a 'good' inbox, but we need to clear the counter
            fatal_error()

    def on_bad_inbox(self, e = None):
        log.error('Got a bad inbox page, exception was: %r', e)
        setattr(self, '_inbox_request_error_count', getattr(self, '_inbox_request_error_count', 0) + 1)

    def on_good_inbox(self):
        setattr(self, '_inbox_request_error_count', 0)

    def detect_livemail(self, html):
        return True # All microsoft mail accounts are live enabled now.

    def open_folders(self):
        log.info('Opening %s\'s folders', self.name)
        for folder in self.folders:
            folder.open()
        log.info('Done opening folders for %s', self.name)

    def update(self):
        common.emailaccount.EmailAccount.update(self)

        if not self.logged_in:
            log.info('%s has not yet authenticated', self.name)
            return self.authenticate()

        self.request('inbox')

    def bad_pw(self):
        if self.offline_reason != self.Reasons.CONN_FAIL:
            common.emailaccount.EmailAccount.bad_pw(self)
        else:
            log.error('Skipping call to "bad_pw" because %r is already offline with CONN_FAIL', self)

    def sort_emails(self, new=None):
        # Already sorted by date- thanks hotmail!
        pass

    def filter_new(self, new, old):
        return super(Hotmail, self).filter_new(new, False)

    def compose_link(self, email='', subject='', body='', cc='',bcc='',):

        kw = dict()

        if email:
            kw['to'] = email

        for name in 'subject body cc bcc'.split():
            if vars()[name]:
                kw[name] = vars()[name]

        if kw:
            kw['mailto'] = 1

        kw['n'] = '123456789'

        url = util.UrlQuery(util.httpjoin(self.base_url, '/mail/EditMessageLight.aspx'),
                            fti='yes', **kw)

        log.info('compose_link returning: %s', url)

        return url

    def compose(self, *a, **k):
        use_client = k.pop('use_client', True)
        url = self.compose_link(*a, **k)

        if self.mailclient and use_client and not url.startswith('http'):
            self._goto_hotmail_url(url, error = lambda *a: self.start_client_email(url, use_client = False))
        else:
            return util.httpjoin(self.base_url, url, True)

    def __iter__(self):
        for email in self.inbox:
            yield email

    def markAsRead(self, email):
        common.emailaccount.EmailAccount.markAsRead(self, email)
        util.threaded(email.mark_as_read)()

    def delete(self, email):
        common.emailaccount.EmailAccount.delete(self, email)
        util.threaded(email.delete)()

    def reportSpam(self, email):
        common.emailaccount.EmailAccount.reportSpam(self, email)
        util.threaded(email.spam)()

    def urlForEmail(self, email):
        '''
        Returns the URL for the provided email object.
        '''
        return email.link

    #### ajax stuff
    @util.callsback
    def send_email(self, to='', subject='', body='', cc='', bcc='', callback = None):

        def _try_form(*a):
            self._send_email_form(to, subject, body, cc, bcc, callback = callback)
            return True

        self._send_email_ajax(to, subject, body, cc, bcc, success = callback.success, error = _try_form)

    @util.callsback
    def _send_email_ajax(self,to, subject, body, cc, bcc, callback = None):
        if not hasattr(self.HM, 'SendMessage_ec'):
            return callback.error("Sending email with AJAX call is not supported for build %r",
                                  util.try_this(lambda:self.HM.app_info['BUILD'], "unknown"))

        self.HM.SendMessage_ec(
                               to,                 # to
                               self.name,          # from
                               '',                 # cc
                               '',                 # bcc
                               0,                  # priority
                               subject,            # subject
                               body,               # message
                               [],                 # attachments
                               None,               # draftId
                               str(uuid.UUID(int=folderids.drafts)),   # draftFolderId
                               None,               # originalMessageId
                               None,               # rfc822MessageId
                               None,               # rfc822References
                               None,               # rfc822InReplyTo
                               0,                  # sentState
                               True,               # sendByPlainTextFormat
                               [],                 # ignoredWordsFromSpellCheck
                               None,               # hipAnswer
                               'audio',            # hipMode
                               None,               # meetingIcalId
                               callback,
                               )

    @util.callsback
    def _send_email_form(self, to, subject, body, cc, bcc, callback = None):
        cfg = self.HM.Network.configuration
        import ClientForm

        form = ClientForm.HTMLForm(util.UrlQuery(util.httpjoin(self.inbox_url, '/mail/SendMessageLight.aspx'), _ec = 1, n = ntok()),
                                   method="POST", request_class = self.RequestFactory)
        form.new_control('hidden', '__VIEWSTATE',               {'value' : ''})
        form.new_control('hidden', cfg.CanaryToken,             {'value' : cfg.CanaryValue})
        form.new_control('hidden', 'MsgPriority',               {'value' : '0'})
        form.new_control('hidden', 'ToolbarActionItem',         {'value' : 'SendMessage'})
        form.new_control('hidden', 'InfoPaneActionItem',        {'value' : ''})
        form.new_control('hidden', 'folderCache',               {'value' : ''})
        form.new_control('hidden', 'fDraftId',                  {'value' : ''})
        form.new_control('hidden', 'fMsgSentState',             {'value' : 'NOACTION'})
        form.new_control('hidden', 'IsSpellChecked',            {'value' : 'false'})
        form.new_control('hidden', 'fFrom',                     {'value' : self.username})
        form.new_control('hidden', 'cpselectedAutoCompleteTo',  {'value' : '[]'})
        form.new_control('hidden', 'fTo',                       {'value' : '"" <%s>;' % to})
        form.new_control('hidden', 'cpselectedAutoCompleteCc',  {'value' : ''})
        form.new_control('hidden', 'fCc',                       {'value' : cc})
        form.new_control('hidden', 'cpselectedAutoCompleteBcc', {'value' : ''})
        form.new_control('hidden', 'fBcc',                      {'value' : bcc})
        form.new_control('hidden', 'fSubject',                  {'value' : subject})
        form.new_control('hidden', 'fAttachment_data',          {'value' : ''})
        form.new_control('hidden', 'isFirstPL',                 {'value' : ''})
        form.new_control('hidden', 'RTE_MessageType',           {'value' : 'PlainText'})
        form.new_control('hidden', 'fMessageBody',              {'value' : body})

        request = form.click()

        log.info('Request obj = %r, vars = %r', request, vars(request))

        def check_success_send(resp):
            if resp is None:
                # assume it worked?
                return callback.success()

            data = resp.read()
            if 'SentMailConfirmation' in data:
                log.info('sent email!')
                callback.success()
            else:
                log.info('failed to send email: %r', data)
                callback.error()

        def check_error_send(exc):
            log.info('failed to send email: %r', exc)
            callback.error()

        util.threaded(self.open)(request, success = check_success_send, error = check_error_send)

    def make_mlri(self, folder, timestamp = False):
        if timestamp:
            ts = datetime.datetime.utcnow().isoformat() + 'Z'
        else:
            ts = None

        return self.HM.GetFppTypeConstructor('MessageListRenderingInfo')(
                FolderId = folder.id,
                MessageCount = 99,
                LastUpdateTimestamp = ts,
        )

    def make_mri(self, msg, old = True):
        return self.HM.GetFppTypeConstructor('MessageRenderingInfo')(
            MessageId = msg.id,
            FolderId = msg.folder.id,
            HmAuxData = msg.make_message_aux_data(),
        )

    @callbacks.callsback
    def GetInboxData(self, folders = False, messages = False, message = False, mri = None, callback = None):
        mlri = self.make_mlri(self.inbox)
        self.HM.GetInboxData(
                             fetchFolderList = folders,
                             renderUrlsInFolderList = True,
                             fetchMessageList = messages,
                             messageListRenderingInfo = mlri,
                             fetchMessage = message,
                             messageRenderingInfo = mri,
                             callback = callback)

    #### end of ajax stuff




def createMessageListRenderingInfo(defaults_from_message_list):
    ajax.MessageListRenderingInfo()
    b = defaults_from_message_list
    return b


def parsedate(datestring):
    return datestring

class SSO_Authorizer(object):
    def __init__(self, username, password, pp_auth_version):
        self.username = username
        self.password = password
        self.callback = None
        self.pp_auth_version = pp_auth_version

    @property
    def url(self):
        if _is_login_domain_exception(self.username):
            url = 'https://msnia.login.live.com/pp%s/RST.srf'
        else:
            url = 'https://login.live.com/pp%s/RST.srf'

        url %= self.pp_auth_version
        return url

    @util.callsback
    def auth(self, callback = None):
        self.callback = callback

        sectokreq = mail.passport.SecurityTokenRequest(0, 'http://Passport.NET/tb', '')
        env = mail.passport.make_auth_envelope(self.username, self.password, [sectokreq])
        url = self.url
        self.username = self.password = None

        try:
            util.xml_tag.post_xml(url,
                          env._to_xml(pretty = False),
                          success = self.finish,
                          error =   self.error)
        except Exception, e:
            traceback.print_exc()
            self.error(e)

    def finish(self, resp):
        RSTS = resp.Body.RequestSecurityTokenResponseCollection._children
        assert len(RSTS) == 1, resp._to_xml()

        RST = RSTS[0]
        callback, self.callback = self.callback, None

        if callback:
            callback.success(RST, resp)

    def error(self, e = None):
        callback, self.callback = self.callback, None

        if callback:
            callback.error(e)

@util.callsback
def SSO_Auth(username, password, pp_auth_version, callback = None):
    SSO_Authorizer(username, password, pp_auth_version).auth(callback = callback)

def hotmail_token(token, tag, rru='/cgi-bin/HoTMaiL'):
    nonce = bits.getrandbytes(24)

    secret = base64.b64decode(str(token.RequestedProofToken.BinarySecret))

    key = mail.passport.derive_key(secret, 'WS-SecureConversation'+nonce)
    info = (
        ('ct',str(int(time.time()))),
        ('bver','4'),
        ('id','2'),
        ('rru', rru),
        ('svc','mail'),
        ('js','yes'),
        ('pl','?id=2'),
        ('da', extract_encrypted(tag)),
        ('nonce',base64.b64encode(nonce)),
    )

    message = []
    add = message.append
    for k,v in info:
        add('&')
        add(k)
        add('=')

        v = v.encode('url')

        if k == 'rru':
            v = v.replace('/', '%2F').replace('.', '%2E')

        if k == 'da':
            v = v.replace('%3A', ':')

        add(v)

    message.pop(0)

    message = ''.join(message)
    hash = hmac.HMAC(key, message, hashlib.sha1).digest()

    message += '&hash=%s' % base64.b64encode(hash).encode('url')

    return 'token=%s' % message.encode('url').replace('%3A', ':')

def extract_encrypted(t):
    src = t._source

    if src:
        token = util.get_between(src, '<wst:RequestedSecurityToken>', '</wst:RequestedSecurityToken>')
    else:
        token = t.RequestedSecurityToken.EncryptedData._to_xml(pretty=False)

    return token

def jsdict_to_python(s):
    ''' use sparingly. '''
    class dumb(dict):
        def __getitem__(self, x):
            try:
                return dict.__getitem__(self, x)
            except KeyError:
                return x

    s = _remove_js_functions(s)

    s = ''.join(s.strip().splitlines())
    _globals = dumb(false = False, true = True, null = None)
    try:
        exec s in _globals, _globals
    except:
        pass

    for key in ('__builtins__', 'false', 'true', 'null'):
        _globals.pop(key, None)

    if len(_globals) == 0:
        return eval(s, _globals, _globals)
    return dict(_globals)

def _remove_js_functions(s):
    return re.sub('function\s*\(.*?\)\s*\{.*?\}', 'null', s)

def _is_login_domain_exception(username):
    return False

def main(un, password):
    Hotmail._decryptedpw = lambda h: h.password
    html = Hotmail(name=un, password=password)
    html.authenticate()

if __name__ == '__main__':
    #from wx.py.PyCrust import main
    main('digsby03@hotmail.com', 'passwords dont go here')
