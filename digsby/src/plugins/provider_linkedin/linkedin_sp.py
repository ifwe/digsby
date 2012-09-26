import services.service_provider as SP

class LinkedInServiceProvider(SP.OAuthServiceProvider):

    def get_options(self, ctype = 'social'):
        options = super(LinkedInServiceProvider, self).get_options(ctype)
        options.update({'informed_ach': True, 'post_ach_all': False})
        return options
