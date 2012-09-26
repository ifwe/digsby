import wx
from util import import_function, callany

from gui.toolbox import GetTextFromUser


def getinput(obj, parent, needs, callback, **k):
    diag = None
    if hasattr(needs, 'Prompt'):
        diag = needs(parent, obj)


    elif isinstance(needs, basestring) and needs.startswith('@'):
        diag = import_function(needs[1:])(parent, obj)


    if diag is not None:
        diag.Prompt(callback)
        diag.Destroy()
    else:
        if callable(needs):
            needs = needs(obj)

        from pprint import pprint
        pprint(needs)

        if len(needs) == 1 and issubclass(needs[0][0], basestring):
            type, name, default = needs[0]
            val = GetTextFromUser(name, caption = name, default_value = default)
            if val is not None:
                return callback(val)
            return

        FormFrame(obj, parent, needs, callback, **k)


def maketext(self, name = '', default = '', obj = None):
    if default is None:
        default = ''

    if callable(default):
        default = callany(default, obj)
    ctrl = wx.TextCtrl(self.content, -1, name=name, value=default)
    return (name, ctrl)

typetable = { str        : maketext,
              int        : maketext,
              unicode    : maketext, }

class FormFrame(wx.Frame):

    def __init__(self, obj, parent, needs, callback, title = None):

        wx.Frame.__init__( self, parent, title = title or 'Please enter a value' )

        self.content = content = wx.Panel(self)
        content.Sizer = s = wx.FlexGridSizer(0, 2, 15, 15)
        self.callback = callback

        # Throw the object at needs if it's callable

        self.needs = needs

        self.gui_items = [self.gentype(need, obj) for need in self.needs]

        for i, item in enumerate(self.gui_items):
            if i == 0:
                item[1].SetFocus()

            s.Add(wx.StaticText(content, -1, label = _(item[0])), 0, wx.EXPAND | wx.ALL, 3)
            s.Add(item[1], 0, wx.EXPAND | wx.ALL, 3)

        b = wx.Button(content, -1, label = 'Submit')
        b.Bind(wx.EVT_BUTTON, self.getvalues)
        b.SetDefault()


        s.Add(b, 1, wx.EXPAND | wx.ALL, 7)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(content, 1, wx.EXPAND)

        self.Fit()
        self.CenterOnParent()
        self.Show(True)


    def gentype(self, need, obj):
        try:
            return typetable[need[0]](self, *need[1:], **{'obj': obj})
        except KeyError, e:
            raise TypeError("I don't know how to get %r from the user" % need[0])

    def getvalues(self, e):
        vals = []
        for i in range(len(self.gui_items)):
            t = self.needs[i][0] if isinstance(self.needs[i], tuple) else self.needs[i]
            vals.append(t(self.gui_items[i][1].GetValue()))

        self.Show(False)
        self.callback(*vals)
        self.Close()
        self.Destroy()


####Testing####

def printstuff(*stuff):
    for item in stuff:
        print 'type', type(item), 'item', item


if __name__ == '__main__':
    app = wx.PySimpleApp()

    stuff = ((str,"name1","bleh"),
             (int,"name2","45"),
             (str,"name3","bleh3"),)

    def callback():
        print 'yay'

    frame = FormFrame( None, None, callback = printstuff, needs=stuff)
    app.SetTopWindow( frame )
    app.MainLoop()
