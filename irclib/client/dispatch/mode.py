from irclib.common.numerics import *

""" Dispatch mode setting """
def dispatch_mode(client, line):
    ch = client.channels.get(line.params[1], None)
    if ch is None: return

    modestring = ' '.join(line.params[2:])
    ch.modes.parse_modestring(modestring)


""" Dispatch timestamp setting """
def dispatch_ts(client, line):
    channel = self.params[1]
    client.channels[channel].timestamp = int(self.params[-1])


""" Dispatch channel URL setting """
def dispatch_url(client, line):
    channel = self.params[1]
    client.channels[channel].url = self.params[-1]


hooks_in = (
    ('MODE', 0, dispatch_mode),
    (RPL_CHANNELMODEIS, 0, dispatch_mode),
    (RPL_CREATIONTIME, 0, dispatch_ts),
    (RPL_CHANNELURL, 0, dispatch_url),
)

