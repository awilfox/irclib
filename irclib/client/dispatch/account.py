from irclib.client.user import User

""" Do account-notify stuff """
def dispatch_account(client, line):
    nick = line.hostmask.nick

    account = line.params[-1]
    if account == '*':
        # Unset
        account = None

    if nick not in client.users[nick]:
        user = line.hostmask.user
        host = line.hostmask.host

        client.users[nick] = User(nick, user, host)

    client.users[nick].account = account


hooks_in = (
    ('ACCOUNT', 0, dispatch_account),
)
