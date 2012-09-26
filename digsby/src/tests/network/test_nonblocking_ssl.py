import socket
import ssl
import select
from time import clock

from errno import EALREADY, EINPROGRESS, EWOULDBLOCK, EISCONN

def log(msg):
    print msg, clock()

def main():
    s = socket.socket()
    s.setblocking(0.0)

    while True:
        log('connect')
        err = s.connect_ex(('twitter.com', 443))
        if err in (EINPROGRESS, EALREADY, EWOULDBLOCK):
            continue
        if err in (0, EISCONN):
            break

    s = ssl.wrap_socket(s, do_handshake_on_connect=False)
    i = 0
    while True:
        try:
            log('do_handshake')
            s.do_handshake()
        except ssl.SSLError, err:
            if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                log('want read')
                select.select([s], [], [])
            elif err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                log('want write')
                select.select([], [s], [])
            else:
                raise
        except Exception:
            i +=1
            print clock(), i
        else:
            break

    log('finished')


if __name__ == '__main__':
    main()
