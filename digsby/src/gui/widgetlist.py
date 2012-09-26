'''

GUI for showing a list of widgets.

'''

import wx

from gui.anylists import AnyRow, AnyList
import common

class WidgetRow(AnyRow):

    checkbox_border = 3
    row_height = 24
    image_offset = (6, 5)

    def __init__(self, parent, widget):
        AnyRow.__init__(self, parent, widget, use_checkbox = True)

        self.Bind(wx.EVT_CHECKBOX, self.on_check)

    def on_check(self, e):
        row    = e.EventObject.Parent
        widget = row.data
        widget.set_enabled(row.IsChecked())

    def PopulateControls(self, widget):
        self.text = widget.title
        self.checkbox.Value = widget.on

    @property
    def image(self):
        return None

    @property
    def popup(self):
        if hasattr(self, '_menu') and self._menu: self._menu.Destroy()
        from gui.uberwidgets.umenu import UMenu
        menu = UMenu(self)
        if not self.data.type == 'fb':
            menu.AddItem(_('&Edit'),   callback = lambda: self.on_edit())
        menu.AddItem(_('&Delete'), callback = lambda: self.on_delete())
        menu.AddSep()
        common.actions.menu(self, self.data, menu)

        self._menu = menu
        return menu


    def ConstructMore(self):

        # Extra component--the edit hyperlink

        if not self.data.type == 'fb':
            edit = self.edit = wx.HyperlinkCtrl(self, -1, _('Edit'), '#')
            edit.Hide()
            edit.Bind(wx.EVT_HYPERLINK, lambda e: self.on_edit())
            edit.HoverColour = edit.VisitedColour = edit.ForegroundColour

        remove = self.remove = wx.HyperlinkCtrl(self, -1, _('Delete'), '#')
        remove.Hide()
        remove.Bind(wx.EVT_HYPERLINK, lambda e: self.on_delete())
        remove.HoverColour = remove.VisitedColour = remove.ForegroundColour

    def LayoutMore(self, sizer):
        sizer.AddStretchSpacer()
        if not self.data.type == 'fb':
            sizer.Add(self.edit, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

        sizer.Add(self.remove, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

class WidgetList(AnyList):
    'Widgets list.'

    def __init__(self, parent, widgets, edit_buttons = None):
        AnyList.__init__(self, parent, widgets,
                         row_control = WidgetRow,
                         edit_buttons = edit_buttons,
                         draggable_items = False)
        Bind = self.Bind
        Bind(wx.EVT_LISTBOX_DCLICK, self.on_doubleclick)
        Bind(wx.EVT_LIST_ITEM_FOCUSED,self.OnHoveredChanged)

    def on_doubleclick(self, e):


        self.on_edit(self.GetDataObject(e.Int))

    def on_edit(self, widget):

        if widget.type == 'fb':
            return

        widget.edit()



    def OnHoveredChanged(self,e):
        row = self.GetRow(e.Int)



        if row:
            if row.IsHovered():
                if not row.data.type == 'fb':
                    row.edit.Show()
                row.remove.Show()
                row.Layout()
                row.Refresh()
            else:
                if not row.data.type == 'fb':
                    row.edit.Hide()
                row.remove.Hide()
                row.Layout()

    def OnDelete(self, widget):
        'Called when the minus button above this list is clicked.'

#        widget = self.GetDataObject(self.Selection)
        if not widget: return

        # Display a confirmation dialog.
        message = _('Are you sure you want to delete widget "{widgetname}"?').format(widgetname=widget.title)
        caption = _('Delete Widget')
        style   = wx.ICON_QUESTION | wx.YES_NO
        parent  = self

        if wx.MessageBox(message, caption, style, parent) == wx.YES:
            widget.delete()

    def OnNew(self, e = None):
        'Called when the plus button above this list is clicked.'

        wx.LaunchDefaultBrowser("http://widget.digsby.com")

#        from digsby.widgets import create
#        create()

