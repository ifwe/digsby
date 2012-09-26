'''
Digsby IRC client.

Here's what IRC traffic from the server looks like:

:user!hostname.com PRIVMSG yourname     :some text

origin             command destination  text

'''
import common
from common import netcall, caps, profile
from irc.ircconversation import RoomConvo, PrivConvo
from util import no_case_dict
from util.Events import EventMixin
from contacts import Group
from util.observe import ObservableDict

from logging import getLogger
log = getLogger('irc')
rawin, rawout  = getLogger('irc.raw.in'), getLogger('irc.raw.out')

CR, LF = '\x0d', '\x0a'
CRLF   = CR + LF
IRC_ENCODING = 'utf8'

from irccmds import IRCCommander

class IrcBuddy(common.buddy):
    __slots__ = ['modes']

    service = 'irc'
    buddy_icon = icon = None
    increase_log_size = Null
    history = property(lambda self: iter([]))
    status_orb = 'available'
    online = True
    idle = None
    @property
    def serviceicon(self):
        return self.protocol.serviceicon
    caps = [caps.IM]
    blocked = False
    sms = False
    status_message = ''


    def __init__(self, name, protocol):
        self.status = 'available'
        common.buddy.__init__(self, name, protocol)
        self.modes = {}

class IrcBuddies(ObservableDict):#no_case_dict):
    'dict subclass that creates IrcBuddy objects on demand'

    def __init__(self, protocol):
        ObservableDict.__init__(self)
        self.protocol = protocol

    def __getitem__(self, buddy_name):
        if not isinstance(buddy_name, (str,unicode)):
            raise TypeError('buddy name must be a string (you gave a %s)' % \
                            (type(buddy_name)))

        buddy_name = str(buddy_name).lower()

        try:
            return ObservableDict.__getitem__(self, buddy_name)
        except (KeyError,):
            return self.setdefault(buddy_name, IrcBuddy(buddy_name, self.protocol))

def _origin_user(origin_string):
    return origin_string.split('!',1)[0]

class ProtocolCommon(object):
    def set_message(self, *a, **k):
        pass

    def set_buddy_icon(self, *a, **k):
        pass

    def set_idle(self, *a, **k):
        pass

