'''
Objects representing interactions with other Yahoo buddies.
'''

from common.Conversation import Conversation
from util import dictadd, callsback
from .yahoobuddy import YahooBuddy
from .yahoolookup import ykeys
from . import yahooformat
from logging import getLogger; log = getLogger('yahoo.convo')

class YahooConvoBase(Conversation):
    'Base class of all Yahoo conversations, providing buddy management.'

    def __init__(self, protocol):
        Conversation.__init__(self, protocol)
        self.__dict__.update(
            buddies = protocol.buddies,
            self_buddy = protocol.self_buddy)


    def buddy_join(self, buddy):
        self.typing_status[buddy] = None
        if buddy not in self.room_list:
            self.room_list.append(buddy)
            super(YahooConvoBase, self).buddy_join(buddy)

    def buddy_leave(self, buddy):
        if buddy in self.room_list:
            self.room_list.remove(buddy)
            del self.typing_status[buddy]

        super(YahooConvoBase, self).buddy_leave(buddy)


    def incoming_message(self, buddy, message, timestamp = None, content_type = 'text/yahoortf'):
        if not isinstance(buddy, YahooBuddy):
            raise TypeError()

        # Convert formatting to HTML.
        if content_type == 'text/html':
            message = yahooformat.tohtml(message)
            message = yahooformat.fix_font_size(message)
        if content_type == 'text/yahoortf':
            message = yahooformat.tohtml(message.encode('xml'))
            content_type = 'text/html'

        # convert newlines
        message = newlines_to_brs(message)

        self.typing_status[buddy] = None

        if timestamp is None:
            kws = {}
        else:
            kws = dict(timestamp=timestamp)
        kws['content_type'] = content_type
        if self.received_message(buddy, message, **kws):
            Conversation.incoming_message(self)

    @property
    def myname(self):
        "Returns the self buddy's name."

        return self.self_buddy.name

    def send_typing_status(self, status=None):
        pass

#
# instant messages
#

class YahooConvo(YahooConvoBase):
    'A one-to-one instant message conversation.'

    ischat = False

    def __init__(self, parent_protocol, buddy):
        YahooConvoBase.__init__(self,parent_protocol)

        #self.buddy = buddy
        self.buddy_join(parent_protocol.self_buddy)
        self.buddy_join(buddy)
        self.name = buddy.alias

        # These values will always be added to any ydicts going out.
        self.to_from = {'1': self.myname,
                        '5': buddy.name  }

    @callsback
    def _send_message(self, message, auto = False, callback=None, **options):
        '''
        Sends an instant message to the buddy this conversation is chatting
        with.
        '''
        network_msg = message.format_as('yahoo')
        network_msg = network_msg.encode('utf-8')

        d = {
             ykeys['message']: network_msg,
             ykeys['msg_encoding']: '1', #1==utf-8, which we just encoded it as
             }

        import YahooProtocol
        servicekey = YahooProtocol.PROTOCOL_CODES.get(self.buddy.service, None)
        if servicekey is not None: #if this follows the rest of the api, this is the right thing to do
            d[ykeys['buddy_service']] = servicekey

        log.info('Sending message to %r. buddy_service=%r', self.buddy, self.buddy.service=='msn')

        try:
            self.protocol.send('message', 'offline', dictadd(self.to_from, d))
        except Exception, e:
            callback.error(e)
        else:
            callback.success()

        #self.sent_message(message.encode('utf-8').encode('xml').decode('utf-8').replace('\n', '<br />'), format)

    @property
    def self_buddy(self):
        return self.protocol.self_buddy

    def send_typing_status(self, status=None):
        '''
        Sends a typing status packet.

        Sends the typing state if status is "typing."
        '''
        typing_now = status == 'typing'

        log.debug('sending %styping', ('not ' if not typing_now else ''))

        self.protocol.send('notify','typing', [
                           'typing_status', 'TYPING',
                           'frombuddy', self.self_buddy.name,
                           'message', '',
                           'flag', '1' if typing_now else '0',
                           'to', self.buddy.name])

    def exit(self):
        self.protocol.exit_conversation(self)
        Conversation.exit(self)

    def __repr__(self):
        return '<%s with %s from %s>' % (self.__class__.__name__, self.buddy, self.protocol.username)

#
# conferences
#

class YahooConf(YahooConvoBase):
    'A Yahoo conference is a multi-user chat.'

    ischat = True

    def __init__(self, parent_protocol, name):
        YahooConvoBase.__init__(self, parent_protocol)
        self.name = name

    def _bind_reconnect(self):
        pass # do not reconnect to Yahoo conferences.

    @property
    def chat_room_name(self):
        return self.name

    @callsback
    def invite(self, buddy, message=None, callback=None):
        bname = getattr(buddy, 'name', buddy)

        self.protocol.invite_to_conference(self.name, bname, message, callback=callback)

    @callsback
    def _send_message(self, message, callback=None):
        'Sends an instant message to this conference.'

        # create list of users to send to
        users = []
        [users.extend([ykeys['conf_entering'], buddy.name])
         for buddy in self.room_list if buddy != self.self_buddy]

        if len(self.room_list) == 1 and self.room_list[0] == self.protocol.self_buddy:
            # Yahoo whines when you send a message to a conference
            # in which you are the only participant.
            log.info('You are the only person in this chatroom.')
        else:
            self.protocol.send('confmsg', 'available', [
              'frombuddy', self.self_buddy.name,
              'conf_name', self.name,
              'message',   message.format_as('yahoo').encode('utf-8'),
            ] + users)

        callback.success()

    def exit(self):
        buddies_to_notify_of_exit = []
        for buddy in self.other_buddies:
            buddies_to_notify_of_exit.extend([
                'conf_from', buddy.name])

        self.protocol.send('conflogoff', 'available', [
            'frombuddy', self.self_buddy.name,
            'conf_name', self.name,
            ] + buddies_to_notify_of_exit)

        Conversation.exit(self)

    def __repr__(self):
        return '<YahooConf %s (%d members)>' % (self.name, len(self.room_list))

#
# chats
#

class YahooChat(YahooConvoBase):
    'A public Yahoo chatroom.'

    def __init__(self, parent_protocol, name="Yahoo Chat", topic=""):
        YahooConvoBase.__init__(self,parent_protocol)
        self.name = name    # the room name
        self.topic = topic

    def _send_message(self, message):
        log.info_s('send_message for %r: %s', self, message)
        self.protocol.send('comment', 'available', dictadd(dict(
            frombuddy = self.myname,
            room_name = self.name,
            chat_message = message.format_as('yahoo')),
            {'124':'1'})
        )



    def exit(self):
        log.info('YahooChat exit: sending chatlogout_available')
        self.protocol.send('chatlogout', 'available', frombuddy = self.myname)
        Conversation.exit(self)

    def __repr__(self):
        return '<YahooChat %s (%d members, topic: %s)' % \
                (self.name, len(self.room_list), self.topic)

def newlines_to_brs(s, br = '<br />'):
    return s.replace('\r\n', '\n').replace('\n', br).replace('\r', br)
