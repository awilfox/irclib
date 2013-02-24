from time import ctime

""" Foreign privmsg (NOT CTCP) """
def dispatch_privmsg(client, line):
    if line.hostmask is None:
        return

    if line.params[0] != client.current_nick:
        return

    nick = line.hostmask.nick

    if nick in client.users:
        # Re-up if needed
        if len(client.users[nick].channels) == 0:
            timername = 'expire_user_{}'.format(nick)
            client.timer_cancel(timername)
            expire = partial(lambda x: client.users.pop(x, None), nick)
            client.timer_oneshot(timername, 300, expire)


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

hooks_in = (
    ('PRIVMSG', 0, dispatch_ctcp),
    ('PRIVMSG', 1, dispatch_privmsg),
)

