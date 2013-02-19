from collections import defaultdict, namedtuple

class Dispatcher:
    DispatchItem = namedtuple('dispatchitem', 'priority uid function')


    def __init__(self):
        self.dispatch = defaultdict(list)

        # Map UID's to names
        self.uid_to_item = dict()

        self.uid = 0


    def add(self, name, priority, function):
        item = self.DispatchItem(priority, self.uid, function)
        self.dispatch[name].append(item)

        # ok unless there's lots (e.g. 10,000+) dispatches
        self.dispatch[name].sort()

        self.uid += 1
        self.uid_to_item[self.uid] = name

        return self.uid 


    def remove(self, name=None, uid=None):
        if (name, uid) is (None, None):
            raise ValueError("Valud uid or name required")

        if uid is not None:
            # Delete by UID
            if uid not in self.uid_to_item:
                raise ValueError("No such UID")

            name = self.uid_to_item[uid]

            for index, item in enumerate(self.dispatch[name]):
                if item.uid == uid:
                    delindex = index
                    break

            # Remove it
            del self.dispatch[name][delindex]
            del self.uid_to_item[uid]
        else:
            # Delete by name.
            if name not in self.dispatch:
                raise ValueError("No such name")

            # Clear UID's
            for item in self.dispatch[name]:
                del self.uid_to_item[item.uid]

            # Now purge the dictionary
            del self.dispatch[name]


    def has_name(self, name):
        return name in self.dispatch


    def run(self, name, args=[], kwargs={}):
        if name not in self.dispatch:
            raise ValueError("No such hook name")

        ret = list()
        for item in self.dispatch[name]:
            retval = item.function(*args, **kwargs)
            ret.append((item.function, retval))

        return ret

