#:25
import traceback
from common import profile
from util import unpack_pstr, pack_pstr
from common.emailaccount import EmailAccount, localprefs_key
from AccountManager import NETWORK_FLAG
from prefs import localprefprop

SMTP_UPGRADING = True

import smtplib, re

import logging
log = logging.getLogger('smtp')

#****************************************************************
#below is from
#http://trac.edgewall.org/browser/trunk/trac/notification.py
#****************************************************************
MAXHEADERLEN = 76

class SMTPsender(object):
    _ignore_domains = []
    addrfmt = r'[\w\d_\.\-\+=]+\@(?:(?:[\w\d\-])+\.)+(?:[\w\d]{2,4})'
    shortaddr_re = re.compile(r'%s$' % addrfmt)
    longaddr_re = re.compile(r'^\s*(.*)\s+<(%s)>\s*$' % addrfmt)

    def __init__(self, name, password, server, port=25, use_tls=False,
                 from_name=None, reply_to=None):
        self.user_name = name
        self.password = password

        self.smtp_server = server
        self.smtp_port = port

        #intelligent defaults, for now
        self.from_name = from_name if from_name is not None else name #self.user_name
        self.replyto_email = reply_to if reply_to is not None else name #self.user_name

        self._use_tls = use_tls

        self._init_pref_encoding()



    def format_header(self, key, name, email=None):
        from email.Header import Header #@UnresolvedImport
        maxlength = MAXHEADERLEN-(len(key)+2)
        # Do not sent ridiculous short headers
        if maxlength < 10:
            raise AssertionError, "Header length is too short"
        try:
            tmp = name.encode('utf-8') if isinstance(name, unicode) else name
            header = Header(tmp, 'utf-8', maxlinelen=maxlength)
        except UnicodeEncodeError:
            header = Header(name, self._charset, maxlinelen=maxlength)
        if not email:
            return header
        else:
            return '"%s" <%s>' % (header, email)

    def add_headers(self, msg, headers):
        for h in headers:
            msg[h] = self.encode_header(h, headers[h])

    def get_smtp_address(self, address):
        if not address:
            return None

        def is_email(address):
            pos = address.find('@')
            if pos == -1:
                return False
            if address[pos+1:].lower() in self._ignore_domains:
                return False
            return True

        if not is_email(address):
            if address == 'anonymous':
                return None
            if self.email_map.has_key(address):
                address = self.email_map[address]
            elif SMTPsender.nodomaddr_re.match(address):
                if self.config.getbool('notification', 'use_short_addr'):
                    return address
                domain = self.config.get('notification', 'smtp_default_domain')
                if domain:
                    address = "%s@%s" % (address, domain)
                else:
                    self.env.log.info("Email address w/o domain: %s" % address)
                    return None

        mo = self.shortaddr_re.search(address)
        if mo:
            return mo.group(0)
        mo = self.longaddr_re.search(address)
        if mo:
            return mo.group(2)
        self.env.log.info("Invalid email address: %s" % address)
        return None

    def _init_pref_encoding(self):
        from email.Charset import Charset, QP, BASE64 #@UnresolvedImport
        self._charset = Charset()
        self._charset.input_charset = 'utf-8'
        pref = 'base64' #self.env.config.get('notification', 'mime_encoding').lower()
        if pref == 'base64':
            self._charset.header_encoding = BASE64
            self._charset.body_encoding = BASE64
            self._charset.output_charset = 'utf-8'
            self._charset.input_codec = 'utf-8'
            self._charset.output_codec = 'utf-8'
        elif pref in ['qp', 'quoted-printable']:
            self._charset.header_encoding = QP
            self._charset.body_encoding = QP
            self._charset.output_charset = 'utf-8'
            self._charset.input_codec = 'utf-8'
            self._charset.output_codec = 'utf-8'
        elif pref == 'none':
            self._charset.header_encoding = None
            self._charset.body_encoding = None
            self._charset.input_codec = None
            self._charset.output_charset = 'ascii'
        else:
            raise AssertionError, 'Invalid email encoding setting: %s' % pref

    def encode_header(self, key, value):
        if isinstance(value, tuple):
            return self.format_header(key, value[0], value[1])
        if isinstance(value, list):
            items = []
            for v in value:
                items.append(self.encode_header(v))
            return ',\n\t'.join(items)
        mo = self.longaddr_re.match(value)
        if mo:
            return self.format_header(key, mo.group(1), mo.group(2))
        return self.format_header(key, value)

    def begin_send(self):
        self.server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        # self.server.set_debuglevel(True)
        if self._use_tls:
            self.server.ehlo()
            if not self.server.esmtp_features.has_key('starttls'):
                raise AssertionError, "TLS enabled but server does not support TLS"
            self.server.starttls()
            self.server.ehlo()
        if self.user_name:
            try:
                self.server.login(self.user_name, self.password)
            except:
                pass

    def send_email(self, to='', subject='', body='', cc='', bcc=''):
        self.begin_send()
        self.send([to], [], subject, body)
        try:
            self.finish_send()
        except:
            pass

    def send(self, torcpts, ccrcpts, subject, body, mime_headers={}):
        from email.MIMEText import MIMEText #@UnresolvedImport
