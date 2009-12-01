#!/usr/bin/env python


# Standard library imports
import getpass
import logging
import os.path
import time
from optparse import OptionParser

# PyGTK imports
import pygtk
pygtk.require('2.0')
import gobject
import gtk
import gtk.gdk
import gtk.glade

# TweepyDeck imports
from TweepyDeck import bases
from TweepyDeck import decorators
from TweepyDeck import timeline
from TweepyDeck import twitter
from TweepyDeck import util

if os.getenv('DEBUG'):
    logging.basicConfig(level=logging.DEBUG)

gobject.threads_init()

class Tweep(object):
    widget_tree = None
    last_status = None
    since_id = None

    # Timelines
    friends = None
    replies = None
    searches = None

    search_terms = None

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
            dialog.hide()

    @decorators.accessor
    def statusbar():
        doc = 'Set main window status bar'
        
        def fset(self, value):
            label = self.widget_tree.get_widget('TweepyStatusBar')
            if label:
                label.push(1, value)
        return locals()

    @decorators.accessor
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
        self.statusbar = 'Status last updated at %s' % util.readable_time()

    def login(self, button, **kwargs):
        dialog = self.widget_tree.get_widget('LoginDialog')
        login_entry = self.widget_tree.get_widget('UsernameEntry')
        pass_entry = self.widget_tree.get_widget('PasswordEntry')

        user, password = login_entry.get_text(), pass_entry.get_text()
        
        self.api = twitter.TwitterApi(user, password)


        self.friends = timeline.Timeline(self.api, 
                        parent=self.widget_tree.get_widget('DeckHBox'))
        self.timelines.append(self.friends)
        self.friends.start() # The friends timeline is the only default one

        dialog.destroy()

    def prompt_search(self, *args, **kwargs):
        self.widget_tree.get_widget('SearchTermEntry').set_text('')
        self.widget_tree.get_widget('SearchDialog').show()

    def search_cancel(self, *args, **kwargs):
        self.widget_tree.get_widget('SearchDialog').hide()

    def _spawnSearch(self, term):
        search = timeline.SearchesTimeline(self.api, 
                        parent=self.widget_tree.get_widget('DeckHBox'),
                        term=term)
        self.timelines.append(search)
        search.start()

    def search_okay(self, *args, **kwargs):
        entry = self.widget_tree.get_widget('SearchTermEntry')
        term = entry.get_text()
        if not term:
            return
        self._spawnSearch(term)
        self.widget_tree.get_widget('SearchDialog').hide()

    def toggle_replies(self, button, **kwargs):
        if button.get_active():
            self.replies = timeline.RepliesTimeline(self.api, 
                            parent=self.widget_tree.get_widget('DeckHBox'))
            self.timelines.append(self.replies)
            self.replies.start()
        else:
            print ('replies', locals())

    def toggle_followers(self, button, **kwargs):
        print ('followers', locals())

    def __init__(self, *args, **kwargs):
        self.timelines = []
        self.widget_tree = gtk.glade.XML('tweepydeck.glade')
        self.window = self.widget_tree.get_widget('TweepyMainWindow')
        self.window.connect('destroy', self.destroy)
        self.widget_tree.get_widget('StatusProgressBar').pulse()

        self._events = {
                'on_QuitMenuItem_activate' : self.destroy,
                'on_AboutMenuItem_activate' : self.show_about,
                'on_StatusEntry_key_release_event' : self.status_key,
                'on_StatusEntry_key_press_event' : self.status_autocomplete,

                # Dialogs
                'on_LoginCancelButton_clicked' : self.destroy,
                'on_LoginOkayButton_clicked' : self.login,
                'on_SearchDialogOkay_clicked' : self.search_okay,
                'on_SearchDialogCancel_clicked' : self.search_cancel,

                # Toolbar
                'on_ToolbarSearchButton_clicked' : self.prompt_search,
                'on_RepliesToggle_toggled' : self.toggle_replies,
                'on_FollowersToggle_toggled' : self.toggle_followers,

            }
        self.widget_tree.signal_autoconnect(self._events)


    def main(self):
        gtk.main()


def main():
    app = Tweep()
    util.set_global('app', app)
    app.main()

if __name__ == "__main__":
    main()

# vim: shiftwidth=4 tabstop=4 expandtab
