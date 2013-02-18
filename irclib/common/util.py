from string import ascii_letters, digits
from random import choice, randint
from os import strerror

import socket

""" Generate a random string """
def randomstr(minlen=6, maxlen=30):
    validstr = string.ascii_letters + string.digits + ' '
    return ''.join([choice(validstr) for x in range(randint(minlen, maxlen))])


""" Raise a socket error """
def socketerror(network, errno, errstr=None):
    network.connected = False
    if not errstr:
        errstr = strerror(errno)
        raise socket.error(errno, errstr)

