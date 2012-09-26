import wx, os

# add all platform-specific wx extensions to the wx API here so
# they're always available.
from gui.native.extensions import *

# now add all platform-indepdenent extensions as well.
from gui.wxextensions import *

def dist(here, there):
    'Returns the euclidean distance from here to there.'
    return sum(map(lambda a, b: (a-b) ** 2, here, there)) ** .5

wx.Point.DistanceTo = dist

def yes(msg, title = ''):
    return wx.MessageBox(msg, title, wx.YES_NO) == wx.YES


