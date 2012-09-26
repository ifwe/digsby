if __name__ == '__main__':
    __builtins__._ = lambda s: s

import sys
import os.path
import unittest

# the src directory
unittest_basedir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../..'))

def plugin_test_dirs(plugins):
    '''Given a list of PluginLoader objects, returns a sequence of "test"
    directories, if they exist, under each plugin's path.'''

    dirs = []
    for p in plugins:
        for dir in ('unittests', 'tests'):
            dir = p.path / dir
            if dir.isdir():
                dirs.append(dir)
    
    return dirs

def get_tests(app):
    dirs = [os.path.dirname(__file__)] + plugin_test_dirs(app.plugins)

    from discover import DiscoveringTestLoader
    loader = DiscoveringTestLoader()

    all_tests = unittest.TestSuite()
    for rootdir in dirs:
        tests = loader.discover(rootdir, pattern='*test*.py', top_level_dir=unittest_basedir)
        all_tests.addTests(tests)

    return all_tests

def run_tests():
    from tests.testapp import testapp
    app = testapp()

    runner = unittest.TextTestRunner(verbosity = 2)

    all_tests = get_tests(app)

    orig_dir = os.getcwd()
    os.chdir(unittest_basedir)
    try:
        test_result = runner.run(all_tests)
    finally:
        os.chdir(orig_dir)

    sys.exit(not test_result.wasSuccessful())

if __name__ == '__main__':
    run_tests()

