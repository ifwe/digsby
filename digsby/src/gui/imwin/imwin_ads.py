'''
im window ad
'''

import sys
import traceback
import wx
import cgui
import simplejson
import random
from time import time
from gui.browser.webkit import WebKitWindow
from common import pref, profile
from util.primitives.funcs import Delegate

from logging import getLogger; log = getLogger('imwin_ads')
from util.net import UrlQuery

# number of minutes which must elapse with no IM windows open for us to clear cookies on the next IM window open
AD_COOKIE_CLEAR_MINS = 60

IMFRAME_MINSIZE = (320, 220)
IMFRAME_WITH_AD_MINSIZE_H = (490, 350)
IMFRAME_WITH_AD_MINSIZE_V = (320, 397)
SHOULD_ROTATE = True
PREF_FLASH_DISABLED = 'imwin.ads_disable_flash'

CAMPAIGNS = {
    # version controlled at
    # svn.tagged.com/web/cool/www/digsbytag.html
    'tagged':'http://www.tagged.com/digsbytag.html',
    # SVN/dotSyntax/s3/trunk/serve.digsby.com/rubicon.html
    'rubicon':'http://serve.digsby.com/rubicon.html',
    # not under VCS
    'rubicon_vertical':'http://serve.digsby.com/rubicon2.html'
}

def get_ad_campagin():
    if _adposition() in ('left', 'right'):
        return 'rubicon_vertical'
    else:
        return 'tagged'

PREF_AD_POSITION = 'imwin.ads_position'
def _adposition():
    return pref(PREF_AD_POSITION, default='bottom')

PREF_ADS_ENABLED = 'imwin.ads'
def _adsenabled():
    return pref(PREF_ADS_ENABLED, default=False)


AD_PANEL_MINSIZE_H = (466, 58)
AD_PANEL_MINSIZE_V = (-1, -1) # (102, 384)

AD_PANEL_MAXSIZE_H = (728, 90)
AD_PANEL_MAXSIZE_V = (160, 600)

allowed_trigger_modes = ('focus', 'sendim')
allowed_time_modes = ('real', 'engagement')

ad_scenarios = [
    (120, 'real', 'focus'),
    #(180, 'real', 'focus'),
    #(240, 'real', 'focus'),
    #(60, 'engagement', 'focus'),
    #(90, 'engagement', 'focus'),
    #(120, 'engagement', 'focus'),
    #(180, 'engagement', 'focus'),
    #(120, 'real', 'sendim'),
    #(180, 'real', 'sendim'),
    #(240, 'real', 'sendim'),
    #(60, 'engagement', 'sendim'),
    #(90, 'engagement', 'sendim'),
    #(120, 'engagement', 'sendim'),
    #(180, 'engagement', 'sendim'),
]

assert all(isinstance(s[0], int) and s[0] > 0 for s in ad_scenarios)
assert all(s[1] in allowed_time_modes for s in ad_scenarios)
assert all(s[2] in allowed_trigger_modes for s in ad_scenarios)

def choose_ad_scenario():
    s = ad_scenarios[:]
    random.shuffle(s)
    return s[0]

class AdRotater(object):

    def __repr__(self):
        from gui.imwin.imtabs import ImFrame
        return '<AdRotater (secs=%s, time_mode=%s, trigger_mode=%s, has_focus=%r, idle=%r) (%.02f secs engagement)>' % (self.timer_secs, self.time_mode, self.trigger_mode, self.has_focus, ImFrame.engage_is_idle, self._engagement())

    def __init__(self, timer_secs, time_mode, trigger_mode, current_time_func=time):
        assert isinstance(timer_secs, int)
        assert trigger_mode in allowed_trigger_modes
        assert time_mode in allowed_time_modes

        self.has_focus = False

        self.timer_secs = timer_secs
        self.time_mode = time_mode
        self.trigger_mode = trigger_mode

        self.scenario_identifier = '%s_%s_%s' % (timer_secs, time_mode, trigger_mode)

        assert hasattr(current_time_func, '__call__')
        self._get_time = current_time_func

        self._reset_time(start=False) # the last UNIX time we showed an ad ( = now).
        self.on_reload = Delegate()

        if self.trigger_mode == 'focus':
            self.wx_timer = wx.PyTimer(self._on_wxtimer)
            self.wx_timer.StartRepeating(1000)

    def _on_wxtimer(self):
        if not self.has_focus:
            return

        if (self.time_mode == 'engagement' and not self.timer.paused) or \
           self.time_mode == 'real':
            self.trigger_event('focus')

    def trigger_event(self, event):
        if self.should_rotate(event):
            self.on_reload()

    def should_rotate(self, trigger_event):
        '''Returns True if enough time has passed to show a new ad. Resets
        internal timers if that is the case.'''

        if not SHOULD_ROTATE: # for debugging
            return False

        assert trigger_event in allowed_trigger_modes, '%r not in %r' % (trigger_event, allowed_trigger_modes)

        from gui.imwin.imtabs import ImFrame
        if ImFrame.engage_is_idle:
            return False

        if self.trigger_mode != trigger_event:
            return False

        if not self._enough_time_elapsed():
            return False

        return True

    def pause(self):
        if self.time_mode == 'engagement':
            return self.timer.pause()

    def unpause(self):
        if self.time_mode == 'engagement':
            return self.timer.unpause()

    def _reset_time(self, start=True):
        self.timer = Timer(get_time_func=self._get_time)
        if start:
            self.timer.start()

    def _engagement(self):
        return self.timer.get_ticks()

    def _enough_time_elapsed(self):
        return self._engagement() >= self.timer_secs

