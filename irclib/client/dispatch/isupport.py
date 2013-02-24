import re

from irclib.common.numerics import *

def dispatch_isupport(client, line):
    try:
        isupport = line.params[2:-1]
    except:
        client.logger.error('ISUPPORT broken, probably old server')
        return

    for token in isupport:
        name, sep, value = token.partition('=')

        # We parse the most common ones.
        # Pretty much anything else is up to you.
        if value:
            if name == 'PREFIX':
                # This is surprisingly a job best done for regex.
                m = re.match(r'\((.+)\)(.+)', value)

                # No match. :(
                if m is None: continue
                letter, prefix = m.groups()

                if len(letter) != len(prefix):
                    # Your server is fucked yo.
                    client.logger.warn('Broken IRC server; PREFIX is broken '
                                     '(unbalanced prefixes and modes)')
                    continue

                value = list(zip(letter, prefix))

                # Update the map
                client.preifx_to_mode = {s:m for m,s in value}
            elif name.endswith('LEN') or name in ('MODES', 'MONITOR'):
                # These are probably numeric values
                if value.isdigit:
                    value = int(value)
            elif name == 'EXTBAN':
                # Urgh this breaks the de-facto spec
                split = value.partition(',')
                if split[1]:
                    value = (split[0], split[2])
            else:
                # Attempt to parse as follows:
                #
                # - Comma separated values
                # - key : value pairs
                split = value.split(',')
                valuelist = []

                for item in split:
                    key, sep, value = item.partition(':')
                    if sep:
                        item = (key, value)

                    valuelist.append(item)

                if len(valuelist) == 1:
                    # One item only
                    value = valuelist[0]
                elif len(valuelist) > 1:
                    value = valuelist
        else:
            # No value
            value = None

        # Set
        client.isupport[name] = value
        client.logger.debug('ISUPPORT token: {} {}'.format(name, value))


hooks_in = (
    (RPL_ISUPPORT, 0, dispatch_isupport),
)
