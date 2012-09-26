'''

Monkeypatches to Python 2.5's logging module

- LogRecord: catch exceptions in getMessage method
- StreamHandler: missing streams result in logs going to stderr

'''

######################################
import logging
######################################

# XXX: unless py3k's logging module is drastically different,
# a lot of this can be done with subclasses instead of monkeypatches.

LOGGING_ENABLED = True

import sys
from threading import currentThread

_LogRecord = logging.LogRecord
class LogRecord(_LogRecord):

    def __init__(self, *a, **k):
        _LogRecord.__init__(self, *a, **k)
        self.threadCount = getattr(currentThread(), 'loopcount', 0)

    def getMessage(self):
        """
        Return the message for this LogRecord.

        Return the message for this LogRecord after merging any user-supplied
        arguments with the message.
        """
        msg = self.msg

        if type(msg) not in (unicode, str):
            try:
                msg = str(self.msg)
            except UnicodeError:
                msg = repr(self.msg)      #Defer encoding till later

        if self.args:
            try:
                msg = msg % self.args
            except Exception, e:
                try:
                    return 'Error in log message (%r:%r): msg=%r, args=%r' % (self.filename, self.lineno, msg, self.args)
                except Exception, e2:
                    return 'Error in log message (%r:%r)' % (self.filename, self.lineno)

        if isinstance(msg, unicode):
            msg = msg.encode('utf8')
        return msg

logging.LogRecord = LogRecord

class StreamHandler(logging.Handler):
    """
    A handler class which writes logging records, appropriately formatted,
    to a stream. Note that this class does not close the stream, as
    sys.stdout or sys.stderr may be used.
    """
    def __init__(self, strm=None):
        """
        Initialize the handler.

        If strm is not specified, sys.stderr is used.
        """
        logging.Handler.__init__(self)
        self._stream = strm
        self.formatter = None
        self.has_stream = True

    @property
    def stream(self):
        if self._stream is None and self.has_stream:
            return sys.stderr
        elif self.has_stream:
            return self._stream
    def flush(self):
        """
        Flushes the stream.
        """
        try:
            self.stream.flush()
        except:
            if self._stream is not None:
                self._stream = None
            else:
                self.has_stream = False

    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline
        [N.B. this may be removed depending on feedback]. If exception
        information is present, it is formatted using
        traceback.print_exception and appended to the stream.
        """
        if not self.has_stream:
            return
        try:
            msg = self.format(record)
            fs = "%s\n"
            try:
                self.stream.write(fs % msg)
            except UnicodeError:
                self.stream.write(fs % msg.encode("UTF-8"))
            except Exception:
                # Assume stream has died.
                self.has_stream = False
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

logging.StreamHandler = StreamHandler
logging.FileHandler.__bases__ = (StreamHandler,) + logging.FileHandler.__bases__[1:]

_logcolors = [
    (40, 'red bold'),
    (30, 'yellow bold'),
    (20, 'white'),
    (10, 'grey'),
]

def logcolor_for_level(level):
    for lvl, color in _logcolors:
        if level >= lvl:
            return color

    return color

class ColorStreamHandler(StreamHandler):
    pass

if getattr(getattr(sys, 'opts', None), 'console_color', False):
    try:
        from gui.native.win import console
    except ImportError:
        pass
    else:
        class ColorStreamHandler(StreamHandler):
            def emit(self, record):
                with console.color(logcolor_for_level(record.levelno)):
                    StreamHandler.emit(self, record)

def setup_sensitive_logs():
    '''
    Add methods like debug_s and info_s to log objects which, in the release build,
    do not write out to log files.
    '''
    from logging import Logger
    dev = getattr(sys, 'DEV', False)
    full_log = getattr(getattr(sys, 'opts', None), 'full_log', False)
    nolog = lambda self, *a, **k: None

    for log_type in ['critical', 'debug', 'error', 'exception', 'fatal',
                 'info', 'log', 'warn', 'warning']:
        def make_sensitive(name):
            if dev or full_log:
                def sensitive(self, *a, **k):
                    getattr(self, name)(*a, **k)
            else:
                sensitive = nolog
            return sensitive
        func = make_sensitive(log_type)
        setattr(Logger, log_type + '_s', func)

setup_sensitive_logs()


if not LOGGING_ENABLED:
    class NullRoot(object):
        stream = None

        setLevel = \
        addHandler = \
        info = \
        lambda *a: None

    class NullLogger(object):
        root = NullRoot()
        handlers = []

        debug = debug_s = \
        info = info_s = \
        warning = error = \
        critical = \
        lambda *a: None

    _null_logger = NullLogger()

    class NullManager(object):
        def getLogger(self, name):
            return _null_logger

    _null_manager = NullManager()

    NullLogger.manager = _null_manager

    logging.Logger = NullLogger
