import digsbysite
import AsyncoreThread
import logging
from tests.testapp import testapp


connection_settings = {
                       'jabber' : (('digsby@jabber.org', 'NO PASSWORD FOR YOU!', Null,),
                                   {'hide_os': False, 'block_unknowns': False,
                                    'autologin': False, 'verify_tls_peer': True,
                                    'do_tls': True, 'plain': True, 'sasl_md5': True,
                                    'do_ssl': False,
                                    'server': ('', 443), 'require_tls': True,
                                    'sasl_plain': True, 'use_md5': True}),
                       'gtalk' :  (('digsby03@gmail.com', 'not here either, haha', Null,),
                                   {'hide_os': False, 'block_unknowns': False,
                                    'autologin': False, 'verify_tls_peer': False,
                                    'do_tls': False, 'plain': True, 'sasl_md5': True,
                                    'do_ssl': True,
                                    'server': ('talk.google.com', 443), 'require_tls': False,
                                    'sasl_plain': True, 'use_md5': True}),
                      }


def fix_logging():
    logging.Logger.debug_s = logging.Logger.debug

def main():
    fix_logging()
    AsyncoreThread.start()
    import wx; a = testapp('../../..')

    a.toggle_crust()

    from jabber import protocol
    global jabber
    jargs, jkwargs = connection_settings['gtalk']
    jabber = protocol(*jargs, **jkwargs)
    jabber.Connect()

    a.MainLoop()
    try:
        jabber.Disconnect()
    except:
        pass

    AsyncoreThread.join(timeout = None)

if __name__ == '__main__':
    main()