#!/usr/bin/env python

# Standard library imports
import gettext
import logging
import math

# PyGTK imports
import cairo
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
_ = gettext.gettext

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


class RoundedBox(gtk.EventBox):
    color = 'white'
    padding = 2 # Padding from edges of parent
    rounded = 10 # How round to make the edges

    def __init__(self, *args, **kwargs):
        super(RoundedBox, self).__init__(*args, **kwargs)

        self.connect('size-allocate', self._on_size_allocate)
        self.modify_bg(gtk.STATE_NORMAL, 
                    self.get_colormap().alloc_color(self.color))

    def _on_size_allocate(self, win, allocation):
        """Shape the window into a rounded rectangle."""
        w,h = allocation.width, allocation.height
        bitmap = gtk.gdk.Pixmap(None, w, h, 1)

        # Clear the bitmap
        fg = gtk.gdk.Color(pixel=0)
        bg = gtk.gdk.Color(pixel=-1)
        fg_gc = bitmap.new_gc(foreground=fg, background=bg)
        bitmap.draw_rectangle(fg_gc, True, 0, 0, w, h)

        # Draw our shape into the pixmap using cairo
        # Let's try drawing a rectangle with rounded edges.
        padding = self.padding
        rounded = self.rounded
        cr = bitmap.cairo_create()
        cr.set_source_rgb(0,0,0)
        # Move to top corner
        cr.move_to(0+padding+rounded, 0+padding)

        # Top right corner and round the edge
        cr.line_to(w-padding-rounded, 0+padding)
        cr.arc(w-padding-rounded, 0+padding+rounded, rounded, math.pi/2, 0)
        # Bottom right corner and round the edge
        cr.line_to(w-padding, h-padding-rounded)
        cr.arc(w-padding-rounded, h-padding-rounded, rounded, 0, math.pi/2)
        # Bottom left corner and round the edge.
        cr.line_to(0+padding+rounded, h-padding)
        cr.arc(0+padding+rounded, h-padding-rounded, rounded, math.pi+math.pi/2, math.pi)
        # Top left corner and round the edge
        cr.line_to(0+padding, 0+padding+rounded)
        cr.arc(0+padding+rounded, 0+padding+rounded, rounded, math.pi/2, 0)
        # Fill in the shape.
        cr.fill()
        # Set the window shape
        win.shape_combine_mask(bitmap, 0, 0)

class Status(object):
    text = None
    timestamp = None

    def __init__(self, text, when, **kwargs):
        self.text = text
        self.timestamp = when

    def _markup_generator(self, pieces):
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

    def markup_text(self, text):
        status = util.escape(text)
        pieces = status.split(' ')
        return ' '.join(self._markup_generator(pieces))

    def clickedLink(self, label, uri, data, **kwargs):
        if not uri.startswith('tweepy://'):
            return False

        command = uri[9:]
        command, arg = command.split('/')
        if command == 'search':
            util.get_global('app')._spawnSearch('#%s' % arg)
        return True

    def widget(self):
        roundedbox = RoundedBox()
        roundedbox.show()

        labelbox = gtk.EventBox()
        labelbox.set_border_width(5)
        labelbox.modify_bg(gtk.STATE_NORMAL, 
                labelbox.get_colormap().alloc_color(roundedbox.color))

        what = gtk.Label()
        what.set_markup('%s\n<i><span size="x-small" weight="light">%s</span></i>' %
                (self.markup_text(self.text), self.timestamp))
        what.connect('activate-link', self.clickedLink, None)
        what.set_size_request(280, -1)
        what.set_line_wrap(True)
        what.set_selectable(True)
        what.set_alignment(0.0, 0.0)
        labelbox.add(what)
        roundedbox.add(labelbox)
        labelbox.show()
        what.show()
        return roundedbox


class BasicRow(AbstractRow):
    @classmethod
    def matchForText(cls, text):
        return True

    def _renderStatus(self, container):
        self.status = Status(self.what, self.when)
        container.pack_start(self.status.widget(), expand=True, fill=True)

    def _render(self, container):
        self._renderAvatar(container)
        self._renderStatus(container)

    def _avatarTooltip(self):
        tooltip  = _('''<b>Name:</b> %(name)s
<b>About:</b> %(description)s
<b>Where:</b> %(time_zone)s
<b>Following back:</b> %(following)s''')
        return tooltip % {
        'name' : util.escape(self.fullname),
        'description' : util.escape(self.user['description']),
        'time_zone' : util.escape(self.user['time_zone']),
        'following' : self.user['following'] and _('yes') or _('no')}

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

