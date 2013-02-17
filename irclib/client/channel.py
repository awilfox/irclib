#!/usr/bin/env python3

import weakref

class Channel:
    def __init__(self, network, name):
        self.network = network
        self.name = name

        self.users = weakref.WeakValueDictionary()

        self.modes = network.modes[self.name]

        self.parting = False
