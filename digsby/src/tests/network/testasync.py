import AsyncoreThread
import logging
from tests.testapp import testapp

def fix_logging():
    logging.Logger.debug_s = logging.Logger.debug

def main():
    fix_logging()
    AsyncoreThread.start()
    import wx; a = testapp('../../..')

    a.toggle_crust()

    from oscar import protocol
    oscar = protocol('digsby01', 'no passwords', user = object(), server = ('login.oscar.aol.com',5190))
    oscar.Connect()

    oscar.send_im('digsby04', u'hello world')

    a.MainLoop()
    #AsyncoreThread.join(timeout = None)

def main():
    import email
    msg = 'Server: NS8.0.54.6\r\nLocation: http://www.apple.com/favicon.ico\r\nContent Type: text/html\r\nCache Control: private\r\nConnection: close'
    x = email.message_from_string(msg)

if __name__ == '__main__':
    main()
