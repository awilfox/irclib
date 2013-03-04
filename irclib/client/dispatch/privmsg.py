from time import time, ctime
from functools import partial
from copy import deepcopy

from irclib.common.dispatch import PRIORITY_DEFAULT, PRIORITY_LOW
from irclib.client.user import User
from irclib.common.line import Line, Hostmask
from irclib.common.util import splitstr


""" Foreign privmsg (NOT CTCP) """
def dispatch_privmsg(client, line):
    if line.hostmask is None:
        return

    nick = line.hostmask.nick

    if line.params[0] != client.current_nick:
        # Update just in case (for old ircd's/hyperion)
        user = line.hostmask.user
        host = line.hostmask.host

        if nick in client.users:
            client.users[nick].user = user
            client.users[nick].host = host

    if nick not in client.users:
        # TODO - maybe whois?
        client.users[nick] = User(nick, line.hostmask.user, line.hostmask.host)
        client.expire_user(nick)
        

""" Dispatch CTCP """
def dispatch_ctcp(client, line):
    if len(line.params) <= 1:
        return

    if not line.hostmask:
        return

    target = line.hostmask.nick 
    message = line.params[-1]

    if not (message.startswith('\x01') or message.endswith('\x01')):
        return

    message = message.strip('\x01')
    command, sep, param = message.partition(' ')
    command = command.upper()

    # Call CTCP dispatch
    client.call_ctcp_in(line, target, command, param)


""" Dispatch CTCP VERSION """
def dispatch_ctcp_version(client, line, target, command, param):
    client.nctcpwrite(target, command, client.version)


""" Dispatch CTCP TIME """
def dispatch_ctcp_time(client, line, target, command, param):
    client.nctcpwrite(target, command, ctime())


""" Dispatch CTCP PING """
def dispatch_ctcp_ping(client, line, target, command, param):
    client.nctcpwrite(target, command, param)


""" Dispatch CTCP FINGER """
def dispatch_ctcp_finger(client, line, target, command, param):
    client.nctcpwrite(target, command, client.current_nick)


""" Do some buffering """
def dispatch_pace_msg(client, line):
    wait = False
    if hasattr(client, '_msg_last'):
        last_time = time - client._privmsg_last
        if last_time < 0.25:
            wait = True

    if not wait:
        client._privmsg_last = time()
    else:
        privmsg_out = partial(client.linewrite, Line(str(line)))
        cient.timer_oneshot('dispatch_msg', 0.3, privmsg_out)
        line.cancelled = True
        return True


""" Split long messages """
def dispatch_split_msg(client, line):
    if len(line.params) <= 0:
        return

    if line.cancelled:
        return

    message = line.params[-1]

    if message.startswith('\x01') or message.endswith('\x01'):
        # CTCP. don't touch.
        return

    if client.current_host and client.current_user:
        # Compute the maximum possible length
        if not line.hostmask:
            # Create a hostmask object
            # Servers will truncate lines sent to other users, so let's look at
            # it like they will.
            line.hostmask = Hostmask(client.current_nick, client.current_user,
                                     client.current_host)

        # Length of the bare command
        startlen = len(str(line)) - len(line.params[-1])

        # Maximum line length
        # Why 510? crlf
        maxlen = 510 - startlen
    else:
        # Conservative default
        maxlen = 300

    if len(message) > maxlen:
        split = splitstr(message, maxlen)
        buf = []
        for msg in split:
            newline = deepcopy(line)
            newline.params[-1] = msg
            client.linewrite(newline)

        line.cancelled = True
        return True


hooks_in = (
    ('PRIVMSG', PRIORITY_DEFAULT, dispatch_ctcp),
    ('PRIVMSG', PRIORITY_LOW, dispatch_privmsg),
)

hooks_out = (
    ('PRIVMSG', PRIORITY_LOW, dispatch_split_msg),
    ('PRIVMSG', PRIORITY_LOW, dispatch_pace_msg),
    ('NOTICE', PRIORITY_LOW, dispatch_split_msg),
    ('NOTICE', PRIORITY_LOW, dispatch_pace_msg),
)

hooks_ctcp_in = (
    ('VERSION', PRIORITY_DEFAULT, dispatch_ctcp_version),
    ('TIME', PRIORITY_DEFAULT, dispatch_ctcp_time),
    ('PING', PRIORITY_DEFAULT, dispatch_ctcp_ping),
)


