from irclib.client.user import User
from irclib.client.channel import Channel
from irclib.common.numerics import *

from random import randint
from functools import partial

""" Dispatch other user join """
def dispatch_other_join(client, line):
    if not line.hostmask: return

    if line.hostmask.nick == client.current_nick:
        return

    channel = line.params[0]
    if len(line.params) > 1:
        # extended-join
        account = line.params[1]
        realname = line.params[2]

        if account == '*':
            account = None
    else:
        account = None
        realname = None

    nick = line.hostmask.nick
    user = line.hostmask.user
    host = line.hostmask.host

    # Cancel outstanding destruction requests
    client.timer_cancel('expire_user_{}'.format(nick))

    # Create a user if one doesn't exist
    if nick not in client.users:
        client.users[nick] = User(client, nick, user, host, realname, account)

    if channel in client.channels:
        client.channels[channel].user_add(nick, client.users[nick])
        client.users[nick].channel_add(client.channels[channel])
    else:
        client.logger.critical('DESYNC detected! Join detected in a channel we'
                               ' are not in')


""" Dispatch us joining """
def dispatch_client_join(client, line):
    if not line.hostmask: return
    if line.hostmask.nick != client.current_nick:
        return

    # Probably not gonna happen but better safe than sorry. :P
    chlist = line.params[0].split(',')
    if client.pending_channels.issuperset(chlist):
        client.pending_channels.difference_update(chlist)

    # Add the channel
    for channel in chlist:
        client.channels[channel] = Channel(client, channel)

        # Request modes
        client.cmdwrite('MODE', [channel])

        if 'WHOX' in client.isupport:
            num = randint(0, 999)
            count = 0
            while num in client._whox_pending:
                num = randint(0, 999)
                count += 1
                if count > 1024: return

            client._whox_pending.add(num)

            num = str(num)
            whoparam = (channel, '%tcuisnflar,'+num)
        else:
            whoparam = (channel,)

        whofunc = partial(client.cmdwrite, 'WHO', whoparam)

        # I'm gonna need bout tree fiddy (seconds)
        # No but seriously, this is a load-lessening measure
        wait = randint(30, 60)

        # Initial who request
        client.timer_oneshot('sendwho_{}'.format(channel), wait/10, whofunc)
        
        if not all(x in client.supported_cap for x in ('away-notify',
                                                       'account-notify')):
            # Add a recurring check if needed 
            client.timer_repeat('sendwho_r_{}'.format(channel), wait, whofunc)


""" Dispatch errors joining """
def dispatch_err_join(client, line):
    client.logger.warn('Could not join channel {}: {} {}'.format(
        line.params[1], line.command, line.params[-1]))

    client.pending_channels.discard(line.params[1])


""" Outgoing hook for pending joins """
def dispatch_pending_join(client, line):
    if len(line.params) == 0: return

    chlist = line.params[0].split(',')
    client.pending_channels.update(chlist)


""" Dispatch timestamp setting """
def dispatch_ts(client, line):
    channel = line.params[1]
    client.channels[channel].timestamp = int(line.params[-1])


""" Dispatch channel URL setting """
def dispatch_url(client, line):
    channel = line.params[1]
    client.channels[channel].url = line.params[-1]


hooks_in = (
    ('JOIN', 0, dispatch_other_join),
    ('JOIN', 5, dispatch_client_join),
    (ERR_LINKCHANNEL, 0, dispatch_err_join),
    (ERR_CHANNELISFULL, 0, dispatch_err_join),
    (ERR_INVITEONLYCHAN, 0, dispatch_err_join),
    (ERR_BANNEDFROMCHAN, 0, dispatch_err_join),
    (ERR_BADCHANNELKEY, 0, dispatch_err_join),
    (ERR_NEEDREGGEDNICK, 0, dispatch_err_join),
    (ERR_BADCHANNAME, 0, dispatch_err_join),
    (ERR_THROTTLE, 0, dispatch_err_join),
    (ERR_KEYSET, 0, dispatch_err_join),
    (RPL_CREATIONTIME, 0, dispatch_ts),
    (RPL_CHANNELURL, 0, dispatch_url),
)

hooks_out = ( 
    ('JOIN', 5, dispatch_pending_join),
)

