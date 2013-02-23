""" Dispatches CAP stuff """
def dispatch_cap(client, line):
    if line.params[1] == 'ACK':
        dispatch_cap_ack(client, line)


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


hooks_in = (
    ('CAP', 0, dispatch_cap),
)

