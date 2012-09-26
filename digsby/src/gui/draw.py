import wx

def border(dc, rect, top=True, bottom=True, left=True, right=True,
           rounded=False, size=None):
    """
    Draws a border for the specified rectangle. The current brush and pen are
    used.

    Defaults are to draw the whole rectangle, but if you want to leave sides
    out, specify them as False, like

    >>> draw.border(dc, rect, left=False, right=False)

    If the rounded keyword argument is set to True, then a full rectangle will
    be drawn with rounded edges.
    """
    dc.SetPen(wx.BLACK_PEN)

    if top and bottom and left and right:
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        if rounded:
            dc.DrawRoundedRectangle(rect.x,rect.y,rect.width,rect.height, rounded)
        else:
            dc.DrawRectangle(rect.x,rect.y,rect.width, rect.height)
    else:
        pen_width = dc.GetPen().GetWidth()
        bottompos = rect.y + rect.height - pen_width
        rightpos  = rect.x + rect.width  - pen_width

        if top:    dc.DrawLine(rect.x, rect.y, rightpos, rect.y)
        if bottom: dc.DrawLine(rect.x, bottompos, rightpos, bottompos)
        if left:   dc.DrawLine(rect.x, rect.y, rect.x, bottompos)
        if right:  dc.DrawLine(rightpos, rect.y, rightpos, bottompos)