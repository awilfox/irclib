from functools import partial

from irclib.common.dispatch import PRIORITY_DEFAULT

""" Dispatch foreign user """
def dispatch_other_part(client, line):
    if not line.hostmask: return

    if line.hostmask.nick != client.current_nick:
        return

    nick = line.hostmask.nick
    channel = line.params[0]

    if channel not in client.channels:
        client.logger.critical('DESYNC detected! Part detected in a channel we '
                               'did NOT know about!')
        return

    client.channels[channel].user_del(nick)

    if nick not in client.users:
        return

    client.users[nick].channel_del(channel)

    if len(client.users[nick].channels) == 0:
        if 'MONITOR' in client.isupport:
            # We support monitor :D
            client.cmdwrite('MONITOR', ('+', nick))
        else:
            # :( use ISON as a fallback
            isoncheck = partial(client.cmdwrite, 'ISON', (nick,))
            timername = 'ison_user_{}'.format(nick)
            client.timer_repeat(timername, 60, isoncheck)

            isoncheck()


""" Dispatch us parting/being kicked """
def dispatch_self_part(client, line):
    if not line.hostmask: return

    if line.hostmask.nick != client.current_nick:
        return

    channel = line.params[0]
    client.pending_channels.discard(channel)

    ch = client.channels.pop(channel, None)
    if ch is None: return

    if not ch.parting:
        client.logger.warn('Removed from channel {}'.format(channel))

    if line.command == 'KICK' or not ch.parting:
        if client.autorejoin:
            # Use key if needed
            key = ch.modes.has_mode('k')
            if not key:
                key = ''

            # synthesise a function to do the rejoin, and fire it on a timer
            rejoin_func = partial(client.cmdwrite, 'JOIN', (channel, key))
            client.timer_oneshot('rejoin_ch_{}'.format(channel),
                                 client.autorejoin_wait, rejoin_func)


""" Outgoing hook for pending parts """
def dispatch_pending_part(client, line):
    if len(line.params) == 0: return

    chlist = line.params[0].split(',')
    client.pending_channels.difference_update(chlist)

    for channel in chlist:
        if channel not in client.channels: continue

        # Mark us as parting
        client.channels[channel].parting = True


hooks_in = (
    ('PART', PRIORITY_DEFAULT, dispatch_other_part),
    ('KICK', PRIORITY_DEFAULT, dispatch_other_part),
    ('PART', PRIORITY_DEFAULT, dispatch_self_part),
    ('KICK', PRIORITY_DEFAULT, dispatch_self_part),
)

hooks_out = (
    ('PART', PRIORITY_DEFAULT, dispatch_pending_part),
)