_ad_scenario = None
def ad_scenario():
    global _ad_scenario
    if _ad_scenario is None:
        _ad_scenario = choose_ad_scenario()
    return _ad_scenario

class AdPanel(WebKitWindow):
    def __init__(self, parent, rotater):
        self.rotater = rotater
        self.refresh_campaign()

        WebKitWindow.__init__(self, parent, simple_events=True)

        self._update_flash_enabled()
        profile.prefs.add_gui_observer(self._update_flash_enabled, PREF_FLASH_DISABLED)

        self.set_jsqueue_enabled(False)
        self.set_window_open_redirects_to_browser(self._url_callback)
        self.SetMinimumFontSize(10)

        # indicates that we've actually arrived at the AD url
        self._navigated_to_base_url = False

        self.Bind(wx.webview.EVT_WEBVIEW_BEFORE_LOAD, self.OnBeforeLoad)
        self.Bind(wx.webview.EVT_WEBVIEW_LOAD, self.on_loading)

        self.update_minsize()

        from gui.browser.webkit import setup_webview_logging
        jslog = getLogger('imwin_ads_js')
        setup_webview_logging(self, jslog)

        self._did_notify_click = False
        self.SetFineGrainedResourceEvents(True)

    def update_minsize(self):
        if _adposition() in ('left', 'right'):
            self.SetMinSize(AD_PANEL_MINSIZE_V)
            self.SetMaxSize(AD_PANEL_MAXSIZE_V)
        else:
            self.SetMinSize(AD_PANEL_MINSIZE_H)
            self.SetMaxSize(AD_PANEL_MAXSIZE_H)

    def refresh_campaign(self):
        campaign = get_ad_campagin()
        self.ad_url_base = CAMPAIGNS[campaign]

        old_ad_url = getattr(self, 'ad_url', None)
        self.ad_url = UrlQuery(self.ad_url_base,
                          utm_source='digsby_client',
                          utm_medium='im_window',
                          utm_content=self.rotater.scenario_identifier,
                          utm_campaign=campaign,
                          )

        if old_ad_url is not None and old_ad_url != self.ad_url:
            self._reload_ad()

    def _update_flash_enabled(self, *a):
        if not wx.IsDestroyed(self):
            flash_enabled = not pref(PREF_FLASH_DISABLED, default=False)
            self.WebSettings.SetPluginsEnabled(flash_enabled)

    @property
    def URL(self):
        return self.RunScript('window.location.href')

    def on_loading(self, e):
        try:
            url = self.URL
        except wx.PyDeadObjectError:
            return e.Skip()

        if not url or e.State != wx.webview.WEBVIEW_LOAD_TRANSFERRING:
            return e.Skip()

        at_base = url.startswith(self.ad_url_base)

        if at_base:
            self._navigated_to_base_url = True

        hijacked_url = getattr(self, '_did_hijack_url', None)

        # if we have never successfully navigated to serve.digsby.com, assume that a proxy
        # is blocking access to it
        if not at_base and not self._navigated_to_base_url:
            log.info('loading blank window b/c caught possible proxy block to url %r', self.ad_url)
            self.LoadURL('about:blank')

        elif not at_base and self._navigated_to_base_url and \
                (hijacked_url is None or not urls_have_same_domain(url, hijacked_url)):
            self._did_hijack_url = url
            log.warning('!!!! escaped from serve.digsby.com: %r', url)
            self._url_callback(url)
            self.RefreshAd()

    def _url_callback(self, url):
        wx.LaunchDefaultBrowser(url)
        self.notify_click(url)

    def _is_double_url_call(self, url):
        last = getattr(self, '_last_url_launched', None)
        new = (url, time())
        if last is not None and url == last[0]:
            if abs(new[1] - last[1]) < 200:
                return True
        self._last_url_launched = new

    def OnBeforeLoad(self, e):
        url = e.URL
        skip = True
        if e.NavigationType == wx.webview.WEBVIEW_NAV_LINK_CLICKED:
            e.Cancel() # don't navigate in webkit
            self._url_callback(url)
            skip = False
        elif e.NavigationType == wx.webview.WEBVIEW_NAV_OTHER:
            # just catch page requests if we're not in "ad debug mode"
            if not _debug_ads():
                self._log_ad_url(url)
        elif e.NavigationType == wx.webview.WEBVIEW_NAV_REQUEST:
            url = e.URL
            # all resource requests can be cancelled when
            # SetFineGrainedResourceEvents(True) was called
            if self._should_blacklist_ad_url(url):
                log.info('ad URL BLACKLISTED, cancelling request %s', url)
                e.Cancel()
                skip = False
            elif _debug_ads():
                self._log_ad_url(url)

        e.Skip(skip)

    def _log_ad_url(self, url):
        last = getattr(self, '_last_logged_url', None)
        if last is not None and last == url:
            del self._last_logged_url
        else:
            log.info('ad URL %s', url)
            self._last_logged_url = url

    blacklisted_urls = set((
        'http://qnet.hit.gemius.pl/pp_gemius.js',
    ))

    def _should_blacklist_ad_url(self, url):
        if url in self.blacklisted_urls:
            return True

        return False

    def _reload_ad(self):
        self._did_notify_click = False
        self.rotater._reset_time()

        log.info('Loading ad URL: %r', self.ad_url)
        self._navigated_to_base_url = False
        self.LoadURL(self.ad_url)

    def notify_click(self, url):
        if self._did_notify_click:
            return

        self._did_notify_click = True
        log.info('notifying ad click: %r', url)
        self._track_analytics_event('click')

    def _track_analytics_event(self, action):
        assert wx.IsMainThread()
        script = '_gaq.push(%s);' % \
                simplejson.dumps(['_trackEvent', self.rotater.scenario_identifier, action])
        print script
        result = self.RunScript(script)
        print 'RESULT', result


