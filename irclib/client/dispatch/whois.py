from irclib.common.dispatch import PRIORITY_DEFAULT
from irclib.common.numerics import *

""" Dispatch WHOIS """
def dispatch_whois(client, line):
    info = line.command
    nick = line.params[1]
    if nick not in client.users:
        return

    if info == RPL_WHOISUSER:
        client.user, client.host, unused, client.realname = line.params[2:]
    elif info == RPL_WHOISCHANNELS:
        # Through each channel
        channels = line.params[-1].split()
        chantypes = client.isupport['CHANTYPES']
        for channel in channels:
            mode = [] 
            orig = channel
            while channel[0] in client.prefix_to_modes:
                # Check for broken servers etc.
                if (channel[0] in chantypes and channel[1] not in chantypes and
                    channel[1] not in client.prefix_to_modes):
                    break

                # Add the mode to the list
                mode.append(client.prefix_to_modes[channel[0]])
                channel = channel[1:]

            if channel not in client.channels: continue

            ch = client.channels[channel]

            for m in mode:
                ch.modes.add_mode(m, nick)

            # Add user to channel and vice versa
            client.users[nick].channel_add(channel, ch)
            ch.user_add(nick, client.users[nick])
    elif info == RPL_WHOISHOST:
        iphost = line.params[-1].split()
        
        if len(iphost) < 2: return

        # Last two
        host, ip = iphost[-2:]

        client.users[nick].host = host
        client.users[nick].ip = ip
    elif info == RPL_WHOISSECURE:
        client.users[nick].ssl = True
    elif info == RPL_WHOISOPERATOR:
        client.users[nick].operator = True
    elif info == RPL_WHOISLOGGEDIN:
        client.users[nick].account = line.params[2]
    elif info == RPL_ENDOFWHOIS:
        # Last checks
        if client.users[nick].ssl is None:
            # Probably not using SSL
            client.users[nick].ssl = False

        if client.users[nick].account is None:
            # No account ... ?
            client.users[nick].account = ''

hooks_in = (
    (RPL_WHOISUSER, PRIORITY_DEFAULT, dispatch_whois),
    (RPL_WHOISCHANNELS, PRIORITY_DEFAULT, dispatch_whois),
    (RPL_WHOISHOST, PRIORITY_DEFAULT, dispatch_whois),
    (RPL_WHOISSECURE, PRIORITY_DEFAULT, dispatch_whois),
    (RPL_WHOISOPERATOR, PRIORITY_DEFAULT, dispatch_whois),
    (RPL_WHOISLOGGEDIN, PRIORITY_DEFAULT, dispatch_whois),
    (RPL_ENDOFWHOIS, PRIORITY_DEFAULT, dispatch_whois),
)

