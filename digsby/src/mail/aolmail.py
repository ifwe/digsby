from util import UrlQuery, threaded
#from util.ie import *
import common
import mail
import mail.smtp
from mail.imap import IMAPMail

from common import pref

import time
import logging
log = logging.getLogger('aolmail')

class AOLMail(IMAPMail):
    protocol = 'aolmail'

    default_domain = 'aol.com'

    AIM_SERVER = "imap.aol.com"

    def __init__(self, *a, **kws):
        self._name = None
        log.info('aolmail: %r', kws)

        # All AOLMAil accounts use the same server.
        kws.update(dict( imapserver = self.AIM_SERVER))

        IMAPMail.__init__(self, *a, **kws)
#        self.ie = None

    get_email_address = common.emailaccount.EmailAccount.get_email_address # We don't want the superclass function because it doesn't do default domains.

    def _get_name(self):
        return self._name

    def _set_name(self, name):
        self._name = name

    name = property(_get_name, _set_name)

    def _get_mailclient(self):
        return pref('privacy.www_auto_signin', False)

    def _not_supported(self, val):
        '''
        Not supported.
        '''
        return

    mailclient = property(_get_mailclient, _not_supported)

#    def update(self):
#        import wx
#        wx.CallAfter(self.getie)
#        IMAPMail.update(self)


    can_has_preview = True

    def reportSpam(self, msg):
        IMAPMail.reportSpam(self, msg)
        self.move(msg, "Spam")

    def delete(self, msg):
        IMAPMail.delete(self, msg)
        self.move(msg, "Trash")

    def archive(self, msg):
        IMAPMail.archive(self, msg)
        self.move(msg, "Saved Mail")

    def open(self, msg):
#        # this will open a new IE window so we don't need to show ours.
#        self.getie().open_msg(msg.id)
#        self.ie = None

        OpenAOLMail(self.name, self._decryptedpw(), msg.id)

    def urlForEmail(self, msg):
        assert not self.mailclient
        return UrlQuery('http://webmail.aol.com/Lite/MsgRead.aspx?', dict(folder='Inbox',uid='1.' +msg.id, seq='1', start='0'))

    def compose(self, to='', subject='', body='', cc='', bcc='', **k):
        if self.mailclient:
            print 'edit compose', to, subject, body, cc, bcc, k
            #self.ie_compose(*a, **k)
            body = body.replace('\n', '<br>')
            ComposeAOLMail(self.name, self._decryptedpw(), to=to, subject=subject, body=body, **k)
            print 'edit compose', 'done'
        else:
            print 'return url'
            return self._compose(to, subject, body, cc, bcc, **k)

    def _compose(self, to='', subject='', body='', cc='', bcc='', **k):
        ##TODO: match kwargs and return url
        return UrlQuery("http://webmail.aol.com/25045/aim/en-us/Mail/compose-message.aspx",
                        to=to, subject=subject, body=body, cc=cc, bcc=bcc, **k)

    #@threaded
#    def ie_compose(self, *a, **k):
#        #self.getie().compose(*a, **k)
#        self.ie = None

    @property
    def inbox_url(self):
        return "http://mail.aol.com"

    def goto_inbox(self):
        if self.mailclient:
            SelectAOLMail(self.name, self._decryptedpw())
#            self.getie().select_mail()
#            self.getie().show(True)
#            self.ie = None

    def start_client_email(self, email=None):
        assert self.mailclient
        if email is not None:
            self.open(email)
        else:
            self.goto_inbox()

#        self.ie = None

#    def getie(self, f=lambda *a, **k:None):
#        if not self.ie:
#            self.ie = None#IEAOLMail(self.name, self._decryptedpw(), f)
#        else:
#            f()
#        return self.ie
#
#    def ie_lost(self, *a,**k):
#        print 'lost ie'
#        self.ie = None

    def _get_options(self):
        opts = IMAPMail._get_options(self)
        opts.pop('email_address', None)
        opts.pop('mailclient', None)
        return opts

