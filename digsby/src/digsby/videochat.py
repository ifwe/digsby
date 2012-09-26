'''

Video Chat

'''
from __future__ import with_statement

import string
import re
from operator import attrgetter

from digsby.web import DigsbyHttp, DigsbyHttpError
import simplejson as json
from contacts.buddyinfo import BuddyInfo
from common import profile, netcall
from util import threaded, traceguard
from util.primitives.funcs import Delegate

from logging import getLogger; log = getLogger('videochat')

# Sent to buddy when requesting a video conference.
INVITE_URL = 'http://v.digsby.com/?id=%(video_token)s&t=%(widget_id)s&v=%(tb_version)s'

TOKBOX_VERSION = '2'

VALID_TOKEN_CHARACTERS = string.ascii_letters + string.digits

VIDEO_CHAT_TITLE = _('Audio/Video Call with {name}')

def gui_call_later(cb, *a, **k):
    import wx
    wx.CallAfter(cb, *a, **k)

class VideoChat(object):
    '''
    Represents a link between a video widget and a buddy.

    - Uses VideoChatHttp to register video widget tokens with the server.
    - Creates and manages a video window
    - Maintains a link to a buddy, working with DigsbyProtocol to route
      messages to and from the correct IM window
    '''

    def __init__(self, buddy):
        self.buddy_info = BuddyInfo(buddy)
        self.http = VideoChatHttp(profile.username, profile.password)

        self._widget_jid = None
        self._stopped    = False
        self.on_stop = Delegate()

        self.handle_buddy_state(buddy)

        # Video chat aliases
        my_alias = buddy.protocol.self_buddy.name
        friend_alias = buddy.name

        # fetch a video token on the threadpool
        create = threaded(self.http.create_video)
        create(my_alias, friend_alias, success = self.on_token, error = self.error_token)

    def handle_buddy_state(self, buddy):
        # when the protocol you're chatting from goes offline, close the video window
        proto = buddy.protocol

        def on_protocol_state(proto, attr, old, new):
            if not proto.connected:
                self.stop()

        proto.add_observer(on_protocol_state, 'state', obj = self)
        self.on_stop += lambda: proto.remove_observer(on_protocol_state, 'state')


    def __repr__(self):
        return '<VideoChat with %s>' % self.buddy_info

    def on_token(self):
        'Called back when VideoChatHttp successfully obtains tokens.'

        token = self.http.video_token
        log.info('received video token: %s', token)
        profile.connection.add_video_chat(token, self)
        gui_call_later(self.on_url, self.http.invite_url(), self.http.widget_id)

    def on_url(self, invite_url, widget_id):
        'Called back when VideoChatHttp successfully creates a new video widget token.'

        # Send an invite message.
        buddy = self.buddy_info.buddy()
        if buddy is not None:
            message = _('Join me in an audio/video call: %s') % invite_url

            def send_and_echo_invite():
                convo = buddy.protocol.convo_for(buddy)
                convo.send_plaintext_message(message)
                convo.system_message(_('You have invited {name} to an audio/video chat.').format(name=buddy.name))

            netcall(send_and_echo_invite)

        # Show the video chat window.
        title = VIDEO_CHAT_TITLE.format(name=self.buddy_info.buddy_name)

        from gui.video.webvideo import VideoChatWindow
        frame = self.video_frame = VideoChatWindow(title, widget_id, on_close = self.stop)
        gui_call_later(frame.Show)

    def error_token(self):
        'Called when there is an error retreiving tokens from the server.'

        log.warning('error receiving token')
        self.system_message(_('Audio/Video chat is currently unavailable.'))

    def send_im(self, message):
        'Sends an unechoed IM to the video widget.'

        convo = self.widget_convo
        if convo is not None:
            netcall(lambda: convo.send_plaintext_message(message))

    @property
    def widget_convo(self):
        'Returns a conversation object with the video widget, if one can be found, or None.'

        if self.widget_jid is None:
            self.widget_jid = self.find_widget_jid()

            if self.widget_jid is None:
                return log.warning('no widget jid, cannot forward message to widget')

        conn = profile.connection
        if not conn:
            return log.warning('no Digsby connection, cannot forward message to widget')

        return conn.convo_for(self.widget_jid)

    def set_widget_jid(self, jid):
        if jid != self._widget_jid:
            self._widget_jid = jid

            # if buddy signs off, stop
            if profile.connection:
                profile.connection.get_buddy(jid).add_observer(self.buddy_status_change, 'status')

    widget_jid = property(attrgetter('_widget_jid'), set_widget_jid)

    def find_widget_jid(self):
        'Checks for a video widget JID on the Digsby connection.'

        conn = profile.connection
        if conn is None:
            return log.warning('cannot find widget jid: no digsby connection')

        # Search for a buddy on the Digsby connection with a matching resource
        # to the one the server told us about.
        #
        # TODO: for loops nested this deep are never a good idea. can have
        # the server tell us about this resource more specifically?
        resource = 'video.' + self.http.video_token

        for buddict in conn.buddy_dictionaries():
            for name, buddy in buddict.iteritems():
                if buddy.jid.domain == u'guest.digsby.org':
                    for jid, res in buddy.resources.iteritems():
                        if jid.resource == resource:
                            return jid

    def buddy_status_change(self, buddy, attr, old, new):
        'Invoked when the widget buddy changes status.'

        # we're looking for the buddy to go offline...
        if buddy.online: return

        log.info('buddy %r went offline...stopping', buddy)

        buddy.remove_observer(self.buddy_status_change, 'status')

        # ...if they do, show a message in the IM window
        if not self._stopped:
            self.system_message(_('Audio/Video call ended by other party.'))

        self.stop()

    def system_message(self, message, **opts):
        'Echoes a system message to the IM window.'

        with traceguard:
            im_buddy = self.buddy_info.buddy()
            if im_buddy is not None:
                convo = im_buddy.protocol.convo_for(im_buddy)
                convo.system_message(message, **opts)

    def stop(self):
        'End all communication with the video widget.'

        self.stop = lambda *a: None # don't stop more than once
        self._stopped = True
        log.info('stopping video chat %r', self)

        # destroy the video window
        if self.video_frame: gui_call_later(self.video_frame.Destroy)

        # appear offline to the widget
        convo = self.widget_convo
        if convo is not None:
            netcall(self.widget_convo.buddy.appear_offline_to)

        # remove IM window link
        token = self.http.video_token
        if token is not None:
            conn = profile.connection
            if conn is not None:
                conn.remove_video_chat(token)

        # tell the server to kill the video info
        threaded(self.http.close_video)()

        self.on_stop()

