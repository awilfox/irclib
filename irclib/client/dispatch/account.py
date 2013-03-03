from irclib.common.dispatch import PRIORITY_DEFAULT
from irclib.client.user import User

""" Do account-notify stuff """
def dispatch_account(client, line):
    nick = line.hostmask.nick

    account = line.params[-1]
    if account == '*':
        # Unset
        account = ''

    if client.users.get(nick) is None:
        user = line.hostmask.user
        host = line.hostmask.host

        client.users[nick] = User(nick, user, host)

    client.users[nick].account = account


hooks_in = (
    ('ACCOUNT', PRIORITY_DEFAULT, dispatch_account),
)

