'''
Some tools to convert a .plist into python objects. Incomplete.

TODO: add load(s)/dump(s) functions to match the 'data shelving' interfaces of pickle, simplejson, pyyaml, etc.
'''

#_type_map = dict(real    =     (float, 'cdata'),
#                 integer =     (int,   'cdata'),
#                 true    =     (lambda x: True, 'cdata'),
#                 false   =     (lambda x: False, 'cdata'),
#                 data    =     (_from_data, 'cdata'),
#                 array   =     (_to_plist, 'children'),
#                 dict    =
#                 )


def plisttype_to_pytype(plist):
    type = plist._name
    transformer = globals().get('plist_to_%s' % type, None)
    if transformer is not None:
        return transformer(plist)
    else:
        return plist

def _from_data(cdata):
    return cdata.decode('base64')

def _to_data(data):
    return data.encode('base64')

def plist_to_real(plist):
    return float(plist._cdata)

def plist_to_string(plist):
    return unicode(plist._cdata)

def plist_to_array(plist):
    return map(plisttype_to_pytype, plist._children)

def plist_to_dict(plist):
    result = {}
    key = None
    value = None
    for child in plist._children:
        if child._name == 'key':
            key = child._cdata
        else:
            value = plisttype_to_pytype(child)
            result[key] = value
            key = value = None
    return result

