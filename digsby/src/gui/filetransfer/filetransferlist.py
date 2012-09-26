'''

GUI for managing file transfers

'''
from __future__ import with_statement
from __future__ import division

import wx
from wx import Point, FONTWEIGHT_NORMAL, FONTWEIGHT_BOLD, RectPS, Size, \
    HORIZONTAL, VERTICAL, EXPAND, RIGHT, ALIGN_RIGHT, BOTTOM, TOP, BoxSizer, Colour

import os
from traceback import print_exc

from gui import skin
from gui.skin.skinobjects import SkinColor
from gui.anylists import AnyList, AnyRow
from gui.toolbox import persist_window_pos, check_destroyed, AutoDC, calllimit
from gui.uberwidgets.clearlink import ClearLink
from gui.textutil import default_font
from gui.uberwidgets.UberProgressBar import UberProgressBar
from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.umenu import UMenu
from util.primitives.error_handling import traceguard
from util.primitives.funcs import Delegate
from util.primitives.mapping import Storage as S
from path import path
from common import bind
from common.filetransfer import FileTransfer
from gettext import ngettext
from logging import getLogger; log = getLogger('filetransferlist')



xs = FileTransfer.states

FILEXFER_ICON = 'AppDefaults.NotificationIcons.FileTransfer'

class FTLinkControl(ClearLink):
    def __init__(self, parent, text, on_click=None, should_be_active=None, align='right'):

        self._on_click = Delegate()

        if on_click:
            self._on_click += on_click

        ClearLink.__init__(self, parent, -1, text, on_click, style = wx.NO_BORDER | getattr(wx, 'HL_ALIGN_%s' % align.upper()))
        linkfont = skin.get('filetransfers.fonts.link', default_font)

        self.SetFont(linkfont)

        self._is_active = Delegate(collect_values=True)
        if should_be_active:
            self._is_active += should_be_active

#        self.Bind(wx.EVT_HYPERLINK, on_click)

    def on_click(self, e=None):
        return self._on_click(e)

    def is_active(self):
        return all(self._is_active())


