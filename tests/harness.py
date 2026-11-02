"""Run the add-on outside Kodi, and assert what Kodi would do with the result.

The harness replaces ``xbmc``, ``xbmcgui``, ``xbmcplugin``, ``xbmcaddon`` and the
third-party modules the add-on imports, then calls the add-on entry point exactly as
Kodi does.  Two behaviours are copied from Kodi on purpose, because getting them wrong
is invisible here and shows up as an empty folder on the device:

* items added after ``endOfDirectory`` are dropped;
* a dialog is a failure, not a message: a section that reports an error is broken.

Usage:
    tests/harness.py --self-test            run the offline tests
    tests/harness.py walk tutti_programmi [k=v ...] [--depth 2]
    tests/harness.py smoke                  walk every section in SECTIONS
"""

import datetime
import os
import sys
import types
import unittest
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_PATH = ROOT

ITEMS = []      # directory items, in the order the add-on added them
RESOLVED = []   # setResolvedUrl calls
DIALOGS = []    # every dialog box, as text: any of them fails a test
ENDINGS = []    # every endOfDirectory call, as {'succeeded': bool}
LOGS = []       # every xbmc.log line, in the order the add-on wrote it
CLOSED = False  # Kodi: after endOfDirectory, the directory is closed
DROPPED = 0     # items Kodi would have discarded

# the day a smoke run asks the guide for: it lists the days that have aired, so the
# newest day it can be asked about is yesterday
YESTERDAY = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%d-%m-%Y')

# Every section the add-on must be able to open; grows with the code.
# (mode, parameters, minimum entries)
SECTIONS = [
    ('', {}, 8),                                     # the root menu
    ('tutti_programmi', {}, 10),                     # the groups of the programs page + A-Z
    ('tutti_programmi', {'gruppo': 'Prima serata'}, 3),
    ('tutti_programmi', {'lettera': 'tutti'}, 20),
    ('rivedi_la7', {}, 3),                           # the days of the guide
    ('rivedi_la7cinema', {}, 3),
    ('rivedi_la7', {'giorno': YESTERDAY}, 3),        # the replays of a day
    ('tutti_programmi', {'link': 'https://www.la7play.it/otto-e-mezzo'}, 3),          # a program page
    ('tutti_programmi', {'link': 'https://www.la7play.it/otto-e-mezzo/puntate'}, 3),  # a category of one
]


class ListItem(object):
    def __init__(self, label='', offscreen=False):
        self.label = label
        self.art = {}
        self.info = {}
        self.properties = {}
        self.path = ''
        self.content = ''
        self.mimetype = ''

    def setArt(self, art):
        self.art.update(art)

    def setInfo(self, kind, info):
        self.info.update(info)

    def setProperty(self, key, value):
        self.properties[key] = value

    def setIsPlayable(self, value=True):
        pass

    def setPath(self, path):
        self.path = path

    def setContentLookup(self, value):
        pass

    def setMimeType(self, value):
        self.mimetype = value

    def setSubtitles(self, value):
        pass

    def addContextMenuItems(self, value, replace=False):
        pass


class Dialog(object):
    def ok(self, heading, message=''):
        DIALOGS.append('%s: %s' % (heading, message))

    def notification(self, heading, message='', **kw):
        DIALOGS.append('notification %s: %s' % (heading, message))

    def yesno(self, heading, message='', **kw):
        DIALOGS.append('yesno %s: %s' % (heading, message))
        return False

    def input(self, heading, default='', **kw):
        return ''

    def select(self, heading, options, **kw):
        return -1


class Addon(object):
    def getAddonInfo(self, name):
        return {'id': 'plugin.video.rivedila7', 'name': 'RivediLA7',
                'icon': os.path.join(ADDON_PATH, 'icon.png'),
                'path': ADDON_PATH, 'profile': '/tmp/rivedila7-profile'}.get(name, '')

    def getLocalizedString(self, string_id):
        return 'string %s' % string_id

    def getSetting(self, name):
        return ''

    def setSetting(self, name, value):
        pass

    def openSettings(self):
        pass


