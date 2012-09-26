"""
imwin_native.py

This file contains the code needed for the 'native', that is, not skinned, version of the
IM window.

Blame Rests With: Kevin Ollivier
"""

import sys

import wx
import wx.lib.flatnotebook as fnb
import wx.lib.newevent

from wx.lib import pubsub

import actionIDs

import gui
import gui.imwin.imtabs
import gui.imwin.imwin_gui as imwin_gui

from gui import capabilitiesbar
from gui import skin
from gui.addcontactdialog import AddContactDialog
from gui.filetransfer import FileTransferDialog
from gui.uberwidgets.uberbook.OverlayImage import OverlayImage
from gui.windowfx import fadein

buttonIDs = {
                'info': actionIDs.InfoMode,
                'im': actionIDs.IMMode,
                'email': actionIDs.EmailMode,
                'video': actionIDs.CallMode,
            }

FlatNotebookDragStarted, EVT_FNB_DRAG_STARTED = wx.lib.newevent.NewCommandEvent()

class NativeDragTimer(wx.Timer):
    """
        A timer handling the movement of the tab preview, Dropmarker hiding,
        and showing of hidden tabbars when dragged over a window.
    """
    def __init__(self, source):
        wx.Timer.__init__(self)
        self.source = source

    def Notify(self):
        """
            On the trigger time does D&D operations
        """

        if not wx.LeftDown():
            self.Stop()
            self.source.OnDragFinish()
        else:
            self.source.OnDragging()

class FrameDragManager(wx.EvtHandler):
    """
    Used to manage the drag overlay preview image and alert a callback to a drag finished event.
    Designed to be reusable across various frame classes.
    """
    def __init__(self, frame):
        wx.EvtHandler.__init__(self)
        self.frame = frame
        self.dragtimer = NativeDragTimer(self)
        self.draggedidx = -1
        self.dragimage = None
        self.dragwindow = None
        self.callback = None
        # since we take a snapshot of the whole window,
        # we need to know where the mouse is in that window
        self.mousePosOffset = None

    def StartDrag(self, callback = None, draggedidx = -1, dragwindow = None):
        """
        Called when a drag event starts, generates the preview image and sets the drag
        finished callback function.
        """
        self.mousePos = wx.GetMousePosition()
        self.draggedidx = draggedidx
        self.dragtimer.Start(1)
        screendc = wx.ScreenDC()

        self.mousePosOffset = self.mousePos - self.frame.GetScreenRect().GetPosition()

        if dragwindow:
            self.dragwindow = dragwindow
            self.dragwindow.Move(wx.GetMousePosition() - self.mousePosOffset)
        else:
            dragimage = screendc.GetAsBitmap().GetSubBitmap(self.frame.GetScreenRect())
            self.dragimage = OverlayImage(self.frame, dragimage, size=(dragimage.GetWidth(), dragimage.GetHeight()))

        if self.dragimage:
            self.dragimage.SetTransparent(172)
            self.dragimage.Move(wx.GetMousePosition() - self.mousePosOffset)

            self.dragimage.Show()

        self.callback = callback

    def OnDragging(self):
        """
        Update the dragging image as the mouse moves
        """
        pos = wx.GetMousePosition() - self.mousePosOffset
        if self.dragimage:
            self.dragimage.Move(pos)

        if self.dragwindow:
            self.dragwindow.Move(pos)

    def OnDragFinish(self):
        """
        Remove the drag image and call the drag finished callback to process the drag.
        """
        if self.dragimage:
            self.dragimage.Hide()
            self.dragimage.Destroy()
            self.dragimage = None

        self.callback(draggedidx=self.draggedidx)

