from __future__ import with_statement

import traceback
import cookielib
import urllib2

from threading import Lock
from datetime import datetime
from urlparse import urlparse
from urllib import quote
from logging import getLogger

import util.net
from mail import Email, MailException
from util import UrlQuery, WebFormData, get_func_name, GetDefaultHandlers, threaded
from util.primitives.error_handling import try_this
from common.emailaccount import EmailAccount

log = getLogger('YahooMail')

class YahooMailException(MailException): pass
class YahooMailAuthException(YahooMailException): pass
class YahooMailAuthRedirect(YahooMailException): pass
class YahooMailBadDataException(YahooMailException): pass
class YahooMailNoAccountException(YahooMailBadDataException): pass

SessionIdReissue   = 'Client.ClientRedirect.SessionIdReissue'
ExpiredCredentials = 'Client.ExpiredCredentials'
backup_server      = 'us.mg1.mail.yahoo.com' #should be calculated with "accellerator" i.e. uk.mg...

def ymail_action(func):
    def ymail_action_wrapper(self, *a, **k):

        if self._current_action is None:
            self._current_action = func.func_name

        try:
            return func(self, *a,**k)
        except YahooMailAuthException, e:
            self.bad_pw()
        except YahooMailNoAccountException, e:
            self.no_mailbox()
        except Exception, e:
            traceback.print_exc()
        finally:
            self._current_action = None

    return threaded(ymail_action_wrapper)



class YahooMail(EmailAccount):
    protocol = 'ymail'
    default_domain = 'yahoo.com'
    def __init__(self, *args, **kwargs):
        EmailAccount.__init__(self, *args, **kwargs)
        self.init_jar()
        self.update_lock = Lock()
        self.updated_emails  = None
        self.updated_count   = None
        self.isBeta = True
        self._current_action = None

    def timestamp_is_time(self, tstamp):
        return False

    def get_email_address(self):
        val = getattr(self, '_default_send_address', None)
        return val or EmailAccount.get_email_address(self)

    def init_jar(self):
        try:
            del self.u
        except AttributeError:
            pass
        try:
            del self._json_endpoint
        except AttributeError:
            pass

        self.jar = cookielib.CookieJar()
        self.http_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.jar), *GetDefaultHandlers())
        self.http_opener.addheaders = [('User-Agent',  util.net.user_agent())]

    def get_json_endpoint(self):
        try:
            return self._json_endpoint
        except AttributeError:
            newurl = UrlQuery('http://'+ self.hostname + '/ws/mail/v1.1/jsonrpc', appid='YahooMailRC')
            #hostname is likely to do an auth in this case, at which point, we might have a real endpoint to return
            try:
                return self._json_endpoint
            except AttributeError:
                self._json_endpoint = newurl
                return self._json_endpoint

    def set_json_endpoint(self, val):
        self._json_endpoint = val

    json_endpoint = property(get_json_endpoint, set_json_endpoint)

    def _reset_state(self):
        self.init_jar()
        try:
            del self.u
        except AttributeError:
            pass
        try:
            del self._json_endpoint
        except AttributeError:
            pass

    def update(self):
        log.error('ymail.update called from %s', get_func_name(2))
        if self.offline_reason == self.Reasons.BAD_PASSWORD and hasattr(self, 'u'):
            self.init_jar()
        EmailAccount.update(self)
        self.real_update(success = self.finish_update, error=self.warning)

    def warning(self, e=None):
        log.warning("yahoo blew up: %s", e)
        log.error('ymail.warning called from %s', get_func_name(2))

        if isinstance(e, YahooMailAuthException):
            self.bad_pw()
        else:
            self.on_error(self._current_action)

        return True

    def bad_pw(self):
        self.init_jar()
        EmailAccount.bad_pw(self)

    def finish_update(self, update):
        if self.state == self.Statuses.OFFLINE:
            log.error('finish_update exiting early, state is %r, reason is %r', self.state, self.offline_reason)
            return
        if update is None:
            log.warning('two updates were running at the same time')
            return
        try:
            (updated_emails, updated_count) = update
            self.updated_emails = True
            self._received_emails(updated_emails, updated_count)
        except (TypeError, ValueError), e:
            # all the proper error reporting functions should have been called by now
            log.error('Invalid response from real_update: %r', update)

    @threaded
    def real_update(self):
        # don't change to with, the idea is a non-blocking get on the lock
        if self.update_lock.acquire(False):
            try:
                result = self.get_yMsgs()
                if result:
                    return self._process_update_result(result)
                else:
                    log.info('Got bad result from get_yMsgs: %r', result)
                    raise Exception('bad result')
            finally:
                self.update_lock.release()

    def _process_update_result(self, result):
        (msgs, incount) = result
        updated_count = incount

        emails = []
        for msg in msgs:
            if msg.get('flags', {}).get('isRead', False):
                continue

            from_ = msg.get('from', {})
            if not from_:
                fromname = ''
            else:
                fromname = from_.get('name', from_.get('email', ''))

            e = Email(id         = msg['mid'],
                      fromname   = fromname,
                      sendtime   = try_this(lambda: datetime.fromtimestamp(msg['receivedDate']), None),
                      subject    = msg.get('subject', u''),
                      attachments= [True] * msg.get('flags', {}).get('hasAttachment', 0))

            emails.append(e)

        updated_emails = emails
        log.info('reporting %d emails', incount)
        #self.change_state(self.Statuses.ONLINE)
        return updated_emails, updated_count

    def get_auth_form(self):
        import ClientForm
        try:
            forms = ClientForm.ParseResponse(self.http_opener.open('https://mail.yahoo.com'), backwards_compat=False)
            for f in forms:
                if f.action == 'https://login.yahoo.com/config/login':
                    form = f
                    break
            else:
                raise AssertionError('there should be a login form here')
        except Exception, e:
            traceback.print_exc()

            form = ClientForm.HTMLForm('https://login.yahoo.com/config/login?', method="POST")
            form.new_control('hidden', '.done',  {'value' : 'http://mail.yahoo.com'})
            form.new_control('text',   'login',  {'value' : self.name.encode('utf-8')})
            form.new_control('text',   'passwd', {'value' : self._decryptedpw().encode('utf-8')})
            form.new_control('hidden', '.save',  {'value' : 'Sign+In'})
            form.new_control('hidden', '.done',  {'value' : 'http://mail.yahoo.com'})
        else:
            form['login'] = self.name.encode('utf-8')
            form['passwd'] = self._decryptedpw().encode('utf-8')
        return form

    def authenticate(self, tries=1):
        form = self.get_auth_form()
        try:
            resp = self.http_opener.open(form.click())
        except Exception, e:
            raise YahooMailException("failed to load url: %r" % e)
