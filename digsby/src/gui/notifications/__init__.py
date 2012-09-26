from __future__ import with_statement

from gui import skin
from util import odict, odict_from_dictlist
import syck

def underscores_to_dots(d):
    '''
    YAML syntax does really allow for

        contact.away: stuff

    so we have

        contact_away: stuff

    instead. Turns a dictionary from the second to the first.
    '''

    for key in d.keys()[:]:
        if key and '_' in key:
            d[key.replace('_','.')] = d.pop(key)

