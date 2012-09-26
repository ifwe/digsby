from time import clock
start_time = clock()

import gc
import os
import sys
import wx
from os.path import join as pathjoin
from random import shuffle

imgexts = 'png gif bmp ico jpg jpeg'.split()

def isimage(filename):
    e = filename.endswith
    return any(e(ext) for ext in imgexts)

def images(path):
    for name in os.listdir(path):
        if isimage(name):
            yield pathjoin(path, name)

def all_images(path):
    for root, dirs, files in os.walk(path):
        for file in files:
            f = pathjoin(root, file)
            if isimage(f):
                yield f

def main():
    a = wx.PySimpleApp()

    imgs = list(all_images('res'))[:20]
    #imgs = ['res/happynewdigsby.png']

    print len(imgs), 'images'
    #shuffle(imgs)

    excludes = ()

    for img in imgs:
        if img not in excludes:
            print >> sys.stderr, img
            wx.Bitmap(img)


    print clock() - start_time


if __name__ == '__main__':
    main()
