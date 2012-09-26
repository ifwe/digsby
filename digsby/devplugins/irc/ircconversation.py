#__LICENSE_GOES_HERE__

from common.Conversation import Conversation
import common
from util import callsback

import string
import re

from logging import getLogger
log = getLogger('irc')

mirc_formatting = {
  2:  'b',
  31: 'u',
}

mirc_colors = ('000000 000000 00007b 009200 '
               'ff0000 7b0000 9c009c ff7d00 '
               'ffff00 00ff00 929400 00ffff '
               '0000ff ff00ff 7b7d7b d6d3d6').split(' ')
assert len(mirc_colors) == 16

color_code_re = re.compile(r'(\d+)(,\d+)?')

def mirc_to_html(msg):
    'Converts mIRC formatting codes to HTML.'

    new_msg = ''
    toggle = set()

    open_tag, close_tag = '<%s>', '</%s>'

    idx = 0
    while idx < len(msg):
        ch = msg[idx]

        if ord(ch) in mirc_formatting:
            elem = mirc_formatting[ord(ch)]
            if elem not in toggle:
                new_msg += open_tag % elem
                toggle.add(elem)
            else:
                new_msg += close_tag % elem.split(' ',1)[0]
                toggle.remove(elem)
        elif ord(ch) == 3:
            # colors come as \003foreground,background
            col_codes = msg[idx+1:]
            match = color_code_re.match(col_codes)
            if match:
                fg, bg = match.groups()
                elem = 'font color="#%s"' % mirc_colors[int(fg)]
                if elem not in toggle:
                    new_msg += open_tag % elem
                    toggle.add(elem)
                else:
                    new_msg += close_tag % elem.split(' ',1)[0]
                    toggle.remove(elem)
                idx = match.end()
        else:
            new_msg += ch
        idx += 1

    if len(toggle):
        for elem in toggle:
            new_msg += close_tag % elem.split(' ',1)[0]
    toggle.clear()

    return new_msg

class IRCConversation(Conversation):
    def __init__(self, irc):
        Conversation.__init__(self, irc)
        self.irc = irc
        self.buddies = irc.buddies
        self.cmds = irc.cmds
        self.self_buddy = self.irc.self_buddy

    def _tobuddy(self, bname):
        if isinstance(bname, (str, unicode)):
            return self.irc.buddies[str(bname)]
        return bname

    def buddy_join(self, buddy):
        buddy = self._tobuddy(buddy)
        if buddy not in self:
            self.system_message(u'%s has joined the room' % buddy.name)

        assert isinstance(buddy, common.buddy)
        self.room_list.append(buddy)

    def buddy_leave(self, buddy, leave_msg = ''):
        buddy = self._tobuddy(buddy)
        if buddy in self.room_list:
            self.room_list.remove(buddy)

        msg = '%s left the room' % buddy.name
        if leave_msg:
            msg += ": " + leave_msg
        self.system_message(unicode(msg))

    def ctcpcmd(self, msg):
        sp = chr(1)
        assert msg.find(sp) != 1

        lidx, ridx = msg.find(chr(1)), msg.rfind(chr(1))

        msg = msg[lidx+1:ridx]
        special = msg.split(' ',1)
        assert len(special) <= 2

        cmd = special[0]
        msg = special[1] if len(special) == 2 else None
        return cmd, msg

    def incoming_message(self, buddy, message):
        message = mirc_to_html(message)
        if message.find(chr(1)) != -1:
            cmd, msg = self.ctcpcmd(message)
            if cmd == 'ACTION':
                self.system_message(buddy.name + ' ' + msg)
        else:
            self.received_message(buddy, unicode(message))

    def send_typing_status(self, status=None):
        # um. don't.
        pass

    def send(self, *args, **kws):
        self.irc.sendraw(*args, **kws)

    def buddy_display_name(self, buddy):
        if self.name in buddy.modes:
            name = buddy.name
            modeset = buddy.modes[self.name]
            usermodes = self.irc.user_modes[::2]
            for char in usermodes:
                if char in modeset:
                    name = char + name

            return name
        else:
            return buddy.name

    @callsback
    def _send_message(self, message, callback=None):
        if not isinstance(message, basestring):
            message = message.format_as('plaintext')

        if message.startswith('/') and len(message) > 1:
            cmd = self.cmds(message)


            if cmd:
                if cmd.find('$') != -1:
                    cmd = string.Template(cmd).safe_substitute(
                        room = self.name
                    )

                if cmd.startswith(self.cmds._echomarker):
                    cmd = cmd[len(self.cmds._echomarker):]
                    self.system_message(cmd)
                    return

                return self.irc.sendraw(cmd)
            else:
                self.send(message[1:])
                return

        self.send(self.cmds.privmsg(self.destination, message))

        # IRC does not echo
        self.buddy_says(self.irc.self_buddy, unicode(message))

    def exit(self):
        self.room_list[:] = []
        Conversation.exit(self)

class RoomConvo(IRCConversation):
    ischat = True
    def __init__(self, irc, name):
        IRCConversation.__init__(self, irc)
        self.destination = self.name = name
        self.exit_message = ''

    def exit(self):
        self.send(self.cmds.part(self.name, self.exit_message))
        IRCConversation.exit(self)


class PrivConvo(IRCConversation):
    ischat = False
    def __init__(self, irc, name):
        IRCConversation.__init__(self, irc)
        self.destination = self.name = name

        me, other = self.irc.self_buddy, self.irc.buddies[name]
        self.room_list.extend([me, other])


