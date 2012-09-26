import logging
log = logging.getLogger('pop_sp')

import services.service_provider as SP
import digsby_email.smtp_sp as SMTP_SP

class POPServiceProvider(SMTP_SP.SMTPServiceProvider):
    def update_info(self, info):
        self.require_ssl = info.get('require_ssl')

        if 'popport' in info:
            try:
                info['popport'] = int(info['popport'])
            except ValueError:
                log.error("port is not an int, it is %r", info['popport'])
                raise SP.AccountException()
            if 'popport' in info:
                self.popport = info['popport']
        else:
            if not hasattr(self, 'popport'):
                self.popport = self.get_metainfo('email')[1].info.defaults['popport_ssl' if self.require_ssl else 'popport']

        if not info.get('popserver'):
            log.debug("popserver not provided")
            raise SP.AccountException()

        self.popserver = info['popserver']

        super(POPServiceProvider, self).update_info(info)

    def get_options(self, ctype = 'email'):
        options = super(POPServiceProvider, self).get_options(ctype)
        options['popserver'] = self.popserver
        options['popport'] = self.popport
        options['require_ssl'] = self.require_ssl

        return options
