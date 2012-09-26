#TODO: This should be replaced with Tenjin templates similar to how Social Networks are handled
'''
List of emails shown in the infobox.
'''

from __future__ import with_statement

import sys, wx
import traceback
from wx import Rect, RectS, BLACK
from datetime import datetime

from gui import skin
from gui.textutil import default_font, CopyFont
from gui.skin.skinobjects import SkinColor
from gui.toolbox import add_image_text
from gui.uberwidgets.pseudosizer import PseudoSizer
from gui.uberwidgets.clearlink import ClearLink
from cgui import SimplePanel
from common import actions, pref
from gui.textutil import GetFontHeight

link_style = wx.NO_BORDER | wx.HL_ALIGN_LEFT | wx.TRANSPARENT_WINDOW

class Header(SimplePanel):
    def __init__(self, parent):
        """
            This is the header for the infobox used when displaying Email or
            Social networks.  Shows the account name and a number of related
            links.
        """

        SimplePanel.__init__(self, parent)
        self.account=None
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.linkage = PseudoSizer()
        self.extralinkage = None
        self.UpdateSkin()

    def SetAccount(self, account):
        """
            Set an account to the header
            Handles unloading the previous acount and setting up the links
            and observer callbacks for the new account
        """

        if account is self.account:
            return

        if self.account is not None:
            try:
                self.account.unobserve_count(self.Refreshxor)
            except NotImplementedError:
                pass
            try:
                self.account.unobserve_state(self.Refreshxor)
            except NotImplementedError:
                pass

        self.account = account
        self.icon    = account.icon.Resized(16)

        # Construct action links
        self.linkage.Clear(True)
        for linkfunc in account.header_funcs:
            link = ClearLink(self, -1, linkfunc[0], lambda l=linkfunc: self.do_link(l),
                             style = link_style, pos = (-400, -400))
            link.NormalColour = link.HoverColour = link.VisitedColour = self.linkfc
            link.Font = self.linkfont
            self.linkage.Add(link)

        self.linkage.Layout()

        if self.extralinkage:
            self.extralinkage.Show(False)
            self.extralinkage.Destroy()
            self.extralinkage = None

        if getattr(account, 'extra_header_func', None) is not None:
            self.extralinkage = elink =  ClearLink(self, -1, account.extra_header_func[0], lambda l=account.extra_header_func: self.do_link(l),
                                          style = link_style, pos = (-400, -400))

            elink.NormalColour = elink.HoverColour = elink.VisitedColour = self.linkfc
            elink.Font = self.elinkfont

            self.ExtraLinkLayout()




        try:
            self._unbound_cbs.clear()
        except AttributeError:
            pass

        try:
            account.observe_count(self.Refreshxor)
        except NotImplementedError:
            pass
        try:
            account.observe_state(self.Refreshxor)
        except NotImplementedError:
            pass


        self.Refresh(False)

    def OnSize(self, event):
        event.Skip()
        self.ExtraLinkLayout()

    def ExtraLinkLayout(self):
        elink = self.extralinkage
        if elink is not None:
            elink.Size = elink.BestSize
            elinkposx = self.Size.width - self.padding[0] - elink.BestSize.width
            elinkposy = self.headerfont.Height+2*self.padding[1]
            elink.SetPosition((elinkposx, elinkposy))

    def do_link(self, link):
        if len(link) > 2:
            if link[2]: #False == don't hide
                wx.GetTopLevelParent(self).Hide()
        else:
            wx.GetTopLevelParent(self).Hide()

        if callable(link[1]):
            link[1]()
        else:
            wx.LaunchDefaultBrowser(link[1])


    def Refreshxor(self, *a):
        """
           Just a wrapper for refresh, used instead of a lambda so there's a
           function to unbind later
        """

        self.Refresh(False)

    def UpdateSkin(self):
        self.padding    = wx.Point(4, 4)

        self.headerfont = skin.get('infobox.fonts.header',lambda: default_font())
        self.linkfont   = CopyFont(skin.get('infobox.fonts.link',lambda: default_font()), underline=True)
        self.elinkfont  = CopyFont(self.linkfont, weight=wx.FONTWEIGHT_BOLD)
        self.headerfc=skin.get('infobox.fontcolors.navbarheader', lambda: wx.BLACK)
        self.linkfc=skin.get('infobox.fontcolors.navbarlink', lambda: wx.BLUE)

        linkposx = self.padding[0]*2 + 16
        linkposy = self.headerfont.Height+2*self.padding[1]
        self.linkage.SetPosition((linkposx,linkposy))


        for link in self.linkage:
            link.NormalColour=link.HoverColour=link.VisitedColour=self.linkfc
            link.Font=self.linkfont
        self.linkage.Layout()


        elink = self.extralinkage
        if elink:
            elink.NormalColour = elink.HoverColour = elink.VisitedColour = self.linkfc
            elink.Font = self.elinkfont

            elink.Size = elink.BestSize
            elinkposx = self.Size.width - self.padding[0] - elink.BestSize.width
            elink.SetPosition((elinkposx, linkposy))


        self.bg   = skin.get('infobox.backgrounds.header', lambda: SkinColor(wx.Color(225, 255, 225)))
