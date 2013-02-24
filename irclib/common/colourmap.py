from __future__ import unicode_literals

from irclib.common.six import u

colourmap = {
    0 : (1, 37),
    1 : (0, 30),
    2 : (0, 34),
    3 : (0, 32),
    4 : (0, 31),
    5 : (0, 33),
    6 : (0, 35),
    7 : (0, 33),
    8 : (1, 33),
    9 : (1, 32),
    10 : (0, 36),
    11 : (1, 36),
    12 : (1, 34),
    13 : (1, 31),
    14 : (1, 30),
    15 : (0, 37),
}

bold = 1
underline = 4
boldoff = 22
underlineoff = 24

base = '\x1b[{}m'

def get_colour(colourfg=None, colourbg=None):
    fmt = ''
    if colourfg is not None:
        c1, c2 = colourmap[colourfg % 16]

        c1, c2 = str(c1), str(c2)
        f = ';'.join((c1, c2))
        fmt += base.format(f)

    if colourbg is not None:
        c1, c2 = colourmap[colourbg % 16]
        c2 += 10 # offset for bg

        c1, c2 = str(c1), str(c2)
        f = ';'.join((c1, c2))
        fmt += base.format(f)

    return fmt


# Is the colour intense?
def intense_colour(colour):
    if colour is None:
        return False

    return bool(colourmap[colour % 16][0])


# reset colour, but keep bold/underline
def reset_colour(isbold=False, isunderline=False):
    fmt = [base.format(0)]

    if isbold:
        fmt.append(base.format(bold))

    if isunderline:
        fmt.append(base.format(underline))

    return ''.join(fmt)

def replace_colours(message):
    if message.startswith('\x01') or message.endswith('\x01'):
        return message

    # Start of colour position
    colour_start = None

    isbold = False
    isunderline = False
    colourfg = None
    colourbg = None

    oldmessage = message
    newmessage = []
    for index, char in enumerate(message):
        if char == '\x03':
            # Start of colour format string
            colour_start = index + 1
            continue
        elif char == '\x1f':
            isunderline = not isunderline
            
            if isunderline:
                newmessage.append(base.format(underline))
            else:
                newmessage.append(base.format(underlineoff))

            continue
        elif char == '\x02':
            isbold = not isbold

            if isbold:
                newmessage.append(base.format(bold))
            else:
                if not (intense_colour(colourfg) and intense_colour(colourbg)):
                    newmessage.append(base.format(boldoff))

            continue
        elif char == '\x0f':
            # Reset
            isbold = False
            isunderline = False
            colourfg = None
            colourbg = None
            newmessage.append(reset_colour())

            continue
        elif colour_start is not None:
            if not (char.isdigit() or char == ','):
                specifier = message[colour_start:index]
                colourfg, sep, colourbg = specifier.partition(',')

                colour_start = None

                # Foreground
                if not colourfg.isdigit():
                    colourfg = None
                else:
                    colourfg = int(colourfg)

                # Background
                if not colourbg.isdigit():
                    colourbg = None
                else:
                    colourbg = int(colourbg)

                fmt = get_colour(colourfg, colourbg)
                if fmt:
                    newmessage.append(fmt)
                else:
                    newmessage.append(reset_colour(isbold, isunderline))
            else:
                continue

        # Add to the string
        newmessage.append(char)

    # Reset term
    newmessage = u('').join(newmessage)
    if newmessage != oldmessage:
        newmessage += reset_colour()

    return newmessage
