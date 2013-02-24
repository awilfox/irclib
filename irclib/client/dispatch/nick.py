from irclib.client.user import User
from irclib.common.numerics import *

""" Nickname tracking """
def dispatch_nick(client, line):
    oldnick = line.hostmask.nick
    newnick = line.param[-1]

    # We might even have these :P
    user = line.hostmask.user
    host = line.hostmask.host

    if oldnick == client.current_nick:
        # Our own nick
        client.current_nick = newnick
        return

    # Other user's nick
    if oldnick in client.users:
        client.users[newnick] = client.users[oldnick]
        client.users[newnick].nick = newnick
        client.users[newnick].user = user
        client.users[newnick].host = host

        # Update in channels
        for channel, ch in client.channels.items():
            if oldnick in ch.users:
                ch.user_rename(oldnick, newnick)

        # Delete the old nick :3
        del client.users[oldnick]
    else:
        client.logger.debug('Got a nick change for unknown user {}:{}'.format(
            oldnick, newnick))
        # Not sure why this is happening but ok.
        client.users[newnick] = User(client, newnick, user, host)


hook_in = (
    ('NICK', 0, dispatch_nick),
)
