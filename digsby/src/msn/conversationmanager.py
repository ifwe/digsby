import util.primitives.funcs as funcs

from logging import getLogger
log = getLogger('msn.conversationmanager')

class ConversationManager(object):
    def __init__(self, msn):
        '''
        msn is an MSNProtocol object
        '''
        self.msn = msn
        self._convs = {}

    def find_convo(self, name=(), count=(), type=(), f=None):
        '''
        Finds all conversation such that:
            All names in the sequence 'name' are also in the conversation, and vice versa
            the number of buddies is in the sequence 'count'
            the type of the conversation is in the sequence 'type'
            f(conversation) is True

        If an argument is not provided, it is ignored.

        A list is returned. (Empty if no conversations match)
        '''
        result = []

        if f is None:
            f = lambda x:True

        if not funcs.isiterable(name):
            name = name,
        if not funcs.isiterable(type):
            type = type,
        if not funcs.isiterable(count):
            count = count,

        functions = [f]

        def namechecker(c):
            mynames = set(name)
            cnames  = set(c.buddies)

            mynames.discard(self.self_buddy.name)
            cnames. discard(self.self_buddy.name)

            return mynames == cnames

        if name: functions.append(namechecker)

        def typechecker(c):
            return c.type in type

        if type: functions.append(typechecker)

        def countchecker(c):
            return len(c.room_list) in count

        if count: functions.append(countchecker)

        import inspect
        log.debug('find_convo: name=%s,count=%s,type=%s,f=%s',
                    name,count,type, inspect.getsource(f).strip())
        for conv in self._convs.values():
            log.debug('%r: names=%r,count=%s,type=%s,id=%s',
                        conv, conv.buddies, len(conv.room_list), conv.type, id(conv))
            if all(_f(conv) for _f in functions):
                result.append(conv)

        return result