#        from email.Utils import formatdate #@UnresolvedImport
#        public_cc = self.config.getbool('notification', 'use_public_cc')
        headers = {}
        headers['Subject'] = subject
        headers['From'] = (self.from_name, self.from_name)

        def build_addresses(rcpts):
            """Format and remove invalid addresses"""
            return filter(lambda x: x, \
                          [self.get_smtp_address(addr) for addr in rcpts])

        def remove_dup(rcpts, all):
            """Remove duplicates"""
            tmp = []
            for rcpt in rcpts:
                if not rcpt in all:
                    tmp.append(rcpt)
                    all.append(rcpt)
            return (tmp, all)

        toaddrs = build_addresses(torcpts)
#        ccaddrs = build_addresses(ccrcpts)
#        bccaddrs = build_addresses(bccrcpts)
#        accaddrs = build_addresses(accparam.replace(',', ' ').split()) or []
#        bccaddrs = build_addresses(bccparam.replace(',', ' ').split()) or []

        recipients = []
        (toaddrs, recipients) = remove_dup(toaddrs, recipients)
#        (ccaddrs, recipients) = remove_dup(ccaddrs, recipients)
#        (bccaddrs, recipients) = remove_dup(bccaddrs, recipients)

        # if there is not valid recipient, leave immediately
        if len(recipients) < 1:
#            self.env.log.info('no recipient for a ticket notification')
            return

#        pcc = accaddrs
#        if public_cc:
#            pcc += ccaddrs
#            if toaddrs:
        headers['To'] = ', '.join(toaddrs)
#        if pcc:
#            headers['Cc'] = ', '.join(pcc)
#        headers['Date'] = formatdate()
        # sanity check
#        if not self._charset.body_encoding:
#            try:
#                dummy = body.encode('ascii')
#            except UnicodeDecodeError:
#                raise AssertionError, "Ticket contains non-Ascii chars. " \
#                                 "Please change encoding setting"
        msg = MIMEText(body.encode('utf-8'), 'plain')
        # Message class computes the wrong type from MIMEText constructor,
        # which does not take a Charset object as initializer. Reset the
        # encoding type to force a new, valid evaluation
        del msg['Content-Transfer-Encoding']
        msg.set_charset(self._charset)
        self.add_headers(msg, headers);
        self.add_headers(msg, mime_headers);
#        self.env.log.info("Sending SMTP notification to %s:%d to %s"
#                           % (self.smtp_server, self.smtp_port, recipients))
        msgtext = msg.as_string()
        # Ensure the message complies with RFC2822: use CRLF line endings
        recrlf = re.compile("\r?\n")
        msgtext = "\r\n".join(recrlf.split(msgtext))
        self.server.sendmail(msg['From'], recipients, msgtext)

    def finish_send(self):
        if self._use_tls:
            # avoid false failure detection when the server closes
            # the SMTP connection with TLS enabled
            import ssl
            try:
                self.server.quit()
            except ssl.SSLError:
                pass
        else:
            self.server.quit()


