import sys, os.path as path
sys.path.append(path.join(path.split(__file__)[0], 'aspell'))
del sys, path


from pyaspell import Aspell
from spellcheck import spellchecker, SpellChecker, SpellEngine
