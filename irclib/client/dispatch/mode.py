from irclib.common.six import u, b
from irclib.common.numerics import *

""" Dispatch SNOMASK storage """
def dispatch_snomask(client, line):
    client.snomask = line.params[1][1:]


""" Dispatch MODE for channel/user """
def dispatch_mode(client, line):
    target = line.params[0]
    if target == client.current_nick:
        # Us
        client.umodes.parse_modestring(line.params[1:])
        return

    ch = client.channels.get(target, None)
    if ch is None: return

    modestring = u(' ').join(line.params[1:])
    ch.modes.parse_modestring(modestring)


""" Dispatch mode setting """
def dispatch_rpl_mode(client, line):
    ch = client.channels.get(line.params[1], None)
    if ch is None: return

    modestring = u(' ').join(line.params[2:])
    ch.modes.parse_modestring(modestring)


hooks_in = (
    (RPL_SNOMASK, 0, dispatch_snomask),
    ('MODE', 0, dispatch_mode),
    (RPL_CHANNELMODEIS, 0, dispatch_rpl_mode),
)

