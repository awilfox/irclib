#!/usr/bin/env python3

import errno
import warnings
import socket
import logging

from irclib.common.line import Line
from irclib.common.util import socketerror

try:
    import ssl
except ImportError:
    warnings.warn('Could not load SSL implementation, SSL will not work!',
                  RuntimeWarning)
    ssl = None


class IRCClientNetwork:
    def __init__(self, **kwargs):
        self.host = kwargs.get('host')
        self.port = kwargs.get('port')
        self.use_ssl = kwargs.get('use_ssl', False)
        self.use_starttls = kwargs.get('use_starttls', True)
        self.hs_callback = kwargs.get('handshake_cb')
        self.log_callback = kwargs.get('logging_cb')
        self.reset_callback = kwargs.get('connreset_cb')

        if self.hs_callback is None:
            raise RuntimeError('No valid connection handshaking in place')

        if self.log_callback is None:
            self.log_callback = lambda x, y: None

        if self.reset_callback is None:
            self.reset_callback = lambda: None

        if any(e is None for e in (self.host, self.port)):
            raise RuntimeError('No valid host or port specified')

        if ssl is None:
            if self.use_ssl:
                # Explicit SSL use
                raise RuntimeError('SSL support is unavailable')
            elif self.use_starttls:
                # Implicit SSL use
                warnings.warn('Unable to use STARTTLS; SSL support is unavailable')
                self.use_starttls = False

        if self.use_ssl:
            # Unneeded and probably harmful. :P
            self.use_starttls = False

        # Connection flag
        self.connected = False
        self.sock = None

        # Dispatch
        self.dispatch_cmd_in = dict()
        self.dispatch_cmd_out = dict()

        # Our logger
        self.logger = logging.getLogger(__name__)


    """ Write a Line instance to the wire """
    def linewrite(self, line):
        # Call hook for this command
        # if it returns true, cancel
        if self.call_dispatch_out(line):
            self.logger.debug("Cancelled event due to hook request")
            return

        self.log_callback(line, False)
        self.send(bytes(line))


    """ Write a raw command to the wire """
    def cmdwrite(self, command, params=[]):
        self.linewrite(Line(command=command, params=params))


    """ Connect to the server

    timeout for connect defaults to 10. Set to None for no timeout.
    Note gevent will not be pleased if you do not have a timeout.
    """
    def connect(self, timeout=10):
        if not self.connected:
            self.sock = socket.socket()
            self.__buffer = ''
            self.reset_callback()

        if timeout is not None:
            self.sock.settimeout(timeout)
        self.sock.connect((self.host, self.port))
        self.connected = True

        if self.use_ssl and not self.use_starttls:
            self.wrap_ssl()

        self.hs_callback()


    """ Wrap the socket in SSL """
    def wrap_ssl(self):
        self.sock = ssl.wrap_socket(self.sock)
        self.use_ssl = True


    """ Recieve data from the wire """
    def recv(self):
        self.sock.settimeout(None)
        while '\r\n' not in self.__buffer:
            try:
                data = self.sock.recv(2048)
            except socket.error:
                self.connected = False
                raise

            if not data:
                socketerror(errno.ECONNRESET, instance=self)

            self.__buffer += data.decode('UTF-8', 'replace')

        lines = self.__buffer.split('\r\n')
        self.__buffer = lines.pop() 

        return lines


    """ Send data onto the wire """
    def send(self, data):
        sendlen = len(data)
        curlen = 0
        while curlen < sendlen:
            try:
                curlen += self.sock.send(data[curlen:])
            except socket.error:
                self.connected = False
                raise


    """ Dispatch for a command incoming """
    def call_dispatch_in(self, line):
        if line.command in self.dispatch_cmd_in:
            self.dispatch_cmd_in[line.command](line)


    """ Dispatch for a command outgoing """
    def call_dispatch_out(self, line):
        if line.command in self.dispatch_cmd_out:
            return self.dispatch_cmd_out[line.command](line)


    """ Recieve lines """
    def process_in(self):
        if not self.connected:
            self.connect()
        lines = [Line(line=line) for line in self.recv()]

        for line in lines:
            self.log_callback(line, True)
            self.call_dispatch_in(line)

        return lines

