from irclib.common.dispatch import PRIORITY_DEFAULT

""" Do account-notify stuff """
def dispatch_account(client, line):
    nick = line.hostmask.nick

    account = line.params[-1]
    if account == '*':
        # Unset
        account = ''

    if nick not in client.users:
        # Not entirely sure why this would happen but ok :p.
        user = line.hostmask.user
        host = line.hostmask.host

        client.create_user(nick, user, host)

    client.users[nick].account = account


hooks_in = (
    ('ACCOUNT', PRIORITY_DEFAULT, dispatch_account),
)

