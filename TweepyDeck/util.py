#!/usr/bin/env python

import os
import time
import urllib2

def readable_time():
    return time.strftime('%H:%M:%S', time.localtime())

def cachedImagePath(who):
    return '/tmp/%s.png' % who

def saveImageToFile(who, img_url):
    img = cachedImagePath(who)
    if os.path.exists(img):
        return img

    web_fd = urllib2.urlopen(img_url)
    data = web_fd.read()
    web_fd.close()

    fd = open(img, 'w')
    fd.write(data)
    fd.close()
    return img
