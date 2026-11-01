"""The Kodi boundary: the only package that imports xbmc, xbmcgui or xbmcplugin.

Everything the add-on knows about directories, list items, dialogs and resolved
URLs is behind these two modules, so the rest of the code can be read and tested
without Kodi in the room.
"""
