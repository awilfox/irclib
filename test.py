from irclib.client import network
from irclib.common.line import Line

def reply(line, generator):
    if len(line.params) <= 1: return

    target = line.params[0]
    msg = line.params[-1]

    # TODO more words for dicks.
    if msg.lower() not in ('dicks', 'dongs', 'cocks', 'penises'):
        return

    # we just assume these are the only valid channels for now
    # XXX not upheld on ircnet
    if target[0] not in ('#', '&'):
        target = line.hostmask.nick

    generator.send(Line(command='PRIVMSG', params=(target, 'mmm :) cocks.')))

n = network.IRCClient(nick='shittybot', host='irc.interlinked.me', port=6667,
                      channels=['#alyx'])
n.connect()

g = n.get_lines()
for l in g:
    if l.command == "PRIVMSG":
        reply(l, g)

