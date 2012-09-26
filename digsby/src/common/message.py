from datetime import datetime
from util.primitives import Storage, curly

class Message(Storage):
    def __init__(self, buddy = None, message = None, conversation = None, type = 'incoming', timestamp = None, **other):
        self.buddy        = buddy
        self.message      = message
        self.type         = type
        self.conversation = conversation
        self.timestamp    = timestamp if timestamp is not None else datetime.utcnow()

        self.update(other)

    def copy(self):
        m = Message()
        m.update(self)
        return m

    def __hash__(self):
        return hash(self._attrs)

    def __eq__(self, other):
        return self is other or self._attrs == getattr(other, '_attrs', None)

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def _attrs(self):
        # round timestamps off to the same granularity used by the logger
        from common import logger
        datetime = logger.message_timestamp_id(self.timestamp)
        return hash((self.message, self.type, datetime))

class StatusUpdateMessage(Message):
    def __init__(self, **info):
        buddy   = info['buddy']
        message = curly(info['header'], source = info)

#       TODO: some of the skins don't have room for longer status lines...
        Message.__init__(self,
                         buddy = buddy,
                         message = message,
                         type = 'status')
