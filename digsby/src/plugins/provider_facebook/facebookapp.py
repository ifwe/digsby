from facebook import facebookapi
import common.oauth_util as oauth_util

class FacebookAppClient(oauth_util.OAuthClientBase):
    urls = {
        'request_token' : 'https://www.facebook.com/dialog/oauth',
        'access_token'  : 'http://api.myspace.com/access_token',
        'authorization' : 'http://api.myspace.com/authorize',
    }

    @property
    def api(self):
        if getattr(self, '_api', None) is None:
            self._api = facebookapi.FacebookAPI(self)
        return self._api

class DigsbyAppConsumer(oauth_util.OAuthConsumerBase):
    KEY = ''
    SECRET = ''

class DigsbyWidgetAppConsumer(oauth_util.OAuthConsumerBase):
    KEY = ''
    SECRET = ''

class DigsbyAchievementsAppConsumer(oauth_util.OAuthConsumerBase):
    KEY = ''
    SECRET = ''

class DigsbyApp(FacebookAppClient):
    name = 'digsby'
    ConsumerFactory = DigsbyAppConsumer

    required_permissions = ['read_stream', 'user_events', 'xmpp_login', 'manage_notifications']
    desired_permissions = required_permissions + ['publish_stream']

class DigsbyWidgetApp(FacebookAppClient):
    name = 'digsby_widget'
    ConsumerFactory = DigsbyWidgetAppConsumer

class DigsbyAchievementsApp(FacebookAppClient):
    name = 'digsby_ach'
    ConsumerFactory = DigsbyAchievementsAppConsumer

    required_permissions = ['publish_stream']
    desired_permissions = required_permissions


