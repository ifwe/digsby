# open_im_window.py

from api import wait
from time import clock

def main():
    before = clock()
    print 'before'
    yield wait(1000)
    print 'after'
    after = clock()

    print after - before

# python Digsby.py --script=open_im_window.py

