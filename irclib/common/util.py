from string import ascii_letters, digits
from random import choice, randint
from os import strerror
from socket import error as SocketError

""" Generate a random string """
def randomstr(minlen=6, maxlen=30):
    validstr = string.ascii_letters + string.digits + ' '
    return ''.join([choice(validstr) for x in range(randint(minlen, maxlen))])


""" Raise a socket error """
def socketerror(error, errstr=None, instance=None):
    if hasattr(instance, 'connected'):
        instance.connected = False

    if not errstr:
        errstr = strerror(error)

    raise SocketError(error, errstr)

