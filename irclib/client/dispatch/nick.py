from random import randint

from irclib.common.dispatch import PRIORITY_DEFAULT
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
        client.create_user(newnick, user, host)


""" Munge a nick """
def munge_nick(nick, trycount):
    leetmap = {'e':'3',
               'a':'4',
               't':'7',
               's':'5',
               'q':'2',
               'b':'8',
               'o':'0',
               'l':'|',
               'i':'|',
               '|':'\\'}

    if trycount == 0:
        return nick + '_'
    elif trycount == 1:
        nick = nick[:-1]
        return nick + '^'
    elif trycount >= 2:
        if trycount == 2:
            nick = nick[:-1]

        oldnick = nick
        for pos, char in enumerate(nick[1:]):
            if char in leetmap:
                newchar = leetmap[nick[pos]]
                nick = ''.join((nick[:pos-1], newchar, nick[pos:]))
                break

        if nick == oldnick:
            nick += '_'

    return nick


""" Oh noes, have to use an alternate nick """
def dispatch_alt_nick(client, line):
    attempt = line.params[1]

    count = getattr(client, '_nick_trycount', None)
    if count is None:
        # Try our alternate first
        nick = client.altnick
        client._nick_trycount = 0
        count = 0
    else:
        nick = munge_nick(attempt, count)
        client._nick_trycount += 1

    client.cmdwrite('NICK', [nick])


hook_in = (
    ('NICK', PRIORITY_DEFAULT, dispatch_nick),
    (ERR_ERRONEUSNICKNAME, PRIORITY_DEFAULT, dispatch_alt_nick),
    (ERR_NICKNAMEINUSE, PRIORITY_DEFAULT, dispatch_alt_nick),
)

