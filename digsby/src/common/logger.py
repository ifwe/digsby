'''

Logging.

'''
from __future__ import with_statement

import sys
import re
import os.path
from operator import itemgetter
import config
from common import profile
from datetime import datetime
from util import soupify, Storage as S, tail, boolify
from util.primitives.misc import fromutc
from path import path
from digsby import iswidget
from traceback import print_exc
from logging import getLogger; log = getLogger('logger'); log_info = log.info
from common.message import Message
from .protocolmeta import SERVICE_MAP

import lxml.html
from util.htmlutils import render_contents

if config.platform == 'win':
    # a faster wildcard find is implemented for windows
    # as blist.findFiles(wildcard)
    import blist
    fastFind = blist.findFiles
else:
    fastFind = None

def get_default_logging_dir():
    "The parent directory for Digsby's log directory."

    from prefs import localprefs as lp
    localprefs = lp()
    return path(localprefs['chatlogdir']) / DEFAULT_LOG_DIR_NAME / profile.username


# The root directory all logs are stored in.
DEFAULT_LOG_DIR_NAME = u'Digsby Logs'

LOGSIZE_PARSE_LIMIT = 1024 * 15

def buddy_path(account, buddy):
    'Determines structure of logging directories.'

    return path(account.name).joinpath(account.username, buddy.name + '_' + buddy.service)

GROUP_CHAT_DIRNAME = 'Group Chats'

def chat_path(account, convo):
    return path(account.name).joinpath(account.username, GROUP_CHAT_DIRNAME)

def message_timestamp_id(dt):
    '''returns a datetime with the same granularity the logger uses'''

    return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

message_timestamp_fmt     = '%Y-%m-%d %H:%M:%S'
message_timestamp_fmt_OLD = '%Y-%m-%d %H:%M'

filename_format_re = re.compile(r'\d{4}-\d{2}-\d{2}\..*')
message_shorttime_fmt = '%H:%M:%S %p'

html_header = \
u'''<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
    "http://www.w3.org/TR/html4/strict.dtd">
<HTML>
   <HEAD>
      <meta http-equiv="Content-Type" content="text/html;charset=UTF-8" />
      <TITLE>%(title)s</TITLE>
   <style>
     .buddy { font-weight: bold; }
     .buddy:after { content: ":" }

     .time {
        color: #a0a0a0;
        font-family: monaco, courier new, monospace;
        font-size: 75%%;
     }
     .time:hover { color: black; }

     .outgoing { background-color: #efefef; }
     .incoming { background-color: #ffffff; }
   </style>
   <script type="text/javascript">
//<![CDATA[
    function convert_time(datetime){
        var dt = datetime.split(" ");
        var date = dt[0].split("-");
        var time = dt[1].split(":");
        var t = new Date;
        t.setUTCFullYear(date[0],date[1]-1,date[2]);
        t.setUTCHours(time[0],time[1],time[2]);
        return t.toLocaleTimeString();
    }

    function utc_to_local(){
        var node;
        for (var i=0; i<document.body.childNodes.length; i++){
            node = document.body.childNodes[i];
            if(node.nodeType == 1 && node.className.match("message")){
                var showtime = convert_time(node.getAttribute('timestamp'));
                var newspan = '<span class="time">(' + showtime + ') </span>';
                var msgnode = node;
                msgnode.innerHTML = newspan + msgnode.innerHTML;
            }
        }
    }
//]]>
   </script>
   </HEAD>
   <BODY onload="utc_to_local()">
'''

html_log_entry = (
'<div class="%(type)s message" auto="%(auto)s" timestamp="%(timestamp)s"><span class="buddy">%(buddy)s</span> '
'<span class="msgcontent">%(message)s</span>'
'</div>\n'
)

