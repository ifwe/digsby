from .YahooSocket import YahooSocket
from .yahoologinbase import YahooLoginBase
from logging import getLogger
log = getLogger('YahooLoginSocket')

class YahooLoginSocket(YahooLoginBase, YahooSocket):
    def __init__(self, yahoo, server):
        YahooSocket.__init__(self, yahoo, server)
        YahooLoginBase.__init__(self, yahoo)

        log.info( "connecting to %s with user: %s", self.server,
                                                    self.yahoo.username)

        def onfail(exc = None):
            self.yahoo.set_disconnected(self.yahoo.Reasons.CONN_FAIL)
            self.close()

        self.connect(self.server, error = onfail)

        if not self.readable():
            onfail()

    def logon_err(self):
        y = self.yahoo
        y.set_disconnected(y.Reasons.CONN_FAIL)
        self.close()

    def handle_connect(self):
        log.info("Yahoo Socket connected to %s:%d", *self.server)

        self.async_proc(self.logon())

    def handle_close(self):
        log.critical('handle_close')
        if self.yahoo.offline_reason == self.yahoo.Reasons.NONE:
            rsn = self.yahoo.Reasons.CONN_LOST
        else:
            rsn = self.yahoo.offline_reason
        self.yahoo.set_disconnected(rsn)
        self.close()
        self.yahoo = None

    def handle_error(self, *a, **k):
        import traceback;traceback.print_exc()
        log.error('handle_error')
        if self.yahoo:
            self.yahoo.set_disconnected(self.yahoo.Reasons.CONN_LOST)
        super(YahooSocket, self).handle_error(*a, **k) #skip over YahooSocket.handle_error, it raises NotImplementedError

    def handle_expt(self):
        log.error("handle_expt: out-of-band data")
        self.yahoo.set_disconnected(self.yahoo.Reasons.CONN_LOST)
        self.close()
        self.yahoo = None
