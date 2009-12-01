#!/usr/bin/env python


# Standard library imports
import logging
import os
import threading
import urllib


# PyGTK imports
import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import gobject
import pango

# TweepyDeck imports
from TweepyDeck import bases
from TweepyDeck import util

INTERVAL = 120

class Timeline(bases.BaseChildWidget):
    api = None
    since_id = None
    timeline = 'statuses/friends_timeline.json'
    users = None
    rows = None
    rendered = False
    parent = None
    timeline_widget = None

    def __init__(self, api, **kwargs):
        super(Timeline, self).__init__(**kwargs)
        self.api = api
        self.users = set()
        self.rows = []

    def start(self):
        self.reset_timer()

    def reset_timer(self):
        gobject.timeout_add_seconds(1, self._timerCallback)

    def _timerCallback(self, **kwargs):
        self.api.timeline(timeline=self.timeline, since_id=self.since_id, 
                        callback=self._timerUpdatedCallback)
        return False

    def _grabNecessities(self, status):
        return status['user']['screen_name'], status['created_at'], status['user']['profile_image_url']



    def renderTo(self, parent, start=False):
        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.show()
        parent.pack_start(self.scrolled_window)

        self.viewport = gtk.Viewport()
        self.viewport.show()
        self.scrolled_window.add(self.viewport)

        self.timeline_widget = gtk.VBox()
        self.timeline_widget.show()
        self.timeline_widget.set_homogeneous(False)
        self.viewport.add(self.timeline_widget)


    def _timerUpdatedCallback(self, data, **kwargs):
        if not self.rendered:
            self.renderTo(self.parent)

        odd = True
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
                    image = util.saveImageToFile(who, img_url)
                    self.users.add(who)
                    row = BasicTimelineRow(who=who, what=what, when=when, 
                                image=image, odd=odd)
                    odd = not odd
                    self.rows.insert(0, row)
                    row.renderTo(self.timeline_widget)
        finally:
            gobject.timeout_add_seconds(INTERVAL, self._timerCallback)


class RepliesTimeline(Timeline):
    timeline = 'statuses/mentions.json'

class SearchesTimeline(Timeline):
    timeline = 'search.json'
    searches = None
    count = 30

    def __init__(self, widget, api, searches, **kwargs):
        super(SearchesTimeline, self).__init__(widget, api, **kwargs)
        self.searches = searches or []

    def _grabNecessities(self, status):
        return status['from_user'], status['created_at'], status['profile_image_url']

    def _timerCallback(self, **kwargs):
        if not self.searches:
            return False
        args = {'q' : ' OR '.join(self.searches)}
        timeline = '%s?%s' % (self.timeline, urllib.urlencode(args))
        self.api.timeline(timeline=timeline, since_id=self.since_id, 
                        callback=self._timerUpdatedCallback, count=self.count)
        return False

class BasicTimelineRow(bases.BaseChildWidget):
    def _buildContainer(self):
        container = gtk.HBox()
        container.set_size_request(350, -1)
        container.set_homogeneous(False)
        return container

    def _renderAvatar(self, container):
        vbox = gtk.VBox()
        vbox.set_size_request(70, -1)
        vbox.set_homogeneous(False)

        image = gtk.Image()
        image.set_from_file(self.image)
        image.set_size_request(50, 50)

        who = gtk.Label()
        who.set_markup('<b>%s</b>' % self.who)

        vbox.pack_start(image)
        vbox.pack_start(who)
        who.show()
        image.show()
        vbox.show()

        container.pack_start(vbox, expand=False, fill=False, padding=3)

    def renderTo(self, parent, start=False):
        to_show = []
        container = self._buildContainer()
        to_show.append(container)

        self._renderAvatar(container)

        what = gtk.Label()
        self.what = self._markupStatus(self.what)
        what.set_markup('%s    <i><span size="x-small" weight="light">%s</span></i>' % (
                self.what, self.when))
        what.set_size_request(280, -1)
        what.set_line_wrap(True)
        what.set_selectable(True)
        what.set_alignment(0.0, 0.0)
        to_show.append(what)

        container.pack_start(what, expand=True, fill=True)

        for s in to_show:
            s.show()

        _method = parent.pack_start
        if not start:
            _method = parent.pack_end
        _method(container)

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
                    yield '<a href="%s"><b>%s</b></a>' % (piece, piece)
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

