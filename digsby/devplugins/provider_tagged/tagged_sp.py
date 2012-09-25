import logging
log = logging.getLogger('tagged_sp')
import services.service_provider as SP

class TaggedServiceProvider(SP.EmailPasswordServiceProvider):
    def update_info(self, kwds):
        super(TaggedServiceProvider, self).update_info(kwds)

        if 'filters' in kwds:
            self.filters = kwds.get('filters')

    def get_options(self, ctype = 'social'):
        options = super(TaggedServiceProvider, self).get_options(ctype)

        if hasattr(self, 'filters'):
                options['filters'] = self.filters

        return options