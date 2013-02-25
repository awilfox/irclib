from irclib.common.dispatch import PRIORITY_DEFAULT

""" Dispatch quitting """
def dispatch_quit(client, line):
    if line.hostmask.nick == client.current_nick:
        client.logger.info('Quitting network')
        return

    nick = line.hostmask.nick
    if nick in client.users:
        client.users.pop(nick, None)


hooks_in = (
    ('QUIT', PRIORITY_DEFAULT, dispatch_quit),
)