GLASS_TRANSPARENT_COLOR = (0, 0, 0) # the color that Vista will turn into glass

glass = lambda: cgui.isGlassEnabled() and pref('imwin.ads_glass', default=True)

def construct_ad_panel(self, mainPanel, new_tab_cb, bind_pref=True):
    if bind_pref:
        def on_ad_pref(src, attr, old, new):
            ap = getattr(self, 'ad_panel', None)
            if ap is None and _adsenabled():
                with self.Frozen():
                    construct_ad_panel(self, mainPanel, new_tab_cb, bind_pref=False)
                    self.Layout()
            else:
                self.build_ad_sizer()

        profile.prefs.add_gui_observer(on_ad_pref, PREF_ADS_ENABLED, obj=self)

    if not _adsenabled():
        return

    should_clear_cookies = setup_cookie_timer(self)

    adpos = _adposition()

    borderSize = 1
    extra_top = 8

    rotater = AdRotater(*ad_scenario())
    self.ad_panel = ad_panel = AdPanel(self, rotater)
    if should_clear_cookies:
        self.ad_panel.ClearCookies()
    self._ad_rotater = rotater

    self.on_engaged_start += rotater.unpause
    self.on_engaged_end += rotater.pause

    def on_message(mode, imwin_ctrl):
        if mode == 'im':
            rotater.trigger_event('sendim')

    self.on_sent_message += on_message

    self._did_show_ad = False

    def check_focus():
        if wx.IsDestroyed(self):
            return

        is_foreground = self.Top.IsForegroundWindow()

        rotater.has_focus = is_foreground and not self.IsIconized()
        if rotater.has_focus:
            if not self._did_show_ad:
                self._did_show_ad = True
                rotater.on_reload()
            else:
                rotater.trigger_event('focus')

    wx.CallLater(50, check_focus)

    # listen for when the frame is activated
    def on_iconize(e):
        e.Skip()
        wx.CallAfter(check_focus)

    def on_activate(e):
        e.Skip()
        wx.CallAfter(check_focus)
        if not glass():
            self.Refresh() # the ad background color changes with activation

    self.Bind(wx.EVT_ACTIVATE, on_activate)
    self.Bind(wx.EVT_ICONIZE, on_iconize)

    ###

    horiz_padding = 8
    extra_horizontal = 1

    def build_ad_sizer(adpos=None, layout_now=True):
        if wx.IsDestroyed(self):
            return
        enabled = _adsenabled()
        if adpos is None:
            adpos = _adposition()

        with self.Frozen():
            self.SetSizer(None)

            if not enabled:
                minsize = IMFRAME_MINSIZE
            elif adpos in ('left', 'right'):
                minsize = IMFRAME_WITH_AD_MINSIZE_V
            else:
                minsize = IMFRAME_WITH_AD_MINSIZE_H
            self.SetMinSize(minsize)

            if enabled:
                ad_panel.Show()


            if not enabled:
                ad_panel.Hide()
                sz = wx.BoxSizer(wx.VERTICAL)
                sz.Add(mainPanel, 1, wx.EXPAND)
            elif adpos == 'top':
                sz = wx.BoxSizer(wx.VERTICAL)
                sz.Add((borderSize, borderSize))# + (0 if glass() else 7)))
                sz.Add(ad_panel, 0, wx.ALIGN_CENTER_HORIZONTAL)
                sz.Add((borderSize, borderSize+extra_top))
                sz.Add(mainPanel, 1, wx.EXPAND)
            elif adpos == 'left':
                sz = wx.BoxSizer(wx.HORIZONTAL)
                sz.Add((extra_horizontal,1))
                sz.Add(ad_panel, 0, wx.ALIGN_CENTER_VERTICAL)
                sz.Add((horiz_padding, 1))
                sz.Add(mainPanel, 1, wx.EXPAND)
            elif adpos == 'right':
                sz = wx.BoxSizer(wx.HORIZONTAL)
                sz.Add(mainPanel, 1, wx.EXPAND)
                sz.Add((horiz_padding, borderSize))
                sz.Add(ad_panel, 0, wx.ALIGN_CENTER_VERTICAL)
                sz.Add((extra_horizontal, 1))
            else: # == 'bottom':
                sz = wx.BoxSizer(wx.VERTICAL)
                sz.Add(mainPanel, 1, wx.EXPAND)
                sz.Add((borderSize, borderSize+extra_top))
                sz.Add(ad_panel, 0, wx.ALIGN_CENTER_HORIZONTAL)
                sz.Add((borderSize, borderSize))# + (0 if glass() else 7)))

            self.SetSizer(sz)
            if layout_now:
                self.Layout()

    build_ad_sizer(adpos, layout_now=False)
    self.build_ad_sizer = build_ad_sizer

    def on_pref_change(src, attr, old, new):
        if wx.IsDestroyed(self):
            return
        build_ad_sizer(_adposition())
        ad_panel.update_minsize()
        on_resize()
        ad_panel.refresh_campaign()


    profile.prefs.add_gui_observer(on_pref_change, PREF_AD_POSITION, obj=self)

    if 'wxMSW' in wx.PlatformInfo:
        from gui.native.win.winutil import get_frame_color
    else:
        get_frame_color = lambda active: wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)

    def paint(e):
        r = mainPanel.Rect
        x, y = r.BottomLeft
        x += (r.Width - x) / 2 - ad_panel.Size.width / 2

        dc = wx.AutoBufferedPaintDC(self)

        dc.Pen = wx.TRANSPARENT_PEN
        if glass():
            dc.Brush = wx.Brush(wx.Color(*GLASS_TRANSPARENT_COLOR))
        else:
            dc.Brush = wx.Brush(get_frame_color(self.IsActive()))

        dc.DrawRectangleRect(self.ClientRect)

        if not _adsenabled():
            if glass():
                cgui.glassExtendInto(self, 0, 0, 0, 0)
            return

        if borderSize:
            r = ad_panel.Rect
            r.y -= borderSize
            r.height += 1 + borderSize
            r.x -= borderSize
            r.width += 1 + borderSize
            dc.DrawBitmap(_get_border_image(r.Size), r.x, r.y, True)

        if glass():
            adpos = _adposition()
            glass_width = horiz_padding + ad_panel.Size.width + extra_horizontal
            glass_height = borderSize*2+extra_top + (extra_top if not glass() else 0) + ad_panel.Size.height
            if adpos == 'top':
                cgui.glassExtendInto(self, 0, 0, glass_height, 0)
            elif adpos == 'left':
                cgui.glassExtendInto(self, glass_width, 0, 0, 0)
            elif adpos == 'right':
                cgui.glassExtendInto(self, 0, glass_width, 0, 0)
            else: # 'bottom'
                cgui.glassExtendInto(self, 0, 0, 0, glass_height)


    self.Bind(wx.EVT_PAINT, paint)

    def _ad_panel_shown():
        ad_panel = getattr(self, 'ad_panel', None)
        if ad_panel is not None:
            return ad_panel.IsShown()

    def on_resize(e=None):
        if hasattr(e, 'Skip'):
            e.Skip()

        if wx.IsDestroyed(self) or not _ad_panel_shown():
            return

        if _adposition() in ('left', 'right'):
            maxw, maxh = AD_PANEL_MAXSIZE_V
            cheight = self.ClientSize.height
            ad_h = min(maxh, cheight)
            if ad_h < maxh:
                ad_h -= 2
            zoom = float(ad_h) / maxh
            ad_w = zoom*maxw
        else:
            maxw, maxh = AD_PANEL_MAXSIZE_H
            cwidth = self.ClientSize.width
            ad_w = min(maxw, cwidth)
            if ad_w < maxw:
                ad_w -= 2 # leave room for border on sides when smaller
            zoom = float(ad_w) / maxw
            ad_h = zoom*maxh

        ad_panel.SetMinSize((ad_w, ad_h))
        ad_panel.SetPageZoom(zoom)
        ad_panel.Parent.Layout()
        ad_panel.Parent.Refresh()

    self.Bind(wx.EVT_SIZE, on_resize)

    def RefreshAd():
        if _ad_panel_shown():
            ad_panel._reload_ad()
            wx.CallLater(50, on_resize)

    rotater.on_reload += RefreshAd
    ad_panel.OnDoc += on_resize
    ad_panel.RefreshAd = RefreshAd

    # new tab callback

    def on_new_tab(*a):
        if not getattr(self, '_first_tab_opened', False):
            self._first_tab_opened = True
            return

        ad_panel.RefreshAd()
    new_tab_cb += on_new_tab

    # allow dragging the frame by grabbing the area around the ad.
    self.PushEventHandler(cgui.DragMixin(self))


