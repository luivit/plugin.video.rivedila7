"""One episode, one stream: the page says which, and the add-on only asks.

Since the restyling, an episode page carries its player data in the page payload as
`videoData`: the same node the listings show, with the fields that say how to play
it. Three answers are possible, and each has one way to play it:

* a plain URL (`urlVideo`) - play it as it is;
* a DRM protected node (`drm`) - its `uploadVideo.cf_remote_url` names the stream on
  the DRM CDN, and `drm.py` plays it with the license the Conax server wants;
* a clear node - the CDN builds an HLS playlist out of the progressive renditions
  the node publishes, and Kodi plays that playlist itself.

The page also publishes the player's own settings - the two CDN hosts, the license
servers one scheme each, the token endpoint, the content id - so none of those is a
constant of the add-on: they are read from the page, and the addresses in `globals`
are what the site answered when this was written, used only when a page stops
publishing its settings. A moved license server needs no release.

Nothing here scrapes markup or guesses a CDN path from a regex over the HTML: the
page's own data says what the stream is, and a page that does not say it fails with
the usual one dialog instead of playing something else.
"""

from resources.lib.globals import G
from resources.lib.kodi import player
from resources.lib.kodi.dialogs import AddonError
from resources.lib.la7play import client, payload
from resources.lib.playback import drm

# where a node's DRM stream and its clear renditions live, below the CDN host the
# page publishes
DRM_PATH = '/%s/DASH/%s.mpd'
CLEAR_PATH = '/local/hls/,%s,.mp4.urlset/master.m3u8'

# the two keys the page keeps its player data under: the stream, and the player
VIDEO = 'videoData'
SETTINGS = 'playerSettings'


def play_video(page):
    """Play the stream a page of the site publishes."""
    text = _text(page)
    manifest, licence = _stream(payload.value(text, VIDEO) or {},
                                payload.value(text, SETTINGS) or {})
    if licence:
        drm.play(manifest,
                 drm.token_url('VOD', licence['content_id'], licence['token']),
                 licence['license'])
        return
    player.resolve(manifest)


def _text(page):
    """The page as one payload, or an AddonError naming this section."""
    try:
        return payload.decode(client.fetch_html(page))
    except client.SiteError as cause:
        raise AddonError(G.MODE, cause)


def _stream(node, settings):
    """The manifest of a node, and what its license needs, if it has one."""
    if not isinstance(node, dict):
        raise AddonError(G.MODE, LookupError('the page publishes no video data'))
    if node.get('urlVideo'):
        return node['urlVideo'], None
    upload = node.get('uploadVideo') or {}
    remote = (upload.get('cf_remote_url') or '').strip()
    if not remote:
        raise AddonError(G.MODE, LookupError('%s publishes no stream' % payload.node_path(node)))
    if node.get('drm'):
        # encrypted content is one DASH stream on the DRM CDN, named after its entry
        name = remote.strip('/').split('/')[-1].replace('.mp4', '')
        return _host(settings, 'hostnameCdnDrm', G.URL_CDN_DRM) + DRM_PATH % (name, name), \
            _licence(node, settings)
    # clear content is a list of progressive renditions the CDN turns into HLS
    return (_host(settings, 'hostnameCdn', G.URL_CDN_VOD) + CLEAR_PATH
            % _renditions(remote, upload.get('cf_old_entry_id')), None)


def _host(settings, key, fallback):
    """One CDN host as the page publishes it, without a trailing slash."""
    return (settings.get(key) or '').strip().rstrip('/') or fallback


def _licence(node, settings):
    """Where a protected node's license and token live, as the page names them.

    A page publishes `drmLicenseServer` as the list of the schemes it accepts
    (`com.widevine.alpha|<url>;com.microsoft.playready|<url>;...`), plus
    `drmTokenEndpoint` and `drmContentId`. What the page does not say keeps the
    addresses the site answered with when this was written.
    """
    return {'content_id': settings.get('drmContentId') or node.get('drmContentId')
            or G.DRM_CONTENT_ID,
            'token': (settings.get('drmTokenEndpoint') or '').strip() or G.URL_DRM_TOKEN,
            'license': _license_server(settings.get('drmLicenseServer')) or G.KEY_WIDEVINE}


def _license_server(servers):
    """The license URL one scheme is served by, or '' when the page names none."""
    for entry in (servers or '').split(';'):
        scheme, _, url = entry.partition('|')
        if scheme.strip() == G.DRM and url.strip():
            return url.strip()
    return ''


def _renditions(remote, old_entry):
    """The rendition paths of a node, in the form the CDN's HLS endpoint expects."""
    paths = remote.replace('.mp4', '')
    if old_entry:
        # an old entry is published with its paths already rooted
        return paths if paths.startswith('/') else '/' + paths
    entries = []
    for entry in paths.split(','):
        entry = entry.strip()
        if entry and not entry.startswith('/'):
            entry = '/' + entry
        if entry and not entry.startswith('/nk/'):
            entry = '/nk' + entry
        entries.append(entry)
    return ','.join(entries)
