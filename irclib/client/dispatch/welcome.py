from irclib.common.numerics import *
from irclib.common.util import randomstr

from socket import error as SocketError
from time import time
from functools import partial

""" Sends a keepalive message """
def dispatch_keepalive(client):
    if client._last_pingstr is not None:
        raise SocketError('Socket timed out')

    client._last_pingtime = time()
    client._last_pingstr = randomstr()

    client.cmdwrite('PING', [client._last_pingstr])


""" Generic dispatch for RPL_WELCOME 

The default does joins and such
"""
def dispatch_welcome(client, line):
    # Set our nickname
    client.current_nick = line.params[0]

    # Set up timer for lagometer
    keepalive = partial(dispatch_keepalive, client)
    client.timer_repeat('keepalive', client.keepalive, keepalive)

    # Do joins
    client.combine_channels(client.default_channels, client.channel_keys)


hooks_in = ( 
    (RPL_WELCOME, 0, dispatch_welcome),
)

