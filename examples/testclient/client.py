from irclib.client.client import IRCClient
from irclib.common import numerics as num

from select import POLLIN, POLLOUT

class CustomClient(IRCClient):
    def __init__(self, **kwargs):
        IRCClient.__init__(self, **kwargs)

        self.window = kwargs.get('window')
        self.pollobj = kwargs.get('pollobj')

        self.add_dispatch_out('PRIVMSG', 100, format_privmsg_out)
        self.add_dispatch_in('PRIVMSG', 100, format_privmsg_in)
        self.add_dispatch_in('NOTICE', 100, format_privmsg)
        self.add_ctcp_out('ACTION', 100, format_ctcp_out)
        self.add_ctcp_in('ACTION', 100, format_ctcp_in)

    def log_callback(self, line, recv):
        pass


def format_privmsg_in(client, line):
    format_privmsg(client, line, True)

def format_privmsg_out(client, line):
    format_privmsg(client, line, False)

def format_ctcp_in(client, line, target, command, param):
    format_ctcp(client, line, target, command, param, True)

def format_ctcp_out(client, line, target, command, param):
    format_ctcp(client, line, target, command, param, False)

def format_privmsg(client, line, incoming):
    if line.hostmask:
        whofrom = line.hostmask.nick
    else:
        if incoming:
            whofrom = '***'
        else:
            whofrom = client.current_nick

    target = line.params[0]
    message = line.params[-1]
    if message.startswith('\x01') or message.endswith('\x01'):
        return

    if line.command == 'PRIVMSG':
        fmt = '[{target}] <{whofrom}> {message}'
    else:
        fmt = '[{target}] -{whofrom}- {message}'

    client.window.add_buffertext(fmt.format(**locals()), target)


def format_ctcp(client, line, target, command, param, incoming):
    if command != 'ACTION': return

    if line.hostmask:
        whofrom = line.hostmask.nick
    else:
        if incoming:
            whofrom = '***'
        else:
            whofrom = client.current_nick

    target = line.params[0]
    message = param

    fmt = '[{target}] * {whofrom} {message}'

    client.window.add_buffertext(fmt.format(**locals()), target)

