'''
MySpace IM is a (mostly) text-based protocol. The basic format of protocol messages is as follows:

'\\persistr\\\\cmd\\257\\dsn\\512\\uid\\0\\lid\\20\\rid\\29690261\\body\\AdUnitRefreshInterval=3\x1cAlertPollInterval=360\\final\\'

Which translates into the following data structure (using the msmsg and msdict classes from MSIMUtil.py)

msmsg([
 ('persistr', ''),
 ('cmd', 257),
 ('dsn', 512),
 ('uid', 0),
 ('lid', 20),
 ('rid', 29690261),
 ('body', msdict(AdUnitRefreshInterval = '3', AlertPollInterval = '360'))
])

Things to note:
 - the type of a message is determined by its first key. this is a 'persistr' message. See varios classes in MSIMApi.py
   for more info.
 - messages are roughly lists of key-value pairs, separated by slash characters.
 - all messages end with the key 'final', which does not have a value.
 - the value for the key 'body' may have another list of key-value pairs embedded in it, which has a different format:
   pairs are separated by a '\x1c' byte, and the key/value portions of each pair are separated with an '=' character
 - the uid key usually indicates the sender. a uid of 0 indicates the message originated from the server.
 - the dsn and lid keys determine the data the message is about, and the cmd key determines what the message is
   requesting to do with the data. Together they all affect the behavior of the client and/or server. (the meaning of
   these values is mostly determined via trial and error)
 - rid is the reference ID, which is basically an incrementing counter for sent messages, which are included in response
   messages.

So:
 this message is of type 'persistr' (usually the type for control messages from the server)
 cmd is 257, which indicates it's a reply for a Get message (Get(1) + Reply(256))
 the dsn and lid (512, 20) pair indicates the data is for ad settings
 rid is 29690261, which means it's a response to the client's request with the same ID.
 uid is 0 indicating it's a server message
 the body indicates the actual settings for advertisements in the official client.
'''

from MSIMProtocol import MyspaceIM as protocol
from MSIMSocket import myspace_socket as socket
import MSIMUtil as msutil

Myspace = protocol

decrypt = msutil.decrypt
crypt = msutil.crypt
make_key = msutil.make_key
