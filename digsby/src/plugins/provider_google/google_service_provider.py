import util
import services.service_provider as SP

class GoogleServiceProvider(SP.EmailPasswordServiceProvider):
    def get_options(self, type):
        opts = super(GoogleServiceProvider, self).get_options(type)

        msp, msc = self.get_metainfo(type)

        if type == 'im':
            opts.update(

            )
        util.dictrecurse(dict)(opts)
        return opts