class NativeIMFrameEventHandler(wx.EvtHandler):
    """
    Controller class for the native version of ImFrame. Using controllers helps us to
    separate (and sometimes share) logic between native and skinned versions.
    """
    def __init__(self, frame):
        wx.EvtHandler.__init__(self)
        self.frame = frame
        self.dragManager = FrameDragManager(self.frame)
        self.frameID = self.frame.GetId()
        self.potentialNewWin = None

        self.BuildToolBar()
        self.BindEventsToFrame()

    def BindEventsToFrame(self):
        """
        Any events the native IM frame should always handle (i.e. even when inactive) should be connected here.
        """
        self.frame.Bind(wx.EVT_ACTIVATE, self.OnActivate)
        self.frame.Bind(wx.EVT_CLOSE, self.OnClose)
        self.frame.notebook.Bind(EVT_FNB_DRAG_STARTED, self.OnFNBTabDragStart)

        publisher = pubsub.Publisher()
        publisher.subscribe(self.OnPageTitleUpdated, 'tab.title.updated')
        publisher.subscribe(self.OnPageIconUpdated, 'tab.icon.updated')

    def OnActivate(self, event):
        """
        Only sign up this frame to handle toolbar/menu events when it's the active frame.
        """
        event.Skip()
        if event.Active:
            self.ConnectToolBarEvents()
        else:
            self.DisconnectToolBarEvents()

    def OnClose(self, event):
        """
        Disconnect any notifications we have in place.
        """

        if self.frame.CloseAndSaveState(event):
            publisher = pubsub.Publisher()
            publisher.unsubscribe(self.OnPageTitleUpdated, 'tab.title.updated')
            publisher.unsubscribe(self.OnPageIconUpdated, 'tab.icon.updated')

            self.DisconnectToolBarEvents()

            self.frame.Destroy()
            del self
        else:
            event.Veto()

    # ---- Drag Handling ----
    def OnFNBTabDragStart(self, event):
        """
        Called when a drag is initiated on a FlatNotebook tab.
        """

        if self.frame.notebook.GetTabCount() > 1:
            newpos = wx.GetMousePosition()
            newpos[1] = newpos[1] - self.frame.Size.height
            newwin = gui.imwin.imtabs.ImFrame(pos = newpos, size = self.frame.Size)
            newwin.SetTransparent(123)

            page = self.frame.notebook.GetPage(event.draggedidx)
            newwin.AddTab(page, False)
            newwin.ShowNoActivate(True)
            self.potentialNewWin = newwin
        else:
            self.frame.SetTransparent(123)
            newwin = self.potentialNewWin = self.frame

        self.dragManager.StartDrag(self.OnDragFinish, event.draggedidx, dragwindow = newwin)

    def OnDragFinish(self, draggedidx):
        """
        Called when a drag completes. Determine whether to create a new IM window, add a tab, etc.
        and handle destruction of the current frame if all notebook frames are gone.
        """

        assert draggedidx != -1

        # FIXME: Really the drop targets themselves should respond to the event IMHO.
        # Not sure what the proper way of notifying the app that a target was dropped on "desktop space"
        # is though.
        pos = wx.GetMousePosition()

        for imframe in gui.imwin.imtabs.all_imframes():
            notebook = imframe.notebook
            localcoords = notebook._pages.ScreenToClient(pos)
            notebook._pages._isdragging = True
            where = notebook._pages.HitTest(localcoords)[0]
            notebook._pages._isdragging = False
            if not imframe == self.potentialNewWin and where == fnb.FNB_TAB:
                # this is ugly, but having external DND handling requires us to fiddle with the class internals
                page = self.frame.notebook.GetPage(draggedidx)
                imframe.AddTab(page, True)
                self.potentialNewWin.Destroy()
                break

        else:
            fadein(self.potentialNewWin, 'normal')
            self.potentialNewWin.Raise()

        self.frame.notebook.RemovePage(draggedidx)

    # ---- Toolbar handling ----

    def BuildToolBar(self):
        """
        Create the toolbar for the native IM window frame.
        """
        toolbar = self.frame.CreateToolBar()

        s = lambda name, d = None: skin.get('AppDefaults.FormattingBar.%s' % name, d)
        icons = s('icons').get
        actionIcons = skin.get('ActionsBar.Icons')

        iconsize = (24, 24)
        eicon = icons('emote').Resized(iconsize)

        toolbar.AddLabelTool(actionIDs.BuddyOptions, "Buddy", wx.EmptyBitmap(32, 32))
        toolbar.AddLabelTool(actionIDs.Files, "Files", getattr(actionIcons, 'files').Resized(iconsize))
        toolbar.AddSeparator()

        app = wx.GetApp()
        for attr, title, tooltip in capabilitiesbar.buttons:
            if attr in ["files", "sms", "video"]:
                continue
            baricon = getattr(actionIcons, attr).Resized(iconsize)
            buttonID = buttonIDs[attr]
            toolbar.AddLabelTool(buttonID, title, baricon)
            app.AddHandlerForID(buttonID, self.OnModeClicked)

        toolbar.AddSeparator()
        toolbar.AddLabelTool(actionIDs.SetFont, "Font", getattr(actionIcons, "font").Resized(iconsize))
        toolbar.AddLabelTool(actionIDs.SetBackgroundColor, "Bg Color", getattr(actionIcons, "background").Resized(iconsize))
        toolbar.AddLabelTool(actionIDs.ChooseEmoticon, "Emoticon", eicon)

        toolbar.AddSeparator()

        toolbar.AddLabelTool(actionIDs.AddContact, "Add Contact", getattr(actionIcons, "addcontact").Resized(iconsize))
        toolbar.AddLabelTool(actionIDs.ViewPastChats, "View Past Chats", getattr(actionIcons, "viewpastchats").Resized(iconsize))
        toolbar.AddLabelTool(actionIDs.AlertMeWhen, "Alert Me When", getattr(actionIcons, "alertmewhen").Resized(iconsize))

        toolbar.Realize()

    def ConnectToolBarEvents(self, event=None):
        """
        Used to dynamically connect event handlers to the frame."
        """
        app = wx.GetApp()
        app.AddHandlerForID(actionIDs.SetFont, self.OnFontClicked)
        app.AddHandlerForID(actionIDs.SetBackgroundColor, self.OnBCToolClicked)
        app.AddHandlerForID(actionIDs.ChooseEmoticon, self.OnEmoteToolClicked)
        app.AddHandlerForID(actionIDs.AddContact, self.OnAddContact)
        app.AddHandlerForID(actionIDs.ViewPastChats, self.OnViewPastChats)
        app.AddHandlerForID(actionIDs.AlertMeWhen, self.OnAlert)
        app.AddHandlerForID(actionIDs.Files, self.OnFilesClicked)
        app.AddHandlerForIDs(buttonIDs.values(), self.OnModeClicked)

        app.AddHandlerForID(actionIDs.FileTransferHistory, self.OnFileTransferHistory)
        app.AddHandlerForID(actionIDs.SendFile, self.OnSendFile)

    def DisconnectToolBarEvents(self, event=None):
        """
        Used to remove event handlers from the frame.
        """
        app = wx.GetApp()
        app.RemoveHandlerForID(actionIDs.SetFont)
        app.RemoveHandlerForID(actionIDs.SetBackgroundColor)
        app.RemoveHandlerForID(actionIDs.ChooseEmoticon)
        app.RemoveHandlerForID(actionIDs.AddContact)
        app.RemoveHandlerForID(actionIDs.ViewPastChats)
        app.RemoveHandlerForID(actionIDs.AlertMeWhen)
        app.RemoveHandlerForID(actionIDs.Files)
        app.RemoveHandlerForIDs(buttonIDs.values())

    def OnAddContact(self, event):
        """
        Show the add contact dialog.
        """
        if self.frame.notebook.ActiveTab:
            buddy = self.frame.notebook.ActiveTab.Buddy
            AddContactDialog.MakeOrShow(service = buddy.service, name = buddy.name)

    def OnViewPastChats(self, event):
        """
        Load up the active buddy's past chats.
        """

        # FIXME: Why is this stuff gotten through IMControl?
        if self.frame.notebook.ActiveTab:
            im_control = self.frame.notebook.ActiveTab.IMControl
            im_control.Buddy.view_past_chats(im_control.Account)

    def OnPageIconUpdated(self, message):
        """
        Update the notebook when a convo's icon changes.
        """

        page = message.data[0]
        icon = message.data[1]

        # FIXME: This should probably be part of the notebook
        if self.frame:
            assert getattr(self.frame.notebook, "_name", "") != "[unknown]"
            #sys.stderr.write("icon = %r\n" % icon)
            for pagenum in xrange(self.frame.notebook.GetPageCount()):
                if self.frame.notebook.GetPage(pagenum) == page:
                    self.frame.notebook.UpdatePageImage(pagenum, icon)
                    self.frame.ToolBar.SetToolNormalBitmap(actionIDs.BuddyOptions, icon.Resized((32, 32)))

            if self.frame.notebook.ActiveTab == page:
                self.frame.SetFrameIcon(icon)

    def OnPageTitleUpdated(self, message):
        """
        Update the frame and notebook when a convo's name and/or typing status changes
        """
        page = message.data[0]
        title = message.data[1]
        window_title = message.data[2]

        if self.frame:
            assert getattr(self.frame.notebook, "_name", "") != "[unknown]"
            pageInNotebook = False
            for pagenum in xrange(self.frame.notebook.GetPageCount()):
                if self.frame.notebook.GetPage(pagenum) == page:
                    self.frame.notebook.SetPageText(pagenum, title)
                    pageInNotebook = True

            if pageInNotebook:
                if window_title:
                    self.frame.SetTitle(self.frame.WindowName + ' - ' + window_title)
                else:
                    self.frame.SetTitle(self.frame.WindowName + ' - ' + title)

    def OnAlert(self, event):
        """
        Show alert preferences
        """
        gui.pref.prefsdialog.show('notifications')

    def OnFilesClicked(self, event):
        """
        Show popup menu for Files button
        """
        popup = wx.Menu()

        popup.Append(actionIDs.SendFile, _('Send File'))
        popup.Append(actionIDs.FileTransferHistory, _('Transfer History'))

        self.frame.PopupMenu(popup, self.frame.ScreenToClient(wx.GetMousePosition()))

    def OnSendFile(self, event):
        """
        Load up the active buddy's past chats.
        """

        # FIXME: Why is this stuff gotten through IMControl?
        if self.frame.notebook.ActiveTab:
            im_control = self.frame.notebook.ActiveTab.IMControl
            im_control.Buddy.send_file()

    def OnFileTransferHistory(self, event):
        FileTransferDialog.Display()

    def OnModeClicked(self, event):
        """
        Toggle between IM/Info/Email/Video panes
        """
        eventid = event.GetId()
        for name in buttonIDs:
            if buttonIDs[name] == eventid:
                self.frame.notebook.ActiveTab.set_mode(name, toggle_tofrom = True)
                break

    def OnFontClicked(self, event):
        """
        Show the font dialog
        """
        self.frame.notebook.ActiveTab.input_area.ShowModalFontDialog()

    def OnBCToolClicked(self, event):
        """
        Set the background color for messages
        """
        tc = self.frame.notebook.ActiveTab.input_area.tc
        newcolor = wx.GetColourFromUser(self.frame, tc.BackgroundColour, _('Choose a background color'))

        if newcolor.IsOk():
            #input_area.tc.BackgroundColour = newcolor
            attrs = tc.GetDefaultStyle()
            attrs.SetBackgroundColour(newcolor)
            tc.SetDefaultStyle(attrs)

        tc.Refresh()
        self.frame.notebook.ActiveTab.FocusTextCtrl()

    def OnEmoteToolClicked(self, event):
        """
        Show emoticon picker
        """
        wx.MessageBox("Not working yet. (need to decide the best way to share code between this and the formattinb bar) Just type smileys by hand, it won't hurt. ;)")
        #input_area = self.frame.notebook.ActiveTab.input_area
        #point = wx.GetMousePosition()
        #input_area.DisplayEmotibox(wx.Rect(point.x, point.y, 16, 16))

