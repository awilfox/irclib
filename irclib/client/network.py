#!/usr/bin/env python3

import errno
import warnings
import socket

from irclib.common.line import Line

try:
    import ssl
except ImportError:
    warnings.warn("Could not load SSL implementation, SSL will not work!",
                  RuntimeWarning)
    ssl = None

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
        self.default_keys = kwargs.get('channel_keys', {})

        if any(e is None for e in (self.host, self.port)):
            raise RuntimeError("No valid host or port specified")

        if ssl is None and self.use_ssl:
            raise RuntimeError("SSL support is unavailable")

        self.__buffer = ''

        self.sock = socket.socket()
        self.identified = False
        self.isupport = dict()

        # Capabilities
        self.caps = ['multi-prefix']
        # TODO - support these
        #, 'account-notify', 'away-notify', 'extended-join', 'sasl', 'tls'*]

        # Dispatch
        self.dispatch_cmd = dict()

        self.dispatch_cmd["001"] = self.dispatch_001
        self.dispatch_cmd["PING"] = self.dispatch_ping

        # Authoriative
        self.channels = dict()
        self.users = dict()


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
        self.writeprint(line)
        self.sock.send(bytes(line))


    """ Write a raw command to the wire """
    def cmdwrite(self, command, params=[]):
        self.linewrite(Line(command=command, params=params))


    """ Connect to the server

    timeout for connect defaults to 10. Set to None for no timeout.
    Note gevent will not be pleased if you do not have a timeout.
    """
    def connect(self, timeout=10):
        if timeout is not None:
            self.sock.settimeout(timeout)
        self.sock.connect((self.host, self.port))
        self.cmdwrite("USER", [self.user, '*', '8', self.realname])
        self.cmdwrite("NICK", [self.nick])


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


    """ Generic dispatcher for ping """
    def dispatch_ping(self, line):
        self.cmdwrite('PONG', line.params)


    """ Generic dispatch for RPL_WELCOME 
    
    The default does joins and such
    """
    def dispatch_001(self, line):
        # Combine channels
        chcount = 0
        buflen = 0
        sbuf = []
        chbuf = []
        keybuf = []
        MAXLEN = 500
        for ch in self.default_channels:
            clen = len(ch) + 1
            key = None 
            if ch in self.default_keys:
                # +1 for space
                key = self.default_keys[ch]
                clen = len(key) + 1

            # Sod it. this will never fit. :/
            if clen > MAXLEN: continue

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

