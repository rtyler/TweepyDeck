#!/usr/bin/env python
from __future__ import with_statement

import logging
import threading

import gobject


# Enumeration of signals
PROGRESS_START = -100
PROGRESS_STOP  = -101


__main_lock = threading.RLock()
__signals = None

def observe(the_signal, callback):
    global __signals
    with __main_lock:
        if __signals is None:
            __signals = {}
        __signals.setdefault(the_signal, []).append(callback)

def emit(the_signal, **kwargs):
    global __signals
    with __main_lock:
        if __signals is None or not __signals.get(the_signal):
            return
        for callback in __signals[the_signal]:
            gobject.idle_add(lambda: callback(**kwargs))
    


