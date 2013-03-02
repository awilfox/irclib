#!/usr/bin/env python3

import errno
import warnings
import socket
import logging
from threading import RLock
from abc import ABCMeta, abstractmethod

from irclib.common.six import u
from irclib.common.dispatch import Dispatcher
from irclib.common.line import Line
from irclib.common.util import socketerror
from irclib.common.timer import Timer

try:
    import ssl
except ImportError:
    warnings.warn('Could not load SSL implementation, SSL will not work!',
                  RuntimeWarning)
    ssl = None


class IRCClientNetwork(object):
    __metaclass__ = ABCMeta

    def __init__(self, **kwargs):
        self.host = kwargs.get('host')
        self.port = kwargs.get('port')
        self.use_ssl = kwargs.get('use_ssl', False)
        self.use_starttls = kwargs.get('use_starttls', True)
        self.blocking = kwargs.get('blocking', True)

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

        # Non-blocking errors
        errs = ('EINPROGRESS', 'EWOULDBLOCK', 'EAGAIN', 'EINTR', 'ERESTART',
                'ENOBUFS', 'ENOENT')
        self.nonblock = list(filter(None, [getattr(errno, e, None) for e in
                                           errs]))

        if ssl:
            sslerrs = (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE,
                       ssl.SSL_ERROR_WANT_CONNECT)
            self.nonblock.extend(sslerrs)

        # Connection flag
        self.connected = False
        self.sock = None
        self.ssl_wrapped = False

        # Dispatch
        self.dispatch_cmd_in = Dispatcher()
        self.dispatch_cmd_out = Dispatcher()

        self.dispatch_ctcp_in = Dispatcher()

        # Our logger
        self.logger = logging.getLogger(__name__)

        # Our I/O lock
        self.inlock = RLock()
        self.outlock = RLock()
        self.connlock = RLock()


    """ Default connection reset method """
    @abstractmethod
    def reset(self):
        pass


    """ Default logging callback """
    @abstractmethod
    def log_callback(self, line, recv):
        pass


    """ Write a Line instance to the wire """
    def linewrite(self, line):
        # Call hook for this command
        # Also call the hook matching all commands (None)
        # if any return true, cancel
        ret = list()
        ret.extend(self.call_dispatch_out(line))
        ret.extend(self.call_dispatch_out(None))

        if any(x[1] for x in ret):
            self.logger.debug('Cancelled event due to hook request')
            return

        # Check also if the line's been cancelled
        if line.cancelled:
            self.logger.debug('Line cancelled due to hook')

        self.log_callback(line, False)
        self.send(bytes(line))


    """ Write a CTCP request to the wire """
    def ctcpwrite(self, target, command, params=''):
        response = u('\x01{} {}\x01').format(command, params)
        self.cmdwrite('PRIVMSG', (target, response))


    """ Write a CTCP reply to the wire """
    def nctcpwrite(self, target, command, params=''):
        response = u('\x01{} {}\x01').format(command, params)
        self.cmdwrite('NOTICE', (target, response))


    """ Write a raw command to the wire """
    def cmdwrite(self, command, params=[]):
        self.linewrite(Line(command=command, params=params))


    """ Connect to the server

    timeout for connect defaults to 10. Set to None for no timeout.
    Note gevent will not be pleased if you do not have a timeout.
    """
    def connect(self, timeout=10):
        with self.connlock:
            if not self.connected:
                self.sock = socket.socket()
                self.setblocking(self.blocking)

                if self.use_ssl and not self.use_starttls:
                    self.wrap_ssl()

                self.send_buffer = bytes()
                self.recv_buffer = bytes() 
                self.ssl_wrapped = False
                self.reset()

            if timeout is not None:
                self.sock.settimeout(timeout)

            self.sock.connect((self.host, self.port))
            if self.blocking:
                self.connected = True


    """ Wrap the socket in SSL """
    def wrap_ssl(self):
        with self.connlock:
            if self.connected:
                self.logger.info('Beginning SSL wrapping')

            if self.ssl_wrapped:
                self.logger.warn('Attempting to wrap SSL-wrapped class')

            try:
                self.sock = ssl.wrap_socket(self.sock)
            except (IOError, OSError) as e:
                if e.errno in self.nonblock:
                    self.use_ssl = True
                    self.ssl_wrapped = True
                raise

            self.use_ssl = True
            self.ssl_wrapped = True


    """ Set the socket non-blocking """
    def setblocking(self, block):
        with self.connlock:
            self.sock.setblocking(block)
            self.blocking = block


    """ Recieve data from the wire """
    def recv(self):
        with self.inlock:
            # Assume connected
            self.connected = True

            self.sock.settimeout(None)
            try:
                data = self.sock.recv(2048)
            except (IOError, OSError) as e:
                if e.errno not in self.nonblock:
                    self.connected = False
                raise

            if not data:
                socketerror(errno.ECONNRESET, instance=self)

            self.recv_buffer += data
            lines = self.recv_buffer.split(b'\r\n')
            self.recv_buffer = lines.pop()

            if lines:
                lines = [l.decode('utf-8', 'replace') for l in lines]

            return lines


    """ Send data onto the wire """
    def send(self, data=None):
        with self.outlock:
            # Assume connected
            self.connected = True

            if data:
                self.send_buffer += data
                if not self.blocking:
                    # Non-blocking mode
                    return

            if not self.send_buffer:
                return

            try:
                sendlen = self.sock.send(self.send_buffer)
                self.send_buffer = self.send_buffer[sendlen:]
            except (IOError, OSError) as e:
                if e.errno not in self.nonblock:
                    self.connected = False
                raise

            if self.blocking:
                # Drain the buffer in blocking mode
                while self.send_buffer:
                    self.send()


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


    """ Dispatch for a command incoming """
    def call_dispatch_in(self, line):
        if line is None:
            if self.dispatch_cmd_in.has_name(None):
                return self.dispatch_cmd_in.run(None, (self, line))
        else:
            if self.dispatch_cmd_in.has_name(line.command):
                return self.dispatch_cmd_in.run(line.command, (self, line))

        return [(None, None)]


    """ Dispatch for a command outgoing """
    def call_dispatch_out(self, line):
        if line is None:
            if self.dispatch_cmd_out.has_name(None):
                return self.dispatch_cmd_out.run(None, (self, line))
        else:
            if self.dispatch_cmd_out.has_name(line.command):
                return self.dispatch_cmd_out.run(line.command, (self, line))
        
        return [(None, None)]


    """ Dispatch for CTCP incoming """
    def call_ctcp_in(self, line, target, command, param):
        if self.dispatch_ctcp_in.has_name(command):
            return self.dispatch_ctcp_in.run(command, (self, line, target,
                                                       command, param))


    """ Add command dispatch for input
    
    callback function must take line as first argument
    """
    def add_dispatch_in(self, command, priority, function):
        self.dispatch_cmd_in.add(command, priority, function)


    """ Add command dispatch for output

    callback function must take line as first argument

    for a wildcard callback, use None as your command (as in type(None))
    """
    def add_dispatch_out(self, command, priority, function):
        self.dispatch_cmd_out.add(command, priority, function)


    """ Add CTCP dispatch function """
    def add_ctcp_in(self, command, priority, function):
        self.dispatch_ctcp_in.add(command, priority, function)


    """ Recieve and process lines (blocking version) """
    def process_in(self):
        if not self.connected:
            self.connect()

        return self.process_lines(self.recv())


    """ Process lines for real """
    def process_lines(self, lines):
        lines = [Line(line=line) for line in lines]

        for line in lines:
            self.call_dispatch_in(line)
            self.log_callback(line, True)

        return lines

