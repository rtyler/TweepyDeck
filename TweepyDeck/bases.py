#!/usr/bin/env python

class NotImplementedException(Exception):
    pass

class BaseListView(object):
    widget = None
    def __init__(self, widget, *args, **kwargs):
        assert widget, ('Need a widget', widget)
        self.widget = widget

class BaseChildWidget(object):
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

    def renderTo(self, parent, start=False):
        raise NotImplementedException('Subclasses should implement renderTo()')

