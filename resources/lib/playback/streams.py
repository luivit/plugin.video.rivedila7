"""One episode, one stream: the page says which, and the add-on only asks.

Since the restyling, an episode page carries its player data in the page payload as
`videoData`: the same node the listings show, with the fields that say how to play
it. Three answers are possible, and each has one way to play it:

* a plain URL (`urlVideo`) - play it as it is;
* a DRM protected node (`drm`) - its `uploadVideo.cf_remote_url` names the stream on
  the DRM CDN, and `drm.py` plays it with the license the Conax server wants;
* a clear node - the CDN builds an HLS playlist out of the progressive renditions
  the node publishes, and Kodi plays that playlist itself.

Nothing here scrapes markup or guesses a CDN path from a regex over the HTML: the
page's own data says what the stream is, and a page that does not say it fails with
the usual one dialog instead of playing something else.
"""

from resources.lib.globals import G
from resources.lib.kodi import player
from resources.lib.kodi.dialogs import AddonError
from resources.lib.la7play import client, payload
from resources.lib.playback import drm

# where a node's DRM stream and its clear renditions live
DRM_PATH = '/%s/DASH/%s.mpd'
CLEAR_PATH = '/local/hls/,%s,.mp4.urlset/master.m3u8'

# the key the episode page keeps its player data under
VIDEO = 'videoData'


def play_video(page):
    """Play the stream a page of the site publishes."""
    node = _video(page)
    manifest, content_id = _stream(node)
    if content_id:
        drm.play(manifest, drm.token_url('VOD', content_id))
        return
    player.resolve(manifest)


def _video(page):
    """The player data one page publishes, as the node that describes the stream."""
    try:
        text = payload.decode(client.fetch_html(page))
    except client.SiteError as cause:
        raise AddonError(G.MODE, cause)
    node = payload.value(text, VIDEO)
    if not isinstance(node, dict) or not node:
        raise AddonError(G.MODE, LookupError('%s publishes no video data' % page))
    return node


def _stream(node):
    """The manifest of a node, and the content id its license needs, if any."""
    if node.get('urlVideo'):
        return node['urlVideo'], None
    upload = node.get('uploadVideo') or {}
    remote = (upload.get('cf_remote_url') or '').strip()
    if not remote:
        raise AddonError(G.MODE, LookupError('%s publishes no stream' % payload.node_path(node)))
    if node.get('drm'):
        # encrypted content is one DASH stream on the DRM CDN, named after its entry
        name = remote.strip('/').split('/')[-1].replace('.mp4', '')
        return G.URL_CDN_DRM + DRM_PATH % (name, name), node.get('drmContentId') or G.DRM_CONTENT_ID
    # clear content is a list of progressive renditions the CDN turns into HLS
    return G.URL_CDN_VOD + CLEAR_PATH % _renditions(remote, upload.get('cf_old_entry_id')), None


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
