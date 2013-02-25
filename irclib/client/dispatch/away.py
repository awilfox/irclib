from irclib.common.dispatch import PRIORITY_DEFAULT

""" Implement AWAY notifications """
def dispatch_away(client, line):
    if line.hostmask is None: return

    nick = line.hostmask.nick
    if nick == client.current_nick:
        # o_O
        return

    if len(line.params) == 0:
        setaway = False
        message = None
    else:
        setaway = True
        message = line.params[-1]

    if nick in client.users:
        client.users[nick].away = setaway
        client.users[nick].away_message = message


hooks_in = (
    ('AWAY', PRIORITY_DEFAULT, dispatch_away),
)

