from irclib.common.six import u, b

""" Dispatches CAP stuff """
def dispatch_cap(client, line):
    dispatch = {
        'ACK' : dispatch_cap_ack,
        'LS' : dispatch_cap_ls,
        'NAK' : dispatch_cap_nak,
    }
   
    if line.params[1] in dispatch:
        return dispatch[line.params[1]](client, line)


def dispatch_cap_ls(client, line):
    client.timer_cancel('cap_terminate')

    # Request common caps
    caps = line.params[-1].split()

    common = u(' ').join(client.cap_req.intersection(caps))

    if not common:
        # No common caps
        self.cap_terminate()

    # Request common caps
    client.cmdwrite('CAP', ('REQ', common))

    # Restart the timer
    client.timer_oneshot('cap_terminate', 10, client.cap_terminate)


def dispatch_cap_ack(client, line):
    # Cancel
    client.timer_cancel('cap_terminate')

    # Caps follow
    client.supported_cap = line.params[-1].lower().split()

    if 'tls' in client.supported_cap and client.use_starttls and not client.use_ssl:
        # Start TLS negotiation
        client.cmdwrite('STARTTLS')
    else:
        # Register only if we don't need STARTTLS
        client.dispatch_register()


def dispatch_cap_nak(client, line):
    client.timer_cancel('cap_terminate')

    client.logger.warn('caps could not be approved: {}'.format(
        line.params[-1]))

    client.cap_terminate()


hooks_in = (
    ('CAP', 0, dispatch_cap),
)

