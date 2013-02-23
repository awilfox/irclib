from collections import Sequence
from itertools import chain

class ModeSet:
    """ Initalise

    p_set - modes that take a param only when set (+k)
    p_unset - modes that take a param only when unset (normally unused)
    p_both - modes that take a param when set and unset
    p_list - modes which are list modes
    p_prefix - modes which are status modes (+ov)
    """
    def __init__(self, p_set='', p_unset='', p_both='', p_list='',
                 p_prefix=''):
        self.p_set = p_set
        self.p_unset = p_unset
        self.p_both = p_both
        self.p_list = p_list
        self.p_prefix = p_prefix

        self.modes = dict()

        # Lists
        for m in chain(self.p_list, self.p_prefix):
            self.modes[m] = list()


    """ Does this mode use a param? """
    def use_param(self, mode, adding):
        # Unconditional param use
        if mode in chain(self.p_both, self.p_list, self.p_prefix):
            return True

        if adding:
            if mode in self.p_set: 
                return True
        else:
            if mode in self.p_unset:
                return True

        return False


    """ Match up a list mode
    
    NOTE - no pattern matching is done, yet.
    """
    def list_match(self, mode, param):
        if not isinstance(self.modes[mode], list):
            return # -.-

        if param == None:
            return # nothing to do
        
        for index, item in enumerate(self.modes[mode]):
            if param == item: return index

        return False


    """ Add a list mode """
    def add_listmode(self, mode, param):
        match = self.list_match(mode, param)
        if match is not False:
            return

        self.modes[mode].append(param)


    """ Delete a list mode """
    def del_listmode(self, mode, param):
        match = self.list_match(mode, param) 
        if match is None or match is False:
            return

        del self.modes[mode][match]


    """ Add a mode """
    def add_mode(self, mode, param):
        if mode in chain(self.p_list, self.p_prefix):
            return self.add_listmode(mode, param)
        
        self.modes[mode] = param


    """ Delete a mode """
    def del_mode(self, mode, param):
        if mode in chain(self.p_list, self.p_prefix):
            return self.del_listmode(mode, param)

        del self.modes[mode]


    """ Set a mode """
    def set_mode(self, mode, adding, param):
        if adding:
            self.add_mode(mode, param)
        else:
            self.del_mode(mode, param)


    """ Parse a modestring """
    def parse_modestring(self, string):
        # Split the params up
        split = string.split()
        modes = split[0]
        if len(split) > 1:
            params = split[1:]
        else:
            params = []

        # Parse the mode string
        adding = True # default
        pindex = 0
        plen = len(params)
        for mode in modes:
            print(mode)
            if mode == '+':
                adding = True
            elif mode == '-':
                adding = False
            elif mode == '=':
                # I've seen some crappy ircd's use this :|
                continue
            else:
                if self.use_param(mode, adding):
                    if (pindex+1) > plen:
                        warnings.warn('Unexpected parameter')
                        continue
                    param = params[pindex]
                    pindex += 1
                else:
                    param = True 

                self.set_mode(mode, adding, param)

        if plen > (pindex+1):
            warnings.warn('Excessive parameters passed')


    """ Check if a mode is set """
    def is_set(self, mode, param=None):
        if mode in chain(self.p_list, self.p_prefix):
            # List modes
            if not param:
                # Return param list
                return self.modes[mode]

            match = self.list_match(mode, param)
            if isinstance(match, int):
                # We got a match!
                return self.modes[mode][match]

            # Failure :(
            return match
        else:
            if mode not in self.modes:
                return False

            return self.modes[mode]

