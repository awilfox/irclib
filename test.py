from irclib.client import network
from irclib.common.line import Line

n = network.IRCClient(nick='shittybot', host='irc.interlinked.me', port=6667,
                      channels=['#alyx'])
n.connect()

g = n.get_lines()
for l in g:
    pass
#    print(l)

