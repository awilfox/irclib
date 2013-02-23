from time import time

""" Generic dispatcher for ping """
def dispatch_ping(client, line):
    client.cmdwrite('PONG', line.params)


""" Dispatches keepalive message """
def dispatch_pong(client, line):
    if client._last_pingstr is None:
        return

    if line.params[-1] != client._last_pingstr:
        return

    client._last_pingstr = None
    client.lag = time() - client._last_pingtime
    client.logger.info('LAG: {}'.format(client.lag))


hooks_in = (
    ('PING', 0, dispatch_ping),
    ('PONG', 0, dispatch_pong),
)