class FileTransferRow(AnyRow):
    '''
    One row in the file transfer manager.
    '''

    update_interval = 1000

    def __init__(self, parent, data):
        self.xfer = data

        self.text = ''

        self.links = {}

        self.UpdateSkin(first = True)
        AnyRow.__init__(self, parent, data, use_checkbox = False, linkobservers = False)

        self.SetMinSize((20, self.MinSize.height))

        self._bc_timer = wx.PyTimer(lambda: wx.CallAfter(self.on_completed_changed, self.xfer, None, None, None))
        self._bc_timer.Start(self.update_interval)

        data.add_gui_observer(self.on_completed_changed, 'completed')
        data.add_gui_observer(self.on_update_gui, 'state')

        if getattr(self.xfer, 'autoremove', False):
            if self.xfer.state in self.xfer.autoremove_states:
                self.on_remove()

    def on_close(self):
        self.data.remove_gui_observer(self.on_completed_changed)
        self.data.remove_gui_observer(self.on_update_gui)
        AnyRow.on_close(self)

    def UpdateSkin(self, first = False):
        s = skin.get('filetransfers')
        self.normalbg         = s.get('backgrounds.normal',[SkinColor(wx.Color(238, 238, 238)),SkinColor(wx.Color(255, 255, 255))])
        self.selectedbg = s.get('backgrounds.selected',SkinColor(wx.Color(180, 180, 180)))
        self.hoveredbg = s.get('backgrounds.hovered',SkinColor(wx.Color(220, 220, 220)))
        self.padding    = s.get('padding', lambda: Point(5, 5))
        self.margins    = s.get('margins', lambda: skin.ZeroMargins)

        if not first:
            with traceguard: self.details.SetFont(skin.get('filetransfers.fonts.other', default_font))

            linkfont = skin.get('filetransfers.fonts.link', default_font)
            for link in self.links.values():
                link.SetFont(linkfont)

            self.layout()
            self.Refresh(False)

    @calllimit(.3)
    def on_update_gui(self, *a):
        if not wx.IsDestroyed(self):
            self.PopulateControls(self.xfer)
            if getattr(self.xfer, 'autoremove', False):
                if self.xfer.state in self.xfer.autoremove_states:
                    self.on_remove()

    @calllimit(.2)
    def on_completed_changed(self, xfer, attr, old, new):
        if wx.IsDestroyed(self):
            return

        sz = xfer.size
        if sz < 1:
            self.pbar.Pulse() # indicate indeterminate progress
        else:
            self.pbar.SetValue(xfer.completed / float(xfer.size) * 100.0)

        try:
            self.on_update_gui()
        except Exception:
            self._bc_timer.Stop()
            print_exc()
        else:
            if xfer.state in xfer.states.TransferringStates:
                self._bc_timer.Start(self.update_interval)
            else:
                self._bc_timer.Stop()

    def construct(self, use_checkbox):
        self.details  = wx.StaticText(self, -1, '')
        with traceguard: self.details.SetFont(skin.get('filetransfers.fonts.other', default_font))
        self.ConstructMore()

    def ConstructMore(self):
        self.pbar = UberProgressBar(self, range = 100, skinkey = 'ProgressBar')
        self.pbar.SetMinSize((50, 13))

        self.right_links = []
        for name, txt, cb, act in self.xfer.get_right_links():

            fn = lambda e = None, nm=name, _cb = cb: (_cb(), getattr(self, 'on_%s'%nm, self._on_default_link)(e))
            ln = FTLinkControl(self, txt, fn, act)
            self.right_links.append(ln)

            assert name not in self.links
            self.links[name] = ln

        self.bottom_links = []

        for name, txt, cb, act in self.xfer.get_bottom_links():

            fn = lambda e = None, nm=name, _cb = cb: (_cb(), getattr(self, 'on_%s'%nm, self._on_default_link)(e))
            ln = FTLinkControl(self, txt, fn, act, align='left')
            self.bottom_links.append(ln)

            assert name not in self.links
            self.links[name] = ln

    def _on_default_link(self, e = None):
        if e is not None:
            log.info("No callback function found for link %r", e.GetEventObject().Label)
        else:
            log.info("Default link callback called.")

    def layout(self):
        self.Sizer = None

        #
        # overrides AnyRow.layout
        #
        sz = BoxSizer(HORIZONTAL)
        p  = self.padding
        links = self.links
        rlinks = self.right_links
        blinks = self.bottom_links

        if self.image:
            sz.AddSpacer((p.x + self.image.Width + p.x, self.row_height))

        v = BoxSizer(VERTICAL)

        topH = BoxSizer(HORIZONTAL)
        topH.AddSpacer((1, self.Parent.fonts.filename.LineHeight), 0, EXPAND)
        topH.AddStretchSpacer(1)
        if rlinks:
            topH.Add(rlinks[0], 0, EXPAND | RIGHT | ALIGN_RIGHT, p.x)

        v.Add(topH, 0, EXPAND | TOP | BOTTOM, p.y)
        v.Add(self.pbar, 0, EXPAND | RIGHT, p.x)

        bottomH = BoxSizer(HORIZONTAL); Add = bottomH.Add
        Add(self.details,    0, EXPAND)
        if blinks:
            for link in blinks:
                Add(link,   0, EXPAND | RIGHT, p.x)

        bottomH.AddStretchSpacer(1)
        if rlinks:
            for link in rlinks[1:]:
                Add(link, 0, EXPAND | RIGHT, p.x)


        v.Add(bottomH, 0, EXPAND | TOP | BOTTOM, p.y)
        sz.Add(v, 1)

        # apply margins
        self.Sizer = self.margins.Sizer(sz)


    def on_open(self, e = None):
        try:
            os.startfile(self.xfer.filepath)
        except WindowsError, e:
            strerror = '%s:\n%s' % (e.strerror, self.xfer.filepath.abspath())
            wx.MessageBox(strerror, _('File not found'), style=wx.OK | wx.ICON_ERROR)


    def on_open_folder(self, e = None):
        xfer = self.xfer
        try:
            xfer.filepath.openfolder()
        except WindowsError, e:
            strerror = '%s:\n%s' % (e.strerror, xfer.filepath.parent.abspath())
            wx.MessageBox(strerror, _('File not found'), style=wx.OK | wx.ICON_ERROR)

    def on_cancel(self, e = None):
        self._bc_timer.Stop()
        wx.CallAfter(self.PopulateControls, self.xfer)

    def on_remove(self, e = None):
        s, sts = self.xfer.state, self.xfer.states
        if s in (sts.CONNECTING, sts.TRANSFERRING):
            return log.info('not removing transfer, state is CONNECTING or TRANSFERRING')

        xfers = self.Parent.data

        log.info('removing transfer %r', xfers)
        xfers.remove(self.xfer)
        log.info('transfers: %r', xfers)

        self._bc_timer.Stop()
        wx.CallAfter(self.Parent.Layout)

    def on_save(self, e=None, path=None):
        # get default save directory, try to save there - if it fails then fall back to on_saveas
        pass

    def on_saveas(self, e=None):
        # get directory from user and then pass it to on_save
        pass

    def on_reject(self, e=None):
        # reject the file
        pass

    def CalcColors(self, selected = None):
        selected = self.IsSelected() if selected is None else selected

        self.bg = self.selectedbg if selected else self.hoveredbg if self.IsHovered() else self.normalbg[self.Index % len(self.normalbg)] if isinstance(self.normalbg,list) else self.normalbg

        fontcolors = self.Parent.fontcolors
        for ctrl in self.links.values():
            color = getattr(fontcolors, 'link' + ('selected' if selected else ''))
            if isinstance(color, Colour):
                ctrl.SetForegroundColour(color)

    def PaintMore(self, dc):

        p    = self.padding
        xfer = self.xfer
        fonts, fontcolors = self.Parent.fonts, self.Parent.fontcolors
        iconsize = 16

        selected = self.IsSelected()
        def col(name):
            return getattr(self.Parent.fontcolors, name + ('selected' if selected else ''))

        states = xfer.states

        if xfer.state in (states.TRANSFERRING, states.WAITING_FOR_YOU, states.WAITING_FOR_BUDDY) and getattr(xfer, 'use_serviceicon', True):
            icon = xfer.buddy.serviceicon.Resized(iconsize)

            if self.pbar.Shown:
                r    = self.pbar.Rect
                x, y = r.Right - icon.Width, r.Top - icon.Height - p.y
            else:
                r    = self.ClientRect.AddMargins(self.margins)
                x, y = r.Right - icon.Width - p.y, r.Top + p.y

            dc.DrawBitmap(icon, x, y, True)

        if self.text:
            fontcolors = self.Parent.fontcolors
            cr    = self.ClientRect
            pp    = cr.TopLeft + Point(p.x * 2 + self.Parent.filetype_icon_size, p.y)

            first_shown_rlink = ([x for x in self.right_links if x.IsShown()] or [None])[0]
            if first_shown_rlink is not None:
                _move_width = first_shown_rlink.Size.width
            else:
                _move_width = iconsize

            mainw = cr.width - pp.x - p.x*2 - _move_width

            f = self.Parent.fonts.filename

            drect = RectPS(pp, Size(mainw, f.Height))
            f.Weight = FONTWEIGHT_BOLD
            dc.Font = f

            w, h = dc.GetTextExtent(self.text)
            dc.TextForeground = col('filename')
            dc.DrawTruncatedText(self.text, drect)

            if drect.width:
                dc.Font = fonts.filename
                f = dc.Font
                f.Weight = FONTWEIGHT_NORMAL
                dc.Font = f

                drect.Subtract(left = w)
                dc.TextForeground = col('filename')
                dc.DrawTruncatedText(self.buddytext_Label, drect)

        if self.details_Label:
            dc.Font = self.details.Font

            details = self.details
            for link in self.right_links[::-1]:
                if link.IsShown():
                    r = link.Position + Point(-p.x, link.Size.height)
                    break
            else:
                r = self.Rect.BottomRight - p


            drect = RectPS(details.Position, wx.Size(r.x - details.Position.x, details.Size.height))
            dc.TextForeground = col('other')
            dc.DrawTruncatedText(self.details_Label, drect)

    def draw_text(self, dc, x, sz):
        pass

    @property
    def BuddyText(self):
        dir, name = self.xfer.direction, self.xfer.buddy.name

        if  dir == 'incoming':
            return ' from %s' % name
        else:
            return ' to %s' % name

    if hasattr(wx.Icon, 'ForFileType'):
        @property
        def image(self):
            if hasattr(self.xfer, 'icon'):
                return self.xfer.icon.Resized(self.Parent.filetype_icon_size)

            # use wxIcon.ForFileType to look up the system icon for a filetype
            fname = self.xfer.filepath if self.xfer.filepath is not None else self.xfer.name

            icon = None
            try:
                ext = path(fname).ext
                icons = self.Parent.filetype_icons

                if ext not in icons:
                    icons[ext] = None # only check for the filetype icon once
                    with traceguard:
                        icon = wx.Icon.ForFileType(ext)
                        if icon is not None and icon.IsOk():
                            icons[ext] = icon.WXB

                icon = icons.get(ext)
            except Exception:
                print_exc()

            if not icon:
                icon = skin.get(FILEXFER_ICON).Resized(self.Parent.filetype_icon_size)

            return icon
    else:
        @property
        def image(self):
            if hasattr(self.xfer, 'icon'):
                return self.xfer.icon.Resized(self.Parent.filetype_icon_size)

            return skin.get(FILEXFER_ICON).Resized(self.Parent.filetype_icon_size)

    def PopulateControls(self, xfer, *a):
        if self.text != xfer.name:
            self.text = xfer.name

        s, states = xfer.state, xfer.states

        for link in self.links.values():
            link.Show(link.is_active())

        self.buddytext_Label = self.BuddyText if xfer.should_show_buddy_name else ''

        self.pbar.Show(xfer.state in states.TransferringStates)
        # XXX: Raise an exception here and it might not show!
        if not getattr(xfer, 'size', None):
            val = 1
        else:
            val = xfer.completed / float(xfer.size) * 100.0

        self.percent_done = val
        self.pbar.SetValue(val)

        self.Layout()
        self.Parent.Layout()
        self.Parent.Refresh()

        self.Parent.update_title()

    @property
    def details_Label(self):
        return self.xfer.details_string

    @property
    def popup(self):
        return self.Parent.xfer_popup

