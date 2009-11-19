#!/usr/bin/env python

class NotImplementedException(Exception):
    pass

class BaseListView(object):
    widget = None
    model = None
    def __init__(self, widget, *args, **kwargs):
        assert widget, ('Need a widget', widget)
        self.widget = widget
        self.model = self._generateModel()
        self.widget.set_model(self.model)

    def _addColumn(self, widget, column):
        column.set_resizable(True)      
        widget.append_column(column)

    def initializeList(self):
        raise NotImplementedException('Subclass failed to implement initializeList()')

    def _generateModel(self):
        raise NotImplementedException('Subclass failed to implement _generateModel()')


