import jabber, pyxmpp.sasl

from .fbsasl import XFacebookPlatformClientAuthenticator
pyxmpp.sasl.all_mechanisms_dict['X-FACEBOOK-PLATFORM']  = (XFacebookPlatformClientAuthenticator, None)
pyxmpp.sasl.safe_mechanisms_dict['X-FACEBOOK-PLATFORM'] = (XFacebookPlatformClientAuthenticator, None)
jabber.JabberProtocol.methods_dict['fb_login'] = 'sasl:X-FACEBOOK-PLATFORM'

