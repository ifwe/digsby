import logging
log = logging.getLogger("aol_sp")
import hooks
import util.net as net

import mail.smtp as smtp
import services.service_provider as SP

class AOLServiceProvider(SP.EmailPasswordServiceProvider):
    def update_info(self, kwds):
        super(AOLServiceProvider, self).update_info(kwds)
        self.updatefreq = kwds.get('updatefreq', 300)

    def get_options(self, type):
        options = super(AOLServiceProvider, self).get_options(type)

        if type == 'email':
            email_address = options.get('email_address', None)
            if email_address is not None:
                options['username'] = email_address

            username = options.get('username', options.get('name'))
            if username is not None:
                username = ''.join(username.split()).lower()
                username = str(net.EmailAddress(username, 'aol.com'))
                options['name'] = options['username'] = username

        elif type == 'im':
            email_address = options.get('username', options.get('name'))

            pinfo = self.get_metainfo().info.provider_info
            try:
                email_addr_obj = net.EmailAddress(email_address, pinfo['default_domain'])
                username, domain = email_addr_obj.name, email_addr_obj.domain
            except ValueError:
                username, domain = email_address, None

            domains = pinfo['equivalent_domains']
            domains.append(pinfo['default_domain'])

            if domain is None or domain in domains:
                options['username'] = options['name'] = username
            else:
                options['username'] = options['name'] = email_address

        options['updatefreq'] = self.updatefreq
        log.info_s("got options for type=%r: %r", type, options)
        return options

    def add_account_email(self, acct):
        retval = super(AOLServiceProvider, self).add_account_email(acct = acct)
        log.info("Changing %r's username from %r to %r", acct, acct.username, self.email_address)
        acct.name = self.email_address

        try:
            pw, smtppw = smtp.SMTPEmailAccount._unglue_pw(acct.password)
        except ValueError:
            pass
        else:
            self.password = pw

        return retval

    def add_account_im(self, acct):
        retval = super(AOLServiceProvider, self).add_account_im(acct = acct)
        options = self.get_options('im')
        log.info("Changing %r's username from %r to %r", acct, acct.username, options['username'])
        acct.name = options['username']

        return retval

def validate_icq(info, MSP, is_new):
    valid = hooks.first('digsby.services.validate', info, MSP, is_new,
                        impl = "digsby_service_editor", raise_hook_exceptions = True)

    password = info.get('_real_password_')
    if password is not None:
        if len(password) > 8:
            raise SP.AccountException(_("Password should be 8 characters or less."), fatal = False)
