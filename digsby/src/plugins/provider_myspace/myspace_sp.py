import logging
log = logging.getLogger("myspace_sp")
import services.service_provider as SP

class MyspaceServiceProvider(SP.UsernamePasswordServiceProvider, SP.OAuthServiceProvider):
    def update_info(self, info):

        super(MyspaceServiceProvider, self).update_info(info)

        if 'filters' in info:
            self.filters = info.get('filters')

    def add_account_social(self, acct):
        acct_options = acct.get_options()
        if 'filters' in acct_options:
            self.filters = acct_options.get('filters')
        super(MyspaceServiceProvider, self).add_account_social(acct)

    def get_options(self, ctype):
        options = super(MyspaceServiceProvider, self).get_options(ctype)
        if ctype == 'social':
            options.update({'informed_ach': True, 'post_ach_all': False})
            if hasattr(self, 'filters'):
                options['filters'] = self.filters

        return options
