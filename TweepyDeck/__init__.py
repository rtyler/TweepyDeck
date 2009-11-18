#!/usr/bin/env python
import pygtk
pygtk.require('2.0')
import gobject
import gtk
import gtk.gdk
import gtk.glade
import pango

import base64
import getpass
import httplib
import logging
import os.path
import string
import threading
import time
import urllib
import urllib2

from optparse import OptionParser

try:
    import json
except ImportError:
    import simplejson as json

if os.getenv('DEBUG'):
    logging.basicConfig(level=logging.DEBUG)

gobject.threads_init()

INTERVAL = 120
DEFAULT_FETCH = 35

def threaded(f):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=f, args=args, kwargs=kwargs)
        t.start()
    return wrapper

def readable_time():
    return time.strftime('%H:%M:%S', time.localtime())

def accessor(func):
    return property(**func())

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

class TwitterApi(object):
    user = None
    password = None
    
    def __init__(self, user, password, **kwargs):
        self.user = user
        self.password = password

    def _auth_header(self):
        return 'Basic ' + string.strip(base64.encodestring(self.user + ':' + self.password))

    def _fetch(self, url):
        logging.debug('_fetch("%s")' % url)
        connection = httplib.HTTPSConnection('twitter.com')
        connection.putrequest('GET', url)
        connection.putheader('Authorization', self._auth_header())
        connection.endheaders()

        try:
            response = connection.getresponse()
            return json.loads(response.read())
        except Exception, ex:
            logging.error(ex)
            return []
        finally:
            connection.close()

    @threaded
    def timeline(self, timeline=None, since_id=None, count=DEFAULT_FETCH, 
            callback=None, loadImages=True):
        args = {'count' : count}
        search = False
        if timeline.startswith('search.json'):
            # Special case search timeline
            search = True
            args = {'rpp' : count}

        if since_id:
            args['since_id'] = since_id

        sep = '?'
        if timeline.find('?') >= 0:
            sep = '&'
        data = self._fetch('/%s%s%s' % (timeline, sep, urllib.urlencode(args)))
        if loadImages:
            if search:
                data = data['results']
            for status in data:
                who, img = None, None
                if not search:
                    who = status['user']['screen_name']
                    img = status['user']['profile_image_url']
                else:
                    who = status['from_user']
                    img = status['profile_image_url']

                try:
                    saveImageToFile(who, img)
                except Exception, ex:
                    logging.error('Downloading failed: %s %s' % (status, ex))

        if not callback:
            return data
        gobject.idle_add(callback, data) 

    @threaded
    def update(self, status, in_reply_to=None, callback=None):
        args = {'status' : status}
        if in_reply_to:
            args['in_reply_to_status_id'] = in_reply_to
        args = urllib.urlencode(args)
        headers = {
                'Content-type' : 'application/x-www-form-urlencoded',
                'Accept' : 'text/plain',
            }
        headers['Authorization'] = self._auth_header()
        connection = httplib.HTTPSConnection('twitter.com')
        connection.request('POST', '/statuses/update.json', args, headers)
        try:
            response = connection.getresponse()
            data = json.loads(response.read())
            if not callback:
                return data
            else:
                gobject.idle_add(callback, data)
        finally:
            connection.close()

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
                                    saveImageToFile(who, img_url), 50, 50)
                    except Exception, ex:
                        logging.error('Failed to laod image: %s' % ex)
                        if os.path.exists(cachedImagePath(who)):
                            # Prune the dead image file if it's there
                            os.unlink(cachedImagePath(who))
                    
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

class Tweep(object):
    widget_tree = None
    last_status = None
    since_id = None

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def status_key(self, widget, event, **kwargs):
        if gtk.gdk.keyval_name(event.keyval) == 'Return':
            status = widget.get_text()
            if status and not status == self.last_status:
                self.last_status = status
                self.statusbar = 'Updating...'
                self.statusentry = ''
                self.api.update(status, callback=self._status_complete)
    
    def status_autocomplete(self, widget, event, **kwargs):
        if not gtk.gdk.keyval_name(event.keyval) == 'Tab':
            return False
        status = widget.get_text()
        parts = status.split(' ')
        if not parts:
            return False
        
        last = parts[-1].replace('@', '')
        if not last:
            return False
        for timeline in self.timelines:
            for user in timeline.users:
                if user.startswith(last):
                    parts[-1] = '@%s' % user
                    text = ' '.join(parts) 
                    widget.set_text(text)
                    widget.set_position(len(text))
                    return True
    
    def show_about(self, widget, **kwargs):
        dialog = self.widget_tree.get_widget('TweepyAboutDialog')
        if dialog:
            dialog.run()
            dialog.destroy()

    @accessor
    def statusbar():
        doc = 'Set main window status bar'
        
        def fset(self, value):
            label = self.widget_tree.get_widget('TweepyStatusBar')
            if label:
                label.push(1, value)
        return locals()

    @accessor
    def statusentry():
        doc = 'Get/set the main window status entry textfield'

        def fget(self):
            entry = self.widget_tree.get_widget('StatusEntry')
            if entry:
                return label.get_text()
        def fset(self, value):
            entry = self.widget_tree.get_widget('StatusEntry')
            if entry:
                entry.set_text(value)
        return locals()
    
    def _status_complete(self, data, **kwargs):
        self.statusbar = 'Status last updated at %s' % readable_time()

    def __init__(self, user, password, searches):
        self.api = TwitterApi(user, password)
        self.timelines = []

        self.widget_tree = gtk.glade.XML('tweepydeck.glade')
        self.window = self.widget_tree.get_widget('TweepyMainWindow')
        self.window.connect('destroy', self.destroy)

        self.friends = Timeline(self.widget_tree.get_widget('FriendsTreeView'), self.api)
        self.timelines.append(self.friends)
        self.replies = RepliesTimeline(self.widget_tree.get_widget('RepliesTreeView'), 
                        self.api)
        self.timelines.append(self.replies)

        if searches:
            self.searches = SearchesTimeline(self.widget_tree.get_widget('SearchTreeView'), self.api, searches)
            self.timelines.append(self.searches)
        else:
            self.widget_tree.get_widget('SearchScrolledWindow').destroy()
    
        for t in self.timelines:
            t.start()

        self._events = {
                'on_QuitMenuItem_activate' : self.destroy,
                'on_AboutMenuItem_activate' : self.show_about,
                'on_StatusEntry_key_release_event' : self.status_key,
                'on_StatusEntry_key_press_event' : self.status_autocomplete,
            }
        self.widget_tree.signal_autoconnect(self._events)

    def main(self):
        gtk.main()

if __name__ == "__main__":
    op = OptionParser()
    op.add_option('-u', '--user', dest='user', help='Your twitter username')
    op.add_option('-s', '--searches', default=None, dest='searches', 
                    help='Comma-separated list of searches')
    opts, args = op.parse_args()
    if not opts.user:
        op.print_help()
        quit()

    password = getpass.getpass('Twitter password for %s: ' % opts.user)
    searches = opts.searches and opts.searches.split(',')

    Tweep(opts.user, password, searches).main()

# vim: shiftwidth=4 tabstop=4 expandtab
