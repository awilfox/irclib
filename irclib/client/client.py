#!/usr/bin/env python3

import copy
import warnings
import string
import time
import logging

from random import choice, randint
from threading import Timer, Lock

from irclib.client.network import IRCClientNetwork
from irclib.common.line import Line
from irclib.common.util import randomstr

""" Basic IRC client class. Takes a variety of parameters:

    host - hostname to connect to
    port - port to connect to
    nick - nickname to use
    altnick - alternate nickname
    user - username to use (defaults to same as nick)
    realname - GECOS to use
    version - CTCP version reply
    use_ssl - use SSL (default False)
    use_starttls - use STARTTLS where available (default True)
    password - server passwrod
    default_channels - default places to join
    channel_keys - key:value pair of channel keys
    keepalive - interval to send keepalive pings (for lagcheck etc.)
    use_cap - use CAP
"""
class IRCClient:
    def __init__(self, **kwargs):
        self.host = kwargs.get('host')
        self.port = kwargs.get('port')
        self.nick = kwargs.get('nick', 'irclib')
        self.altnick = kwargs.get('altnick', 'irclib_')
        self.user = kwargs.get('user', self.nick)
        self.realname = kwargs.get('realname', 'Python IRC library')
        self.version = kwargs.get('version', 'Python irclib v0.1. (C) Elizabeth Myers')
        self.use_ssl = kwargs.get('use_ssl', False)
        self.password = kwargs.get('password', None)
        self.default_channels = kwargs.get('channels', [])
        self.channel_keys = kwargs.get('channel_keys', {})
        self.keepalive = kwargs.get('keepalive', 15)
        self.use_cap = kwargs.get('use_cap', True)
        self.use_starttls = kwargs.get('use_starttls', True)


        nkwargs = copy.copy(kwargs)
        nkwargs['handshake_cb'] = self.handshake
        nkwargs['logging_cb'] = self.irc_log
        self.network = IRCClientNetwork(**nkwargs)

        # Identified with nickserv
        self.identified = False

        # ISUPPORT storage
        self.isupport = dict()

        # Default handlers
        self.default_dispatch()

        # Are we registered as a user?
        self.registered = False

        # Lag stats
        self.__last_pingstr = None
        self.__last_pingtime = 0
        self.lag = 0

        # Timers
        self.timers = dict()

        # Authoriative
        self.channels = dict()
        self.users = dict()

        # Our logger
        self.logger = logging.getLogger(__name__)


    """ Logging callback """
    def irc_log(self, line, recv):
        if recv:
            ch = '>'
        else:
            ch = '<'

        print('{} {}'.format(ch, line))


    """ Generator for IRC lines, e.g. non-terminating stream """
    def get_lines(self):
        while True:
            for l in self.network.process_in():
                line = (yield l)
                if line is not None:
                    self.linewrite(line)


    """ Create default dispatches
    
    Only override this if you know what this does and what you're doing.
    """
    def default_dispatch(self):
        self.network.dispatch_cmd_in['001'] = self.dispatch_001
        self.network.dispatch_cmd_in['PING'] = self.dispatch_ping
        self.network.dispatch_cmd_in['PONG'] = self.dispatch_pong

        if self.use_starttls:
            self.network.dispatch_cmd_in['670'] = self.dispatch_starttls
            self.network.dispatch_cmd_in['691'] = self.dispatch_starttls

        # CAP state
        if self.use_cap:
            self.network.dispatch_cmd_in['CAP'] = self.dispatch_cap

            # Capabilities
            # TODO - sasl
            self.cap_req = ['multi-prefix', 'account-notify',
                            'away-notify', 'extended-join']

            if self.use_starttls:
                self.cap_req.append('tls')

            # Caps we know
            self.supported_cap = []


    """ Spawns a oneshot timer """
    def timer(self, name, time, function, *args, **kwargs):
        self.timers[name] = Timer(time, function, args=args,
                                  kwargs=kwargs)
        self.timers[name].start()


    """ Cancels a timer if it has not run yet """
    def canceltimer(self, name):
        self.timers[name].cancel()
        del self.timers[name]


    """ Write the user/nick line """
    def dispatch_register(self):
        if not self.registered:
            self.network.cmdwrite('USER', [self.user, '*', '8', self.realname])
            self.network.cmdwrite('NICK', [self.nick])
            self.registered = True

            # TODO - sasl!


    """ Start initial handshake """
    def handshake(self):
        if not self.use_starttls or not self.use_cap:
            self.dispatch_register()
        elif self.use_cap:
            # Request caps
            self.network.cmdwrite('CAP', ['REQ', ' '.join(self.cap_req)])


    """ Dispatches CAP stuff """
    def dispatch_cap(self, line):
        if line.params[1] == 'ACK':
            # Caps follow
            self.supported_cap = line.params[-1].lower().split()
            
            # End negotiation
            self.network.cmdwrite('CAP', ['END'])

            if 'tls' in self.supported_cap and self.use_starttls and not self.use_ssl:
                # Start TLS negotiation
                self.network.cmdwrite('STARTTLS')

            else:
                # Register only if we don't need STARTTLS
                self.dispatch_register()


    """ Dispatch STARTTLS """
    def dispatch_starttls(self, line):
        if line.command == '670':
            # Wrap the socket
            self.network.wrap_ssl()

            # Now safe to do this
            self.dispatch_register()
        elif line.command == '691':
            # Failed somehow.
            self.use_ssl = False
            self.logger.critical('SSL is non-functional on this connection!')
        else:
            self.logger.warn('STARTTLS handler called for no reason o.O')
            pass


    """ Generic dispatcher for ping """
    def dispatch_ping(self, line):
        self.network.cmdwrite('PONG', line.params)


    """ Sends a keepalive message """
    def dispatch_keepalive(self):
        if self.__last_pingstr is not None:
            raise socket.error('Socket timed out')

        self.__last_pingtime = time.time()
        self.__last_pingstr = randomstr()

        self.network.cmdwrite('PING', [self.__last_pingstr])
        self.timer('keepalive', self.keepalive, self.dispatch_keepalive)


    """ Dispatches keepalive message """
    def dispatch_pong(self, line):
        if self.__last_pingstr is None:
            return

        if line.params[-1] != self.__last_pingstr:
            return

        self.__last_pingstr = None
        self.lag = time.time() - self.__last_pingtime
        self.logger.info('LAG: {}'.format(self.lag))


    """ Generic dispatch for RPL_WELCOME 
    
    The default does joins and such
    """
    def dispatch_001(self, line):
        # Set up timer for lagometer
        self.timer('keepalive', self.keepalive, self.dispatch_keepalive)

        # Do joins
        self.combine_channels(self.default_channels, self.channel_keys)


    """ Combine channels """
    def combine_channels(self, chlist, chkeys={}):
        chcount = 0
        buflen = 0
        sbuf = []
        chbuf = []
        keybuf = []
        MAXLEN = 500
        for ch in chlist:
            clen = len(ch) + 1
            key = None 
            if ch in chkeys:
                # +1 for space
                key = chkeys[ch]
                clen = len(key) + 1

            # Sod it. this will never fit. :/
            if clen > MAXLEN:
                self.logger.error('Unable to join channel:key; too long: {}:{}'.format(
                    ch, key))
                continue

            # Full buffer!
            if (buflen + clen) > MAXLEN or len(chbuf) >= 4:
                sbuf.append((chbuf, keybuf))

                chbuf = []
                keybuf = []
                buflen = 0

            # Add to the buffer
            chbuf.append(ch)
            if key: keybuf.append(key)
            buflen += clen

        # Remainder
        if len(chbuf) > 0:
            sbuf.append((chbuf, keybuf))

        for buf in sbuf:
            channels, keys = ','.join(buf[0]), ' '.join(buf[1])
            self.network.cmdwrite('JOIN', (channels, keys))
