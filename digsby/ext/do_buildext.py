#__LICENSE_GOES_HERE__
'''
A script that drives buildexts.py and installs the built extension into a platform
subdir of the main ext dir. This way we won't have cgui.py or cgui.pyd/so for various
platforms overwriting each other.
'''

import sys, os, glob
scriptDir = os.path.abspath(sys.path[0])
opj = os.path.join
digsbyDir = opj(scriptDir, "..")
sys.path += [digsbyDir]
clean = False

from config import *

platDir = opj(scriptDir, platformName)

if "clean" in sys.argv:
    os.system("cd %s;%s buildexts.py clean" %
                (scriptDir, sys.executable))
                
    for afile in glob.glob(os.path.join(platDir, "*")):
        os.remove(afile)
        
    sys.exit(0)

argsAsString = ""

for arg in sys.argv[1:]:
    argsAsString += " " + arg
    
if "PYTHONPATH" in os.environ:
    print "PYTHONPATH is %s" % os.environ["PYTHONPATH"]
else:
    print "PYTHONPATH not set!"

os.system("cd %s;%s buildexts.py install --install-platlib=%s --install-scripts=%s%s" %
                (scriptDir, sys.executable, platDir, platDir, argsAsString))
