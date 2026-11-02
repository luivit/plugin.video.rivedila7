"""A folder entry as Kodi takes it: its name, its picture, its text.

Every listing of the add-on shows the same kind of thing - a name, a picture, a
line of text - whatever it was called on the site. This module is that one way, so
a listing decides *which* entries it publishes and in what order, and never builds
a ListItem itself.

The parameters a click carries stay with the listing: they name the mode, the
section and the kind of thing being opened, which is the listing's business.
"""

import xbmcgui

from resources.lib.globals import G


def entry(label, thumb='', plot=''):
    """One entry of a folder: its name, its picture and its text."""
    item = xbmcgui.ListItem(label, offscreen=True)
    art = {'fanart': G.FANART_PATH}
    if thumb:
        art['thumb'] = thumb
    item.setArt(art)
    if plot:
        item.setInfo('video', {'plot': plot})
    return item


def folder(label):
    """A folder: the name of what a click on it opens."""
    return entry(label)


def next_page():
    """The entry that opens the page after the one being listed."""
    return entry('[B]' + G.LANGUAGE(32003) + '[/B]')
