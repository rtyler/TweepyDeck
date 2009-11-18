#!/usr/bin/env python

import threading

def threaded(f):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=f, args=args, kwargs=kwargs)
        t.start()
    return wrapper

def accessor(func):
    return property(**func())
