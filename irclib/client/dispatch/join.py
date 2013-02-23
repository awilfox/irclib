from irclib.client.channel import Channel
from irclib.common.numerics import *

""" Dispatch us joining """
def dispatch_client_join(client, line):
    if not line.hostmask: return

    # When proper nick tracking is implemented, uncomment this
    #if line.hostmask.nick != client.current_nick:
    #    return

    # Probably not gonna happen but better safe than sorry. :P
    chlist = line.params[0].split(',')
    if client.pending_channels.issuperset(chlist):
        client.pending_channels.difference_update(chlist)

    # Add the channel
    for channel in chlist:
        client.channels[channel] = Channel(client, channel)

        # Request modes
        client.cmdwrite('MODE', [channel])


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


hooks_in = (
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
)

hooks_out = ( 
    ('JOIN', 5, dispatch_pending_join),
)

