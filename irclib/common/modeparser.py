import string
import copy

from collections import defaultdict, Sequence
from functools import total_ordering

""" Basic unit for a list mode """
@total_ordering
class ModeList:
    def __init__(self, param, setter=None):
        self.param = param
        self.setter = setter


    def __eq__(self, other):
        if isinstance(other, str):
            return self.param == other

        elif not isinstance(other, ModeList):
            return False

        return (self.param == other.param)


    def __lt__(self, other):
        if isinstance(other, str):
            return self.param < other
        elif not isinstance(other, ModeList):
            return False

        return (self.param < other.param)


    def match(self, other):
        # TODO IMPLEMENT
        raise NotImplementedError("Match is not yet supported")


""" Implements a generic mode parsing and storage interface.

This can be used for channel modes or client modes.
It is designed for maximum flexibility.
"""
class ModeSet:
    """ Create a ModeParser Instance

    args:
        requiresboth - requires a parameter when set and unset.
        requiresset - requires a parameter only when set
        requiresunset - requires a parameter only when unset
        multimode - modes that are a list (e.g. multiple sets)
        noparams - mode consumes no parameters. this is the default
    """
    def __init__(self, requiresboth, requiresset, requiresunset, multimode, noparams=''):
        self.requiresboth = requiresboth
        self.requiresset = requiresset
        self.requiresunset = requiresunset
        self.multimode = multimode
        self.noparams = noparams

        self.modes_noparam = set()
        self.modes_param = dict()
        self.modes_multi = defaultdict(list)


    """ Do we consume a parameter? """
    def consume_param(self, mode, adding):
        if mode in self.requiresboth or mode in self.multimode:
            return True

        if adding and mode in self.requiresset:
            return True
        elif not adding and self.requiresunset:
            return True

        return False


    """ Set a mode """
    def change_mode(self, mode, param, adding):
        if any(mode in x for x in (self.requiresset, self.requiresunset,
                                   self.requiresboth)):
            # parameter modes
            if adding:
                self.modes_param[mode] = param
            else:
                if mode in self.modes_param: del self.modes_param[mode]
            
        elif mode in self.multimode:
            # List mode
            if not isinstance(param, Sequence):
                param = (param, None)

            if adding:
                if param[0] not in self.modes_multi[mode]:
                    self.modes_multi[mode].append(param)
            else:
                purgelist = []
                for m in self.modes_multi[mode]:
                    if m == param:
                        purgelist.append(m)

                for m in purgelist: self.modes_multi[mode].remove(m)
        else:
            # Other kind of mode
            if adding:
                self.modes_noparam.add(mode)
            else:
                if mode in self.modes_param:
                    self.modes_noparam.remove(mode)


    """ Parses a mode string """
    def parse_modestring(self, modestring):
        # Split up
        s = modestring.split()

        # Urgh -.-
        if len(s) == 0: return

        # First is the mode string
        mode = s[0]

        # Parameters follow, maybe :P
        params = s[1:] if len(s) > 1 else []

        pindex = 0
        pmax = len(params)
        adding = True # Default is to add
        for char in mode:
            if char == '+':
                adding = True
            elif char == '-':
                adding = False
            elif char == '=':
                continue # XXX
            else:
                self.change_mode(char, param, adding)
