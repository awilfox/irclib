import base64

from irclib.common.dispatch import PRIORITY_DEFAULT
from irclib.common.util import splitstr
from irclib.common.numerics import *

""" Authenticate to the server

TODO - other auth types
"""
def dispatch_sasl_authenticate(client, line):
    client.timer_cancel('cap_terminate')

    # We got an authentication message?
    if line.params[0] != '+':
       client.logger.warn('Unexpected response from SASL auth agent, '
                          'continuing')

    if not client.identified:
        # Generate
        send = '{acct}\0{acct}\0{pw}'.format(acct=client.sasl_username,
                                             pw=client.sasl_pw)
        send = base64.b64encode(send.encode('utf-8'))
        send = send.decode('ascii')

        # Split into 400 byte chunks
        split = splitstr(send, 400)
        for item in split:
            client.cmdwrite('AUTHENTICATE', [item])
 
        # Padding, if needed
        if len(split[-1]) == 400:
            client.cmdwrite('AUTHENTICATE', ['+'])

        # Timeout authentication
        client.timer_oneshot('cap_terminate', 15, client.cap_terminate)


def dispatch_sasl_success(client, line):
    client.timer_cancel('cap_terminate')

    client.identified = True
    if line.command == RPL_SASLSUCCESS:
        # end CAP
        client.cap_terminate()


def dispatch_sasl_error(client, line):
    client.timer_cancel('cap_terminate')

    # SASL failed
    client.logger.error('SASL auth failed! Error: {} {}'.format(
                        line.command,
                        line.params[-1]))
    client.cap_terminate()


hooks_in = ( 
    ('AUTHENTICATE', PRIORITY_DEFAULT, dispatch_sasl_authenticate),
    (RPL_LOGGEDIN, PRIORITY_DEFAULT, dispatch_sasl_success),
    (RPL_SASLSUCCESS, PRIORITY_DEFAULT, dispatch_sasl_success),
    (ERR_SASLFAIL, PRIORITY_DEFAULT, dispatch_sasl_error),
    (ERR_SASLTOOLONG, PRIORITY_DEFAULT, dispatch_sasl_error),
)

