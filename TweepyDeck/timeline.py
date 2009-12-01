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
from TweepyDeck import views
from TweepyDeck import util

INTERVAL = 120

class Timeline(bases.BaseChildWidget):
    api = None
    since_id = None
    timeline = 'statuses/home_timeline.json'
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
            self.rendered = True

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

                    renderer = None
                    for view in util.get_global('views'):
                        if not view.matchForText(status):
                            continue
                        renderer = view
                        break

                    logging.debug('rendering %s with %s' % (status['id'], renderer))

                    if not renderer:
                        continue

                    row = renderer.rowForText(status) 
                    self.users.add(row.who)
                    self.rows.insert(0, row)
                    row.renderTo(self.timeline_widget)
        finally:
            gobject.timeout_add_seconds(INTERVAL, self._timerCallback)


class RepliesTimeline(Timeline):
    timeline = 'statuses/mentions.json'

class SearchesTimeline(Timeline):
    timeline = 'search.json'
    term = None
    count = 30

    def _grabNecessities(self, status):
        return status['from_user'], status['created_at'], status['profile_image_url']

    def _timerCallback(self, **kwargs):
        if not self.term:
            return False
        args = {'q' : self.term}
        timeline = '%s?%s' % (self.timeline, urllib.urlencode(args))
        self.api.timeline(timeline=timeline, since_id=self.since_id, 
                        callback=self._timerUpdatedCallback, count=self.count)
        return False

