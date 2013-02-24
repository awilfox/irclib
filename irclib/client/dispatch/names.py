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
            keepscan = False
            for m, p in client.isupport['PREFIX']:
                if p == name[0]:
                    # Match!
                    name = name[1:] # Shift
                    mode += m
                    keepscan = True # Look again
                    break

        # Apply
        for m in mode:
            ch.modes.add_mode(m, name)

        # Add the user
        if name not in client.users:
            client.users[name] = User(client, name)
            # TODO: issue whois request

        # Add channel to user
        client.users[name].channels[ch.name] = ch

        # Add user to channel
        ch.user_add(name, client.users[name])



hooks_in = (
    (RPL_NAMREPLY, 0, dispatch_names),
)