###back to new code
from common.emailaccount import EmailAccount
from util import threaded
class SMTPEmailAccount(EmailAccount):
    DEFAULT_SMTP_REQUIRE_SSL = False
    DEFAULT_SMTP_PORT        = 25

    def __init__(self, **options):
        d = self.default
        self.smtp_server       = options.get('smtp_server', d('smtp_server'))
        self.smtp_require_ssl  = options.get('smtp_require_ssl', d('smtp_require_ssl'))
        self.smtp_port         = options.get('smtp_port', d('smtp_port'))
        self.smtp_username     = options.get('smtp_username', d('smtp_username'))
        self._email_address    = options.get('email_address', d('email_address'))
        self._encrypted_smtppw = profile.crypt_pw(options.get('smtp_password', d('smtp_password')))
        self._encrypted_pw     = options.pop('password')
        EmailAccount.__init__(self, password=self.password, **options)

    def get_email_address(self):
        return self._email_address
    def set_email_address(self, val):
        self._email_address = val

    @property
    def from_name(self):
        return self.email_address

    @classmethod
    def _unglue_pw(cls, password):
        passwordstr = profile.plain_pw(password).encode('utf-8')
        if passwordstr:
            password, r = unpack_pstr(passwordstr)
            try:
                smtppassword, r = unpack_pstr(r)
            except Exception:
                smtppassword, r = '', ''
        else:
            raise ValueError("Can't decrypt %r", password)

        return profile.crypt_pw(password.decode('utf-8')), profile.crypt_pw(smtppassword.decode('utf-8'))

    def _set_password(self, password):
        try:
            self._encrypted_pw, self._encrypted_smtppw = self._unglue_pw(password)
        except Exception, e:
            traceback.print_exc()
            assert SMTP_UPGRADING
            self._encrypted_pw = password


    @classmethod
    def _glue_pw(cls, encrypted_pw, encrypted_smtppw):
        password = pack_pstr(profile.plain_pw(encrypted_pw).encode('utf-8')).decode('utf-8')
        smtppw = pack_pstr(profile.plain_pw(encrypted_smtppw).encode('utf-8')).decode('utf-8')
        return profile.crypt_pw(password + smtppw)

    def _get_password(self):
        return self._glue_pw(self._encrypted_pw, self._encrypted_smtppw)

    password = property(_get_password, _set_password)

    def _decryptedpw(self):
        return profile.plain_pw(self._encrypted_pw)

    def _decrypted_smtppw(self):
        return profile.plain_pw(self._encrypted_smtppw)

    smtp_password = property(_decrypted_smtppw)

    def update_info(self, **info):
        if not self.isflagged(NETWORK_FLAG):
            if 'smtp_password' in info:
                self._encrypted_smtppw = profile.crypt_pw(info.pop('smtp_password'))

                if 'password' in info:
                    self._encrypted_pw = info['password']

            if '_encrypted_pw' in info and '_encrypted_smtppw' in info:
                self._encrypted_pw = info.pop('_encrypted_pw')
                self._encrypted_smtppw = info.pop('_encrypted_smtppw')

            info['password'] = self._glue_pw(self._encrypted_pw, self._encrypted_smtppw)
        else:
            self.password = info.pop('password')

        log.info("smtp update_info: %r", info)
        EmailAccount.update_info(self, **info)

    def _get_options(self):
        opts = EmailAccount._get_options(self)
        opts.update(dict((a, getattr(self, a)) for a in
            'smtp_server smtp_port smtp_require_ssl smtp_username email_address'.split()))
        return opts

    @classmethod
    def from_net(cls, info):
        password = info.password #IS BOTH, NEEDS TO BE ONE
        try:
            encrypted_pw, encrypted_smtppw = cls._unglue_pw(password)
        except Exception, e:
            traceback.print_exc()
            assert SMTP_UPGRADING
            encrypted_pw = password
            encrypted_smtppw = u''
        info.password = encrypted_pw
        smtppw = profile.plain_pw(encrypted_smtppw)
        return EmailAccount.from_net(info, smtp_password=smtppw)

    @threaded
    def send_email(self, to='', subject='', body='', cc='', bcc=''):
        un  = self.smtp_username or self.username
        f   = self.from_name
        password   = self._decrypted_smtppw() or (self._decryptedpw() if not self.smtp_username else '')
        srv = self.smtp_server
        if srv in ("smtp.aol.com", "smtp.aim.com"):
            if un.endswith('aol.com') or un.endswith('aim.com'):
                f = un
            else:
                f = un + u'@aol.com'
        s = SMTPsender(un, password, srv, from_name=f, use_tls=self.smtp_require_ssl)
        s.send_email(to=to, subject=subject, body=body, cc=cc, bcc=bcc)

    # Override the "mailclient" property here so that the default
    # is "sysdefault" instead of None
    mailclient = localprefprop(localprefs_key('mailclient'), 'sysdefault')