class Logger(object):
    'Logs IMs and Chats to file.'

    def __init__(self, output_dir = None,
                 log_ims = True,
                 log_chats = True,
                 log_widgets = False):

        self.OutputType = 'html'

        self.LogChats   = log_chats
        self.LogIMs     = log_ims
        self.LogWidgets = log_widgets

    def calculate_log_sizes(self):
        log_sizes = blist.getLogSizes(self.OutputDir)
        return sorted(((name, size) for name, size in log_sizes.iteritems()),
                key=itemgetter(1), reverse=True)

    def on_message(self, messageobj = None, convo = None, **opts):
        '''
        Called for every incoming and outgoing message.
        '''

        if not self.should_log_message(messageobj):
            return

        messageobj = modify_message(messageobj)

        output = self.generate_output(messageobj)
        assert isinstance(output, str)

        written_size = self.write_output(output, messageobj)

        try:
            buddy = messageobj.conversation.buddy
        except AttributeError:
            pass
        else:
            try:
                buddy.increase_log_size(written_size)
            except AttributeError:
                import traceback
                traceback.print_exc()

    def should_log_message(self, messageobj):

        if messageobj is None:
            return False

        # if not logging this type of message, return
        convo = messageobj.conversation

        if convo.ischat and not self.LogChats:
            return False

        elif not convo.ischat and not self.LogIMs:
            return False

        elif not self.LogWidgets and iswidget(convo.buddy):
            return False

        elif messageobj.buddy is None:
            # this is an "event"
            return False

        elif not messageobj.buddy.protocol.should_log(messageobj):
            # we don't really need to log exciting conversations with "AOL System Message"
            return False

        return True


    def history_for(self, account, buddy):
        'Returns an iterator which yields a succession of message objects back into the past.'

        log.debug('history_for(%r, %r)', account, buddy)

        files = self.logfiles_for(account, buddy)
        log.debug('%d %s log files found', len(files), self.OutputType)

        if not files:
            return iter([])

        if fastFind is None:
            # files come back sorted from fastFind
            files.sort(reverse = True)

        return history_from_files(files, 'html')

    def history_for_safe(self, account, buddy):
        try:
            hist = self.history_for(account, buddy)
        except Exception:
            print_exc()
            hist = iter([])

        return hist

    def logsize(self, account, buddy):
        "Returns the total size of all the files in the specified buddy's log folder."

        return sum(f.size for f in self.logfiles_for(account, buddy))

    def logsize_for_nameservice(self, name, service):
        glob_str = ''.join(('*/', name, '_', service, '/*.html'))

        outpath = self.OutputDir
        types = SERVICE_MAP.get(service, [service])

        total = 0
        for accttype in types:
            logpath = outpath / accttype
            total += sum(f.size for f in logpath.glob(glob_str))

        return total

    def logfiles_for(self, account, buddy):
        '''Returns a list of log files for a buddy on a given account.'''

        logdir = self.pathfor(account, buddy)

        if not logdir.isdir():
            return []

        # Only match files that look like the logs we output.
        global fastFind
        if fastFind is not None:
            pathjoin = os.path.join

            # use an optimized file search if possible
            try:
                wildcard = pathjoin(logdir, '*-*-*.html')
                return [pathjoin(logdir, p) for p in fastFind(wildcard)]
            except Exception:
                print_exc()
                fastFind = None

        return list(f for f in logdir.files('*.' + self.OutputType)
                    if filename_format_re.match(f.name))

    def pathfor(self, account, buddy):
        'Returns the path to the directory where logs for the specified buddy is stored.'

        return self.OutputDir.joinpath(buddy_path(account, buddy))

    #
    # OutputDir property: where to write the logs
    #

    def get_outputdir(self):
        return get_default_logging_dir()

    OutputDir = property(get_outputdir, doc = 'where to write logs')

    def walk_group_chats(self):
        '''
        yields all group chats
        '''

        for service in path(self.OutputDir).dirs():
            for account in service.dirs():
                group_chat_dir = account / GROUP_CHAT_DIRNAME
                if group_chat_dir.isdir():
                    for chat_file in group_chat_dir.files():
                        filename = chat_file.namebase
                        try:
                            if filename.count('-') == 2:
                                time, roomname = datetime.strptime(filename, chat_time_format), None
                            else:
                                time_part, roomname = filename.split(' - ', 1)
                                time = datetime.strptime(time_part, chat_time_format)
                                if isinstance(roomname, str):
                                    roomname = roomname.decode('filesys')
                        except ValueError:
                            pass
                        except Exception:
                            print_exc()
                        else:
                            yield dict(time=time,
                                       service=service.name,
                                       file=chat_file,
                                       roomname=roomname)

    #
    #
    #

    def get_path_for_chat(self, chat):
        pathdir = path(self.OutputDir) / chat_path(chat.protocol, chat)

        # log chats with the same name into the same file if it happened today
        if chat.chat_room_name:
            for f in pathdir.files('*.html'):
                name = f.namebase
                if 'T' in name:
                    day_part = name.split('T')[0]
                    try:
                        dt = datetime.strptime(day_part, chat_time_category)
                    except ValueError:
                        pass
                    else:
                        if fromutc(chat.start_time_utc).date() == dt.date():
                            try:
                                time_part, roomname = name.split(' - ', 1)
                            except ValueError:
                                pass
                            else:
                                if roomname == chat.chat_room_name:
                                    return f

        return pathdir / (convo_time_filename(chat) + '.' + self.OutputType)



    def write_output(self, output,  messageobj):
        '''
        Given output text and a message object, chooses a path for writing
        the log message and appends the output to that file.
        '''

        convo = messageobj.conversation
        proto = convo.protocol

        # Convert THIS timestamp to the local timezone so filenames are chosen based
        # on the local date.

        if convo.ischat:
            p = self.get_path_for_chat(convo)
        else:
            datefilename = fromutc(messageobj.timestamp).date().isoformat() # 2007-17-5
            pathelems    = (buddy_path(proto, convo.buddy), datefilename)
            p = path(path(self.OutputDir).joinpath(*pathelems) + '.' + self.OutputType)

        # assure path exists ( aim/digsby01/dotsyntax1337.html )
        if not p.parent.isdir():
            try:
                p.parent.makedirs()
            except WindowsError, e: # for race condition between exists check and makedirs
                if e.winerror == 183:
                    pass
                else:
                    raise

        written_size = 0
        if not p.isfile():
            # write a header if the file does not exist
            header = globals()['generate_header_' + self.OutputType](messageobj, self.output_encoding)
            assert isinstance(header, str)
            written_size += len(header)
            p.write_bytes(header)

        # write out to file
        written_size += len(output)
        p.write_bytes(output, append = p.isfile())
        return written_size

    def generate_output(self, messageobj):
        'Generates logging output for a message object.'

        return globals()['generate_output_' + self.OutputType](messageobj, self.output_encoding)

    output_encoding = 'utf-8'

