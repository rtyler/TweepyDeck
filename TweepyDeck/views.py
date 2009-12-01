#!/usr/bin/env python

# Standard library imports
import logging

# PyGTK imports
import pygtk
pygtk.require('2.0')
import gobject
import gtk
import gtk.gdk

# TweepyDeck imports
from TweepyDeck import bases
from TweepyDeck import decorators
from TweepyDeck import util

views = []
util.set_global('views', views)

class BasicRow(bases.BaseChildWidget):
    @classmethod
    def matchForText(cls, text):
        return True

    @classmethod
    def rowForText(cls, text):
        who = text['user']['screen_name']
        when = text['created_at']
        image = util.saveImageToFile(who, text['user']['profile_image_url'])
        what = text['text']
        return cls(**locals())

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

    def clickedLink(self, label, uri, data, **kwargs):
        if not uri.startswith('tweepy://'):
            return False

        command = uri[9:]
        command, arg = command.split('/')
        if command == 'search':
            util.registry['app']._spawnSearch('#%s' % arg)
        return True

    def renderTo(self, parent, start=False):
        to_show = []
        container = self._buildContainer()
        to_show.append(container)

        self._renderAvatar(container)

        what = gtk.Label()
        self.what = self._markupStatus(self.what)
        what.set_markup('%s    <i><span size="x-small" weight="light">%s</span></i>' % (
                self.what, self.when))
        what.connect('activate-link', self.clickedLink, None)
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
                    yield '<a href="tweepy://search/%s">%s</a>' % (''.join(piece[1:]), piece)
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

views.append(BasicRow)
