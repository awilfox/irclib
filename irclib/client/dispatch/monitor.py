""" MONITOR/ISON support """
from functools import partial

from irclib.common.numerics import *
from irclib.common.dispatch import PRIORITY_DEFAULT

""" ISON sending hook """
def dispatch_ison_out(client, line):
    if len(line.params) == 0: return

    nicklist = line.params[:-1]
    nicklist.extend(line.params[-1].split())

    client._ison_list.put(nicklist)


""" ISON receiving hook """
def dispatch_ison(client, line):
    nicklist = line.params[:-1]
    nicklist.extend(line.params[-1].split())

    curlist = client._ison_list.get()

    for nick in curlist:
        if nick not in nicklist and nick in client.users:
            # User absent :(.
            client.timer_cancel('ison_user_{}'.format(nick))
            del client.users[nick]


""" MONITOR exit hook """
def dispatch_monitor_exit(client, line):
    users = line.params[-1].split(',')

    for nick in users:
        if nick in client.users:
            # Eh... maybe this timer will exist?
            client.timer_cancel('ison_user_{}'.format(nick))
            del client.users[nick]

    # Stop monitoring said users
    client.cmdwrite('MONITOR', ('-', line.params[-1]))


""" Out of monitor space """
def dispatch_monitor_noroom(client, line):
    users = line.params[-1].split(',')

    for nick in users:
        # Use ISON as a fallback
        isoncheck = partial(client.cmdwrite, 'ISON', (nick,))
        timername = 'ison_user_{}'.format(nick)
        client.timer_repeat(timername, 60, isoncheck)

        # Also send immediate request
        isoncheck()


hooks_out = (
    ('ISON', PRIORITY_DEFAULT, dispatch_ison_out),
)

hooks_in = (
    (RPL_ISON, PRIORITY_DEFAULT, dispatch_ison),
    (RPL_MONOFFLINE, PRIORITY_DEFAULT, dispatch_monitor_exit),
    (ERR_MONLISTFULL, PRIORITY_DEFAULT, dispatch_monitor_noroom),
)

