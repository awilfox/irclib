""" Dispatch us parting/being kicked """
def dispatch_self_part(client, line):
    if not line.hostmask: return

    # When proper nick tracking is implemented, uncomment this
    #if line.hostmask.nick != client.current_nick:
    #    return

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
    ('PART', 5, dispatch_self_part),
    ('KICK', 5, dispatch_self_part),
)

hooks_out = (
    ('PART', 0, dispatch_pending_part),
)

