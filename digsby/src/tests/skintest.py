import wx
import unittest
import util
import struct
import gui
import yaml
from gui.skin import ready_skin

class SkinTestingSuite(unittest.TestCase):

    def setUp(self):
        app = wx.PySimpleApp()
        print 'setting up'
        gui.skin.skininit('../../res')
        assert app.skin

    def testSkinTransform(self):
        s = '''
button:
  font: {color: white}
  menuicon: dropmenuicon.png
  color: green
  border: {color: black, width: 0, style: solid}
  spacing: [5, 5]
  image:
    regions: {}
    source: buttonblue.png
    corners:
      side: all
      size: [3, 3]
    style: stretch
  down:
    color: dark green
    image:
      regions: {}
      source: buttonmagenta.png
      corners:
        side: all
        size: [3, 3]
      style: stretch
    border: {color: black, width: 0, style: solid}
    font: {color: black}
  over:
    color: light green
    image:
      regions: {}
      source: buttoncyan.png
      style: stretch
      corners:
        side: all
        size: [3, 3]
    font: {color: green}
    border: {color: black, width: 0, style: solid}
  active:
    color: dark green
    image:
      regions: {}
      source: buttonmagenta.png
      corners:
        side: all
        size: [3, 3]
      style: stretch
    over:
      color: light green
      image:
        regions: {}
        source: buttoncyan.png
        style: stretch
        corners:
          side: all
          size: [3, 3]
      font: {color: green}
      border: {color: black, width: 0, style: solid}
    border: {color: black, width: 0, style: solid}
    font: {color: black}
  disabled:
    color: grey
    image:
      regions: {}
      source: buttongrey.png
      style: stretch
      corners:
        side: all
        size: [3, 3]
    border: 1px black solid
    font: {color: light grey}
'''
        s = util.to_storage(yaml.load(s))
        ready_skin(s)
        print s


if __name__ == '__main__':
    unittest.main()