import types
import Queue

class P2PSendItem(object):

    def __init__(self, remote, remoteGuid, message, callback = None):
        self.Remote = remote
        self.RemoteGuid = remoteGuid
        self.p2pMessage = message
        self.callback = callback

    def __repr__(self):
        return '%s(remote = %r, remoteGuid = %r, message = %r)' % (type(self).__name__,
                                                                   self.Remote.account,
                                                                   self.RemoteGuid,
                                                                   self.p2pMessage)

class P2PSendQueue(Queue.Queue):
    def Enqueue(self, remote, remoteGuid = None, message = None, callback = None):
        if remoteGuid is None and message is None:
            assert type(remote) is P2PSendItem
            item = remote
        else:
            item = P2PSendItem(remote, remoteGuid, message, callback)

        return self.put(item)

    def Dequeue(self):
        if not self.queue:
            return None

        sendItem = self.queue[0]

        if isinstance(sendItem.p2pMessage, types.GeneratorType):
            try:
                message = sendItem.p2pMessage.next()
            except StopIteration:
                self.get_nowait()
                return self.Dequeue()
            else:
                return P2PSendItem(sendItem.Remote, sendItem.RemoteGuid, message, sendItem.callback)
        else:
            try:
                return self.get_nowait()
            except Queue.Empty:
                return None

    def __len__(self):
        return self.qsize()


class P2PSendList(list):
    def append(self, remote, remoteGuid = None, message = None, callback = None):

        if remoteGuid is None and message is None:
            assert type(remote) is P2PSendItem
            item = remote
        else:
            item = P2PSendItem(remote, remoteGuid, message, callback)

        return list.append(self, item)

    def __contains__(self, thing):
        if list.__contains__(self, thing):
            return True

        if thing in [x.p2pMessage for x in self]:
            return True

        return False

    def remove(self, thing):
        if list.__contains__(self, thing):
            list.remove(self, thing)

        mything = None
        for mything in self:
            if mything.p2pMessage == thing:
                break
            else:
                mything = None

        if mything is None:
            raise ValueError("x not in list: %r" % thing)
        else:
            list.remove(self, mything)