class DigsbyFlatNotebook(fnb.FlatNotebook):
    """
    Version of FlatNotebook customized for Digsby to match UberBook impl. and so that we can use our own DND logic.
    """

    def __init__(self, *args, **kwargs):
        fnb.FlatNotebook.__init__(self, *args, **kwargs)

        self.imageList = wx.ImageList(16, 16)
        self.SetImageList(self.imageList)

        # FNB overrides needed for DND
        self.isDragging = False
        self._pages.Bind(wx.EVT_MOTION, self.OnNotebookMouseMove)

    def OnNotebookMouseMove(self, event):
        """
        Determine whether a drag has started or finished and fire an event if so.
        """
        where, tabidx = self._pages.HitTest(event.GetPosition())
        if event.Dragging() and where == fnb.FNB_TAB:
            if not self.isDragging:
                assert tabidx != -1
                event = FlatNotebookDragStarted(self.GetId(), draggedidx=tabidx)
                self.ProcessEvent(event)
                self.isDragging = True

        else:
            if self.isDragging:
                self.isDragging = False

        event.Skip()

    def Pages(self):
        """
        Page iterator needed for compatibility with UberBook impl.
        """
        pagelist = []
        for page in xrange(self.GetPageCount()):
            pagelist.append(self.GetPage(page))

        return pagelist

    def Add(self, ctrl, focus = None):
        """
        Needed for compatibility w/ UberBook impl., adds the tab and fires off title and icon updated events.
        """
        ctrl.show_actions_bar = False
        page = self.AddPage(ctrl, "Chat Name", select = focus)
        ctrl.update_title()
        ctrl.update_icon()
        return page

    def Insert(self, ctrl):
        """
        Needed for compatibility w/UberBook, here it is the same as Add.
        """
        self.Add(ctrl, False)

    def IndexForPage(self, ctrl):
        """
        Retrieve the index for a particular control, or -1 if not found.
        """
        for index in xrange(self.GetPageCount()):
            if ctrl == self.GetPage(index):
                return index

        assert False
        return -1

    def Remove(self, ctrl):
        """
        Remove the control from the notebook.
        """
        index = self.IndexForPage(ctrl)
        assert index >= 0
        self.RemovePage(index)

    def GetTabCount(self):
        """
        Needed for compatibility w/ UberBook impl, calls GetPageCount.
        """
        return self.GetPageCount()

    @property
    def ActiveTab(self):
        """
        Property that returns the selected NoteBook page, or None if there isn't one.
        """
        sel = self.GetSelection()
        if sel != -1:
            return self.GetPage(sel)
        elif self.GetPageCount() > 0:
            return self.GetPage(0)

        return None

    def UpdatePageImage(self, pagenum, icon):
        """
        Update the tab's image - we need to also update it in the imageList.
        """
        imageList = self.GetImageList()
        iconnum = pagenum
        if pagenum >= imageList.GetImageCount():
            imageList.Add(icon.Resized((16, 16)))
            iconnum = imageList.GetImageCount() - 1
        else:
            imageList.Replace(pagenum, icon.Resized((16, 16)))

        self.SetPageImage(pagenum, iconnum)

