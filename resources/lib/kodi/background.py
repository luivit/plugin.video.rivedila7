"""Asking Kodi for a second, invisible call: the work that happens while the user reads.

A folder page is rebuilt from scratch on every click, and Kodi gives it one call to
answer in. Reading the next hundred episodes of an archive inside that call would make
the click the user just made wait for it, so the next block is asked for the way a
plugin asks for anything else: another invocation, started by Kodi, in the background.
It fills the store and closes; the call that asked for it has already answered.

This module is the only place that builds a plugin URL for that call: a listing says
what it wants, not how to ask Kodi for it.
"""

import urllib.parse

import xbmc

from resources.lib.globals import G


def later(mode, **parameters):
    """Ask Kodi to call the add-on again, with these parameters, and return at once."""
    query = urllib.parse.urlencode(dict({'mode': mode}, **parameters))
    xbmc.executebuiltin('RunPlugin(%s?%s)' % (G.PLUGIN_URL, query))