class IRCClient(common.protocol, ProtocolCommon):
    'One connection to an IRC server.'

    name = 'irc'

    codes = {
     353: 'name_list',
     366: 'end_name_list',
     372: 'MOTD',
     433: 'nick_used'
    }

    user_modes = [
        '@', 'Channel Operator',
        '+', 'Voice',
        '%', 'Half-operator',
        '.', 'Owner',
        '~', 'Owner',
        '&', 'Protected user',
        '!', 'Administrator',
        '*', 'Administrator',
    ]

    def __init__(self, username, password, msg_hub,
                 server=('irc.penultimatefire.com',6667)):
        common.protocol.__init__(self, username, password, msg_hub)

        assert isinstance(server, tuple)
        self.server = server

        self.nick = username

        self.rooms    = dict()
        self.privates = dict()

        self.buddies = IrcBuddies(self)

        self.cmds = IRCCommander(self)

        self.socket = IrcSocket()
        self.socket.bind_event('connected', self._on_connected)
        self.socket.bind_event('incoming_line', self.incoming_line)

        self.root_group = Group('Root', self, 'Root')

    def _on_connected(self):
        self.self_buddy = self.buddies[self.username]
        self.sendraw(self.cmds.nick(self.username))
        self.sendraw('USER %s +iw %s' % (self.username, 'Digsby Dragon'))
        self.change_state(self.Statuses.ONLINE)

    def chat_with(self, buddy):
        if hasattr(buddy,'name'): buddy = buddy.name
        return self.convo_for(buddy)

    def Connect(self, invisible=False):
        if invisible:
            log.warning('Connect ignoring invisbile argument')

        netcall(lambda: self.socket.connect(self.server))

    def Disconnect(self):
        self.socket.close()

    #
    # the following methods handle incoming IRC traffic
    #

    def NOTICE(self, *args):
        pass

    def PING(self, msg, text, origin):
        self.sendraw('PONG :' + text)

    def MOTD(self, msg,text,origin):
        pass

    def KICK(self, origin, target, text=None):
        pass

    def PRIVMSG(self, dest, text, origin):
        from_user = _origin_user(origin)
        if dest.lower() == self.username.lower():
            # this is a private message
            convo = self.convo_for(from_user)
        else:
            # this is a message to a room
            convo = self.convo_for(dest)

        profile.on_message(convo=convo)
        convo.incoming_message(self.buddies[from_user], text)

    def MODE(self, msg, text, origin):
        print 'YOu are now ' + text + '! Rawkz'

    def PART(self, room_name, user, origin):
        'Buddy is leaving a room.'

        self.convo_for(room_name).buddy_leave( self.buddies[user] )

    def QUIT(self, _msg, quit_msg, origin):
        'Buddy is quiting the server.'

        buddy = self.buddies[_origin_user(origin)]
        for room in self.rooms.values():
            if buddy in room:
                room.buddy_leave(buddy, quit_msg)

        if buddy.name in self.buddies:
            del self.buddies[buddy.name]


    def nick_used(self, msg, text, origin):
        self.hub.on_error(self, 'Nickname is already being used.')

    def convo_for(self, name):
        if hasattr(name, 'name'):
            name = name.name.lower()

        if name.startswith('#'):
            try: return self.rooms[name]
            except KeyError:
                return self.rooms.setdefault(name, RoomConvo(self,name))
        else:
            try: return self.privates[name]
            except KeyError:
                return self.privates.setdefault(name, PrivConvo(self,name))

    def JOIN(self, args, room_name, origin):
        buddy_joining = _origin_user(origin)

        # is this the ack for us joining a room?
        if buddy_joining.lower() == self.self_buddy.name.lower():
            profile.on_entered_chat(self.convo_for(room_name))
        else:
            # no, it's another user joining a room we're in
            self.convo_for(room_name).buddy_join(self.buddies[buddy_joining])

    def INVITE(self, msg, _notext, fromuser):
        'Someone has invited you to a channel.'
        fromuser = _origin_user(fromuser)

        for elem in msg.split(' '):
            if elem.startswith('#'):
                self.hub.on_invite(self, self.buddies[fromuser], elem)

    def name_list(self, room_name, names, origin):
        'An incoming room list.'

        room_idx = room_name.find('#')
        if room_idx != -1:
            room_name = room_name[room_idx:]
        else:
            return log.error('name_list cannot handle ' + room_name)

        log.info('name_list: %s [%s]' % (room_name, names))

        convo = self.convo_for(room_name)

        # for each name...
        for name in names.split(' '):

            modeset = set()

            # find any special "op" characters
            for symbol in self.user_modes[::2]:
                if name.find(symbol) != -1:
                    # add user privilege
                    modeset.add(symbol)

                    # replace the special character with nothing
                    name = name.replace(symbol, '')

            buddy = self.buddies[name]
            buddy.modes.setdefault(room_name,set()).clear()
            buddy.modes[room_name].update(modeset)

            convo.buddy_join(buddy)

    def NICK(self, none, new_nick, origin):
        '''
        An IRC buddy has changed his or her nickname.

        We must be careful to replace the buddy's name, and also the hash
        key for the buddy.
        '''
        old_nick = _origin_user(origin)
        if not old_nick: return

        buddy = self.buddies.pop(old_nick)
        buddy.name = new_nick
        self.buddies[new_nick] = buddy


    def join_chat_room(self, chat_room_name, server=None):
        if isinstance(chat_room_name, unicode):
            room_name = chat_room_name.encode(IRC_ENCODING)

        self.sendraw(self.cmds.join(chat_room_name))

    def sendcmd(self, func, *args, **kw):
        txt = func(*args, **kw)
        assert isinstance(txt, str)
        rawout.info(txt)
        self.push(txt + CRLF)

    def sendraw(self, rawtext):
        'Sends raw text out to the socket.'

        rawout.info(rawtext)
        data = rawtext + CRLF

        if isinstance(data, unicode):
            data = data.encode(IRC_ENCODING)
        self.socket.push(data)

    def incoming_line(self, line):
        # log the raw IRC
        rawin.info(line)

        if line[0] == ':':
            origin, line = line[1:].split(' ', 1)
        else:
            origin = None

        try: args, text = line.split(' :', 1)
        except ValueError:
            args = line
            text = ''

        # grab function and any arguments
        split =  args.split(' ', 1)
        func = split[0]
        message = len(split) > 1 and split[1] or ''

        if hasattr(self, func):
            return getattr(self,func)(message,text,origin)
        else:
            try:
                n = int(func)
            except:
                # make this catch the right error, not all of them!
                raise
                return

            if n in self.codes:
                func = self.codes[n]
                if hasattr(self, func):
                    return getattr(self, func)(message,text,origin)

class IrcSocket(common.socket, EventMixin):
    events = set((
        'connected',
        'incoming_line',
    ))

    def __init__(self):
        common.socket.__init__(self)
        EventMixin.__init__(self)

        self.set_terminator(CRLF)
        self.data = []

    #
    # asyncore methods
    #

    def handle_connect(self):
        self.event('connected')
        common.socket.handle_connect(self)

    def collect_incoming_data(self, data):
        self.data.append(data)

    def found_terminator(self):
        line = ''.join(self.data)
        self.data = []

        self.event('incoming_line', line)

