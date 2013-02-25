from time import time 

from irclib.common.dispatch import PRIORITY_DEFAULT
from irclib.common.numerics import *

""" Dispatch the channel topic """
def dispatch_rpl_topic(client, line):
    channel = line.params[1]

    if channel not in client.channels:
        client.logger.critical('DESYNC detected! got a topic for a channel we '
                               'are not in!')
        return

    client.channels[channel].topic = line.params[-1]


""" Dispatch the channel topic (who set it) """
def dispatch_rpl_topictime(client, line):
    channel = line.params[1]

    if channel not in client.channels:
        client.logger.critical('DESYNC detected! got a topic for a channel we '
                               'are not in!')
        return

    client.channels[channel].topic_who = line.params[2]
    client.channels[channel].topic_time = line.params[3]


""" Dispatch TOPIC (the command) """
def dispatch_topic(client, line):
    channel = line.params[0]

    if channel not in client.channels:
        client.logger.critical('DESYNC detected! got a topic for a channel we '
                               'are not in!')
        return

    topic = line.params[-1]
    if topic == '':
        topic = None

    client.channels[channel].topic = topic
    client.channels[channel].topic_who = str(line.hostmask)
    client.channels[channel].topic_time = int(time())


hooks_in = (
    (RPL_TOPIC, PRIORITY_DEFAULT, dispatch_rpl_topic),
    (RPL_TOPICWHOTIME, PRIORITY_DEFAULT, dispatch_rpl_topictime),
    ('TOPIC', PRIORITY_DEFAULT, dispatch_topic),
)
