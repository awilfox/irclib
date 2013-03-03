""" An implementation of timers using the threading module. """

import sys
import traceback
from threading import Timer, RLock, Event
try:
    from queue import Queue
except ImportError:
    from Queue import Queue


class TimerItem(object):
    def __init__(self, timer, time, repeat, function, args=[], kwargs={}):
        self.timer = timer
        self.time = time
        self.repeat = repeat
        self.function = function
        self.args = args
        self.kwargs = kwargs


    def run_function(self):
        return self.function(*self.args, **self.kwargs)


""" Creates timers """
class TimerList(object):
    def __init__(self):
        self.timers = dict()
        self.timerlock = RLock()

        self.exqueue = Queue()
        self.exceptions = Event()


    def __timer_wrap(self, name):
        with self.timerlock:
            if name not in self.timers:
                return

            item = self.timers[name]

            try:
                item.run_function()
            except:
                print('Exception in timer', name)
                traceback.print_exc()
                self.exqueue.put(sys.exc_info())
                self.exceptions.set()

            if not item.repeat:
                del self.timers[name]
            else:
               # Add it back
               self.add_repeat(name, item.time, item.function, item.args,
                               item.kwargs)


    """ Add a timer """
    def add(self, name, time, repeat, function, args=[], kwargs={}):
        with self.timerlock:
            if name in self.timers:
                self.timers[name].timer.cancel()

            timer = Timer(time, self.__timer_wrap, args=[name])
            self.timers[name] = TimerItem(timer, time, repeat, function, args,
                                          kwargs)

            self.timers[name].timer.start()


    """ Add a oneshot timer """
    def add_oneshot(self, name, time, function, args=[], kwargs={}):
        self.add(name, time, False, function, args, kwargs)


    """ Add a recurring timer, only stops when cancelled """
    def add_repeat(self, name, time, function, args=[], kwargs={}):
        self.add(name, time, True, function, args, kwargs)


    """ Cancel a timer """
    def cancel(self, name):
        with self.timerlock:
            try:
                timer = self.timers[name].timer
                timer.cancel()
                del self.timers[name]
            except KeyError:
                return True


    """ Cancel all timers """
    def cancel_all(self):
        with self.timerlock:
            for name, timer in self.timers.items():
                timer.timer.cancel()

            self.timers.clear()