#class IEAOLMail(object):
#    signout_url = 'http://my.screenname.aol.com/_cqr/logout/mcLogout.psp?sitedomain=startpage.aol.com&siteState=OrigUrl%3Dhttp%253A%252F%252Fwww.aol.com%252F'
#    def __init__(self, un, pw, ready=lambda:None):
#        self.un, self.pw = un, pw
#        self.ready = ready
#        self.init()
#        self.show()
#
#    def init(self):
#        self.ie = GetIE()
#        log.info('%s: Created IE' % self)
#        self.ie._Bind('OnDocumentComplete', self.on_logout)
#        self.ie.Navigate2(self.signout_url)
#
#        self.show = self.ie.show
#        self.hide = self.ie.hide
#
#    def on_logout(self, evt=None):
#        log.info('%s: Logged out' % self)
#        self.ie._UnBind('OnDocumentComplete', self.on_logout)
#        self.ie._Bind('OnDocumentComplete', self.on_loginpageload)
#        self.ie.Navigate2("http://mail.aol.com")
#
#    @property
#    def select_mail(self):
#        return JavaScript('SuiteSvc.SelectTab("mail");', self.ie)
#
#    @property
#    def open_msg(self):
#        return JavaScript('frames["MailFrame"].document.getElementById("message1.%s")'
#                          '.children[3].children[0].onclick();', self.ie);
#
#    def on_loginpageload(self, evt):
#        assert not self.logged_in
#        try:
#            doc = self.ie.Document
#            doc.forms(1).loginId.value = self.un
#            doc.forms(1).password.value = self.pw
#        except:
#            return
#        else:
#            log.info('%s: Login page loaded, submitting' % self)
#            self.ie._UnBind('OnDocumentComplete', self.on_loginpageload)
#            self.ie._Bind('OnDocumentComplete', self.on_formsubmit)
#            doc.forms(1).submit()
#
#    def on_formsubmit(self, evt=None):
#        if self.logged_in:
#            log.info('%s: Logged in' % self)
#            self.ie._UnBind('OnDocumentComplete', self.on_formsubmit)
#            self.ie._Bind("OnDocumentComplete", self.on_mailboxload)
#
#    def on_mailboxload(self, evt=None):
#        try:
#            #if self.ie.Document.parentWindow.SuiteSvc.IsLoaded
#            self.select_mail()
#        except:
#            return
#        else:
#            self.ie._UnBind('OnDocumentComplete', self.on_mailboxload)
#
#        log.info('%s: Mailbox loaded. Calling ready (%r)' % (self, self.ready))
#        self.ready()
#
#    @property
#    def logged_in(self):
#        try:
#            self.open_msg.Config
#        except:
#            return False
#        else:
#            return True
#
#    def compose(self, to='', cc='', subject='', body=''):
#        print 'compose', [to,cc,subject,body]
#        try:
#            cfg = self.open_msg.Config
#            baseurl = cfg.BaseMailPagesURL
#        except:
#            baseurl = 'http://webmail.aol.com/27618/aim/en-us/Mail/'
#
#        kw = dict()
#        for name in 'to subject body cc'.split():
#            if vars()[name]:
#                kw[name] = vars()[name]
#
#        url = UrlQuery(baseurl + 'compose-message.aspx', **kw)
#        self.ie.Navigate2(url)
#        self.ie.show(True)
#
#    def __bool__(self):
#        return bool(self.ie)
#
#    def __repr__(self):
#        return '<%s>' % type(self).__name__

def OpenAOLMail(un,password,msgid):
    from oscar import login2
    login2.go_to_msg(un.encode('utf-8'), password.encode('utf-8'), msgid)


#def OpenAOLMail(un,pw,msgid):
#    ie = IEAOLMail(un, pw)
#
#    def f():
#
#        #HAX: CallLater to wait for javascript to load :-(
#        import wx
#
#        def f2():
#            ie.open_msg(msgid)
#            wx.CallLater(1000,ie.ie.Quit)
#
#        wx.CallLater(2000,f2)
#
#    ie.ready = f

def SelectAOLMail(un,password):
    from oscar import login2
    print "opening", un
    login2.go_to_mail(un.encode('utf-8'), password.encode('utf-8'))

#def SelectAOLMail(un,pw):
#    ie = IEAOLMail(un, pw)
#    def f():
#        ie.select_mail()
#        ie.show()
#    ie.ready = f

def ComposeAOLMail(un,password,**k):
    from oscar import login2
    login2.go_to_compose(un.encode('utf-8'), password.encode('utf-8'),**k)

#def ComposeAOLMail(un,pw,*a,**k):
#    ie = IEAOLMail(un, pw)
#    def f():
#        ie.compose(*a,**k)
#        ie.show()
#    ie.ready = f


if __name__ == '__main__':
    from wx.py.PyCrust import main
    main()

