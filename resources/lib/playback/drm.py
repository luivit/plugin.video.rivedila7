"""DASH and Widevine: the license the Conax server wants, and the item that plays it.

The add-on cannot test this path on a desktop Kodi (there is no Widevine there), so
it stays as small and as literal as the player configuration allows: ask the token
endpoint for a pre-authorization token, hand inputstream.adaptive the manifest
together with the license URL and the header that token belongs in, and stop.

Which license and which token endpoint are not decisions this module makes: an
episode page publishes `drmLicenseServer` and `drmTokenEndpoint` next to its player
data, and they arrive here already extracted. The addresses in `globals` are what
the site answered when the payload said nothing - a site that moves its license
server then needs no release, and an old page still plays.
"""

import time
import urllib.parse

import inputstreamhelper
import requests

from resources.lib.globals import G
from resources.lib.kodi import player
from resources.lib.kodi.dialogs import AddonError

# what the player needs to open a Widevine stream, and nothing else
PLAYER = 'inputstream.adaptive'

# the token the license server expects, then where it goes
TOKEN_HEADER = 'preAuthorization'

# how long the token request may take, in seconds: the token expires by itself
TIMEOUT = 10


def play_live(channel):
    """Play one of the live channels: a fixed manifest, a token for its content id."""
    live = G.LIVE[channel]
    play(live['manifest'], token_url('LIVE', live['content_id']), G.LANGUAGE(live['label']))


def play(manifest, token_url, license_url=None, title='', plot=''):
    """Play one Widevine protected DASH stream: the manifest, and a token to ask for."""
    try:
        pre_auth_token = _token(token_url)
    except (OSError, KeyError, ValueError) as cause:
        # the license is the stream: without the token there is nothing to play
        raise AddonError(G.MODE, cause)
    helper = inputstreamhelper.Helper(G.DRM_PROTOCOL, drm=G.DRM)
    if not helper.check_inputstream():
        raise AddonError(G.MODE, OSError('inputstream.adaptive cannot play Widevine'))
    player.resolve(manifest, title, plot,
                   properties={'inputstream': helper.inputstream_addon,
                               'inputstream.adaptive.manifest_type': G.DRM_PROTOCOL,
                               'inputstream.adaptive.license_type': G.DRM,
                               'inputstream.adaptive.license_key':
                                   _license(pre_auth_token, license_url)},
                   mime='application/dash+xml')


def token_url(kind, content_id, endpoint=None):
    """The pre-authorization token URL the player asks for a stream of this kind."""
    return '%s?id=%s&contentType=%s&v=%d' % (endpoint or G.URL_DRM_TOKEN, content_id, kind,
                                             int(time.time() * 1000))


def _token(url):
    """The pre-authorization token the license server wants for one stream."""
    # no 'host' header: the endpoint derives it from its own URL, and a wrong one
    # makes it answer with an empty body
    return requests.get(url, headers=dict(G.HEADERS_SET), timeout=TIMEOUT,
                        verify=False).json()['preAuthToken']


def _license(pre_auth_token, license_url=None):
    """The license key inputstream.adaptive takes: URL, headers, and the challenge."""
    url = license_url or G.KEY_WIDEVINE
    headers = {'host': urllib.parse.urlsplit(url).netloc,
               TOKEN_HEADER: pre_auth_token,
               'user-agent': G.HEADERS_SET['user-agent'],
               'origin': G.HEADERS_SET['origin'],
               'referer': G.HEADERS_SET['referer']}
    handshake = '&'.join('%s=%s' % (name, value) for name, value in headers.items())
    return '%s?d=%d|%s|R{SSM}|' % (url, int(time.time()), handshake)
