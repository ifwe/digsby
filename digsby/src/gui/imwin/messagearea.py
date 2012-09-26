'''

MessageArea

  Given Message objects and a MessageStyle, this class knows how to fill the IM
  window's browser area with content.

  It also applies IM window specific text transformations to messages like
  linkify and emoticons, and shows "date statuses" between messages that
  happened in different days.

'''
from __future__ import with_statement

from datetime import datetime

from gui.imwin.styles.stripformatting import strip
from gui.browser.webkit import WebKitWindow
from gui.toolbox.scrolling import WheelScrollCtrlZoomMixin, WheelShiftScrollFastMixin, ScrollWinMixin,\
    FrozenLoopScrollMixin

from common import pref, prefprop
from util import Storage as S, takemany, preserve_whitespace, traceguard
from util.primitives.misc import toutc, fromutc

from logging import getLogger; log = getLogger('msgarea')

from common.Conversation import AUTORESP

class quiet_log_messages(object):
    '''
    used by hidden messages system to hide certain messages when replaying logs.
    see imhub.py
    '''
    messages = set()

    def __init__(self, messages):
        self._messages = messages

    def __enter__(self):
        quiet_log_messages.messages = set(self._messages)

    def __exit__(self, exc_type, exc_val, exc_tb):
        quiet_log_messages.messages = set()

def history_enabled():
    'Returns True if the IM window should show history when appearing.'

    return pref('conversation_window.show_history', True) and pref('log.ims', True)

def should_show_time(tstamp1, tstamp2):
    '''
    Given two datetime objects, returns True if a "date status" should be
    shown between them.
    '''
    # show on date boundaries, but
    # convert to local before comparing the dates
    return fromutc(tstamp1).date() != fromutc(tstamp2).date()


try:
    import webview
except:
    import wx.webview as webview

