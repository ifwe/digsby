from traceback import print_exc
import wx

BLIST_ITEM_DATAOBJECT_FMT = 'BuddyListItem'

_df = None
def dataformat():
    global _df
    if _df is None:
        _df = wx.CustomDataFormat(BLIST_ITEM_DATAOBJECT_FMT)
    return _df


def dataobject():
    return wx.CustomDataObject(dataformat())

def add_to_dataobject(data, blist_item):
    '''
    given a buddylist item, potentially adds a wx.CustomDataObject to the given
    wx.DataObjectComposite
    '''

    if hasattr(blist_item, 'idstr'):
        try:
            strdesc = blist_item.idstr()
            if isinstance(strdesc, unicode): strdesc = strdesc.encode('utf8')
        except Exception:
            print_exc()
        else:
            obj = dataobject()
            obj.SetData(strdesc)
            data.Add(obj)

    # TextDataObject for buddy name
    try:
        name = unicode(getattr(blist_item, 'alias', blist_item.name)).encode('utf-8')
        tdata = wx.TextDataObject(name)
    except Exception:
        print_exc()
    else:
        data.Add(tdata)

