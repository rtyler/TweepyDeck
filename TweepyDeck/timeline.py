#!/usr/bin/env python


# Standard library imports
import logging
import os
import threading


# PyGTK imports
import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import gobject
import pango

# TweepyDeck imports
from TweepyDeck import util

INTERVAL = 120

class Timeline(object):
    widget = None
    api = None
    model = None
    timer = None
    since_id = None
    timeline = 'statuses/friends_timeline.json'
    users = None

    def __init__(self, treeview, api, **kwargs):
        self.__dict__.update(kwargs)

        assert treeview, ('Need a widget', treeview)
        self.widget = treeview
        self.api = api
        self.model = self._generateModel()
        self.users = set()

    def start(self):
        self.widget.set_model(self.model)
        self._createListView()

        self.timer = threading.Timer(1, self._timerCallback)
        self.timer.start()

    def _timerCallback(self, **kwargs):
        self.api.timeline(timeline=self.timeline, since_id=self.since_id, 
                        callback=self._timerUpdatedCallback)
        return False

    def _grabNecessities(self, status):
        return status['user']['screen_name'], status['created_at'], status['user']['profile_image_url']


    def _timerUpdatedCallback(self, data, **kwargs):
        try:
            if data:
                logging.debug('_timerUpdatedCallback [%s], # items: %s' % (self.timeline, len(data)))
                self.since_id = data[0]['id']
                data.reverse()
                for i, status in enumerate(data):
                    what = status['text']
                    
                    # *Very* crude dupe checking
                    if i > 0:
                        prev = data[i-1]
                        if prev['text'] == what:
                            continue

                    who, when, img_url = self._grabNecessities(status)
                    self.users.add(who)
                    image = None
                    try:
                        image = gtk.gdk.pixbuf_new_from_file_at_size(
                                    util.saveImageToFile(who, img_url), 50, 50)
                    except Exception, ex:
                        logging.error('Failed to laod image: %s' % ex)
                        if os.path.exists(util.cachedImagePath(who)):
                            # Prune the dead image file if it's there
                            os.unlink(util.cachedImagePath(who))
                    
                    # Mark it up
                    who = '<b>%s</b>' % who
                    what = self._markupStatus(what)
                    what += '    <i><span size="x-small" weight="light">%s</span></i>' % when
                    self.model.insert(0, (image, who, what))
                    self.widget.scroll_to_point(-1, 1)
        finally:
            gobject.timeout_add_seconds(INTERVAL, self._timerCallback)

    def _generateModel(self):
        return gtk.ListStore(gtk.gdk.Pixbuf, str, str)

    def _addColumn(self, widget, column):
        column.set_resizable(True)      
        widget.append_column(column)

    def _createListView(self):
        column = gtk.TreeViewColumn('', gtk.CellRendererPixbuf(), pixbuf=0)
        column.set_min_width(50)
        self._addColumn(self.widget, column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn('Who', cell, markup=1)
        column.set_min_width(20)
        self._addColumn(self.widget, column)

        cell = gtk.CellRendererText()
        cell.set_property('wrap-mode', pango.WRAP_WORD)
        cell.set_property('wrap-width', 300)
        column = gtk.TreeViewColumn('What', cell, markup=2)
        self._addColumn(self.widget, column)

    def _markupStatus(self, status):
        status = status.replace('\n', ' ').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        pieces = status.split(' ')
        def markup():
            for piece in pieces:
                if not piece:
                    continue
                if piece.startswith('@'):
                    yield '<b>%s</b>' % piece
                elif piece.startswith('http://'):
                    yield '<span foreground="blue"><b>%s</b></span>' % piece
                elif piece.startswith('#'):
                    yield '<span foreground="#FF7F00"><b>%s</b></span>' % piece
                elif len(piece) > 2:
                    if piece[0] == '_' and piece[-1] == '_':
                        yield '<i>%s</i>' % piece[1:-1]
                    elif piece[0] == '*' and piece[-1] == '*':
                        yield '<b>%s</b>' % piece[1:-1]
                    else:
                        yield piece
                else:
                    yield piece

        return ' '.join(markup())

class RepliesTimeline(Timeline):
    timeline = 'statuses/mentions.json'

class SearchesTimeline(Timeline):
    timeline = 'search.json'
    searches = None
    count = 30

    def __init__(self, widget, api, searches, **kwargs):
        super(SearchesTimeline, self).__init__(widget, api, **kwargs)
        self.searches = searches

    def _grabNecessities(self, status):
        return status['from_user'], status['created_at'], status['profile_image_url']

    def _timerCallback(self, **kwargs):
        args = {'q' : ' OR '.join(self.searches)}
        timeline = '%s?%s' % (self.timeline, urllib.urlencode(args))
        self.api.timeline(timeline=timeline, since_id=self.since_id, 
                        callback=self._timerUpdatedCallback, count=self.count)
        return False
