import curses
from irclib.client.client import IRCClient

from collections import deque, defaultdict
from functools import partial

def splitstr(buf, length):
    return [buf[i:i+length] for i in range(0, len(buf), length)]

class Buffer(object):
    def __init__(self, maxlen):
        self.maxlen = maxlen
        self.basetext = deque(maxlen=maxlen)
        self.buftext = deque(maxlen=maxlen) 
        self.scrollpos = 0


    def create_scratch(self, length=80):
        self.buftext = list()
        for line in self.basetext:
            self.buftext.extend(splitstr(line, length))


    def add_text(self, text):
        self.basetext.extend(text.split('\n'))


    def buflen(self):
        return len(self.buftext)


class ScrollableWindow(object):
    def __init__(self, stdscr, minposy, minposx, o_maxposy, o_maxposx,
                 maxlen=2000):
        self.stdscr = stdscr

        self.rows, self.cols = self.stdscr.getmaxyx() 

        self.minposy = minposy 
        self.minposx = minposx 
        self.maxposy = (self.rows - 1) - o_maxposy
        self.maxposx = (self.cols - 1) - o_maxposx

        defaultbuffer = partial(Buffer, maxlen)
        self.buffers = defaultdict(defaultbuffer)
        self.curbuf = None

        self.pad = curses.newpad(maxlen, self.cols)
        self.pad.keypad(1)


    """ Change current buffer """
    def change_buffer(self, bufname):
        self.curbuf = bufname
        self.stdscr.erase()
        self.display_pad()

    """ Add text to a buffer """
    def add_buffertext(self, text, bufname=None):
        if bufname is None:
            bufname = self.curbuf
        self.buffers[bufname].add_text(text)

        if bufname == self.curbuf:
            self.resize_pad()

    """ Drop a buffer """
    def delete_buffer(self, bufname):
        if bufname in self.buffers:
            del self.buffers[bufname]


    """ Resize the screen and/or text """
    def resize_pad(self, screenresize=False):
        if screenresize:
            self.rows, self.cols = self.stdscr.getmaxyx()
            self.maxposy = (self.rows - 1) - o_maxposy
            self.maxposx = (self.cols - 1) - o_maxposx

        self.buffers[self.curbuf].create_scratch(self.cols)
        self.fill_pad()


    def fill_pad(self):
        for index, line in enumerate(self.buffers[self.curbuf].buftext):
            self.pad.addstr(index, 0, line)

        self.display_pad()


    def display_pad(self):
        scrollpos = self.buffers[self.curbuf].scrollpos
        self.pad.refresh(scrollpos, 0, self.minposy, self.minposx,
                         self.maxposy, self.maxposx)


    def scroll_pad(self, count):
        maxlen = self.buffers[self.curbuf].buflen() - self.rows
        scrollpos = self.buffers[self.curbuf].scrollpos

        if scrollpos <= 0 and count < 0:
            scrollpos = 0
            curses.flash()
        elif scrollpos >= maxlen and count > 0:
            scrollpos = maxlen 
            curses.flash()
        else:
            scrollpos += count
            if scrollpos < 0:
                scrollpos = 0
            elif scrollpos > maxlen:
                scrollpos = maxlen

        self.buffers[self.curbuf].scrollpos = scrollpos
        self.display_pad()


    def key_event(self, key):
        if key == curses.KEY_UP:
            self.scroll_pad(-1)
            return True
        elif key == curses.KEY_DOWN:
            self.scroll_pad(1)
            return True
        elif key == curses.KEY_PPAGE:
            self.scroll_pad(-int(self.rows * 0.90))
            return True
        elif key == curses.KEY_NPAGE:
            self.scroll_pad(int(self.rows * 0.90))
            return True
        elif key == curses.KEY_RESIZE:
            self.resize_pad(True)
            return True

        return False

