import logging
log = logging.getLogger("smtp_sp")

import cPickle
import traceback
import services.service_provider as SP
import hooks
import common
import common.protocolmeta as protocolmeta
import prefs

import util

import mail.smtp as smtp

def localprefs_key(name):
    def get(acct):
        return '/'.join([acct.provider_id, acct.name, name]).lower()

    return get

class SMTPServiceProvider(SP.UsernamePasswordServiceProvider):
    def update_info(self, kwds):
        if '_encrypted_smtppw' in kwds and '_encrypted_pw' in kwds:
            kwds['password'] = self._encrypted_pw = e_pw = kwds['_encrypted_pw']
            self._encrypted_smtppw = e_spw = kwds['_encrypted_smtppw']
            kwds['smtp_password'] = common.profile.plain_pw(e_spw)

        elif 'password' in kwds:
            try:
                self._encrypted_pw, self._encrypted_smtppw = smtp.SMTPEmailAccount._unglue_pw(kwds.get('password', ''))
                kwds['smtp_password'] = common.profile.plain_pw(self._encrypted_smtppw)
                kwds['password'] = self._encrypted_pw
            except ValueError:
                if 'smtp_password' in kwds:
                    self._encrypted_smtppw = common.profile.crypt_pw(kwds['smtp_password'])
                else:
                    self._encrypted_smtppw = ''
                self._encrypted_pw = kwds['password']

        self.smtp_require_ssl = kwds.get('smtp_require_ssl')

        if 'email_address' in kwds:
            self.email_address = kwds.get('email_address', self.name)
        if 'smtp_username' in kwds:
            self.smtp_username = kwds.get('smtp_username', self.name)
        if kwds.get('smtp_server'):
            self.smtp_server = kwds.get('smtp_server', '')
        else:
            log.debug("smtp_server not provided")
            raise SP.AccountException()
        if 'smtp_port' in kwds:
            try:
                kwds['smtp_port'] = int(kwds['smtp_port'])

            except ValueError:
                log.error("port is not an int, it is %r", kwds['smtp_port'])
                raise SP.AccountException()
        else:
            kwds['smtp_port'] = self.get_metainfo('email')[1].info.defaults['smtp_port_ssl' if self.smtp_require_ssl else 'smtp_port']

        self.smtp_port = kwds.get('smtp_port')

        super(SMTPServiceProvider, self).update_info(kwds)

        mailclient = kwds.get('mailclient', None)
        if mailclient is None and not hasattr(self, 'mailclient'):
            self.mailclient = 'sysdefault'
        custom_inbox_url = kwds.get('custom_inbox_url', None)
        if custom_inbox_url is None and not hasattr(self, 'custom_inbox_url'):
            self.custom_inbox_url = u''
        custom_compose_url = kwds.get('custom_compose_url', None)
        if custom_compose_url is None and not hasattr(self, 'custom_compose_url'):
            self.custom_compose_url = u''

    def _decryptedpw(self):
        return common.profile.plain_pw(self._encrypted_pw)

    def _decrypted_smtppw(self):
        return common.profile.plain_pw(self._encrypted_smtppw)

    mailclient         = prefs.localprefprop(localprefs_key('mailclient'), None)
    custom_inbox_url   = prefs.localprefprop(localprefs_key('custom_inbox_url'), None)
    custom_compose_url = prefs.localprefprop(localprefs_key('custom_compose_url'), None)

    def get_options(self, ctype = "email"):
        options = super(SMTPServiceProvider, self).get_options(ctype)
        options['email_address'] = self.email_address
        options['smtp_username'] = getattr(self, 'smtp_username', self.name)
        options['smtp_server'] = self.smtp_server
        options['smtp_port'] = self.smtp_port
        options['smtp_require_ssl'] = self.smtp_require_ssl
        options['mailclient'] = self.mailclient
        options['custom_inbox_url'] = self.custom_inbox_url
        options['custom_compose_url'] = self.custom_compose_url

        return options

    @property
    def display_name(self):
        return self.email_address
