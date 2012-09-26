from util.observe import Observable
from util.primitives.funcs import do

class SlotsSavable(object):
    '''
    Prereqs:

    1) use slots
    2) only store persistent information in slots
    3) child objects stored in slots must also be SlotSavable (or pickleable)
    '''

    def __getstate__(self):
        return dict((k, getattr(self, k)) for k in self.__slots__)

    def __setstate__(self, info):
        do(setattr(self, key, info.get(key, None)) for key in self.__slots__)

    def __eq__(self, s):
        try:
            return all(getattr(self, attr) == getattr(s, attr) for attr in self.__slots__)
        except Exception:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        val = 0
        for child in [getattr(self, slot) for slot in self.__slots__]:
            if isinstance(child, list):
                for c in child:
                    val ^= c.__hash__()
            elif isinstance(child, dict):
                for k,v in child.iteritems():
                    val ^= v.__hash__()
            else:
                val ^= child.__hash__()
        return val


class ObservableSlotsSavable(SlotsSavable, Observable):
    '''
    Prereqs:

    1) use slots
    2) only store persistent information in slots
    3) child objects stored in slots must also be SlotSavable (or pickleable)
    '''
    def __init__(self):
        Observable.__init__(self)

    def __setstate__(self, info):
        if not hasattr(self, 'observers'):
            Observable.__init__(self)

        return SlotsSavable.__setstate__(self, info)