#        #check to see that we logged in?
        respdata = resp.read()
        resp.close()
        respurl = resp.geturl()
        if '/login' in respurl:
            with self.jar._cookies_lock:
                try:
                    self.jar._cookies['.yahoo.com']['/']['Y']
                    self.jar._cookies['.yahoo.com']['/']['T']
                except KeyError:
                    log.warning('url was: %r', respurl)
                    log.warning('html was: %r', respdata)
                    if tries <= 0:
                        raise YahooMailAuthException("failed to authenticate")
                    else:
                        import time
                        time.sleep(2)
                        return self.authenticate(tries - 1)
        elif 'replica_agree?' in respurl:
            pass
        elif 'verify?' in respurl:
            pass
        elif 'update?' in respurl:
            log.info('update? in resp url.')
        else:
            raise YahooMailAuthException("failed to authenticate, response url not expected", respurl)
        try:
            resp = self.http_opener.open('http://mail.yahoo.com/')
        except Exception, e:
            raise YahooMailException("failed to load url: %r" % e)
        self.u = urlparse(resp.geturl())
        resp.read()
        resp.close()
        try:
            self.user_data = self.api('GetUserData', _recursed=1000)
            self._default_send_address = self.user_data['result']['data']['userSendPref']['defaultFromAddress']
            try:
                self.isBeta = int(self.user_data['result']['data']['userFeaturePref'].get('optInState', '2')) == 2
            except ValueError:
                pass
        except Exception:
            traceback.print_exc()
        log.info('Authenticated successfully')

    @property
    def hostname(self):
        if not hasattr(self, 'u'):
            self.authenticate()
        return self.u.hostname

    def get_yMsgs(self):
        log.info("get_yMsgs")
        try:
            nummessages = [folder for folder in self.api('ListFolders')['result']['folder']
                           if folder['folderInfo']['fid'] == 'Inbox'][0]['unread']
        except YahooMailAuthException:
            raise
        except Exception:
            nummessages = 25
        nummessages = min(nummessages, 25)
        result = self.api('ListMessages',
                          fid='Inbox',
                          numMid=0,
                          groupBy='unRead',
                          startMid=0,
                          numInfo=nummessages,
                          sortKey='date',
                          sortOrder='down')
        incount = result['result']['folder']['unread']
        incount = int(incount) #floats are stupid for countables.
        return (result['result']['messageInfo'], incount)

    def sort_emails(self, new=None):
        pass

    def open_url(self, url, data=None):
        log.debug('open_url called from %s', get_func_name(2))
        return self._open_url(url, data)

    def _open_url(self, url, data=None):
        datastring = '' if not data else " with data: " + data
        log.info("opening url: " + url + datastring)
        try:
            response = self.http_opener.open(url, data)
        except Exception, e:
            ex = YahooMailException("failed to load url: %r" % e)
            log.error('%r', ex)
            raise ex
        else:
            log.info('httpopen succeeded')
            respurl = urlparse(response.geturl())
            if 'login.yahoo.com' in respurl.hostname:
                log.info('login.yahoo.com in URL -- calling authenticate')
                self.authenticate()
                return self.open_url(url, data)

            log.info('reading data from httpresponse')
            strdata = response.read()
            return strdata, respurl
        finally:
            if 'response' in locals():
                log.debug('closing response')
                response.close()

    def delete(self, msg):
        EmailAccount.delete(self, msg)
        self._delete(msg)

    @ymail_action
    def _delete(self, msg):
        self.api('MoveMessages', sourceFid='Inbox', destinationFid='Trash', mid=[msg.id])

    def markAsRead(self, msg):
        EmailAccount.markAsRead(self, msg)
        self._markAsRead(msg)

    @ymail_action
    def _markAsRead(self, msg):
        self.api('FlagMessages', fid='Inbox', mid=[msg.id], setFlags={'read':1})

    def reportSpam(self, msg):
        EmailAccount.reportSpam(self, msg)
        self._reportSpam(msg)

    @ymail_action
    def _reportSpam(self, msg):
        mark = dict(FlagMessages = dict(fid='Inbox', mid=[msg.id], setFlags={'spam':1, 'read':1}))
        move = dict(MoveMessages = dict(sourceFid='Inbox',
                              destinationFid='%40B%40Bulk',
                              mid=[msg.id]))
        self.api('BatchExecute', call=[mark, move])

    def open(self, msg):
        EmailAccount.open(self, msg)

        mid = msg.id

        return UrlQuery('http://mrd.mail.yahoo.com/msg?',
                 mid=mid,
                 fid='Inbox')

    def urlForEmail(self, msg):
        try:
            if self.web_login:
                return str(self.make_login_string() + '&.done=' + quote(self.open(msg), safe=''))
            else:
                return self.open(msg)
        except Exception, e:
            self.warning(e)
            return self.open(msg)

    def compose_link(self, to='', subject='', body='', cc='', bcc=''):
        extra = dict()
        Body = body
        subj = Subj = subject
        To = to
        Cc = cc
        Bcc = bcc

        #depending on what kind of account we're dealing with, they might want one or the other
        #easier just to send them all than figure out which
        for name in 'to To subj Subj subject body Body cc Cc bcc Bcc'.split():
            if vars()[name]:
                val = vars()[name]
                # TODO: This may result in junk data. Which encoding is Yahoo! Mail
                # expecting?
                if isinstance(val, unicode):
                    val = val.encode('utf-8')
                extra[name.title()] = val


        return UrlQuery('http://compose.mail.yahoo.com/', **extra)

    def compose(self, to='', subject='', body='', cc='', bcc=''):
        link = self.compose_link(to=to, subject=subject,
                               body=body, cc=cc, bcc=bcc)
        try:
            if self.web_login:
                return str(self.make_login_string() + '&.done=' + quote(link, safe=''))
            else:
                return link
        except Exception, e:
            self.warning(e)
            return link

    @threaded
    def send_email(self, to='', subject='', body='', cc='', bcc=''):
        result = self.api('SendMessage',
                          message={'subject':subject,
                                   'from':{'email':self.email_address}, #needs to come from user info
                                   'to':{'email':to},
                                   'simplebody':{'text':body}})
        if result['error'] is not None:
            log.error('send_email(to=%r, subject=%r, body=%r) = %r',
                                to, subject, body, result['error'])
            raise YahooMailException(result['error']['message'])
        return True

    def make_login_string(self):
        with self.jar._cookies_lock:
            y = yBrowserCookie(self.jar._cookies['.yahoo.com']['/']['Y'])
            t = yBrowserCookie(self.jar._cookies['.yahoo.com']['/']['T'])
        return "http://msg.edit.yahoo.com/config/reset_cookies?&" + y + "&" + \
                t + '&.ver=2'

    @property
    def inbox_url(self):
        try:
            if self.web_login and hasattr(self, 'u'):
                link = UrlQuery('http://mrd.mail.yahoo.com/inbox')
                loginstr = self.make_login_string()
                log.debug('returning login URL for yahoo inbox')
                return str(loginstr + '&.done=' + quote(link, safe=''))
            else:
                return "http://mrd.mail.yahoo.com/inbox"
        except Exception, e:
            self.warning(e)
            return "http://mrd.mail.yahoo.com/inbox"

    def api(self, method, **params):
        foo = None
        from simplejson import loads, dumps
        recursed = params.pop('_recursed', 0)
        recurse = False
        try:
            foo = self.http_opener.open(self.json_endpoint, dumps(dict(method=method, params=[params]))).read()
            log.debug_s("got data from yahoo: %r", foo)
            if not foo.startswith('{'):
                import zlib
                try:
                    foo = foo.decode('z')
                except zlib.error:
                    raise YahooMailAuthRedirect
            foo = loads(foo)
        except YahooMailAuthException:
            raise
        except Exception, e:
            if hasattr(e, 'read') or isinstance(e, YahooMailAuthRedirect):
                if hasattr(e, 'read'):
                    foo = e.read()
                    log.debug("got error data from yahoo: %r for %r", foo, self.json_endpoint)
                if isinstance(e, YahooMailAuthRedirect) or getattr(e, 'code', None) in (404, 403):
                    self._json_endpoint = UrlQuery('http://'+ backup_server + '/ws/mail/v1.1/jsonrpc', appid='YahooMailRC')
                    recurse = True
                else:
                    try:
                        if not foo.startswith('{'):
                            foo = foo.decode('z')
                        foo = loads(foo)
                        code = foo['error']['code']
                        if code == SessionIdReissue:
                            recurse = True
                            self.json_endpoint = foo['error']['detail']['url']
                        elif code in (ExpiredCredentials, 'Client.MissingCredentials'):
                            recurse = True
                            self.init_jar()
                        else:
                            raise YahooMailException(foo['error']['message'])
                    except YahooMailException:
                        raise
                    except Exception:
                        raise e
            else:
                raise
        finally:
            if recurse and recursed < 5:
                params['_recursed'] = recursed + 1
                return self.api(method, **params)
        return foo

class FakeYmail(YahooMail):
    count = 1337
    def __init__(self, username, password):
        self.name = username
        self.password = password
        self.init_jar()

    def _decryptedpw(self):
        return self.password

    def __len__(self):
        return 1337

if __name__ == '__main__':
    import main
    main.setup_log_system()
    f = FakeYmail('username','passwordShouldNotBeInSourceCode')
    f.authenticate()
#    print f.hostname
#    print f._get_inbox_count()
    from pprint import pprint
    msgs = [m for m in f.get_yMsgs()[0]]
    print len(msgs)
    pprint(msgs)

class yBrowserCookie(str):
    def __new__(cls, cookie):
        return str.__new__(cls, '.' +  cookie.name.lower() + '=' + cookie.name + '='
                   + quote(cookie.value, safe='/=') +  ';+path=' +  cookie.path
                   + ';+domain=' + cookie.domain)