#
# format: HTML
#

def generate_header_html(messageobj, encoding):

    c = messageobj.conversation
    datefmt = messageobj.timestamp.date().isoformat()

    if c.ischat:
        title = 'Chat in %s on %s' % (c.name, datefmt)
    else:
        title = 'IM Logs with %s on %s' % (c.buddy.name, datefmt)

    return (html_header % dict(title = title.encode('xml'))).encode(encoding, 'replace')



def generate_output_html(m, encoding = 'utf-8'):
    return (html_log_entry % dict(buddy     = m.buddy.name if m.buddy is not None else '',
                                  #time      = m.timestamp.strftime(message_shorttime_fmt),
                                  timestamp = m.timestamp.strftime(message_timestamp_fmt),
                                  message   = m.message,
                                  type      = m.type,
                                  auto      = getattr(m, 'auto', False),
                                  )).encode(encoding, 'replace')

class_buddy      = {'class': 'buddy'}
class_message    = {'class': 'message'}
class_msgcontent = {'class': 'msgcontent'}

def parse_html_lxml(html):
    'parses a logfile with lxml'

    messages = []

    doc = lxml.html.document_fromstring(html, parser = lxmlparser())
    for div in doc.xpath('//html/body/div'):
        try:
            message_type = div.attrib.get('class', '')
            if not 'message' in message_type:
                continue

            message_type = message_type.replace('message', '').strip()
            if not message_type in ('incoming', 'outgoing'):
                continue

            buddyname = div.find_class('buddy')[0].text
            timestamp = div.attrib.get('timestamp')
            if timestamp is not None:
                timestamp = parse_timestamp(timestamp)
            message = render_contents(div.find_class('msgcontent')[0])
            auto = boolify(div.attrib.get('auto', 'false'))
        except Exception:
            print_exc()
        else:
            messages.append(Message(buddy = S(name=buddyname),
                                    timestamp = timestamp,
                                    message = message,
                                    type = message_type,
                                    auto = auto,
                                    has_autotext = auto,
                                    ))

    return messages

