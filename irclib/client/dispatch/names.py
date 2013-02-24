from irclib.client.user import User
from irclib.common.numerics import *

""" Dispatch names """
def dispatch_names(client, line):
    ch = client.channels.get(line.params[2], None)
    if ch is None: return

    names = line.params[-1].split()
    for name in names:
        # Go through each name
        keepscan = True # Ensure at least one iteration
        mode = ''
        while keepscan:
            # If we don't find a prefix, there's nothing else to look for.
            # We assume there isn't for this reason.
            keepscan = False

            # Check for prefix
            if name[0] in client.prefix_to_mode:
                # Shift
                prefix = name[0]
                name = name[1:]
                mode += client.prefix_to_mode[prefix]

                # We found one. There could be another, thus
                keepscan = True # look for more

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
    (RPL_NAMREPLY, 0, dispatch_names),
)

