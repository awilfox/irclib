from irclib.common.dispatch import PRIORITY_DEFAULT
from irclib.client.user import User
from irclib.common.numerics import *

""" Dispatch names """
def dispatch_names(client, line):
    ch = client.channels.get(line.params[2], None)
    if ch is None: return

    nicks = line.params[-1].split()
    for nick in nicks:
        # Go through each character in the nick
        # look for channel prefixes
        mode = []
        while nick[0] in client.prefix_to_mode:
            # Shift
            prefix = nick[0]
            nick = nick[1:]
            mode.append(client.prefix_to_mode[prefix])

        # Apply
        for m in mode:
            ch.modes.add_mode(m, nick)

        # Add the user
        if nick not in client.users:
            client.users[nick] = User(client, nick)

        # Add channel to user
        client.users[nick].channel_add(ch.name, ch)

        # Add user to channel
        ch.user_add(nick, client.users[nick])


hooks_in = (
    (RPL_NAMREPLY, PRIORITY_DEFAULT, dispatch_names),
)