class _Lister(object):
    """The xbmcplugin functions, with Kodi's rule that a closed directory is final."""

    def addDirectoryItem(self, handle=None, url='', listitem=None, isFolder=True):
        global DROPPED
        if CLOSED:
            DROPPED += 1
            return False
        ITEMS.append({'url': url, 'label': getattr(listitem, 'label', ''),
                      'item': listitem, 'folder': isFolder})
        return True

    def addDirectoryItems(self, handle, items, totalItems=0):
        for url, listitem, isFolder in items:
            self.addDirectoryItem(handle, url, listitem, isFolder)
        return True

    def endOfDirectory(self, handle=None, succeeded=True, updateListing=False, cacheToDisc=True):
        global CLOSED
        ENDINGS.append({'succeeded': succeeded})
        CLOSED = True
        return True

    def setResolvedUrl(self, handle, succeeded, listitem):
        RESOLVED.append({'succeeded': succeeded, 'item': listitem})

    def setContent(self, handle, content):
        pass

    def addSortMethod(self, handle, method, label2Mask=''):
        pass


class _Response(object):
    def __init__(self, body=b'', status=200):
        self.content = body
        self.status_code = status
        self.text = body.decode('utf-8', 'replace') if isinstance(body, bytes) else body

    def json(self):
        import json
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise OSError('HTTP %s' % self.status_code)


def install_stubs():
    """Make the Kodi and third-party imports of the add-on resolve to the stubs."""
    global CLOSED, DROPPED

    xbmc = types.ModuleType('xbmc')
    xbmc.LOGDEBUG, xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 0, 1, 2, 3
    xbmc.log = lambda message, level=1: LOGS.append(message)
    xbmc.executebuiltin = lambda command, wait=False: None
    xbmc.getCondVisibility = lambda condition: False
    xbmc.getInfoLabel = lambda label: ''
    xbmc.Player = type('Player', (object,), {'isPlaying': lambda self: False,
                                             'play': lambda self, *a, **k: None,
                                             'getPlayingFile': lambda self: ''})
    xbmc.Monitor = type('Monitor', (object,), {'abortRequested': lambda self: False,
                                               'waitForAbort': lambda self, t=1: False})

    xbmcgui = types.ModuleType('xbmcgui')
    xbmcgui.ListItem = ListItem
    xbmcgui.Dialog = Dialog
    xbmcgui.DialogProgress = Dialog
    xbmcgui.Window = type('Window', (object,), {
        '_p': {},
        '__init__': lambda self, wid=10000: None,
        'setProperty': lambda self, k, v: None,
        'getProperty': lambda self, k: '',
        'clearProperty': lambda self, k: None})
    xbmcgui.INPUT_ALPHANUM = 0
    xbmcgui.NOTIFICATION_INFO = 'info'
    xbmcgui.NOTIFICATION_ERROR = 'error'

    xbmcplugin = types.ModuleType('xbmcplugin')
    lister = _Lister()
    xbmcplugin.addDirectoryItem = lister.addDirectoryItem
    xbmcplugin.addDirectoryItems = lister.addDirectoryItems
    xbmcplugin.endOfDirectory = lister.endOfDirectory
    xbmcplugin.setResolvedUrl = lister.setResolvedUrl
    xbmcplugin.setContent = lister.setContent
    xbmcplugin.addSortMethod = lister.addSortMethod
    for name, value in (('SORT_METHOD_LABEL', 1), ('SORT_METHOD_LABEL_IGNORE_FOLDERS', 2),
                        ('SORT_METHOD_NONE', 3), ('SORT_METHOD_UNSORTED', 4),
                        ('SORT_METHOD_TITLE', 5), ('SORT_METHOD_VIDEO_TITLE', 6),
                        ('SORT_METHOD_DATE', 7), ('SORT_METHOD_EPISODE', 8)):
        setattr(xbmcplugin, name, value)

    xbmcaddon = types.ModuleType('xbmcaddon')
    xbmcaddon.Addon = Addon

    helper = types.ModuleType('inputstreamhelper')
    helper.Helper = type('Helper', (object,), {
        'check_inputstream': lambda self, *a, **k: True,
        'install_inputstream': lambda self, *a, **k: True,
        'install_widevine': lambda self, *a, **k: True})

    requests = types.ModuleType('requests')
    requests.get = lambda *a, **k: _Response(b'')
    requests.post = lambda *a, **k: _Response(b'')
    requests.Session = type('Session', (object,), {'get': requests.get,
                                                   'post': requests.post})
    requests.exceptions = types.SimpleNamespace(RequestException=OSError)

    bs4 = types.ModuleType('bs4')
    bs4.BeautifulSoup = lambda *a, **k: types.SimpleNamespace(
        find=lambda *a, **k: None, find_all=lambda *a, **k: [], select=lambda *a, **k: [])

    for name, module in (('xbmc', xbmc), ('xbmcgui', xbmcgui), ('xbmcplugin', xbmcplugin),
                         ('xbmcaddon', xbmcaddon), ('inputstreamhelper', helper),
                         ('requests', requests), ('bs4', bs4)):
        sys.modules[name] = module

    CLOSED = False
    DROPPED = 0
    del ITEMS[:]
    del ENDINGS[:]
    del LOGS[:]