# gdi DrawRect on glass doesn't fill the alpha channel, so use an image
_cached_border_image = (None, None)
_border_color = (93, 108, 122, 255)
def _get_border_image(sz):
    global _cached_border_image
    w, h = sz
    sz = (w, h)
    if _cached_border_image[0] == sz:
        return _cached_border_image[1]
    import PIL
    img = PIL.Image.new('RGBA', (w, h), _border_color).WXB
    _cached_border_image = (sz, img)
    return img

class Timer(object):
    def __init__(self, get_time_func=time):
        self._get_time = get_time_func

        self.start_ticks = 0
        self.paused_ticks = 0
        self.paused = False
        self.started = False

    def start(self):
        self.started = True
        self.paused = False
        self.start_ticks = self._get_time()

    def stop(self):
        self.started = False
        self.paused = False

    def pause(self):
        if not self.started or self.paused:
            return

        self.paused = True
        self.paused_ticks = self._get_time() - self.start_ticks

    def unpause(self):
        if not self.started or not self.paused:
            return

        self.paused = False
        self.start_ticks = self._get_time() - self.paused_ticks
        self.paused_ticks = 0

    def get_ticks(self):
        if not self.started:
            return 0

        if self.paused:
            return self.paused_ticks
        else:
            return self._get_time() - self.start_ticks

