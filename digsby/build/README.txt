building-on-mac-instructions
----------------------------

install python from python.org
make sure "python" on the PATH is python 2.6

svn co http://svn.python.org/projects/sandbox/trunk/setuptools
  cd setuptools
  python setup.py install

install git
install bakefile

cd build
./build-deps.py --wx_trunk --debug --python_deps

