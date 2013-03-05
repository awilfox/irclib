import logging
import curses
import select

from sys import stdin
from ssl import SSLError, SSL_ERROR_WANT_READ, SSL_ERROR_WANT_WRITE

from scrollablewindow import ScrollableWindow
from client import CustomClient
from irclib.common.line import Line

def process_buffer(textbuf):
    if textbuf[0] == '/':
        textbuf = textbuf[1:]
        command, sep, textbuf = textbuf.partition(' ')
        command = command.lower()
        if command == 'win':
            return ('changewin', textbuf)
        elif command == 'join':
            return ('cmd', 'JOIN ' + textbuf)
        elif command == 'part':
            return ('cmd', 'PART ' + textbuf)
        elif command == 'me':
            return ('sendmemsg', textbuf)
        elif command == 'quit':
            return ('quit', textbuf)

    return ('sendmsg', textbuf)

def test(stdscr):
    curses.curs_set(1)
    curses.setsyx(0, 0)

    poll = select.poll()
    poll.register(stdin, select.POLLIN)
    win = ScrollableWindow(stdscr, 1, 0, 1, 0)
    win.pad.nodelay(1)
    client = CustomClient(host='irc.interlinked.me', port=6667,
                          channels=['#irclib'], nick='testclient',
                          window=win)
    win.change_buffer('#irclib')

    logging.basicConfig(filename='irc.log')

    try:
        client.connect()
    except:
        pass

    fdmap = {
        client.sock.fileno() : client
    }

    poll.register(client.sock.fileno(), select.POLLIN|select.POLLOUT)

    textbuf = ''
    curpos = 0
    curinstance = client
    while True:
        for fd, event in poll.poll(1):
            if fd == stdin.fileno():
                key = win.pad.getch()
                if key == -1: continue
                if not win.key_event(key):
                    if key == curses.KEY_BACKSPACE or key == 127:
                        if textbuf: textbuf = textbuf[:-1]
                    elif key == curses.KEY_ENTER or key == 10:
                        verb, text = process_buffer(textbuf)
                        if verb == 'cmd':
                            curinstance.linewrite(Line(text))
                        elif verb == 'sendmsg':
                            if win.curbuf:
                                curinstance.cmdwrite('PRIVMSG', (win.curbuf, text))
                        elif verb == 'sendmemsg':
                            if win.curbuf:
                                curinstance.ctcpwrite(win.curbuf, 'ACTION', text)
                        elif verb == 'changewin':
                            win.change_buffer(text)
                        elif verb == 'quit':
                            curinstance.cmdwrite('QUIT', (textbuf,))
                            curinstance.timer_cancel_all()
                            return
                        
                        textbuf = ''
                    else:
                        textbuf += curses.keyname(key).decode('ascii','replace')
                        curpos = len(textbuf)

                    padding = ' ' * ((win.cols-1) - len(textbuf))
                    stdscr.addstr(win.rows-1, 0, textbuf + padding)
                    stdscr.move(win.rows-1, len(textbuf))

                    stdscr.refresh()
            else:
                if fd not in fdmap: continue 
                instance = fdmap[fd]
                if event & select.POLLIN:
                    try:
                        instance.process_in()
                    except Exception as e:
                        if not instance.connected:
                            raise

                    if win.curbuf and win.curbuf in instance.channels:
                        ch = instance.channels[win.curbuf]
                        if ch.topic:
                            printopic = ch.topic[:win.cols-1]
                            padding = ' ' * ((win.cols-1) - len(printopic))
                            stdscr.addstr(0, 0, printopic + padding)

                    # argh
                    stdscr.move(win.rows-1, len(textbuf))
                    stdscr.refresh()
                if event & select.POLLOUT:
                    if not instance.handshake:
                        instance.do_handshake()

                    try:
                        instance.send()
                    except Exception as e:
                        if not instance.connected:
                            raise
                    else:
                        if len(instance.send_buffer) == 0:
                            poll.modify(fd, select.POLLIN)
                            continue

            if len(curinstance.send_buffer) > 0:
                poll.modify(fd, select.POLLIN|select.POLLOUT)

curses.wrapper(test)
