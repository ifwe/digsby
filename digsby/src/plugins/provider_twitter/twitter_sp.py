import logging
log = logging.getLogger("twitter_sp")
import services.service_provider as SP

class TwitterServiceProvider(SP.UsernamePasswordServiceProvider):

    def get_options(self, ctype):
        options = super(TwitterServiceProvider, self).get_options(ctype)
        options.update({'informed_ach': True, 'post_ach_all': False})
        if ctype == 'social':
            options['post_ach_all'] = getattr(self, 'post_ach_all', True)

        return options