class MessageArea(FrozenLoopScrollMixin, ScrollWinMixin, WheelShiftScrollFastMixin, WheelScrollCtrlZoomMixin, WebKitWindow):
    def __init__(self, parent, header_enabled = True, prevent_align_to_bottom=False):
        super(MessageArea, self).__init__(parent)

        self.inited = False
        self.header_enabled = header_enabled
        self.prevent_align_to_bottom = prevent_align_to_bottom

        self.Bind(webview.EVT_WEBVIEW_BEFORE_LOAD, self._before_load)

    date_context_format = '%A, %B %d, %Y'

    show_fonts     = prefprop('appearance.conversations.show_message_fonts', True)
    show_colors    = prefprop('appearance.conversations.show_message_colors', True)
    show_emoticons = prefprop('appearance.conversations.emoticons.enabled', True)
    htmlize_links  = prefprop('appearance.conversations.htmlize_links', True)

    def _before_load(self, e):
        e.Skip()
        if e.NavigationType == webview.WEBVIEW_NAV_LINK_CLICKED:
            url = e.URL
            if url.startswith('digsby://'):
                from common import urlhandler
                handle_result = urlhandler.handle(url)
                if handle_result.cancel_navigation:
                    e.Cancel()
                else:
                    if url != handle_result.url:
                        e.SetURL(url)

    def init_content(self, theme, chatName = None, buddy = None, show_history = None, prevent_align_to_bottom=False):
        # grab initial theme contents
        self.theme = theme

        # the message area keeps a timestamp, updated with each message, to
        # know when to insert a "date status" line
        now = datetime.now()
        self.tstamp  = toutc(datetime(now.year, now.month, now.day))

        show_header = self.header_enabled and pref('appearance.conversations.show_header', False)
        initialContents = theme.initialContents(chatName, buddy, show_header, prevent_align_to_bottom=prevent_align_to_bottom)

        self.SetPageSource(initialContents, theme.baseUrl)

        if show_history is None:
            show_history = True

        if show_history and history_enabled() and buddy is not None:
            with traceguard:
                self.show_history(buddy)

        self.inited = True

    def show_history(self, buddy):
        num_lines = max(0, pref('conversation_window.num_lines', 5, int))

        if num_lines > 0:
            logsource = buddy
            if pref('conversation_window.merge_metacontact_history', False):
                from common import profile
                metacontact = profile.metacontacts.forbuddy(buddy)
                if metacontact: logsource = list(metacontact).pop()

            msgobjs   = reversed(list(takemany(num_lines, logsource.history)))
            self.replay_messages(msgobjs, buddy)

    def replay_messages(self, msgobjs, buddy, context = True):
        'Displays a sequence of message objects.'

        next         = False
        oldname      = None
        olddirection = None

        num_messages = 0
        skipped_messages = 0

        for msg in msgobjs:
            num_messages += 1

            if msg in quiet_log_messages.messages:
                skipped_messages += 1
                if __debug__: log.info('skipping message: %r', msg)
                continue

            # the theme needs to know which messages to glue together as "adjacent"--
            # so we check the buddy name and the direction attribute for changes.
            name        = msg.buddy.name
            direction   = msg.type
            next        = oldname == name and direction == olddirection

            msg.buddy = buddy_lookup(buddy, name)
            msg.content_type = 'text/html'

            # context means "history" here
            self.format_message(direction, msg, next, context = context)

            oldname = name
            olddirection = direction

        log.info('replay_messages: %d total messages (%d skipped) for buddy %r', num_messages, skipped_messages, buddy)

    def show_header(self, show):
        'Show or hide the message header.'

        return self.RunScript(self.theme.show_header_script(show))

    def date_status(self, dt):
        # "Status" messages are reused as a form of date context for displaying
        # old messages in the history, and for when an IM window is open for
        # more than a day.

        # displayed timestamps need to be converted from UTC->local
        format_dt = fromutc(dt)

        return S(message   = format_dt.strftime(self.date_context_format),
                 timestamp = dt,
                 buddy     = None,
                 type      = None)

    def format_message(self, messagetype, messageobj, next = False, context = False):
        '''
        messagetype    status, incoming, or outgoing
        messageobj     a storage with buddy, message, timestamp, conversation
        next           True if this message is from the same sender as the last one
        context        True if this message is being displayed as message history
        '''
        if messagetype != 'status':

            # don't show date for the first message in the window
            msgtime = messageobj.timestamp

            if msgtime is None:
                msgtime = datetime.utcnow()

            # do the timestamps differ enough to show a date context line?
            if should_show_time(self.tstamp, msgtime):
                self.theme.set_always_show_timestamp(True)
                try:
                    self.format_message('status', self.date_status(msgtime), next = False, context = context)
                finally:
                    self.theme.set_always_show_timestamp(False)

                # This can't be a "next" message, since we just showed a status line.
                next = False

            self.tstamp = msgtime

        content_type = getattr(messageobj, 'content_type', 'text/plain')

        if content_type == 'text/plain':
            messageobj.message = messageobj.message.encode('xml')
            messageobj.message = preserve_whitespace(messageobj.message)
            messageobj.content_type = 'text/html'

        # apply text transformations, including emoticons and stripping
        # colors and formatting (if enabled)
        show_colors = self.theme.allow_text_colors and self.show_colors
        show_emoticons = pref('appearance.conversations.emoticons.pack') if self.show_emoticons else None

        transforms = dict(emoticons = show_emoticons,
                          links     = self.htmlize_links,
                          spaces    = True)

        if not getattr(messageobj, 'linkify', True):
            transforms['links'] = False

        stripped, strip_values = strip(messageobj.message,
                                       formatting           = not self.show_fonts,
                                       colors               = not show_colors,
                                       plaintext_transforms = transforms)

        messageobj = messageobj.copy()
        messageobj.message = stripped

        if getattr(messageobj, 'has_autotext', False):
            extra = {}
        else:
            extra = dict(has_autotext = True, autotext = AUTORESP)

        # If there is one background color, pass it to the conversation theme
        if self.show_colors:
            extra.update(handle_colors(strip_values))

        # get the JS function and complete message (including theme elements)
        func, msg = self.theme.format_message(messagetype, messageobj, next, context, **extra)

        if func:
            script = "%s('%s');" % (func, js_escape(msg))
            self.RunScript(script)

def handle_colors(vals):
    'vals : defaultdict(list) of {keys: ["attrs",...]}'

    bodycolor = None

    if 'bgcolor' in vals:
        bodycolor = vals['bgcolor'][0]
    elif 'back' in vals:
        bodycolor = vals['back'][0]

    if bodycolor:
        return {'textbackgroundcolor': bodycolor}

    return {}

def js_escape(msg):
    # TODO: find a real escape function
    return (msg.replace('\\', '\\\\')
               .replace('\n', '\\\n')
               .replace('\r', '\\\r')
               .replace("'", "&apos;"))

def buddy_lookup(buddy, name):
    protocol = getattr(buddy, 'protocol', None)

    # protocol might be offline, or missing a buddies dictionary.
    if protocol is not None and hasattr(protocol, 'buddies') and protocol.buddies:
        try:
            buddy = buddy.protocol.get_buddy(name)
        except Exception:
            import traceback
            traceback.print_exc_once()

    return buddy
