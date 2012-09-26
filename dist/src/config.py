'''
Not sure if this is the best name, but we need a place for getting the platform dir
that won't indirectly import cgui, as we need this to determine where to look for it. 
'''

import sys

if sys.platform.startswith("win"):
    platformName = "win"
elif sys.platform.startswith("darwin"):
    platformName = "mac"
else:
    platformName = "gtk"
    
newMenubar = 0
nativeIMWindow = (platformName == "mac")


platform = platformName # phase out camelCase

