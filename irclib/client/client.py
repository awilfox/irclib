#!/usr/bin/env python3

import importlib
import logging

from irclib.client.network import IRCClientNetwork
from irclib.common.dispatch import Dispatcher
from irclib.common.timer import Timer

""" Basic IRC client class. """
class IRCClient(IRCClientNetwork):
    """
    Creates an instance of IRCClient

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
    kick_autorejoin - rejoin on kick
    kick_wait - wait time for rejoin (5 seconds default)
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.nick = kwargs.get('nick', 'irclib')
        self.altnick = kwargs.get('altnick', 'irclib_')
        self.user = kwargs.get('user', self.nick)
        self.realname = kwargs.get('realname', 'Python IRC library')
        self.version = kwargs.get('version', 'Python irclib v0.1. (C) Elizabeth Myers')
        self.password = kwargs.get('password', None)
        self.default_channels = kwargs.get('channels', [])
        self.channel_keys = kwargs.get('channel_keys', {})
        self.keepalive = kwargs.get('keepalive', 15)
        self.use_cap = kwargs.get('use_cap', True)
        self.use_sasl = kwargs.get('use_sasl', False)
        self.sasl_username = kwargs.get('sasl_username', None)
        self.sasl_pw = kwargs.get('sasl_pw', None)
        self.autorejoin = kwargs.get('kick_autorejoin', False)
        self.autorejoin_wait = kwargs.get('kick_wait', 5)
        self.custom_dispatch = kwargs.get('custom_dispatch', [])

        if self.use_sasl and (not self.sasl_pw or not self.sasl_username):
            self.logger.warn("Unable to use SASL, no username/password provided")
            self.use_sasl = False
        elif self.sasl_username and self.sasl_pw:
            # Use SASL.
            self.use_sasl = True

        if (self.use_sasl or self.use_starttls) and not self.use_cap:
            self.logger.warn("Enabling CAP because starttls and/or sasl requested")
            self.use_cap = True

        # Identified with nickserv
        self.identified = False

        # ISUPPORT storage
        self.isupport = dict()

        # Defaults for ancient-ass servers
        self.isupport['PREFIX'] = [('o', '@'), ('v', '+')]
        self.isupport['CHANTYPES'] = '#&!+' # Old servers tend to use these.
        self.isupport['NICKLEN'] = 8 # Olden servers
        # Not sure if this is correct but it's good enough
        self.isupport['CHANMODES'] = ['beI', 'k', 'l', 'imntsp']
       
        # Default handlers
        self.default_dispatch()

        # Set everything up
        self.reset()


    """ Default oneshot timer implementation """
    def timer_oneshot(self, name, time, function):
        if not hasattr(self, '_timer'):
            self._timer = Timer()

        return self._timer.add_oneshot(name, time, function)


    """ Default recurring timer implementation """
    def timer_repeat(self, name, time, function):
        if not hasattr(self, '_timer'):
            self._timer = Timer()

        return self._timer.add_repeat(name, time, function)


    """ Default cancellation function for timers """
    def timer_cancel(self, name):
        if not hasattr(self, '_timer'):
            raise ValueError('No timers added!')

        return self._timer.cancel(name)

    
    """ Default cancellation function for all timers """
    def timer_cancel_all(self):
        if not hasattr(self, '_timer'):
            raise ValueError('No timers added!')

        return self._timer.cancel_all()


    """ Logging callback """
    def log_callback(self, line, recv):
        if recv:
            ch = '>'
        else:
            ch = '<'

        print('{} {}'.format(ch, line))


    """ Generator for IRC lines, e.g. non-terminating stream """
    def get_lines(self):
        while True:
            for l in self.process_in():
                line = (yield l)
                if line is not None:
                    self.linewrite(line)


    """ Create default dispatches
    
    Only override this if you know what this does and what you're doing.
    """
    def default_dispatch(self):
        # Default list of dispatchers
        dispatchers = ['account', 'away', 'isupport', 'join', 'mode', 'names',
                       'nick', 'part', 'pingpong', 'privmsg', 'quit',
                       'welcome']

        if self.use_starttls:
            dispatchers.append('starttls')
            self.use_cap = True

        if self.use_sasl:
            dispatchers.append('sasl')
            self.use_cap = True

        # CAP state
        if self.use_cap:
            dispatchers.append('cap')

            # Capabilities
            self.cap_req = ['multi-prefix', 'account-notify',
                            'away-notify', 'extended-join']

            if self.use_starttls:
                self.cap_req.append('tls')

            if self.use_sasl:
                self.cap_req.append('sasl')

        def module_add_hooks(module):
            imp = importlib.import_module(module)
            if hasattr(imp, 'hooks_in'):
                for hook in imp.hooks_in:
                    self.add_dispatch_in(*hook)

            if hasattr(imp, 'hooks_out'):
                for hook in imp.hooks_out:
                    self.add_dispatch_out(*hook)

        # Begin the imports
        for module in dispatchers:
            # Ergh I'd like it to use a relative import.
            module = 'irclib.client.dispatch.{}'.format(module)
            module_add_hooks(module)

        for module in self.custom_dispatch:
            module_add_hooks(module)


    """ Reset everything """
    def reset(self):
        # Pending channels
        self.pending_channels = set()

        # Reset caps
        self.supported_cap = []

        # Registered?
        self.registered = False

        # Identified?
        self.identified = False

        # Lag stats
        self._last_pingstr = None
        self._last_pingtime = 0
        self.lag = 0

        try:
            self.timer_cancel_all()
        except ValueError:
            pass

        # Authoriative
        self.channels = dict()
        self.users = dict()


    """ Write the user/nick line """
    def dispatch_register(self):
        if not self.registered:
            self.cmdwrite('USER', [self.user, '+iw', self.host, self.realname])
            self.cmdwrite('NICK', [self.nick])

            if self.password:
                self.cmdwrite('PASS', [self.password])

            self.registered = True

            # End of CAP if we're not using SASL
            if self.use_cap and not self.use_sasl:
                self.terminate_cap()
            elif self.use_sasl and 'sasl' in self.supported_cap:
                self.cmdwrite('AUTHENTICATE', ['PLAIN'])

                # Abort SASL after some time
                self.timer_oneshot('cap_terminate', 15, self.terminate_cap)


    """ Start initial handshake """
    def connect(self, timeout=10):
        super().connect(timeout)

        if not self.use_cap:
            # Not using CAP :(
            self.dispatch_register()
        elif self.use_cap:
            # Request caps
            self.cmdwrite('CAP', ['REQ', ' '.join(self.cap_req)])

            # Cancel CAP after some time
            self.timer_oneshot('cap_terminate', 15, self.terminate_cap)


    """ Terminate CAP """
    def terminate_cap(self):
        self.cmdwrite('CAP', ['END'])


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
            self.cmdwrite('JOIN', (channels, keys))

