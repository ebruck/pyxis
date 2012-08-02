#!/usr/bin/env python
#
# Copyright (C) Edward G. Bruck <ed.bruck1@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA.

import os
from gi.repository import Gtk, GObject
from gi.repository import AppIndicator3 as appindicator
from Config import Config, toBool
from Debug import cleanDebug, log
from Exceptions import InvalidStream
from Player import Player
from Sirius import Sirius
import atexit
import time


# TODO: check station list downloader to see if we can preserve case
name_cleanup = { 'trafficandnews'  : "Traffic and News",
                 'howardstern'     : 'Howard Stern',
                 'familyandhealth' : 'Family and Health',
                 'hiphop'          : 'Hip Hop',
                 'publicradio'     : 'Public Radio'}


class AppIndicatorInterface(object):

    def __init__(self, opts, station):
        self.app_indicator = appindicator.Indicator.new ("Pyxis",
                                                         os.path.dirname(__file__) + '/data/dog_gray_mono.svg',
                                                         appindicator.IndicatorCategory.APPLICATION_STATUS)

        self.app_indicator.set_status (appindicator.IndicatorStatus.ACTIVE)
        self.app_indicator.connect("scroll-event", self.on_scroll_event)

        cleanDebug()
        self.histfile = None
        self.config = Config()
        self.sirius = Sirius()
        self.player = Player(opts)
        self.options = opts

        # TODO: read/save in config
        self.last_stream = self.sirius.getStreams()[0]['longName']

        atexit.register(self.on_exit)
        self.notification = toBool(self.config.settings.notifications)
        self.update_timer_id = None
        self.build_menu()

        if station != None:
            self.on_play(None, station)


    def build_menu(self):
        menu = Gtk.Menu()

        # state
        self.state_menuitem = Gtk.MenuItem()
        self.state_menuitem.connect('activate', self.on_start_stop)
        menu.append(self.state_menuitem)
        self.update_state(self.last_stream)

        # volume
        menu.append(Gtk.SeparatorMenuItem())
        state = Gtk.MenuItem('Volume: 100%')
        state.set_sensitive(False)
        menu.append(state)
        menu.append(Gtk.SeparatorMenuItem())

        # streams
        genre_menuitems = {}
        for stream in self.sirius.getStreams():
            genre = stream['genreKey']
            if not genre_menuitems.has_key(genre):
                genre_menu = Gtk.MenuItem(name_cleanup[genre]) if name_cleanup.has_key(genre) else Gtk.MenuItem(genre.title())
                stream_menu = Gtk.Menu()
                stream_item = Gtk.MenuItem(stream['longName'].title())
                stream_item.connect('activate', self.on_play, stream['longName'])
                stream_menu.append(stream_item)
                genre_menu.set_submenu(stream_menu)
                menu.append(genre_menu)
                genre_menuitems[genre] = stream_menu
            else:
                stream_item = Gtk.MenuItem(stream['longName'].title())
                stream_item.connect('activate', self.on_play, stream['longName'])
                genre_menuitems[genre].append(stream_item)

        # about
        menu.append(Gtk.SeparatorMenuItem())
        menu_item = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_ABOUT, None)
        menu_item.connect("activate", self.on_about)
        menu.append(menu_item)

        # quit
        menu_item = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_QUIT, None)
        menu_item.connect("activate", self.on_quit)
        menu.append(menu_item)

        menu.show_all()
        self.app_indicator.set_menu(menu)

        
    def update_state(self, stream):
        if not self.player.playing():
            self.state_menuitem.set_label('Play "' + stream.title() + '"')
            self.app_indicator.set_icon(os.path.dirname(__file__) + '/data/dog_gray_mono.svg')
        else:
            self.state_menuitem.set_label('Stop "' + stream.title() + '"')
            self.app_indicator.set_icon(os.path.dirname(__file__) + '/data/dog_white_mono.svg')


    def on_exit(self):
        try:
            self.player.close()
        except:
            pass


    def on_quit(self, widget):
        Gtk.main_quit()


    def on_start_stop(self, widget):
        if not self.player.playing():
            self.on_play(None, self.last_stream)
        else:
            GObject.source_remove(self.update_timer_id)
            self.update_timer_id = None
            self.stop()

        self.update_state(self.last_stream)


    def on_play(self, widget, stream):
        try:
            log('Play %s' % stream)
            self.sirius.setStreamByLongName(stream)
        except InvalidStream:
            print "Invalid station name. Type 'list' to see available station names"
            return

        self.stop()

        if self.update_timer_id == None:
            self.update_timer_id = GObject.timeout_add(30000, self.on_now_playing_timer)

        url = self.sirius.getAsxURL()
        self.player.play(url, stream)
        self.last_stream = stream
        self.update_state(stream)
        self.update_now_playing(self.sirius.nowPlaying())


    def update_now_playing(self, playing):
        if not self.options.quiet:
            print time.strftime('%H:%M' ) + ' - ' + playing['longName'] + ": " + playing['playing']
        if self.notification:
            from gi.repository import Notify
            if Notify.init("Pyxis"):
                icon = os.path.dirname(__file__) + '/data/dog_white_outline.svg'
                n = Notify.Notification.new("SiriusXM", playing['longName'] + ": " + playing['playing'], icon)
                n.show()


    def stop(self):
        try:
            self.player.close()
        except:
            pass
        
    
    def on_about(self, widget):
        pass
    
    
    def on_scroll_event(self, indicator, delta, direction):
        # TODO: extend StreamHandler to issue volume commands to mplayer
        if direction == 0:
            print "volume up"
        else:    
            print "volume down"


    def on_now_playing_timer(self):
        playing =  self.sirius.nowPlaying()
        if playing['new']:
            self.update_now_playing(playing)
        return True


    def run(self):
        Gtk.main()


if __name__== "__main__":
    # {'record': False, 'setup': False, 'list': False, 'quiet': False, 'output': None}
    import optparse
    opts = optparse.Values()
    opts.record = False
    opts.quiet = False
    AppIndicatorInterface(opts, None).run()

