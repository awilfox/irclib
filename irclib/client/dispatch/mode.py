from irclib.common.numerics import *

""" Dispatch mode setting """
def dispatch_mode(client, line):
    ch = client.channels.get(line.params[1], None)
    if ch is None: return

    modestring = ' '.join(line.params[2:])
    ch.modes.parse_modestring(modestring)


hooks_in = (
    ('MODE', 0, dispatch_mode),
    (RPL_CHANNELMODEIS, 0, dispatch_mode),
)

