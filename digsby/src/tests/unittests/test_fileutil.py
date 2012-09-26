from __future__ import with_statement
from tests import TestCase, test_main
from tempfile import NamedTemporaryFile

from util.primitives.files import atomic_write, filecontents
from uuid import uuid4
import os.path

class TestFileUtil(TestCase):
    def test_atomic_write(self):
        temp_name = os.path.join('c:\\', 'test_abc_def.txt')
        assert not os.path.isfile(temp_name)

        try:
            # a fresh file: write to temporary and then rename will be used
            with atomic_write(temp_name) as f:
                f.write('good')

            assert filecontents(temp_name) == 'good'

            # a second time: ReplaceFile will be used on Windows
            with atomic_write(temp_name) as f:
                f.write('good 2')

            assert filecontents(temp_name) == 'good 2'


            # TODO: test error during a write

        finally:
            if os.path.isfile(temp_name):
                os.remove(temp_name)

if __name__ == '__main__':
    test_main()
