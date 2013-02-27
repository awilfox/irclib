from irclib.common.dispatch import PRIORITY_DEFAULT
from irclib.client.user import User
from irclib.common.numerics import *

""" Dispatch names """
def dispatch_names(client, line):
    ch = client.channels.get(line.params[2], None)
    if ch is None: return

    names = line.params[-1].split()
    for name in names:
        # Go through each character in the name
        # look for channel prefixes
        mode = []
        while name[0] in client.prefix_to_mode:
            # Shift
            prefix = name[0]
            name = name[1:]
            mode.append(client.prefix_to_mode[prefix])

        # Apply
        for m in mode:
            ch.modes.add_mode(m, name)

        # Add the user
        if name not in client.users:
            client.users[name] = User(client, name)

        # Add channel to user
        client.users[name].channels[ch.name] = ch

        # Add user to channel
        ch.user_add(name, client.users[name])


hooks_in = (
    (RPL_NAMREPLY, PRIORITY_DEFAULT, dispatch_names),
)