def _debug_ads():
    opts = getattr(sys, 'opts', None)
    return getattr(opts, 'debugads', False)

def urls_have_same_domain(a, b):
    try:
        return UrlQuery.parse(a).netloc == UrlQuery.parse(b).netloc
    except Exception:
        traceback.print_exc_once()
        return a == b

def find_instances(clz):
    return [w for w in wx.GetTopLevelWindows()
            if isinstance(w, clz)]

last_imframe_close = None

def secs_since_last_close():
    if last_imframe_close is not None:
        return time() - last_imframe_close

def should_clear_cookies():
    secs = secs_since_last_close()
    return secs is not None and secs > 60 * AD_COOKIE_CLEAR_MINS

def setup_cookie_timer(imframe):
    '''
    keeps track of the time when the last IM window is closed. if a new IM window is opened
    some time after that, and enough time has elapsed, then we clear cookies.

    this is so that we have a new session for the ad networks and don't serve
    ads on the 'long session time' end of the spectrum too often.
    '''
    imclz = imframe.__class__

    def num_imframes():
        return len(find_instances(imclz))

    def on_close(e):
        global last_imframe_close
        e.Skip()
        if num_imframes() == 1:
            last_imframe_close = time()

    imframe.Bind(wx.EVT_CLOSE, on_close)

    return num_imframes() == 1 and should_clear_cookies()
