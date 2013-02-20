""" An implementation of timers using the threading module. """

from threading import Timer as _Timer
from threading import Lock

class TimerItem:
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
class Timer:
    def __init__(self):
        self.timers = dict()
        self.timerlock = Lock()


    def __timer_wrap(self, name):
        assert name in self.timers

        with self.timerlock:
            # One at a time only
            item = self.timers[name]
            item.run_function()

        if not item.repeat:
            del self.timers[name]
        else:
           # Add it back
           self.add_repeat(name, item.time, item.function, item.args, item.kwargs)


    """ Add a timer """
    def add(self, name, time, repeat, function, args=[], kwargs={}):
        if name in self.timers:
            self.timers[name].timer.cancel()

        timer = _Timer(time, self.__timer_wrap, args=[name])
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
        timer = self.timers[name].timer
        timer.cancel()
        del self.timers[name]


    """ Cancel all timers """
    def cancel_all(self):
        for name, timer in self.timers.items():
            timer.timer.cancel()