class FileTransferList(AnyList):
    def __init__(self, parent, data):

        self.UpdateSkin(first = True)
        self.filetype_icons = {}

        AnyList.__init__(self, parent, data, row_control = FileTransferRow,
                         draggable_items = False)

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

    @calllimit(.5)
    def update_title(self):
        percent = percent_complete(self.data)
        info    = ('%s - ' % percent) if percent is not None else ''
        if not wx.IsDestroyed(self.Top):
            self.Top.SetTitle(info + _('File Transfers'))

    @property
    def xfer_popup(self):
        list = self
        try:
            return list._popupmenu
        except AttributeError:
            pass

        list._popupmenu = menu = UMenu(self, onshow = self.on_rightclick_show)

        menu.open       = menu.AddItem(_('&Open'), callback = lambda: list._menurow.on_open())
        menu.openfolder = menu.AddItem(_('Open &Containing Folder'), callback = lambda: list._menurow.on_open_folder())
        menu.AddSep()
        menu.remove     = menu.AddItem(_('&Remove'), callback = lambda: list._menurow.on_remove())
        return menu

    def on_rightclick_show(self, *a):
        '''
        Invoked just before the menu is shown.

        Enables/disables items as appropriate for the transfer.
        '''
        row  = self._menurow
        xfer = row.data
        menu = self.xfer_popup

        menu.open.Enable(xfer.allow_open())
        menu.openfolder.Enable(xfer.allow_open_folder())
        menu.remove.Enable(xfer.allow_remove())

    def on_paint(self, e):
        dc = AutoDC(self)
        rect = self.ClientRect
        self.bg.Draw(dc, rect)

    def UpdateSkin(self, first = False):
        skin_get = skin.get

        def g(k, default = sentinel):
            elem = skin_get('FileTransfers.Fonts.%s' % k, default)
            if elem is None: return default()
            else:            return elem

        fonts = self.fonts = S()
        fonts.filename = g('filename', lambda: default_font())
        fonts.other    = g('other', lambda: fonts.filename)
        fonts.link     = g('link', lambda: fonts.filename)

        g = lambda k, default = sentinel: (skin_get('FileTransfers.FontColors.%s' % k, default) or default())

        fontcolors = self.fontcolors = S()
        fontcolors.filename = g('filename', lambda: wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
        fontcolors.other    = g('other', lambda: fontcolors.filename)
        fontcolors.link     = g('link', lambda: wx.BLUE)

        fontcolors.filenameselected = g('filenameselected', lambda: wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
        fontcolors.otherselected    = g('otherselected', lambda: fontcolors.filenameselected)
        fontcolors.linkselected     = g('linkselected', lambda: fontcolors.filenameselected)

        self.filetype_icon_size = 32

        self.bg = skin_get('filetransfers.backgrounds.list', lambda: SkinColor(wx.WHITE))

        if not first: wx.CallAfter(self.Layout)

class FileTransferPanel(wx.Panel):
    def __init__(self, parent, xferlist):
        wx.Panel.__init__(self, parent)
        self.xferlist = xferlist

        self.Sizer = s = wx.BoxSizer(wx.VERTICAL)
        ftlist = FileTransferList(self, xferlist)
        s.Add(ftlist, 1, wx.EXPAND | wx.ALL)

        from gui.uberwidgets.UberBar import UberBar
        bar = self.bar = UberBar(self, skinkey = skin.get('FileTransfers.CleanupTaskBar'), alignment = wx.ALIGN_RIGHT)
        s.Add(self.bar, 0, wx.EXPAND)

        bar.AddStretchSpacer(1)
        self.cleanup = cleanup = UberButton(bar, -1, _('Clean Up'))
        cleanup.Bind(wx.EVT_BUTTON, self.on_cleanup)

        # button disabled when there are no transfers
        cleanup.Enable(bool(xferlist))
        xferlist.add_gui_observer(self.on_xfer)
        self.Bind(wx.EVT_WINDOW_DESTROY, lambda e, w=self: self.xferlist.remove_observer(self.on_xfer) if e.EventObject is w else None)

        bar.Add(cleanup)

    def on_xfer(self, xfers, *a):
        if check_destroyed(self): return
        log.info('ENABLE/DISABLE cleanup button: %r' % xfers)
        self.cleanup.Enable(bool(self.xferlist))

    def on_cleanup(self, e = None):
        xferlist = self.xferlist
        xferlist[:] = [x for x in xferlist if not x.is_done()]

    def UpdateSkin(self):
        self.bar.SetSkinKey(skin.get('FileTransfers.CleanUpTaskBar'))
        wx.CallAfter(self.Layout)
        self.Refresh()




class FileTransferDialog(wx.Frame):

    @staticmethod
    @bind('Global.DownloadManager.ToggleShow')
    def ToggleShow(xfers=None):
        for win in wx.GetTopLevelWindows():
            if isinstance(win, FileTransferDialog):
                return win.Close()

        FileTransferDialog._OpenNewWindow(xfers)

    @staticmethod
    def Display(xfers=None):
        for win in wx.GetTopLevelWindows():
            if isinstance(win, FileTransferDialog):
                win.Show()
                win.Raise()
                return

        FileTransferDialog._OpenNewWindow(xfers)

    @staticmethod
    def _OpenNewWindow(xfers):
        if xfers is None:
            from common import profile
            xfers = profile.xfers

        FileTransferDialog(None, xfers).ShowNoActivate(True)

    def __init__(self, parent, xferlist):
        wx.Frame.__init__(self, parent, title = _('File Transfers'), name = 'File Transfers')
        self.SetFrameIcon(skin.get('AppDefaults.TaskbarIcon'))

        with traceguard:
            from gui.toolbox import snap_pref
            snap_pref(self)

        s   = self.Sizer = wx.BoxSizer(wx.VERTICAL)
        ftp = FileTransferPanel(self, xferlist)
        s.Add(ftp, 1, wx.EXPAND)

        persist_window_pos(self, defaultPos = wx.Point(200, 200), defaultSize = wx.Size(450, 300))

        self.Bind(wx.EVT_CLOSE, self.__OnClose)

    def __OnClose(self, e):
        self.Hide()
        e.Skip()

    def UpdateSkin(self):
        wx.CallAfter(self.Layout)


def percent_complete(xfers):
    '''
    given a list of file transfer objects, returns a string like
    "42% of 6 files" or None if no transfers are active
    '''
    count = totalsize = totalcompleted = 0

    for xfer in xfers:
        size      = getattr(xfer, 'size', -1)
        completed = getattr(xfer, 'completed', None)

        if xfer.is_active() and size >= 0 and completed is not None:
            count += 1
            totalsize += size
            totalcompleted += completed

    if count:
        # average
        if totalsize:
            percent  = (totalcompleted / totalsize) * 100
            files    = ngettext('file', 'files', count)
            percent_str = '%.0f' % percent
        else:
            return 'Unknown Size'

        if percent_str != '0':
            return '%s%% of %d %s' % (percent_str, count, files)
