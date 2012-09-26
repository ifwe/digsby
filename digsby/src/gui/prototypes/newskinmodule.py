__metaclass__ = type
from gui import skin as skintree

class SkinProxy(object):
    """
    Simplifies skin lookup by providing a common interface and a easier, common
    fallback system
    """

    #local copy of reference to skin elements, saves lookup time and prevents regeneration of fallbacks


    def __init__(self, skinkey, skindefaults):
        """
        skinkey - were to look for the requested keys in the skintree
        skindefaults - dictionary of defaults if key is not found in the skintree
        """

        self.skinkey = skinkey
        self.skindefaults = skindefaults if skindefaults is not None else {}
        self.localitems = {}

    def __getitem__(self, k):

        #first check the local cache
        if k in self.localitems:
            return self.localitems[k]

        #if not in the local cache look it up in the skintree
        item = skintree.get(".".join([self.skinkey, k]), None) if self.skinkey is not None else None

        #if there is still nothing found, try generating item from the default dict or return None
        if item is None and k in self.skindefaults:
            item = self.skindefaults[k]()

        #store the reference to the item in localitems for faster lookup next time
        self.localitems[k] = item

        return item

    def __setitem__(self, k, i):
        """
        Set a item in the skin locally.
        """
        self.localitems[k] = i


class NewSkinModule(object):
    """
    All new GUI that accesses the skin should inherit from this
    """

    def SetSkinKey(self, skinkey, skindefaults = None):
        """
        Defines where in the skintree to look for skin items
        """

        self.UpdateSkin(skinkey, skindefaults)

    def SetSkinDefaults(self, skindefaults):
        """
        Set the defaults dict for when keys are not defined in the skin
        """

        self.UpdateSkin(defaults = skindefaults)

    def UpdateSkin(self, skinkey=None, skindefaults = None):
        """
        Called by the skin system whenever the skin is changed
        """

        skinproxy = self.GetSkinProxy()

        skin = SkinProxy(skinkey if skinkey is not None else skinproxy.skinkey if skinproxy is not None else None,
                         skindefaults if skindefaults is not None else skinproxy.skindefaults if skinproxy is not None else None)
        self.DoUpdateSkin(skin)

    def DoUpdateSkin(self, skin):
        """
        Called whenever skin is changed, should be overridden by the subclass to
        handle class specific calls that need to happen on skin change
        """
        NotImplementedError('DoUpdateSkin() is not implemented in %s' % self.__class__.__name__)

    def GetSkinProxy(self):
        NotImplementedError('GetSkinProxy() is not implemented in %s' % self.__class__.__name__)

