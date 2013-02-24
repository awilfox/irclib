""" Dispatch quitting """
def dispatch_quit(client, line):
    if line.hostmask.nick == self.current_nick:
        client.logger.info('Quitting network')
        return

    nick = line.hostmask.nick
    if nick in client.users:
        client.users.pop(nick, None)


hooks_in = (
    ('QUIT', 0, dispatch_quit),
)

