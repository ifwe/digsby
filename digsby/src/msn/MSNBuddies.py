from MSNBuddy import MSNBuddy, CircleBuddy
from util.observe import ObservableDict

from common.sms import *

import util
import util.primitives.funcs as funcs
from logging import getLogger
log = getLogger('msn.buddiesdict')

class MSNBuddies(ObservableDict):
    DefaultClass = MSNBuddy
    '''
    A custom dictionary that will always return an MSNBuddy, even if it
    did not exist when it was asked for.
    '''
    def __init__(self, protocol):
        '''
        MSNBuddies(msnobj)

        Create a new MSNBuddies dictionary with msnobj as the owner of all
        buddies that will be in this dictionary

        @param protocol    this dictionaries owner
        '''
        ObservableDict.__init__(self)
        self.protocol = protocol

    def __getitem__(self, buddy):
        '''
        This is where the magic happens -- if the buddy does not exist,
        then a new 'blank' buddy will be returned with only the name and
        protocol set.

        @param buddy    the name to use for the buddy
        '''
        if not buddy: raise NameError

        if (util.is_email(buddy) and self in (self.protocol.buddies, self.protocol.circle_buddies)):
            try:
                return dict.__getitem__(self, buddy)
            except KeyError:
                return self.setdefault(str(buddy),
                                       self.DefaultClass(name=buddy, msn=self.protocol))
        else:
            is_sms = validate_sms(buddy)
            is_int = funcs.isint(buddy)

            if (is_sms or is_int) and self is self.protocol.m_buddies:
                try:
                    return dict.__getitem__(self, buddy)
                except KeyError:
                    return dict.setdefault(self, str(buddy),
                                           self.DefaultClass(name=buddy, msn=self.protocol))

        log.critical('Unknown buddy was requested: %r, %r', type(buddy), buddy)
        raise KeyError(buddy)

    def __delitem__(self, buddy):
        '''
        Delete an item from this dictionary
        '''
        return dict.__delitem__(self, str(buddy))

    def __contains__(self, buddy):
        '''
        Check if a buddy is in the dictionary
        '''
        return dict.__contains__(self, str(buddy))

class CircleBuddies(MSNBuddies):
    DefaultClass = CircleBuddy