class VideoChatException(Exception):
    pass

class VideoChatHttp(DigsbyHttp):
    def __init__(self, username, password):
        '''
        Creates a VideoChat object for setting up web based video chats.

        username   your Digsby ID
        password   your unencrypted digsby password
        '''
        DigsbyHttp.__init__(self, username, password)

    def create_video(self, nick, guest, video_token = None, widget_id = None):
        '''
        Creates an AV page.

        nick   unicode display nickname for your "from" account
        guest  unicode guest nickname for the "to" account
        '''

        vtokens = self.GET(obj   = 'widget',
                           act   = 'video',
                           tbv   = TOKBOX_VERSION,
                           nick  = nick.encode('utf-8'),
                           guest = guest.encode('utf-8'))

        # check to make sure the returned token is alphanumeric
        # TODO: make self.GET return status, resp pair so we can check HTTP
        #       status codes
        assert isinstance(vtokens, str)

        tokens = json.loads(vtokens)

        def invalid():
            raise DigsbyHttpError('invalid video token returned: %r' % tokens)

        def validate(t):
            return isinstance(t, basestring) and set(t).issubset(VALID_TOKEN_CHARACTERS)

        if not isinstance(tokens, dict):
            invalid()

        self.video_token = tokens.get('token')
        self.widget_id   = tokens.get('widget')

        if not validate(self.video_token) or not validate(self.widget_id):
            invalid()

    def invite_url(self):
        if self.video_token is None:
            raise VideoChatException('no AV page has been created')

        return INVITE_URL % dict(video_token = self.video_token,
                                 widget_id   = self.widget_id,
                                 tb_version  = TOKBOX_VERSION)

    def close_video(self):
        'Closes a video chat.'

        log.info('%r.close_video()', self)
        self.GET(obj = 'widget', act = 'killvideo')

video_invite_re = re.compile('http://v\.digsby\.com/\?id=(\w+)&(?:amp;)?t=(\w+)&(?:amp;)?v=2')

def _on_message(messageobj, type, **opts):
    '''
    intercept all messages, catching tokbox invites from other Digsby users,
    and turning them into the special video chat window
    '''

    if type != 'incoming':
        return

    msg = getattr(messageobj, 'message', None)
    if not isinstance(msg, basestring):
        return

    match = video_invite_re.search(msg)
    if match is None:
        return

    id, wid = match.groups()

    # replace the URL
    buddy_name = messageobj.buddy.name
    new_url = '<a href="digsby://avcall/%s/%s">Join Now</a>' % (buddy_name, wid)
    first_part = msg[:match.start()]
    last_part = msg[match.end():]

    if messageobj.content_type == 'text/plain':
        print 'encoding xml and changinge content type'
        first_part = first_part.encode('xml')
        last_part = last_part.encode('xml')
        messageobj.content_type = 'text/html'

    messageobj.message = ''.join(
        (first_part, new_url, last_part))

def show_video_chat_window(buddy_name, widget_id):
    from gui.video.webvideo import VideoChatWindow
    gui_call_later(lambda: VideoChatWindow(VIDEO_CHAT_TITLE.format(name=buddy_name), widget_id).Show())

def register_message_hook():
    import hooks
    hooks.register('digsby.im.msg.pre', _on_message)

    # setup a handler for digsby://avcall links
    from common import urlhandler
    urlhandler.register('avcall/([\w@\.]+)/(\w+)', show_video_chat_window)

def unregister_message_hook():
    raise NotImplementedError('Hook does not have unregister yet')

