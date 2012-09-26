import wx

import digsbysite
import netextensions
import common.favicons
from tests.testapp import testapp


##
## DISABLE USE OF threaded
##
common.favicons.use_threaded = False




def main():
    a = testapp()
    f = wx.Frame(None, title = 'Favicon Test', size = (300, 600))
    f.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

    common.favicons.clear_cache()

    # refresh when new favicons come in
    common.favicons.on_icon.append(lambda domain: f.Refresh(), obj=f)

    domains = [
        'rebates.riteaid.com',  # server doesn't give "reason phrase" for http response
        'message.myspace.com', # goes to myspace.com
        'usaa.com',       # ssl
        'www.53.com',     # ssl
        'technion.ac.il', # israel, may not resolve
        'ebay.com',
        'facebookmail.com',
        'gmail.com',
        'livejournal.com',
        'google.com',
        'digsby.com',
        'aol.com',
        'yahoo.com',
        'hotmail.com',
        'reddit.com',
        'slashdot.com',
        'meebo.com',
        'clearspring.com',
        'rge.com',
        'amazon.com',
        'apple.com', # BROKEASS MAC HEADERS
        'nvidia.com',
        'uq.edu.au',
        'hotmail.co.uk',
        'autodeskcommunications.com',
        'email.hsbcusa.com',
        'bugs.python.org',
        'outpost.com', # has big red F but it never shows the image... however, dimensions are determined
        'connect.vmware.com',
        'reply1.ebay.com',
        'wellsfargo.com',
        #'gmx.net', # has <link rel="shortcut icon" type="image/x-icon" href="//img.ui-portal.de/gmx/homegmx/icons/favicon.ico" />
        'bose.com', # blank looking icon (white square)
        'excelsiorpkg.com',
        'namesdatabase.com', # ssl?
        'fly.spiritairlines.com', # has a weird redirect- url contains port
        'www.dominos.com', #says "You Got...Lost" when going to www.dominos.com/favicon.ico, but firefox definitely has one.
    ]

    x = 5

    def paint(e):

        dc = wx.AutoBufferedPaintDC(f)
        dc.SetFont(f.Font)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangleRect(f.ClientRect)

        y = 0
        for domain in domains:
            icon = common.favicons.favicon(domain)
            dc.DrawText(domain, x + (icon.Width if icon is not None else 16) + 5, y)
            if icon is not None:
                dc.DrawBitmap(icon, x, y, True)

            y += icon.Height if icon is not None else 16

    f.Bind(wx.EVT_PAINT, paint)

    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    main()