class NativeNotebookPanel(wx.Panel):
    """
    Top level panel for ImFrame that contains all controls the native version needs within it.
    """
    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)

        style = fnb.FNB_X_ON_TAB | fnb.FNB_ALLOW_FOREIGN_DND | fnb.FNB_NODRAG | fnb.FNB_BOTTOM | fnb.FNB_FANCY_TABS | fnb.FNB_NO_X_BUTTON
        self.notebook = DigsbyFlatNotebook(self, wx.ID_ANY, style=style)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.notebook, 1, wx.EXPAND)

        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnNotebookPageChanged)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CLOSED, self.OnNotebookPageClosed)

        self.Pages = self.notebook.Pages
        self.ActiveTab = self.notebook.ActiveTab

    def OnNotebookPageClosed(self, event):
        if self.notebook.GetPageCount() == 0:
            tlw = wx.GetTopLevelParent(self.notebook)
            tlw.Close()
            return

    def OnNotebookPageChanged(self, event):
        """
        Fire notifications so that the frame can handle changes to the active convo.
        """
        page = self.notebook.GetPage(event.GetSelection())

        icon = imwin_gui.icons.get(page.icontype, 'buddy')(page.Buddy)
        pubsub.Publisher().sendMessage(('tab', 'icon', 'updated'), (page, icon))
        pubsub.Publisher().sendMessage(('tab', 'title', 'updated'), (page, page.Buddy.alias, None))
