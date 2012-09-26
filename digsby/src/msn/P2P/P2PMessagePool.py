import logging; log = logging.getLogger('msn.p2p.messagepool')
import msn.P2P as P2P

class P2PMessagePool(object):
    def __init__(self):
        self.messages = {}
        self.messages[P2P.Version.V1] = {}
        self.messages[P2P.Version.V2] = {}

    def BufferMessage(self, msg):

        if msg.Header.MessageSize == 0 or msg.Header.SessionId > 0:
            #log.debug("Message not buffered because size is 0")
            return False, msg

        if msg.Version == P2P.Version.V2:
            if ((msg.Header.TFCombination == P2P.TFCombination.First and msg.Header.DataRemaining == 0) or
                (msg.Header.TFCombination > P2P.TFCombination.First)):
                #log.info("Message not buffered: first and complete")
                return False, msg

            if msg.Header.TFCombination == P2P.TFCombination.First and msg.Header.DataRemaining > 0:
                totalMessage = msg.Copy(msg)
                totalSize = msg.Header.MessageSize - msg.Header.DataPacketHeaderLength + msg.Header.DataRemaining
                # TODO: make innerbody a file-like object
                totalMessage.InnerBody = msg.InnerBody

                self.messages[msg.Version][msg.Header.Identifier + msg.Header.MessageSize] = totalMessage
                #log.info("Message buffered with id = %r. data remaining: %r", msg.Header.Identifier + msg.Header.MessageSize, msg.Header.DataRemaining)
                return True, msg

            if msg.Header.TFCombination == P2P.TFCombination.NONE:
                totalMessage = self.messages[msg.Version].get(msg.Header.Identifier, None)
                if totalMessage is None:
                    log.info("Message incomplete. unknown buffered message with id = %r. known ids are: %r", msg.Header.Identifier, self.messages[msg.Version].keys())
                    return True, msg

                if totalMessage.Header.PackageNumber != msg.Header.PackageNumber:
                    log.info("Message incomplete. unknown package number")
                    return True, msg

                dataSize = min(msg.Header.MessageSize - msg.Header.DataPacketHeaderLength, totalMessage.Header.DataRemaining)
                offset = len(totalMessage.InnerBody) #- totalMessage.Header.DataRemaining

                if ((msg.Header.DataRemaining + dataSize == totalMessage.Header.DataRemaining)
                    and ((dataSize + offset + msg.Header.DataRemaining) == (totalMessage.Header.TotalSize + totalMessage.Header.DataRemaining))):

                    # TODO: make innerbody a file-like object
                    totalMessage.InnerBody += msg.InnerBody
                    originalIdentifier = msg.Header.Identifier
                    newIdentifier = msg.Header.Identifier + msg.Header.MessageSize

                    totalMessage.Header.DataRemaining = msg.Header.DataRemaining
                    totalMessage.Header.Identifier = newIdentifier

                    if originalIdentifier != newIdentifier:
                        self.messages[msg.Version].pop(originalIdentifier, None)

                    if msg.Header.DataRemaining > 0:
                        self.messages[msg.Version][newIdentifier] = totalMessage
                        #log.info("message incomplete. newId = %r, data remaining: %r", newIdentifier, msg.Header.DataRemaining)
                        return True, msg
                    else:
                        totalMessage.InnerBody = totalMessage.InnerBody
                        totalMessage.Header.Identifier = newIdentifier - totalMessage.Header.MessageSize

                        log.info("message complete. total size = %r", len(totalMessage.InnerBody))

                        return False, totalMessage
                else:
                    pass
        # V1
        else:
            if (msg.Header.MessageSize == msg.Header.TotalSize) or ((msg.Header.Flags & P2P.Flags.Data) == P2P.Flags.Data):
                log.info("message complete. total size = %r", msg.Header.TotalSize)
                return False, msg

            totalMessage = self.messages[msg.Version].get(msg.Header.Identifier, None)
            if totalMessage is None:
                # TODO: make innerbody a file-like object
                totalPayload = msg.InnerBody
                copy = msg.Copy(msg)
                copy.InnerBody = totalPayload
                copy.Header.Offset = msg.Header.Offset + msg.Header.MessageSize

                self.messages[msg.Version][msg.Header.Identifier] = copy
                #log.info("message incomplete. data remaining = %r", copy.Header.TotalSize - copy.Header.Offset)
                return True, msg

            if (msg.Header.TotalSize == totalMessage.Header.TotalSize) and ((msg.Header.Offset + msg.Header.MessageSize) <= totalMessage.Header.TotalSize):
                # TODO: make innerbody a file-like object, seek to offset
                totalMessage.InnerBody += msg.InnerBody
                totalMessage.Header.Offset = msg.Header.Offset + msg.Header.MessageSize

                if totalMessage.Header.Offset == msg.Header.TotalSize:
                    totalMessage.Header.Offset = 0
                    self.messages[msg.Version].pop(msg.Header.Identifier, None)
                    log.info("message complete. total size = %r", msg.Header.TotalSize)
                    return False, totalMessage

                #log.info("message incomplete. total size = %r", totalMessage.Header.TotalSize - totalMessage.Header.Offset)
                return True, msg

            self.messages[msg.Version].pop(msg.Header.Identifier, None)

        return True, msg

    def Clear(self):
        self.messages.clear()
