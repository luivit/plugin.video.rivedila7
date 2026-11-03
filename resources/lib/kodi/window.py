"""The one thing the add-on keeps between calls: what the user asked for.

A search is opened from the menu, and the same call comes back when playback stops:
Kodi re-opens the folder the video was started from. The query is remembered in a
Kodi window property, which outlives a single add-on invocation, so the folder can
be rebuilt without asking the user to type it again. The menu forgets it, which is
what makes a new search from the menu a new search.
"""

import xbmcgui

PROPERTY = 'rivedila7_%s'


def remember(name, value):
    """Keep a value for the calls that come after this one."""
    xbmcgui.Window(10000).setProperty(PROPERTY % name, value)


def recall(name):
    """The value a previous call kept, or ''."""
    return xbmcgui.Window(10000).getProperty(PROPERTY % name) or ''


def forget(name):
    """Drop a value: the next call that wanted it starts over."""
    xbmcgui.Window(10000).clearProperty(PROPERTY % name)
