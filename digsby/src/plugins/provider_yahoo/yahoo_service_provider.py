import util.net as net

import hooks
import services.service_provider as SP

class YahooServiceProvider(SP.EmailPasswordServiceProvider):
    def update_info(self, kwds):
        super(YahooServiceProvider, self).update_info(kwds)
        self.updatefreq = kwds.get('updatefreq', 300)

    def get_options(self, ctype):
        options = super(YahooServiceProvider, self).get_options(ctype)
        if ctype == 'email':
            options['updatefreq'] = self.updatefreq
        return options
