#!/usr/bin/env python3

from itertools import islice
from collections import deque

from irclib.common.six import u, b

""" Stores a user hostmask

>>> repr(Hostmask(mask="dongs!cocks@lol.org"))
'Hostmask(dongs!cocks@lol.org)'
>>> repr(Hostmask(mask="dongs@lol.org"))
'Hostmask(dongs@lol.org)'
>>> repr(Hostmask(mask="lol.org"))
'Hostmask(lol.org)'
"""
class Hostmask:
    def __init__(self, **kwargs):
        mask = kwargs.get("mask", None)
        self.nick = kwargs.get("nick", None)
        self.user = kwargs.get("user", None)
        self.host = kwargs.get("host", None)
        if mask is not None:
            self.__parse_hostmask(mask)

    def __parse_hostmask(self, mask, encoding='UTF-8'):
        if isinstance(mask, bytes):
            mask = mask.decode(encoding)

        # Step 1: split out host and rest
        part1, sep, part2 = mask.partition('@')

        if len(sep) == 0:
            # Is it a nick or a host?
            if part1.find('.') != -1:
                # Host!
                self.nick = None
                self.user = None
                self.host = part1
            else:
                # Nick!
                self.nick = part1
                self.user = None
                self.host = None
        else:
            # We have a nick and a host, at the minimum
            # Check for a username
            self.host = part2

            part1, sep, part2 = part1.partition('!')
            self.nick = part1 # Always going to be the nick :p

            self.user = part2 if sep else None

    def __str__(self):
        if not any((self.nick, self.user, self.host)):
            return ''

        if self.nick and not self.host:
            # Nick only
            return self.nick

        elif not self.nick and self.host:
            # Host only
            return self.host
        else:
            # Both
            if self.user:
                return self.nick + '!' + self.user + '@' + self.host
            else:
                return self.nick + '@' + self.host

    def __bytes__(self):
        return str(self).encode('UTF-8')

    def __repr__(self):
        return "Hostmask({})".format(str(self))

""" Stores an IRC line

>>> repr(Line(line=":lol.org PRIVMSG"))
'Line(:lol.org PRIVMSG)'
>>> repr(Line(line="PING"))
'Line(PING)'
>>> repr(Line(line="PING Elizacat"))
'Line(PING Elizacat)'
>>> repr(Line(line="PING Elizacat :dongs"))
'Line(PING Elizacat :dongs)'
>>> repr(Line(line="PING :dongs"))
'Line(PING :dongs)'
>>> repr(Line(line=":dongs!dongs@lol.org PRIVMSG loldongs meow :dongs"))
'Line(:dongs!dongs@lol.org PRIVMSG loldongs meow :dongs)'
"""
class Line:
    def __init__(self, *kargs, **kwargs):
        if len(kargs) == 0:
            line = kwargs.get("line", None)
            self.tags = kwargs.get("tags", None)
            self.hostmask = kwargs.get("host", None)
            self.command = kwargs.get("command", None)
            self.params = kwargs.get("params", [])
        elif len(kargs) == 1:
            line = kargs[0]
        elif len(kargs) == 2:
            self.command = kargs[0]
            self.params = kargs[1]
        else:
            self.command = kargs[0]
            self.params = kargs[1:]

        if line is not None:
            self.__parse_line(line)

        self.cancelled = False

    def __parse_line(self, line, encoding='UTF-8'):
        if isinstance(line, bytes):
            line = line.decode(encoding)

        line = line.rstrip('\r\n')

        # Split out the last param, which might have spaces
        # If not there, this transformation does nothing
        # XXX - I don't like partition here like this at all. It might not
        # handle tab. But it works ok and no server I know of will send anything
        # else other than space-separated parameters.
        line, sep, lparam = line.partition(' :')

        # Split
        sp = deque(x for x in line.split() if x is not None)

        # Do we have tags?
        if sp[0].startswith('@'):
            # TODO - more parsing of tags
            self.tags = sp[0][1:]
            sp.popleft()
        else:
            self.tags = None

        # Do we have a mask?
        if sp[0].startswith(':'):
            self.hostmask = Hostmask(mask=sp[0][1:])
            sp.popleft()
        else:
            self.hostmask = None

        assert len(sp) > 0

        # Command next
        self.command = sp.popleft()

        # Params?
        self.params = sp
        if lparam:
            # Append
            self.params.append(lparam)

        # Because deques are poopy and don't support nice things like slicing
        self.params = list(self.params)

    def __str__(self):
        line = []
        if self.hostmask:
            line.append(':' + str(self.hostmask))

        line.append(self.command)

        if self.params:
            if any(x in (' ', ':') for x in self.params[-1]):
                line.extend(self.params[:-1])
                line.append(':' + self.params[-1])
            else:
                line.extend(self.params)

        return u(' ').join(line) + u('\r\n')

    def __bytes__(self):
        return str(self).encode('UTF-8')

    def __repr__(self):
         return 'Line({})'.format(str(self))

if __name__ == "__main__":
    import doctest
    doctest.testmod()

