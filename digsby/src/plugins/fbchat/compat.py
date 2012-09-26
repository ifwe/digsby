'''

Stuff which makes us more "compatible" with facebook's servers.
Read: program around facebook's bugs.

'''

__all__ = []

'''
Unhandled 'iq' stanza:
'<iq from="chat.facebook.com" to="-###id###@chat.facebook.com/Digsby_H3X_CHARS"
    id="fbiq####" type="set">
    <own-message
        xmlns="http://www.facebook.com/xmpp/messages"
        to="-1264188668@chat.facebook.com" self="false">
        <body>Ok I\'m back</body>
    </own-message>
</iq>'
'''

def ignore(*a, **k):
    pass

def ignore_iq(protocol, stream, *a, **k):
    #we don't want to send back anything, chances are, fb might kick us because
    #they don't understand the xmpp equivalent of "I don't understand you"
    #i.e. "Not Implemented"
#    stream.set_iq_set_handler("own-message", "http://www.facebook.com/xmpp/messages", ignore)
    stream.set_iq_get_handler("own-message", "http://www.facebook.com/xmpp/messages", ignore)
