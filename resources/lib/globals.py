# Everything that is to be globally accessible must be defined in this module.
# Kodi's reuseLanguageInvoker is a setting of the add-on, not a property of the code: this
# module may be imported once or on every invocation, so nothing here may assume otherwise.
# What is valid for a single invocation is rebuilt in init_globals(), the rest is derived from
# the add-on itself.

from urllib.parse import parse_qsl

import os
import xbmcaddon


class GlobalVariables(object):
    """The configuration of the add-on, and the parameters of one invocation.

    The values that come from the site, from Kodi or from the licence server are here
    so that no module under la7play/ or playback/ holds a constant of its own; the
    values that change per invocation are rebuilt in init_globals().
    """
    # pylint: disable=attribute-defined-outside-init
    # pylint: disable=invalid-name, too-many-instance-attributes

    PLUGIN_URL = "plugin://plugin.video.rivedila7/"
    FANART_PATH = os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources', 'fanart.jpg')
    THUMB_PATH = os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources', 'images')

    # the site the add-on reads; the old la7.it pages still served here are the ones
    # the scrapers in this release replace, one section at a time
    URL_PLAY_BASE = "https://www.la7play.it"

    URL_RIVEDILA7 = "https://www.la7play.it/guida-tv-rivedi/la7"
    URL_RIVEDILA7CINEMA = "https://www.la7play.it/guida-tv-rivedi/la7-cinema"

    # playback: the CDNs the site's own player uses. Verified on 2026-11-02: the
    # manifest of an episode, the playlist of a clear one, and both live manifests
    # answer 200. The license addresses are what an episode page publishes today and
    # what this add-on uses when the page stops publishing them
    URL_CDN_VOD = "https://awsvodpkg.iltrovatore.it"
    URL_CDN_DRM = "https://d3iki3eydrtvsa.cloudfront.net"
    URL_CDN_LIVE = "https://d15umi5iaezxgx.cloudfront.net"
    URL_DRM_TOKEN = "https://svc-01.la7play.it/DRM/tk.php"
    DRM_CONTENT_ID = "667"      # the content id the token endpoint knows a VOD by

    # the two live channels: a fixed manifest, and the content id its token asks for
    LIVE = {
        'la7': {'manifest': URL_CDN_LIVE + '/LA7/DRM/DASH/Live.mpd',
                'content_id': '1', 'label': 32002},
        'la7cinema': {'manifest': URL_CDN_LIVE + '/LA7D/DRM/DASH/Live.mpd',
                      'content_id': '2', 'label': 32009},
    }

    # la7play.it answers with persisted GraphQL queries: the id of the query, not its
    # text, is part of the URL (re-read them from the site when one stops answering)
    GQL_QUERIES = {
        'allPrograms': 'f7034d55158fc906',
        'filteredNodeReplicas': 'e4ec45c8e38bb081',
        'nodePage': 'e9d39e6838f7f588',
        'nsContentHub': '0f3f2c4225230faf',
        'siteSearch': '4da1e384f8a63808',
    }

    # DRM config
    DRM = 'com.widevine.alpha'
    DRM_PROTOCOL = 'mpd'
    KEY_WIDEVINE = "https://la7.prod.conax.cloud/widevine/license"
    HEADERS_SET = {
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36',
        'origin': 'https://www.la7.it',
        'referer': 'https://www.la7.it/',
    }

    def __init__(self):
        """Do nothing on constructing the object"""
        # Constructing this object must have no side effects: the module is imported before
        # Kodi has called the add-on even once, so anything that needs the add-on (settings,
        # paths, language) is read in init_globals() instead.
        self.ADDON = None

    def init_globals(self, argv):
        """Initialized globally used module variables. Needs to be called at start of each plugin instance!"""
        # xbmcaddon.Addon must be created at every instance otherwise it does not read any new changes to the settings
        self.ADDON = xbmcaddon.Addon()
        self.LANGUAGE = self.ADDON.getLocalizedString
        self.PLUGIN_NAME = self.ADDON.getAddonInfo('name')
        # the handle identifies this invocation: Kodi hands the add-on a new one per call
        self.PLUGIN_HANDLE = int(argv[1])
        self.PARAMS = parameters_string_to_dict(argv[2])
        self.MODE = str(G.PARAMS.get("mode", ""))
        self.GIORNO = str(G.PARAMS.get("giorno", ""))
        self.LINK = str(G.PARAMS.get("link", ""))
        self.GRUPPO = str(G.PARAMS.get("gruppo", ""))
        self.LETTERA = str(G.PARAMS.get("lettera", ""))
        self.TITOLO = str(G.PARAMS.get("titolo", ""))
        self.THUMB = str(G.PARAMS.get("thumb", ""))
        self.PLOT = str(G.PARAMS.get("plot", ""))
        self.PLAY = str(G.PARAMS.get("play", ""))
        self.QUERY = str(G.PARAMS.get("q", ""))
        # the page of a listing, when the folder offered one: 0 means the first
        page = str(G.PARAMS.get("page", ""))
        self.PAGENUM = int(page) if page.isdigit() else 0


def parameters_string_to_dict(parameters):
    return dict(parse_qsl(parameters[1:]))


# We initialize an instance importable of GlobalVariables from run_addon.py,
# where G.init_globals() MUST be called in the addon entry point.
G = GlobalVariables()
