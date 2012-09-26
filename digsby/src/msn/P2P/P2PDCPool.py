import struct
import Queue

class P2PDCPool(object):
    def __init__(self):
        self.messages = Queue.Queue()
        self.lastMessage = ''
        self.bytesLeft = 0
        
    def BufferData(self, readable):
        if self.bytesLeft and self.lastMessage:
            data = readable.read(self.bytesLeft)
            self.lastMessage += data
            self.bytesLeft -= len(data)
            
            if self.bytesLeft == 0:
                self.messages.put(self.lastMessage)
                self.lastMessage = ''
                
        
        data = readable.read(4)
        while data:
            messageLength = struct.unpack('<I', data)[0]
            data = readable.read(messageLength)
            length = len(data)
            self.lastMessage += data
            
            if length < messageLength:
                self.bytesLeft = messageLength - length
            else:
                self.messages.put(self.lastMessage)
                self.lastMessage = ''
            
            data = readable.read(4)
            
            
    def GetNextMessageData(self):
        try:
            return self.messages.get_nowait()
        except Queue.Empty:
            return None
        
    def MessageAvailable(self):
        return not self.messages.empty()