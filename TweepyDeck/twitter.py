#!/usr/bin/env python

# Standard library imports
import base64
import httplib
import logging 
import string
import urllib

try:
    import json
except ImportError:
    import simplejson as json

# PyGTK imports
import gobject

# TweepyDeck imports
from TweepyDeck import decorators
from TweepyDeck import util


DEFAULT_FETCH = 35

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
            if not callback:
                return data
            gobject.idle_add(callback, data) 

    @decorators.threaded
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

