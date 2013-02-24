from irclib.common.numerics import *

""" Dispatch who """
def dispatch_who(client, line):
    try:
        # Fucking eh, WHO is a crock of shit
        channel, username, host, server, nick, status, other = line.params
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

    # Parse the status field
    for char in status:
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

# TODO - whox
hooks_in = (
    (RPL_WHOREPLY, 0, dispatch_who),
)

