#!/usr/bin/env python3

import weakref

class User:
    def __init__(self, network, nick, user=None, host=None, realname=None):
        self.network = network
        self.nick = nick
        self.user = user
        self.host = host
        self.realname = realname

        self.account = None

        self.channels = weakref.WeakValueDictionary()

        self.modes = network.modes[self.nick]

    def userjoin(self, channel):
        self.channels[channel.name] = channel

    def userpart(self, channel):
        del self.channels[channel.name]