def unload_addon_modules():
    """Forget the add-on, so the next import re-reads the sources."""
    for name in [n for n in sys.modules if n.startswith('resources.lib')]:
        del sys.modules[name]


def reset_directory():
    """Reopen the directory, as a new add-on call does: Kodi keeps one per handle."""
    global CLOSED, DROPPED
    CLOSED = False
    DROPPED = 0


def run_addon(query, argv_handle='1', prepare=None):
    """Call the add-on entry point and return (items, resolved, dialogs).

    ``prepare()`` runs after the add-on is imported and before it is called: it is
    how a test hands a section an answer of the site without a network.
    """
    install_stubs()
    del ITEMS[:]
    del RESOLVED[:]
    del DIALOGS[:]

    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    unload_addon_modules()

    from resources.lib import plugin
    if prepare is not None:
        prepare()
    try:
        plugin.run(['plugin://plugin.video.rivedila7/', argv_handle, query])
    except Exception as error:
        # Kodi turns this into "GetDirectory ... failed" and an empty folder: record
        # it as a failure instead of letting it escape as a traceback
        DIALOGS.append('raised %s: %s' % (type(error).__name__, error))

    if DROPPED:
        DIALOGS.append('dropped %d item(s) added after endOfDirectory' % DROPPED)
    return list(ITEMS), list(RESOLVED), list(DIALOGS)


def walk(mode, params=None, depth=1, indent=0):
    """Print a section, recursing into folders when depth allows."""
    query = '?' + urllib.parse.urlencode(dict({'mode': mode}, **(params or {})))
    items, _, dialogs = run_addon(query)
    pad = '  ' * indent
    for item in items:
        print('%s%s%s' % (pad, item['label'], '' if item['folder'] else '  [play]'))
    if not items:
        print('%s(no entries)' % pad)
    for dialog in dialogs:
        print('%s!! %s' % (pad, dialog))
    if depth > 1:
        for item in items:
            if not item['folder']:
                continue
            sub = item['url'].split('?', 1)[-1]
            walk(None, dict(urllib.parse.parse_qsl(sub)), depth - 1, indent + 1)
    return items, dialogs


def smoke():
    """Walk every configured section; fail on an empty list or any dialog."""
    if not SECTIONS:
        # a gate that checks nothing must not report success
        print('no sections configured: nothing was verified')
        return False
    failures = 0
    for name, params, minimum in SECTIONS:
        items, dialogs = walk(name, params)
        problem = ''
        if dialogs:
            problem = 'dialog: %s' % dialogs[0]
        elif len(items) < minimum:
            problem = '%d entries (min %d)' % (len(items), minimum)
        print('%-4s %-20s %-40s %3d entries %s' % (
            'FAIL' if problem else 'ok', name, params, len(items), problem))
        failures += 1 if problem else 0
    print('\n%d section(s) failing' % failures)
    return failures == 0


def main(argv):
    if not argv or argv[0] in ('--self-test', 'test'):
        suite = unittest.defaultTestLoader.discover(os.path.join(ROOT, 'tests'))
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    if argv[0] == 'smoke' or argv[0] == '--smoke':
        return 0 if smoke() else 1
    if argv[0] == 'walk':
        params = dict(p.split('=', 1) for p in argv[2:] if '=' in p)
        depth = int(params.pop('--depth', 1))
        walk(argv[1], params, depth)
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
