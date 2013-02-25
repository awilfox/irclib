from irclib.common.numerics import *

""" Parse flags in WHO """
def parse_flags(client, flags):
    # Parse the status field
    for char in flags:
        if char == '*':
            # Is an IRC operator
            client.users[nick].operator = True
        elif char == 'G':
            # Away
            client.users[nick].away = True
        elif char == 'H':
            # Not away
            client.users[nick].away = False
            client.users[nick].away_message = None
        elif char in client.prefix_to_mode and channel in client.channels:
            # Add the status mode
            ch = client.channels[channel]
            mode = client.prefix_to_mode[char]
            ch.modes.add_mode(mode, nick)
        else:
            client.logger.info('Unknown WHO symbol recieved: {}'.format(char))


""" Dispatch who """
def dispatch_who(client, line):
    try:
        # Shift
        params = line.params[1:]
        # Fucking eh, WHO is a crock of shit
        channel, username, host, server, nick, flags, other = params
    except ValueError:
        # I give up.
        client.logger.warn('Could not parse WHO reply ({})'.format(str(line)))
        return

    # This is gay. I reiterate, WHO is a crock of shit
    hopcount, sep, other = other.partition(' ')

    if 'RFC2812' in client.isupport:
        # Ugh. Fuck IRCNet. They send some extra parameter and I honestly have
        # no idea what it means, what it's for, and it's not documented
        # /anywhere/. Even RFC2812 doesn't tell me anything.
        wtf, sep, realname = other.partition(' ')
    else:
        wtf = None
        realname = other

    if nick == '*':
        return

    # Look up the user
    if nick not in client.users:
        client.users[nick] = User(nick, user, host, realname)

    # Set this...
    client.users[nick].server = server

    parse_flags(client, flags)


""" Dispatch whox """
def dispatch_whox(client, line):
    # Check param count
    if len(line.params) != 11:
        client.logger.debug('Wrong param count for WHOX')
        return

    # Shift
    params = line.params[1:]

    # unpack
    try:
        rid, channel, user, ip, server = params[:5]
        nick, flags, idle, account, realname = params[5:]
    except ValueError:
        client.logger.warn('Could not parse WHOX reply ({})'.format(str(line)))
        return

    # Check if we requested it
    if rid not in client._whox_pending:
        return
    else:
        client._last_rid = rid

    # Don't care
    if channel == '*':
        return
    elif channel not in client.channels:
        # Weird. must be someone else's whox check?
        return

    # Not logged in
    if account == '0':
        account = ''

    # No idle time
    if idle == '0':
        idle = None

    # Cloaked
    if ip == '255.255.255.255':
        ip = None

    if nick not in client.users:
        client.users[nick] = User(nick, user, host, realname, account)
        client.channels[channel].user_add(nick, client.users[nick])
        client.users[nick].channel_add(channel, client.channels[channel])

    # Set some extended info
    client.users[nick].idle = idle
    client.users[nick].ip = ip
    client.users[nick].server = server

    parse_flags(client, flags)


""" End of whox """
def dispatch_end_whox(client, line):
    lastrid = getattr(client, '_last_rid', None)
    if lastrid is None: return

    client._whox_pending.discard(lastrid)


hooks_in = (
    (RPL_WHOREPLY, 0, dispatch_who),
    (RPL_WHOSPCRPL, 0, dispatch_whox),
    (RPL_ENDOFWHO, 0, dispatch_end_whox),
)

