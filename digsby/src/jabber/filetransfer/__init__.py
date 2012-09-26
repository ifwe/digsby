from jabber.objects.bytestreams import BYTESTREAMS_NS
import jabber
feature_neg_ns   = 'http://jabber.org/protocol/feature-neg'
supported_streams = [BYTESTREAMS_NS]
import S5BFileXferHandler, initiateStream
file_transfer_handlers = {BYTESTREAMS_NS: S5BFileXferHandler.SOCKS5Bytestream }
from jabber.filetransfer.StreamInitiation import StreamInitiationHandler
