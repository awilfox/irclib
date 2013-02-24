#!/usr/bin/env python3

import weakref
from irclib.common.modes import ModeSet

class Channel(object):
    def __init__(self, network, name):
        self.network = network
        self.name = name

        self.users = weakref.WeakValueDictionary()

        # Gather these from ISUPPORT
        # Note there is a race here - if you instantiate this, and ISUPPORT is
        # not in yet, you WILL get incorrect modes until you update this. YOU
        # HAVE BEEN WARNED.
        p_prefix = ''.join(p[0] for p in network.isupport['PREFIX'])
        p_list, p_set, p_both, = network.isupport['CHANMODES'][:3]

        self.modes = ModeSet(p_list=p_list, p_set=p_set, p_both=p_both,
                             p_prefix=p_prefix)

        # Are we parting the channel?
        self.parting = False

        # Defaults
        self.timestamp = 0
        self.url = None

        self.topic = None
        self.topic_who = None
        self.topic_time = None


    def user_add(self, nick, user):
        self.users[nick] = user


    def user_del(self, nick):
        self.users.pop(nick, None)


    def user_rename(self, oldnick, newnick):
        user = self.users.pop(oldnick, None)
        if not user: return

        self.users[newnick] = user

