#__LICENSE_GOES_HERE__

'''
Commands exposed as IRC slash commands.

Any functions not beginning with an underscore in this module can be called
from the command-line, so be careful!
'''

class IRCCommander(object):
    def __init__(self, irc): self._irc = irc
    _echomarker = '~~!echo!~~'

    def part(self, room, exit_message = ''):
        'Leaves a room with an optional bye message.'

        return 'PART %s %s' % (_room_name(room), exit_message)

    def quit(self, quit_message = ''):
        'Disconnects from the server, with an optional goodbye message.'

        return 'QUIT %s' % quit_message

    def nick(self, nickname):
        'Changes your nickname.'

        return 'NICK %s' % nickname

    def join(self, room):
        'Joins a channel.'

        return 'JOIN %s' % _room_name(room)

    j = join

    def invite(self, nickname, channel='$room'):
        'Invites a user to a channel.'

        return 'INVITE %s %s' % (nickname, channel)

    def privmsg(self, name, message):
        'Sends a private message.'

        return 'PRIVMSG %s :%s' % (name, message)

    def kick(self, room, name, message=''):
        'Kick a user with.'

        return 'KICK %s %s%s' % (_room_name(room), name,
                                 ' :' + message if message else '')

    def me(self, message):
        'Sends an action to a room. Crazy IRC.'

        return 'PRIVMSG $room :%sACTION %s%s' % (chr(1), message, chr(1))

    def leave(self, room='$room', message=''):
        'Leave a channel, with an optional goodbye message.'
        room = room if room=='$room' else _room_name(room)

        if message:  return 'PART %s :%s' % room, message
        else:        return 'PART %s' % room

    def raw(self, text):
        'Sends raw text to the server.'

        self._irc.sendraw(text)

    def slap(self, buddy):
        if hasattr(buddy, 'name'):
            buddy = buddy.name

        return self.me('slaps ' + buddy + ' around a bit with a large trout')

    def help(self, helpon=None):
        msg = ''
        if helpon:
            msg += '\n'.join(['/%s: %s'% (arg, getattr(self,arg.lower()).__doc__)
                              for arg in helpon.split(' ') if hasattr(self, arg.lower())])
        else:
            msg += ' '.join([elem.upper() for elem in dir(self)
                             if not elem.startswith('_')])

        return self._echomarker + msg

#
##
#
    def __call__(self, command):
        return self._slash_to_irc(command)

    def _slash_to_irc(self, command ):
        if not isinstance(command, (str, unicode)):
            raise TypeError('exec_slash needs a string')

        command = str(command)

        if not command.startswith('/'):
            raise ValueError("Slash command (%s) doesn't start with"
                             "command" % command)

        if len(command) < 2:
            return None

        # do we have a command?
        split = command[1:].split(' ',1)
        cmd = split[0].lower()

        # for saftey
        if cmd.startswith('_') or cmd == 'slash_to_irc':
            return None

        if hasattr(self, cmd):
            func = getattr(self, cmd)
            numargs = func.func_code.co_argcount-1
            args = command[1:].split(' ', numargs)[1:]
            print func.func_name, args
            try:
                return func(*args)
            except TypeError:
                return self._echomarker + '/%s: Not enough arguments.' % func.__name__


def _room_name(room):
    if not isinstance(room, basestring):
        room = room.name

    if not room.startswith('#'):
        room = '#' + room

    return room


