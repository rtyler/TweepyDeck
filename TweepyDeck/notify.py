#!/usr/bin/env python

import logging

USE_LIBNOTIFY = False

try:
    import pynotify
    USE_LIBNOTIFY = True
    pynotify.init('TweepyDeck')
except ImportError:
    print 'Not using libnotify'
    pass


def notify(title, body, iconname):
    if USE_LIBNOTIFY:
        n = pynotify.Notification(title, body, iconname)
        n.set_urgency(pynotify.URGENCY_NORMAL)
        n.set_timeout(pynotify.EXPIRES_DEFAULT)
        n.show()
        return

