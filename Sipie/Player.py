#!/usr/bin/python
# -*- coding: utf-8 -*-
# Eli Criffield < pyeli AT zendo DOT net >
# Licensed under GPLv2 See: http://www.gnu.org/licenses/gpl.txt


from Factory import Factory, LoginError, AuthError, InvalidStream
from StreamHandler import MplayerHandler

class Player(Factory):
    def __init__(self, options):
        super(Player, self).__init__(options)
        self.streamHandler = MplayerHandler(options)
        
    def play(self):
        try:
            self.close()
        except:
            pass
        self.streamHandler.setURL(self.asxURL)
        self.streamHandler.play()

    def mute(self):
        self.streamHandler.mute()

    def pause(self):
        self.streamHandler.pause()

    def close(self):
        self.streamHandler.close()
