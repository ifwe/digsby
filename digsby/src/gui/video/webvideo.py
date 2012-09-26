'''

Web based video GUI.

'''

from __future__ import with_statement
import wx
from gui import skin
from gui.browser import BrowserFrame, reload_plugins
from gui.toolbox import persist_window_pos, snap_pref
from logging import getLogger; log = getLogger('webvideo')

video_frame_url = 'http://v.digsby.com/embed.php?id=%(widget_id)s'
video_frame_style = wx.MINIMIZE_BOX | wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX | wx.CLIP_CHILDREN | wx.STAY_ON_TOP
video_frame_size = (542, 264)

def confirm_invite(buddy_name):
    msg_header = _('{name} has invited you to an audio/video chat.').format(name=buddy_name)
    msg_question = _('Would you like to join?')
    
    msg = u'{header}\n\n{question}'.format(header=msg_header, question=msg_question)
    
    return wx.YES == wx.MessageBox(msg, _('Audio/Video Chat Invitation'), style = wx.YES_NO)

class VideoChatWindow(BrowserFrame):
    def __init__(self, title, widget_id, on_close = None):
        self.widget_url = video_frame_url % dict(widget_id = widget_id)
        reload_plugins()
        BrowserFrame.__init__(self,
                              None,
                              name = 'Video Chat Window',
                              title = title,
                              url   = self.widget_url,
                              style = video_frame_style,
                              external_links=False)

        self.on_close = on_close
        self.SetFrameIcon(skin.get('AppDefaults.TaskBarIcon'))

        self.Bind(wx.webview.EVT_WEBVIEW_BEFORE_LOAD, self.__onbeforeload)

        persist_window_pos(self, position_only = True)
        snap_pref(self)
        self.SetClientSize(video_frame_size)

        log.debug('opening video embed url: %s' % self.widget_url)

        if on_close is not None:
            self.Bind(wx.EVT_CLOSE, self.OnClose)

    def __onbeforeload(self, e):
        if e.NavigationType == wx.webview.WEBVIEW_NAV_LINK_CLICKED:
            url = e.URL
            if not any((url.startswith('digsby:'),
                        url.startswith('javascript:'))):

                # users without flash player get a button linking to Adobe's site.
                # however, if the default browser is IE, the site will link to the
                # ActiveX version of flash--but we need the "Mozilla" or NPAPI
                # plugin for WebKit. intercept the "Get Flash" button click and
                # just open the NPAPI installer exe directly.
                if url == 'http://www.adobe.com/go/getflashplayer':
                    url = 'http://fpdownload.macromedia.com/get/flashplayer/current/install_flash_player.exe'

                wx.LaunchDefaultBrowser(url)
                e.Cancel()
                return

        e.Skip()

    def OnClose(self, e):
        self.Hide()
        e.Skip()
        if self.on_close is not None:
            self.on_close()