# a global lxml.html.HTMLParser object with encoding overridden to be utf-8
_lxmlparser = None
def lxmlparser():
    global _lxmlparser
    if _lxmlparser is None:
        _lxmlparser = lxml.html.HTMLParser(encoding='utf-8')
    return _lxmlparser


def parse_html_slow(html):
    'Uses Beautiful Soup to parse messages out of a log file.'

    html = html.decode('utf-8', 'ignore')

    soup     = soupify(html, markupMassage = ((br_re,lambda m: '<br />'),))
    messages = []
    strptime = datetime.strptime

    for div in soup.findAll(message_divs):
        try:
            buddyname = div.findAll('span', class_buddy)[0].renderContents(None)
            timestamp = parse_timestamp(div['timestamp'])
            message   = div.findAll('span', class_msgcontent)[0].renderContents(None)
            type      = div['class'].replace('message', '').strip()
            auto      = boolify(div.get('auto', 'false'))
        except Exception:
            print_exc()
        else:
            messages.append(Message(buddy     = S(name = buddyname),
                                    timestamp = timestamp,
                                    message   = message,
                                    type      = type,
                                    auto      = auto))

    log_info('parse_html_slow with %d bytes returning %d messages', len(html), len(messages))
    return messages

def message_divs(tag):
    # Returns True for all Beautiful Soup tags which are <div>s with
    # a class including "message"
    return tag.name == 'div' and 'message' in dict(tag.attrs).get('class', '')

show_logparse_tracebacks = True

def parse_html(html):
    'HTML logs -> Message objects'

    # FIXME: On Mac, we are getting crashes when parse_html_fast is run. Disable it
    # for now until we have time to come back and look into what is causing the crash.
    if sys.platform == "darwin":
        messages = parse_html_slow(html)
    else:
        try:
            messages = parse_html_lxml(html)
            if __debug__:
                log.debug('parsed fast: got %d messages', len(messages))
        except Exception:
            global show_logparse_tracebacks
            if __debug__ or show_logparse_tracebacks:
                print_exc()
                show_logparse_tracebacks = False

            messages = parse_html_slow(html)
            log_info('parsed slow: got %d messages', len(messages))

    return messages

def parse_timestamp(timestamp):
    '"2008-02-23 22:34:50" -> datetime object'
    try:
        return datetime.strptime(timestamp, message_timestamp_fmt)
    except Exception:
        return datetime.strptime(timestamp, message_timestamp_fmt_OLD)


def history_from_files(files, logtype = 'html'):
    parse = globals()['parse_' + logtype]

    for logfile in files:
        # grab the last N bytes of the log file
        try:
            bytes = tail(logfile, LOGSIZE_PARSE_LIMIT)
        except Exception:
            print_exc()
        else:
            for msg in reversed(parse(bytes)):
                # yield messages going back into the paaaaast.
                yield msg

            if len(bytes) < logfile.size:
                # if tail only returned part of a file, stop now so we don't skip
                # messages
                break

chat_time_format = '%Y-%m-%dT%H.%M.%S'
chat_time_category = '%Y-%m-%d'

def convo_time_filename(convo):
    '''
    Given a Conversation object, returns a date string which can be used to
    identify its logfile.
    '''

    # remove microseconds; we don't need THAT much precision.
    time_part = fromutc(convo.start_time_utc).replace(microsecond=0).strftime(chat_time_format)

    room_name = convo.chat_room_name
    if room_name:
        return '%s - %s' % (time_part, room_name)
    else:
        return time_part

import config
USE_LXML = config.platform == 'win'

if USE_LXML:
    from util.htmlutils import to_xhtml
else:
    to_xhtml = lambda s:s

def modify_message(msgobj):
    msg = getattr(msgobj, 'message', None)

    if msg is not None:
        # will fixup bad HTML like aim's <HTML><BODY> stuff
        msgobj.message = to_xhtml(msg)

    return msgobj

import re
real_br = '<br />'
br_re = re.compile('<br\s*/?>', re.IGNORECASE)
brfix = lambda s: br_re.sub(real_br, s)

