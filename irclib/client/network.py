#!/usr/bin/env python3

import errno
import warnings
import socket
import string
import time
import logging

from random import choice, randint
from threading import Timer, Lock

from irclib.common.line import Line

try:
    import ssl
except ImportError:
    warnings.warn("Could not load SSL implementation, SSL will not work!",
                  RuntimeWarning)
    ssl = None


def randomstr():
    validstr = string.ascii_letters + string.digits
    return ''.join([choice(validstr) for x in range(randint(3, 10))])


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


        if any(e is None for e in (self.host, self.port)):
            raise RuntimeError("No valid host or port specified")

        if ssl is None and self.use_ssl:
            raise RuntimeError("SSL support is unavailable")

        self.__buffer = ''

        self.sock = socket.socket()
        self.identified = False
        self.isupport = dict()

        # Locks writes
        self.writelock = Lock()

        # Dispatch
        self.dispatch_cmd = dict()

        self.dispatch_cmd["001"] = self.dispatch_001
        self.dispatch_cmd["PING"] = self.dispatch_ping
        self.dispatch_cmd["PONG"] = self.dispatch_pong

        if self.use_starttls:
            self.dispatch_cmd["670"] = self.dispatch_starttls
            self.dispatch_cmd["691"] = self.dispatch_starttls

        # CAP state
        if self.use_cap:
            self.dispatch_cmd["CAP"] = self.dispatch_cap

            # Capabilities
            self.cap_req = ['multi-prefix', 'tls']
            # TODO - support these
            #, 'account-notify', 'away-notify', 'extended-join', 'sasl']

            # Caps we know
            self.supported_cap = []

        # Are we registered as a user?
        self.registered = False

        # Lag stats
        self.__last_pingstr = None
        self.__last_pingtime = 0
        self.lag = 0

        # Handshake
        self.handshake = 0

        # Timers
        self.timers = dict()

        # Authoriative
        self.channels = dict()
        self.users = dict()


        self.logger = logging.getLogger(__name__)


    """ Pretty printing of IRC stuff outgoing
    
    Override this for custom logging.
    """
    def writeprint(self, line):
        print("<", repr(line))


    """ Pretty printing of IRC stuff incoming

    Override this for custom logging
    """
    def readprint(self, line):
        print(">", repr(line))


    """ Write a Line instance to the wire """
    def linewrite(self, line):
        with self.writelock:
            self.writeprint(line)
            self.sock.send(bytes(line))


    """ Write a raw command to the wire """
    def cmdwrite(self, command, params=[]):
        self.linewrite(Line(command=command, params=params))


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
    def __register_self(self):
        if not self.registered:
            self.cmdwrite("USER", [self.user, '*', '8', self.realname])
            self.cmdwrite("NICK", [self.nick])
            self.registered = True

            # TODO - sasl!


    """ Connect to the server

    timeout for connect defaults to 10. Set to None for no timeout.
    Note gevent will not be pleased if you do not have a timeout.
    """
    def connect(self, timeout=10):
        if timeout is not None:
            self.sock.settimeout(timeout)
        self.sock.connect((self.host, self.port))

        if not self.use_starttls or not self.use_cap:
            self.__register_self()
        elif self.use_cap:
            # Request caps
            self.cmdwrite("CAP", ["REQ", ' '.join(self.cap_req)])


    """ Raw receive of lines. Only does basic wrapping in a Line instance.
        Will wait until it has at least one line.
    """
    def raw_receive(self):
        # assume we're connected.
        self.sock.settimeout(None)
        while '\r\n' not in self.__buffer:
            data = self.sock.recv(2048)

            if not data:
                raise socket.error(errno.ECONNRESET,
                                   os.strerror(errno.ECONNRESET))

            self.__buffer += data.decode('UTF-8', 'replace')

        lines = self.__buffer.split('\r\n')
        self.__buffer = lines[-1]
        del lines[-1]

        lines = [Line(line=line) for line in lines]

        for line in lines:
            if line.command in self.dispatch_cmd:
                self.dispatch_cmd[line.command](line)

        return lines


    """ Generator for IRC lines, e.g. non-terminating stream """
    def get_lines(self):
        while True:
            for x in self.raw_receive():
                self.readprint(x)
                line = (yield x)
                if line is not None:
                    self.linewrite(line)


    """ Dispatches CAP stuff """
    def dispatch_cap(self, line):
        if line.params[1] == 'ACK':
            # Caps follow
            self.supported_cap = line.params[-1].lower().split()
            
            # End negotiation
            self.cmdwrite("CAP", ["END"])

            if 'tls' in self.supported_cap and self.use_starttls and not self.use_ssl:
                # Start TLS negotiation
                self.cmdwrite("STARTTLS")

            else:
                # Register only if we don't need STARTTLS
                self.__register_self()


    """ Dispatch STARTTLS """
    def dispatch_starttls(self, line):
        if line.command == '670':
            # Wrap the socket
            self.sock = ssl.wrap_socket(self.sock)
            self.use_ssl = True

            # Now safe to do this
            self.__register_self()
        elif line.command == '691':
            # Failed somehow.
            self.use_ssl = False
            self.logger.critical('SSL is non-functional on this connection!')
        else:
            self.logger.warn('STARTTLS handler called for no reason o.O')
            pass


    """ Generic dispatcher for ping """
    def dispatch_ping(self, line):
        self.cmdwrite('PONG', line.params)


    """ Sends a keepalive message """
    def dispatch_keepalive(self):
        if self.__last_pingstr is not None:
            raise socket.error("Socket timed out")

        self.__last_pingtime = time.time()
        self.__last_pingstr = randomstr()

        self.cmdwrite('PING', [self.__last_pingstr])
        self.timer("keepalive", self.keepalive, self.dispatch_keepalive)


    """ Dispatches keepalive message """
    def dispatch_pong(self, line):
        if self.__last_pingstr is None:
            return

        if line.params[-1] != self.__last_pingstr:
            return

        self.__last_pingstr = None
        self.lag = time.time() - self.__last_pingtime
        self.logger.info("LAG: {}".format(self.lag))


    """ Generic dispatch for RPL_WELCOME 
    
    The default does joins and such

    XXX - dike this out a bit more
    """
    def dispatch_001(self, line):
        # Set up timer for lagometer
        self.timer("keepalive", self.keepalive, self.dispatch_keepalive)

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
                self.logger.error("Unable to join channel:key; too long: {}:{}".format(
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
