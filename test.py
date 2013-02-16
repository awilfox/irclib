#!/usr/bin/env python3

from irclib.client import network
from irclib.common.line import Line
from random import choice, randint

randomshit = [
    'I have to go in five minutes',
    'what?',
    '?',
    'I don\'t know what that is in swedish',
    'I had to go to the fotvårdsspecialist (no idea what that is in English)',
    'I need to shower in a few minutes. make it quick',
    '^',
    'Liz, ^',
    'Night ->',
    'bbl',
    'Perhaps you should use erlang, or scheme.',
    'FORTH is a wonderful language',
    'Use Clojure!',
    'maybe use some kind of message passing',
    'what does that mean',
    'I have no idea what that means',
    'Stop that',
    'that bot is annoying',
    'there, I have it on ignore now.',
    'but can it run emacs? that\'s important',
    'ew vim',
    'LISP is an awesome language',
    'Haskell makes you think in new ways',
    'perhaps you should play nethack',
    'try playing skyrim',
    'where is the data taken from?',
    '\x01ACTION made a bot in bash\x01',
]

def spew(line, generator):
    if randint(0, 24) != 0:
        return

    if len(line.params) <= 1: return

    target = line.params[0]
    msg = line.params[-1]

    # we just assume these are the only valid channels for now
    # XXX not upheld on ircnet
    if target[0] not in ('#', '&'):
        target = line.hostmask.nick

    generator.send(Line(command='PRIVMSG', params=(target, choice(randomshit))))

n = network.IRCClient(nick='Verpel', host='okami.interlinked.me', port=6667,
                      channels=['#alyx', '#sporks', '#irclib'])
n.connect()

g = n.get_lines()
for l in g:
    if l.command == "PRIVMSG":
        spew(l, g)

