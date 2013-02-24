from time import time, ctime
from functools import partial

from irclib.client.user import User
from irclib.common.line import Line
from irclib.common.util import splitstr

""" Expire a user in 5 minutes """
def expire_user(client, u):
    timername = 'expire_user_{}'.format(u.nick)
    client.timer_cancel(timername)
    expire = partial(lambda x: client.users.pop(x, None), u.nick)
    client.timer_oneshot(timername, 300, expire)


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

    # Do expiry stuff
    if nick in client.users:
        # Re-up if needed
        if len(client.users[nick].channels) == 0:
            expire_user(client, client.users[nick])
    else:
        # TODO - maybe whois?
        client.users[nick] = User(nick, user, host)
        expire_user(client, client.users[nick])
        

""" Dispatch CTCP """
def dispatch_ctcp(client, line):
    if len(line.params) <= 1:
        return

    target = line.params[0]
    message = line.params[-1]

    if not (message.startswith('\x01') or message.endswith('\x01')):
        return

    message = message.strip('\x01')
    command, sep, cmdparam = message.partition(' ')
    command = command.upper()

    if target == client.current_nick:
        # privmsg to us, respond in private
        target = line.hostmask.nick

    response = None
    if command == 'VERSION':
        response = 'VERSION ' + client.version
    elif command == 'TIME':
        response = 'TIME ' + ctime()
    elif command == 'PING':
        response = message
    
    if response:
        response = '\x01' + response + '\x01'
        client.cmdwrite('NOTICE', (target, response))


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

    # XXX - could cram more in...
    # That will require self hostname tracking though. :p
    if len(message) > 450:
        split = splitstr(message, 450)
        buf = []
        for msg in split:
            line.params[-1] = msg
            client.linewrite(line)

        line.params[-1] = message
        line.cancelled = True
        return True


hooks_in = (
    ('PRIVMSG', 0, dispatch_ctcp),
    ('PRIVMSG', 1, dispatch_privmsg),
)

hooks_out = (
    ('PRIVMSG', 0, dispatch_split_msg),
    ('PRIVMSG', 1, dispatch_pace_msg),
    ('NOTICE', 0, dispatch_split_msg),
    ('NOTICE', 1, dispatch_pace_msg),
)

