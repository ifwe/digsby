from logging import getLogger
from .YahooSocket import YahooSocket
import common
log = getLogger('YahooP2PSocket')

class YahooP2PSocket(YahooSocket):
    def __init__(self, yahoo, server, session_id):
        YahooSocket.__init__(self, yahoo, server)
        self.session_id = session_id

    def handle_connect(self):
        log.info("Yahoo Socket connected to %s:%d", *self.server)
        self.yahoo.on_connect()

    def handle_close(self):
        log.critical('handle_close')
        self.yahoo.on_close()
        self.close()
        self.yahoo = None

    def handle_error(self, *a, **k):
        import traceback;traceback.print_exc()
        log.error('handle_error')
        self.yahoo.on_close()
        self.yahoo = None
        common.socket.handle_error(self, *a, **k)

    def handle_expt(self):
        log.error("handle_expt: out-of-band data")
        self.yahoo.on_close()
        self.close()
        self.yahoo = None
