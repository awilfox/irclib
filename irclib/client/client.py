#!/usr/bin/env python3

import copy
import warnings
import string
import time
import logging
import base64
import re

from functools import partial
from itertools import zip_longest

from irclib.client.channel import Channel
from irclib.client.network import IRCClientNetwork
from irclib.common.numerics import *
from irclib.common.dispatch import Dispatcher
from irclib.common.line import Line
from irclib.common.util import randomstr
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

        if self.use_sasl and (not self.sasl_pw or not self.sasl_username):
            self.logger.warn("Unable to use SASL, no username/password provided")
            self.use_sasl = False
        elif self.sasl_username and self.sasl_pw:
            # Use SASL.
            self.use_sasl = True

        if self.use_sasl:
            send = '{acct}\0{acct}\0{pw}'.format(acct=self.sasl_username,
                                                 pw=self.sasl_pw)
            send = base64.b64encode(send.encode('UTF-8'))
            self.__sasl_send = send.decode('ascii')

        if (self.use_sasl or self.use_starttls) and not self.use_cap:
            warnings.warn("Enabling CAP because starttls and/or sasl requested")
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
        self.add_dispatch_in(RPL_WELCOME, 0, self.dispatch_welcome)
        self.add_dispatch_in(RPL_ISUPPORT, 0, self.dispatch_isupport)

        self.add_dispatch_in('PING', 0, self.dispatch_ping)
        self.add_dispatch_in('PONG', 0, self.dispatch_pong)

        self.add_dispatch_in('JOIN', 5, self.dispatch_self_join)
        self.add_dispatch_in('PART', 5, self.dispatch_self_part)
        self.add_dispatch_in('KICK', 5, self.dispatch_self_part)

        self.add_dispatch_out('JOIN', 5, self.dispatch_pending_join)
        self.add_dispatch_out('PART', 5, self.dispatch_pending_part)

        self.add_dispatch_in('MODE', 0, self.dispatch_mode)
        self.add_dispatch_in(RPL_CHANNELMODEIS, 0, self.dispatch_mode)
        self.add_dispatch_in(RPL_NAMREPLY, 0, self.dispatch_names)

        # Channel errors
        cherr = [ERR_LINKCHANNEL, ERR_CHANNELISFULL, ERR_INVITEONLYCHAN,
                 ERR_BANNEDFROMCHAN, ERR_BADCHANNELKEY, ERR_BADCHANMASK,
                 ERR_NEEDREGGEDNICK, ERR_BADCHANNAME, ERR_THROTTLE, ERR_KEYSET]
        for e in cherr:
            self.add_dispatch_in(e, 0, self.dispatch_err_join)

        if self.use_starttls:
            self.add_dispatch_in(RPL_STARTTLS, 0, self.dispatch_starttls)
            self.add_dispatch_in(ERR_STARTTLS, 0, self.dispatch_starttls)

        if self.use_sasl:
            self.add_dispatch_in('AUTHENTICATE', 0, self.dispatch_sasl)
            self.add_dispatch_in(RPL_LOGGEDIN, 0, self.dispatch_sasl)
            self.add_dispatch_in(RPL_SASLSUCCESS, 0, self.dispatch_sasl)
            self.add_dispatch_in(ERR_SASLFAIL, 0, self.dispatch_sasl)
            self.add_dispatch_in(ERR_SASLTOOLONG, 0, self.dispatch_sasl)

        # CAP state
        if self.use_cap:
            self.add_dispatch_in('CAP', 0, self.dispatch_cap)

            # Capabilities
            self.cap_req = ['multi-prefix', 'account-notify',
                            'away-notify', 'extended-join']

            if self.use_starttls:
                self.cap_req.append('tls')

            if self.use_sasl:
                self.cap_req.append('sasl')


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
        self.__last_pingstr = None
        self.__last_pingtime = 0
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


    """ Dispatches CAP stuff """
    def dispatch_cap(self, line):
        if line.params[1] == 'ACK':
            # Cancel
            self.timer_cancel('cap_terminate')

            # Caps follow
            self.supported_cap = line.params[-1].lower().split()
            
            if 'tls' in self.supported_cap and self.use_starttls and not self.use_ssl:
                # Start TLS negotiation
                self.cmdwrite('STARTTLS')
            else:
                # Register only if we don't need STARTTLS
                self.dispatch_register()


    """ Terminate CAP """
    def terminate_cap(self):
        self.cmdwrite('CAP', ['END'])


    """ Dispatch STARTTLS """
    def dispatch_starttls(self, line):
        if line.command == RPL_STARTTLS:
            # Wrap the socket
            self.wrap_ssl()

            # Now safe to do this
            self.dispatch_register()
        elif line.command == ERR_STARTTLS:
            # Failed somehow.
            self.use_ssl = False
            self.logger.critical('SSL is non-functional on this connection!')
        else:
            self.logger.warn('STARTTLS handler called for no reason o.O')
            pass


    """ Dispatch SASL """
    def dispatch_sasl(self, line):
        self.timer_cancel('cap_terminate')

        if line.command == 'AUTHENTICATE':
            # We got an authentication message?
            if line.params[0] != '+':
                self.logger.warn('Unexpected response from SASL auth agent, '
                                 'continuing')

            if not self.identified:
                # Separate into 400 byte chunks
                send = self.__sasl_send
                split = [send[i:i+400] for i in range(0, len(send), 400)]
                for item in split:
                    self.cmdwrite('AUTHENTICATE', [item])

                # Padding, if needed
                if len(split[-1]) == 400:
                    self.cmdwrite('AUTHENTICATE', ['+'])

                # Timeout authentication
                self.timer_oneshot('cap_terminate', 15, self.terminate_cap)
        elif line.command == RPL_LOGGEDIN:
            # SASL auth succeeded
            self.identified = True
        elif line.command == RPL_SASLSUCCESS:
            # end CAP
            self.terminate_cap()
        elif line.command in (ERR_SASLFAIL, ERR_SASLTOOLONG):
            # SASL failed
            self.logger.error('SASL auth failed! Error: {} {}'.format(
                              line.command,
                              line.params[-1]))
            self.terminate_cap()
        else:
            self.logger.debug('No handler for SASL numeric {}'.format(
                              line.command))


    """ Dispatch ISUPPORT """
    def dispatch_isupport(self, line):
        try:
            isupport = line.params[2:-1]
        except:
            self.logger.error('ISUPPORT broken, probably old server')
            return

        for token in isupport:
            name, sep, value = token.partition('=')

            # We parse the most common ones.
            # Pretty much anything else is up to you.
            if value:
                if name == 'PREFIX':
                    # This is surprisingly a job best done for regex.
                    m = re.match(r'\((.+)\)(.+)', value)

                    # No match. :(
                    if m is None: continue
                    letter, prefix = m.groups()

                    if len(letter) != len(prefix):
                        # Your server is fucked yo.
                        self.logger.warn('Broken IRC server; PREFIX is broken '
                                         '(unbalanced prefixes and modes)')
                        continue
                    
                    value = list(zip(letter, prefix))
                elif name.endswith('LEN') or name in ('MODES', 'MONITOR'):
                    # These are probably numeric values
                    if value.isdigit:
                        value = int(value)
                elif name == 'EXTBAN':
                    # Urgh this breaks the de-facto spec
                    split = value.partition(',')
                    if split[1]:
                        value = (split[0], split[2])
                else:
                    # Attempt to parse as follows:
                    #
                    # - Comma separated values
                    # - key : value pairs
                    split = value.split(',')
                    valuelist = []

                    for item in split:
                        key, sep, value = item.partition(':')
                        if sep:
                            item = (key, value)

                        valuelist.append(item)

                    if len(valuelist) == 1:
                        # One item only
                        value = valuelist[0]
                    elif len(valuelist) > 1:
                        value = valuelist
            else:
                # No value
                value = None

            # Set
            self.isupport[name] = value
            self.logger.debug('ISUPPORT token: {} {}'.format(name, value))


    """ Generic dispatcher for ping """
    def dispatch_ping(self, line):
        self.cmdwrite('PONG', line.params)


    """ Sends a keepalive message """
    def dispatch_keepalive(self):
        if self.__last_pingstr is not None:
            raise socket.error('Socket timed out')

        self.__last_pingtime = time.time()
        self.__last_pingstr = randomstr()

        self.cmdwrite('PING', [self.__last_pingstr])


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
    def dispatch_welcome(self, line):
        # Set our nickname
        self.current_nick = line.params[0]

        # Set up timer for lagometer
        self.timer_repeat('keepalive', self.keepalive, self.dispatch_keepalive)

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
            self.cmdwrite('JOIN', (channels, keys))


    """ Outgoing hook for pending joins """
    def dispatch_pending_join(self, line):
        if len(line.params) == 0: return

        chlist = line.params[0].split(',')
        self.pending_channels.update(chlist)


    """ Outgoing hook for pending parts """
    def dispatch_pending_part(self, line):
        if len(line.params) == 0: return

        chlist = line.params[0].split(',')
        self.pending_channels.difference_update(chlist)

        for channel in chlist:
            if channel not in self.channels: continue

            # Mark us as parting
            self.channels[channel].parting = True


    """ Dispatch us joining """
    def dispatch_self_join(self, line):
        if not line.hostmask: return

        # When proper nick tracking is implemented, uncomment this
        #if line.hostmask.nick != self.current_nick:
        #    return

        # Probably not gonna happen but better safe than sorry. :P
        chlist = line.params[0].split(',')
        if self.pending_channels.issuperset(chlist):
            self.pending_channels.difference_update(chlist)

        # Add the channel
        for channel in chlist:
            self.channels[channel] = Channel(self, channel)

            # Request modes
            self.cmdwrite('MODE', [channel])


    """ Dispatch errors joining """
    def dispatch_err_join(self, line):
        self.logger.warn('Could not join channel {}: {} {}'.format(
            line.params[1], line.command, line.params[-1]))

        self.pending_channels.discard(line.params[1])


    """ Dispatch us parting/being kicked """
    def dispatch_self_part(self, line):
        if not line.hostmask: return

        # When proper nick tracking is implemented, uncomment this
        #if line.hostmask.nick != self.current_nick:
        #    return

        channel = line.params[0]
        self.pending_channels.discard(channel)

        ch = self.channels.pop(channel, None)
        if ch is None: return 

        if not ch.parting:
            self.logger.warn('Removed from channel {}'.format(channel))

        if line.command == 'KICK' or not ch.parting:
            if self.autorejoin:
                # Use key if needed
                key = ch.modes.has_mode('k')
                if not key:
                    key = ''

                # synthesise a function to do the rejoin, and fire it on a timer
                rejoin_func = partial(self.cmdwrite, 'JOIN', (channel, key))
                self.timer_oneshot('rejoin_ch_{}'.format(channel),
                                   self.autorejoin_wait, rejoin_func)


    """ Dispatch mode setting """
    def dispatch_mode(self, line):
        ch = self.channels.get(line.params[1], None)
        if ch is None: return

        modestring = ' '.join(line.params[2:])
        ch.modes.parse_modestring(modestring)


    """ Dispatch names """
    def dispatch_names(self, line):
        ch = self.channels.get(line.params[2], None)
        if ch is None: return

        names = line.params[-1].split()
        for name in names:
            # Go through each name
            keepscan = True # Ensure at least one iteration
            mode = ''
            while keepscan:
                keepscan = False
                for m, p in self.isupport['PREFIX']:
                    if p == name[0]:
                        # Match!
                        name = name[1:] # Shift
                        mode += m
                        keepscan = True # Look again
                        break

            # Apply
            for m in mode:
                ch.modes.add_mode(m, name)

