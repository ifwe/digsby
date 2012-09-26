from util.primitives.funcs import isiterable
from common.actions import ActionMeta

class BuddyListElement(object):

    __metaclass__ = ActionMeta

    @property
    def num_online(self):
        from Contact import Contact
        if isiterable(self) and not isinstance(self, Contact):
            return sum(elt.num_online for elt in self)
        else:
            return int(self.online)

    def find(self, obj):
        assert isinstance(self, list)
        return list.find(self, obj)

    def chat(self):
        import gui.imwin, wx
        wx.CallAfter(lambda: gui.imwin.begin_conversation(self))
