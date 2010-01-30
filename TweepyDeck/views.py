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

class AbstractRow(bases.BaseChildWidget):
    user = None
    fullname = None
    who = None
    when = None
    image = None
    what = None

    @classmethod
    def matchForText(cls, text):
        return False

    @classmethod
    def rowForText(cls, text):
        user = text['user']
        who = text['user']['screen_name']
        fullname = text['user']['name']
        when = text['created_at']
        image = util.saveImageToFile(who, text['user']['profile_image_url'])
        what = text['text']
        return cls(**locals())

    def clickedLink(self, label, uri, data, **kwargs):
        if not uri.startswith('tweepy://'):
            return False

        command = uri[9:]
        command, arg = command.split('/')
        if command == 'search':
            util.get_global('app')._spawnSearch('#%s' % arg)
        return True

    def _renderContainer(self):
        container = gtk.HBox()
        container.set_size_request(350, -1)
        container.set_homogeneous(False)
        container.show()
        return container

    def _avatarTooltip(self):
        return None

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

        tooltip = self._avatarTooltip()
        if tooltip:
            vbox.set_tooltip_markup(tooltip)


        vbox.show()

        container.pack_start(vbox, expand=False, fill=False, padding=3)

    def renderTo(self, parent, start=False):
        container = self._renderContainer()

        self._render(container)

        _method = parent.pack_start
        if not start:
            _method = parent.pack_end
        _method(container)



class BasicRow(AbstractRow):
    @classmethod
    def matchForText(cls, text):
        return True

    def _renderStatus(self, container):
        what = gtk.Label()
        self.what = self._markupStatus(self.what)
        what.set_markup('%s    <i><span size="x-small" weight="light">%s</span></i>' % (
                self.what, self.when))
        what.connect('activate-link', self.clickedLink, None)
        what.set_size_request(280, -1)
        what.set_line_wrap(True)
        what.set_selectable(True)
        what.set_alignment(0.0, 0.0)
        what.show()
        container.pack_start(what, expand=True, fill=True)

    def _render(self, container):
        self._renderAvatar(container)
        self._renderStatus(container)

    def _avatarTooltip(self):
        return '''<b>Name:</b> %s
<b>About:</b> %s
<b>Where:</b> %s
<b>Following back:</b> %s''' % (util.escape(self.fullname),
        util.escape(self.user['description']),
        util.escape(self.user['time_zone']),
        self.user['following'] and 'yes' or 'no')


    def _markupStatus(self, status):
        status = status.replace('\n', ' ').replace('&', '&amp;')
        pieces = status.split(' ')
        def markup():
            for piece in pieces:
                if not piece:
                    continue
                if piece.startswith('@') and len(piece) >= 2:
                    yield '<b>%s</b>' % piece
                elif piece.startswith('http://'):
                    yield '<a href="%s"><b>%s</b></a>' % (piece, piece)
                elif piece.startswith('#') and len(piece) >= 3:
                    # If it's a two-character or larger hashtag, mark it up
                    yield '<a href="tweepy://search/%s">%s</a>' % (''.join(piece[1:]), piece)
                elif len(piece) > 2:
                    if piece[0] == '_' and piece[-1] == '_':
                        # pieces that are _underlined_ should be emphasized
                        yield '<i>%s</i>' % piece[1:-1]
                    elif piece[0] == '*' and piece[-1] == '*':
                        # pieces that are *bolded* should be 
                        yield '<b>%s</b>' % piece[1:-1]
                    else:
                        yield piece
                else:
                    yield piece

        return ' '.join(markup())

views.insert(0, BasicRow)

class SearchRow(BasicRow):
    @classmethod
    def matchForText(cls, text):
        if text.get('from_user'):
            return True
        return False

    @classmethod
    def rowForText(cls, text):
        who = text['from_user']
        when = text['created_at']
        image = util.saveImageToFile(who, text['profile_image_url'])
        what = text['text']
        return cls(**locals())

    def _avatarTooltip(self):
        return None

views.insert(0, SearchRow)