#        self.sep  = skin.get('infobox.longseparatorimage', None)
        self.Size = self.MinSize = wx.Size(-1, self.headerfont.Height + self.linkfont.Height + self.padding.y * 4)# + self.sep.Size.height

    def OnPaint(self, event):
        dc   = wx.AutoBufferedPaintDC(self)
        rect = RectS(self.Size)
        padx, pady = self.padding

        self.bg.Draw(dc, rect)

        dc.Font = self.headerfont
        font_height = self.headerfont.Height

        dc.TextForeground = self.headerfc
        dc.DrawBitmap(self.icon, padx, padx + (font_height // 2) - self.icon.Height // 2, True)

        printable = rect.width - padx
        curserx   = rect.x + 2 * padx + self.icon.Width
        cursery   = rect.y + pady

        dc.DrawLabel(self.account.display_name, wx.Rect(curserx, cursery, printable-curserx, font_height))

        curserx += dc.GetTextExtent(self.account.display_name+' ')[0]

        # TODO: remove this hack!
        if getattr(self.account, 'service', None) != 'twitter':
            dc.DrawLabel(('' if not hasattr(self.account, 'count') else '(' +  str(self.account.count) + ')'),
                     Rect(curserx, cursery, printable-curserx, dc.Font.Height))

class EmailList(wx.VListBox):
    """
        This is a list of the unread emails currently in the inbox.
        Refreshes on email count change
        Has links for common email actions
        Double click will open the email
    """
    def __init__(self, parent):
        wx.VListBox.__init__(self, parent)

        import common.favicons
        common.favicons.on_icon += self.OnFaviconReceived

        self.emails     = []
        self.account    = None
        self.itemheight = 0

        self.preview_offset = 0
        self.preview_timer = wx.PyTimer(self.on_preview_timer)
        self.marquee_timer = wx.PyTimer(self.on_marquee)

        self.SetItemCount(len(self.emails))

        self.linkage = PseudoSizer()
        self.linkage.Show(False)
        self.errorlink=None

        self.UpdateSkin()

        #links as (object name, String to be displayed,
        #   callback in self.account fitting this call callback(email))
        links = [('olink', 'Open', 'OnClickEmail'),
                 ('rlink', 'Mark as Read', 'markAsRead'),
                 ('alink', 'Archive', 'archive'),
                 ('dlink', 'Delete', 'delete'),
                 ('slink', 'Report Spam', 'reportSpam')]

        # Use the above list to generate ClearLink objects
        for attr, text, method in links:
            link = ClearLink(self, -1, text, method, style = wx.NO_BORDER | wx.HL_ALIGN_CENTRE)
            link.NormalColour=link.HoverColour=link.VisitedColour=self.hoverlinkfc
            link.Font=self.linkfont
            setattr(self, attr, link)

            self.linkage.Add(link)

        self.BBind(HYPERLINK        = self.OnLink,
                   MOTION           = self.OnMouseMotion,
                   LEFT_DCLICK      = self.OnDblClick,
                   LEAVE_WINDOW     = self.OnMouseOut,
                   MOUSEWHEEL       = self.OnMouseWheel,
                   PAINT            = self.OnPaint,
                   SHOW             = self.OnShow)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

    def SetSelection(self, i):
        try:
            self.preview_offset = 0
            self.marquee_timer.Stop()

            if pref('email.marquee.enabled', False):
                if i == -1:
                    self.preview_timer.Stop()
                else:
                    self.preview_timer.Start(1000, True)
        except Exception:
            import traceback
            traceback.print_exc()

        return wx.VListBox.SetSelection(self, i)

    def on_preview_timer(self):
        self.marquee_timer.Start(pref('email.marquee.delay_ms', 50), False)

    def on_marquee(self):
        sel = self.Selection
        if sel == -1:
            self.marquee_timer.Stop()
        else:
            self.preview_offset += 1
            self.RefreshRect(self.preview_rect)

    Selection = property(wx.VListBox.GetSelection, SetSelection)

    def OnFaviconReceived(self, domain):
        'Called when the favicon for "domain" is available.'

        from common.favicons import get_icon_domain

        for i, email in enumerate(self.emails):
            if not email.domain:
                continue
            if domain == get_icon_domain(email.domain):
                self.RefreshLine(i)

    def OnMouseWheel(self, event):
        self.ScrollLines(-event.WheelRotation // abs(event.WheelRotation))

    def OnDblClick(self,event):
        'Open an email on double click of the item'

        self.account.OnClickEmail(self.account.emails[self.Selection])

    def OnMouseOut(self, event):
        'Unselects the email and hide links on mouse out of list.'

        if not self.linkage.Rect.Contains(event.Position) and self.Selection != -1:
            self.RefreshLine(self.Selection)
            self.Selection = -1
            self.linkage.Show(False)

    def OnMouseMotion(self, event):
        'Select the email and show links when mouse passes over an item.'

        i = self.HitTest(event.Position)
        if self.Selection != i:
            oldSelection = self.Selection
            self.Selection=i

            if self.Selection==-1:
                self.linkage.Show(False)
            else:
                self.linkage.Show(True)

            if oldSelection >=0:
                self.RefreshLine(oldSelection)

            if self.Selection >= 0:
                self.RefreshLine(self.Selection)

    def remove_observers(self):
        if self.account is not None:
            self.account.emails.remove_observer(self.ListChanged)

        try:
            self._unbound_cbs.clear()
        except AttributeError:
            pass

    def OnShow(self, event):
        """
            Make sure there is no selection or links shown when the box is shown
            and removes oservers,links, and selection when hidden
        """
        event.Skip()

        if wx.IsDestroyed(self):
            print >> sys.stderr, 'WARNING: emailpanels.py OnShow called, but is destroyed'
            return

        if not self.Shown:
            self.remove_observers()
        self.Selection=-1
        self.linkage.Show(False)
        self.Refresh(False)

    def SetAccount(self, account):
        'Build list and links for the account.'

        self.ScrollToLine(0)
        self.Selection=-1
        self.linkage.Show(False)

        self.remove_observers()
        self.account = account
        self.account.emails.add_observer(self.ListChanged)

        self.ListChanged()

        # Get the actions this account supports
        acts = actions.forclass(account)

        # list of function names for each action
        fnames = [act['call'] if not isinstance(act, basestring) else None for act in acts]

        # if each name exists show the corrosponding link
        self.olink.Show('open' in fnames)
        self.rlink.Show('markAsRead' in fnames)
        self.alink.Show('archive' in fnames)
        self.dlink.Show('delete' in fnames)
        self.slink.Show('reportSpam' in fnames)

        self.linkage.Layout()

        # recalc item height, may be 3 or 4 lines long depending on account
        self.itemheight = self.padding.y * 4  + self.titlefont.Height + self.majorfont.Height + self.linkfont.Height + (self.sep.Size.height if self.sep else 0)
        if account.can_has_preview:
            self.itemheight+=self.minorfont.Height + self.padding.y

        self.RefreshAll()

        self.Show(True)

        with self.Frozen():
            self.GrandParent.DoSizeMagic()

    def ListChanged(self, *args, **kwargs):
        """
            Updates the list of emails when the list is changed and attemps to
            keep the same email under the mouse
        """
        i = self.GetFirstVisibleLine()

        try:
            topemail = self.emails[i]
        except IndexError:
            topemail = None

        self.emails = self.account.emails

        with self.Frozen():
            self.SetItemCount(len(self.emails))
            self.GrandParent.DoSizeMagic()

            if topemail is not None:
                try:
                    i = self.emails.index(topemail)
                except ValueError:
                    pass

            self.ScrollLines(i)
        self.Parent.Refresh(False)


    def UpdateSkin(self):
        s = skin.get

        self.padding    = s('infobox.padding', lambda: wx.Point(4, 4))
        self.headerfont = s('infobox.fonts.header', default_font)
        self.titlefont  = s('infobox.fonts.title',  default_font)
        self.majorfont  = s('infobox.fonts.major',  default_font)
        self.minorfont  = s('infobox.fonts.minor',  default_font)
        self.linkfont   = CopyFont(s('infobox.fonts.link', default_font), underline=True)

        fc = s('infobox.fontcolors'); g = fc.get
        self.titlefc        = g('title', BLACK)
        self.majorfc        = g('major', wx.BLACK)
        self.minorfc        = g('minor', wx.Color(128, 128, 128))
        self.linkfc         = g('link',  wx.BLUE)
        self.hovertitlefc   = g('emailhovertitle', self.titlefc)
        self.hovermajorfc   = g('emailhovermajor', self.majorfc)
        self.hoverminorfc   = g('emailhoverminor', self.minorfc)
        self.hoverlinkfc    = g('emailhoverlink',  self.linkfc)

        for link in self.linkage:
            link.NormalColour = link.HoverColour = link.VisitedColour = self.hoverlinkfc
            link.Font = self.linkfont

        self.linkage.Layout()

        if self.errorlink:
            self.errorlink.Font = self.Parent.Font
            self.errorlink.VisitedColour = self.errorlink.HoverColour = self.errorlink.NormalColour = s('infobox.linkcolor', lambda: wx.BLUE)

        self.bg    = s('infobox.backgrounds.email',      lambda: SkinColor(wx.WHITE))
        self.selbg = s('infobox.backgrounds.emailhover', lambda: SkinColor(wx.Color(225, 255, 225)))
        self.sep   = s('infobox.shortseparatorimage',    None)


    def GetFullHeight(self):
        'Returns the summed height of all items.'

        return (self.ItemCount or 1) * self.OnMeasureItem(0)

    def SkimIt(self, it):
        """
            Given the availible height returns the height it wants in order
            for the number of items shown to exactly fit
        """

        if self.ItemCount:
            h = self.OnMeasureItem(0)
            r = (it // h) * h # Yay for int division and it's always floor attitude

            return r
        return self.OnMeasureItem(0)

    def OnMeasureItem(self, n):
        """
            Since all items have a predetermined height based determined by
            a combination of skin and and weither or not the account type has
            a preview, this just returns that predetermined number
        """
        return self.itemheight

    def OnDrawBackground(self, dc, rect, n):
        'Draws the background for each item.'

        if self.Selection == n:
            self.selbg.Draw(dc, rect, n)
        else:
            self.bg.Draw(dc, rect, n)

    def OnPaint(self,event):

        if self.ItemCount:
            event.Skip()
            return

        dc = wx.AutoBufferedPaintDC(self)
        rect = RectS(self.Size)

        self.OnDrawBackground(dc, rect, 0)

        dc.Font = self.titlefont
        dc.DrawLabel('No Previews' if self.account.count else 'No New Email', rect, wx.ALIGN_CENTER)
#
#        errlink = self.errorlink
#        if errlink:
#            errlink.Position = (self.Size.width  - (errlink.Size.width + self.padding[0]),
#                                self.Size.height - (errlink.Size.height + self.padding[1]))

    def OnDrawItem(self, dc, rect, n):
        """
            Draws the content for the item, and positions the links for
            selection
        """
        issel = n == self.Selection

        email = self.emails[n]
        pad   = self.padding
        sendtime = getattr(email, 'sendtime', None)
        if hasattr(sendtime, 'strftime'):
            strf  = sendtime.strftime

            try:
                # Generate a timestamp for the email -- may raise an exception
                # if the date is < 1900
                iscurdate = strf('%b %d %y') == datetime.now().strftime('%b %d %y')

                date = strf('%b %d')
                time = strf('%I:%M %p')
                if time[0] == '0':
                    time = time[1:]

                if iscurdate and getattr(self.account, 'timestamp_is_time', lambda t: True)(sendtime):
                    timestamp = time
                else:
                    timestamp = date
            except Exception:
                traceback.print_exc_once()
                timestamp = None
        else:
            timestamp = sendtime

        if timestamp is None:
            timestamp = ''

        curserx = rect.x + pad.x
        cursery = rect.y + pad.y

        # Draw the favicon.
        from common.favicons import favicon
        d = email.domain
        icon = favicon(d) if d is not None else None

        iconsize = 16
        if icon is None:
            icon = skin.get('emailpanel.miscicons.defaulticon', None)

        if icon is not None:
            icon = icon.Resized(iconsize)
            dc.DrawBitmap(icon, curserx, cursery, True)

        curserx += iconsize + pad.x

        #draw the timestamp
        dc.Font = self.minorfont
        dc.TextForeground = self.hoverminorfc if issel else self.minorfc
        tste   = dc.GetFullTextExtent(timestamp)
        tsrect = wx.Rect(rect.x+rect.width-tste[0] - pad.x, cursery, tste[0], tste[1] + tste[2] + tste[3])
        dc.DrawTruncatedText(timestamp, tsrect)

        # draw attachment icon
        if email.attachments:

            atticon = skin.get('emailpanel.miscicons.attachmenticon', None)
            if atticon is not None:
                count = len(email.attachments)
                if count > 1:
                    atticon = add_image_text(atticon, str(count))
                dc.DrawBitmap(atticon, tsrect.X - atticon.Width - pad.x, tsrect.Y, True)

        # draw the sender name or email
        dc.Font = self.titlefont
        dc.TextForeground = self.hovertitlefc if issel else self.titlefc
        dc.DrawTruncatedText(u'%s' % (email.fromname or email.fromemail),
                             Rect(curserx, cursery, rect.Width-(curserx + pad.x) - tsrect.width, dc.Font.Height))

        cursery+=dc.Font.Height + self.padding.y

        # Draw the subject
        dc.Font = self.majorfont
        dc.TextForeground = self.hovermajorfc if issel else self.majorfc
        dc.DrawTruncatedText(email.subject or _('(No Subject)'), Rect(curserx, cursery, rect.Width-(curserx+pad.x), dc.Font.Height))

        # Draw the preview line if applicable
        if self.account.can_has_preview:
            cursery += dc.Font.Height + pad.y
            dc.Font = self.minorfont
            dc.TextForeground = self.hoverminorfc if issel else self.minorfc
            self.preview_rect = wx.Rect(curserx, cursery, rect.Width-(curserx + pad.x), GetFontHeight(dc.Font, line_height=True))
            if dc.DrawTruncatedTextInfo(email.content[self.preview_offset:] or _('(No Preview)'), self.preview_rect):
                self.marquee_timer.Stop()

        # draw separator if there is one and not last email
        if self.sep and n < len(self.emails)-1:
            self.sep.Draw(dc, wx.RectPS(rect.Position + (2, rect.height-self.sep.Size.height), (rect.width-4, self.sep.Size.height)))

        # place links if selection
        if issel:
            cursery += dc.Font.Height + pad.y
            self.linkage.SetPosition((curserx, cursery))

    def OnLink(self, event):
        # Hide infobox
        if event.URL =='OnClickEmail':
            wx.GetTopLevelParent(self).Hide()

        # remove selection
        getattr(self.account, event.URL)(self.account.emails[self.Selection])
        self.Selection = -1
        self.linkage.Show(False)


