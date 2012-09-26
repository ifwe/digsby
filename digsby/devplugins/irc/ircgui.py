#__LICENSE_GOES_HERE__

from gui.toolbox import GetTextFromUser

def join_chat_room(irc, join):
    val = GetTextFromUser(_('Enter a room name:'),
                          caption = _('Join IRC Room'))

    if val is not None:
        join(val)

