"""The last step: hand a stream to Kodi, or tell Kodi the stream did not resolve.

Playback is the one place where the add-on talks to the player instead of the
directory, and the two calls it makes are these. Everything a listing does ends in
a folder; everything a play does ends in `resolve()` or in a failure that is
already being reported - and a play that fails must still say so to Kodi, or the
player waits for an answer that never comes.
"""

import xbmcplugin

from resources.lib.globals import G
from resources.lib.kodi import items


def resolve(manifest, title='', plot='', thumb='', properties=None, mime=''):
    """Play one stream: the manifest, and what the player needs to open it."""
    item = items.entry(title or G.TITOLO, thumb or G.THUMB, plot or G.PLOT)
    item.setPath(manifest)
    if mime:
        item.setMimeType(mime)
    for name, value in (properties or {}).items():
        item.setProperty(name, value)
    xbmcplugin.setResolvedUrl(G.PLUGIN_HANDLE, True, item)


def refuse():
    """Tell Kodi this item does not play; the dialog that says why is the caller's."""
    xbmcplugin.setResolvedUrl(G.PLUGIN_HANDLE, False, items.entry(G.TITOLO))
