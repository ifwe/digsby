import logging
log = logging.getLogger('imap_sp')

import services.service_provider as SP
import digsby_email.smtp_sp as SMTP_SP

class IMAPServiceProvider(SMTP_SP.SMTPServiceProvider):
    def update_info(self, info):
        self.require_ssl = info.get('require_ssl')

        if 'imapport' in info:
            try:
                info['imapport'] = int(info['imapport'])
            except ValueError:
                log.error("port is not an int, it is %r", info['imapport'])
                raise SP.AccountException()
            if 'imapport' in info:
                self.imapport = info['imapport']
        else:
            if not hasattr(self, 'imapport'):
                self.imapport = self.get_metainfo('email')[1].info.defaults['imapport_ssl' if self.require_ssl else 'imapport']

        if not info.get('imapserver'):
            log.debug("imapserver not provided")
            raise SP.AccountException()

        self.imapserver = info['imapserver']

        super(IMAPServiceProvider, self).update_info(info)

    def get_options(self, ctype = 'email'):
        options = super(IMAPServiceProvider, self).get_options(ctype)
        options['imapserver'] = self.imapserver
        options['imapport'] = self.imapport
        options['require_ssl'] = self.require_ssl

        return options
