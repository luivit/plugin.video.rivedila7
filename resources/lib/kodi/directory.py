"""The one place that opens and closes a Kodi directory.

Kodi silently drops every item added after ``endOfDirectory``, so a listing that
closes early just shows fewer entries than the code produced: that is how the
7.2.5 "empty folder" bug reached the device while the CLI looked fine. Here the
directory is an object that is alive only inside its ``with`` block, so adding
after closing, closing twice and forgetting to close all stop being things the
code can do.

Deduplication belongs to the directory instance as well: a listing that emits
the same program twice is a bug in that listing, not state for the next one.
"""

import urllib.parse

import xbmcgui
import xbmcplugin

from resources.lib.globals import G


class Directory(object):
    """A Kodi directory, open while the object is in scope."""

    def __init__(self, content=None, sort_method=None):
        self.content = content
        self.sort_method = sort_method
        self.succeeded = True
        self._labels = set()
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        # close on the failure path too; never swallow the exception
        self.close(self.succeeded if exc_type is None else False)

    def add(self, parameters, listitem, folder=True, is_live=False, unique=False):
        """Add one item. ``unique`` skips an item whose label is already listed."""
        if self._closed:
            raise RuntimeError('item added after the directory was closed')
        label = listitem.label
        if unique and label in self._labels:
            return False
        url = G.PLUGIN_URL + '?' + urllib.parse.urlencode(parameters)
        if is_live:
            url += '&_l=.pvr'  # per le dirette: non riprendere dall'ultima volta
        if not folder:
            listitem.setInfo('video', {})
            listitem.setProperty('isPlayable', 'true')
        if unique:
            self._labels.add(label)
        return xbmcplugin.addDirectoryItem(handle=G.PLUGIN_HANDLE, url=url,
                                           listitem=listitem, isFolder=folder)

    def header(self, label):
        """A section title: not a folder, not selectable."""
        if self._closed:
            raise RuntimeError('item added after the directory was closed')
        listitem = xbmcgui.ListItem('[B][COLOR blue]' + label + '[/COLOR][/B]', offscreen=True)
        return xbmcplugin.addDirectoryItem(handle=G.PLUGIN_HANDLE, url='', listitem=listitem)

    def fail(self):
        """Close without a listing: Kodi then reports the plugin error."""
        self.succeeded = False
        self.close(False)

    def close(self, succeeded=True):
        if self._closed:
            return
        self._closed = True
        if self.content:
            xbmcplugin.setContent(G.PLUGIN_HANDLE, self.content)
        if self.sort_method is not None:
            xbmcplugin.addSortMethod(G.PLUGIN_HANDLE, self.sort_method)
        xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=succeeded)
