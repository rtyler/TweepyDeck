#!/usr/bin/env python
from __future__ import with_statement

# Standard library imports
import base64
import httplib
import logging
import os
import string
import urllib

try:
    import yajl as json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        import json

# PyGTK imports
import gobject

# TweepyDeck imports
from TweepyDeck import decorators
from TweepyDeck import signals
from TweepyDeck import util


DEFAULT_FETCH = 35
TWITTER_DOMAIN = 'twitter.com'
DEBUG_HOME_FILE = 'hometimeline.json'
DEBUG_SEARCH_FILE = 'searchtimeline.json'

class TwitterApi(object):
    user = None
    password = None

    def __init__(self, user, password, **kwargs):
        self.user = user
        self.password = password

    def _auth_header(self):
        return 'Basic ' + string.strip(base64.encodestring(self.user + ':' + self.password))

    def _fetch(self, url):
        is_search = url.startswith('/search.json')
        logging.debug('_fetch("%s")' % url)
        if os.environ.get('DEBUG') and os.environ.get('USEFILES'):
            if not is_search:
                with open(DEBUG_HOME_FILE, 'r') as fd:
                    return json.loads(fd.read())
            else:
                with open(DEBUG_SEARCH_FILE, 'r') as fd:
                    return json.loads(fd.read())

        connection = None
        if is_search:
            connection = httplib.HTTPConnection(TWITTER_DOMAIN)
        else:
            connection = httplib.HTTPSConnection(TWITTER_DOMAIN)
        connection.putrequest('GET', url)
        if not is_search:
            # No need to send extra bits in for searches
            connection.putheader('Authorization', self._auth_header())
        connection.endheaders()

        try:
            response = connection.getresponse()
            data = response.read()
            if os.environ.get('DEBUG'):
                if is_search:
                    with open(DEBUG_SEARCH_FILE, 'w') as fd:
                        fd.write(data)
                else:
                    with open(DEBUG_HOME_FILE, 'w') as fd:
                        fd.write(data)
            return json.loads(data)
        except Exception, ex:
            logging.error(ex)
            return []
        finally:
            connection.close()

    @decorators.threaded
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
        data = None
        try:
            util.get_global('app').in_progress = True
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
                        util.saveImageToFile(who, img)
                    except Exception, ex:
                        logging.error('Downloading failed: %s %s' % (status, ex))
        finally:
            util.get_global('app').in_progress = False
            if not callback:
                return data
            gobject.idle_add(callback, data)

    @decorators.threaded
    def update(self, status, in_reply_to=None, callback=None):
        logging.debug('update("%s", in_reply_to=%s)' % (status, in_reply_to))
        signals.emit(signals.PROGRESS_START)
        args = {'status' : status}
        if in_reply_to:
            args['in_reply_to_status_id'] = in_reply_to
        args = urllib.urlencode(args)
        headers = {
                'Content-type' : 'application/x-www-form-urlencoded',
                'Accept' : 'text/plain',
            }
        headers['Authorization'] = self._auth_header()
        connection = httplib.HTTPSConnection(TWITTER_DOMAIN)
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
            signals.emit(signals.PROGRESS_STOP)

    @decorators.threaded
    def retweet(self, status_id, callback=None):
        logging.debug('retweet(%s)' % status_id)
        signals.emit(signals.PROGRESS_START)
        headers = {
                'Content-type' : 'application/x-www-form-urlencoded',
                'Accept' : 'text/plain',
            }
        headers['Authorization'] = self._auth_header()
        connection = httplib.HTTPSConnection(TWITTER_DOMAIN)
        connection.request('POST', '/statuses/retweet/%s.json' % status_id, '', headers)
        try:
            response = connection.getresponse()
            data = json.loads(response.read())
            if not callback:
                return data
            else:
                gobject.idle_add(callback, data)
        finally:
            connection.close()
            signals.emit(signals.PROGRESS_STOP)

