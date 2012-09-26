import logging, gzip
from time import strftime
from traceback import format_exception

COMMA = '#comma#'
LINE  = '#line#'

def csv_escape(s):
    return s.replace(',', COMMA).replace('\n', LINE)

CSV_HEADERS = ("Time, Log Level, Level Name, Log Name, Message,"
               "Pathname, Filename, Module, Function Name, "
               "Line No., Timestamp, Thread Count, Thread Name, "
               "Thread No., Process No.\n")

class CSVFormatter(logging.Formatter):
    _fmt = "%(asctime)s,%(levelno)s,%(levelname)s,%(name)s,%(message)s,%(pathname)s,%(filename)s,%(module)s," \
           "%(funcName)s,%(lineno)d,%(created)f,%(threadCount)d,%(threadName)s,%(thread)d,%(process)d"

    def __init__(self, fmt=None, datefmt=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        self._fmt = CSVFormatter._fmt
        self._asctime = self._fmt.find('%(asctime)') >= 0

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = strftime(datefmt, ct)
        else:
            t = strftime("%Y-%m-%d %H:%M:%S", ct)
            s = "%s.%03d" % (t, record.msecs)
        return s

    def formatException(self, ei):
        s = '\n'.join(format_exception(*ei))
        if s.endswith('\n'):
            s = s[:-1]

        return s

    def format(self, record):
        record.message = ''.join(('"', record.getMessage().replace('"', '""'), '"'))
        if self._asctime:
            record.asctime = self.formatTime(record, self.datefmt)

        s = self._fmt % record.__dict__

        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = csv_escape(self.formatException(record.exc_info))

        if record.exc_text:
            if not s.endswith(","):
                s = s + ","
            s = ''.join((s, record.exc_text))
        return s


class gzipFileHandler(logging.StreamHandler):
    def __init__(self, t, filename=None):
        if not filename:
            filename = 'digsby-' + t + '.log.csv.gz'
        f = open('logs/digsby-' + t + '.log.csv.gz', 'wb')
        self.gzfileobj = gzip.GzipFile(filename, fileobj=f)
        self.gzfileobj.write("Time, Log Level, Level Name, Log Name, Message,"
                             "Pathname, Filename, Module, Function Name, "
                             "Line No., Timestamp, Thread No., "
                             "Thread Name, Process No.\n")
        logging.StreamHandler.__init__(self, self.gzfileobj)

    def close(self):
        logging.StreamHandler.close(self)
        self.gzfileobj.close()

class CloseFileHandler(logging.StreamHandler):
    def __init__(self, openfile, level = None, formatter = None):
        self.fileobj = openfile
        logging.StreamHandler.__init__(self, self.fileobj)

        if level is not None:
            self.setLevel(level)
        if formatter is not None:
            self.setFormatter(formatter)

    def close(self):
        logging.StreamHandler.close(self)
        self.fileobj.close()
