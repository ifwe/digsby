
import config
import sys, os
sys.path += map(os.path.abspath, ['./src', './ext', './ext/' + config.platformName, './lib', './thirdparty'])

import wx

def main():
    from tests.testapp import testapp
    a = testapp()

    from gui.toolbox.fonts import loadfont
    assert loadfont('res/slkscr.ttf')



if __name__ == '__main__':
    main()