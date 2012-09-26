import wx

class TagViewer(wx.Frame):
    def __init__(self, t=None, parent=None, id = -1, expand=False, title=None):
        wx.Frame.__init__(self, parent, id, title if title else "TagViewer")
        import gui
        gui.toolbox.persist_window_pos(self, close_method=self.on_close)
        self.content = wx.BoxSizer(wx.VERTICAL)
        self.expand = expand

        #generate new tree control
        tree_id = wx.NewId()
        self.tree = wx.TreeCtrl(self, tree_id)
        self.content.Add(self.tree,1,wx.GROW)

        self.rootId = self.tree.AddRoot('Root')
        if t: self(t)

        self.SetSizer(self.content)
        self.Show(True)

    def __call__(self, child, parent_id=None, label=""):
        parent_id = parent_id or self.rootId
        if label:
            self.tree.AppendItem(parent_id, label)
        child_id = self.tree.AppendItem(parent_id, "<" + child._name +
                                        "".join(' %s="%s"' % (k,v)
                                            for k,v in child._attrs.items()) +
                                            str(">" if child._children or child._cdata else " />"))
        self.tree.AppendItem(child_id, repr(child._ns)) if any(child._ns) else None
        self.tree.AppendItem(child_id, child._cdata) if child._cdata else None
        for c in child:
            id = self(c,child_id)
            if self.expand: self.tree.Expand(id)
        if child._children or child._cdata:
            self.tree.AppendItem(child_id, str("</%s>" % child._name))
        if self.expand:
            self.tree.Expand(child_id)
            self.tree.Expand(self.rootId)
        return child_id

    def on_close(self, e):
        self.Destroy()

def tag_view(t):
    wx.CallAfter(TagViewer, t, expand=True)
