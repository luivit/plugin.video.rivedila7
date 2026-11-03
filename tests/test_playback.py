"""Playback: what the page says the stream is, and what the player is handed.

The four addresses the add-on builds are the ones the site's own player uses, and
they were verified against the CDNs: the DASH manifest of a protected episode
answers 200, the HLS playlist of a clear one answers 200, and so do both live
manifests. What a test can check without a Widevine device is the part that is the
add-on's: which stream it picks, and what it tells Kodi to open.

The pages here are written, not captured: a page's player data is one structure and
the fixtures of the site are pages of listings. The structures are the site's.
"""

import json
import os
import sys
import unittest

from urllib.error import URLError

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from tests import harness
from tests.site import Site

EPISODE = 'https://www.la7play.it/otto-e-mezzo/puntate/puntata-del-30-10-2026-398336'
FILM = 'https://www.la7play.it/film/passenger-397232'

CLEAR_REMOTE = ('/nk/content/entry/data/0/406/0_qu202eyc_0_om4n7on0_2.mp4,'
                '/nk/content/entry/data/0/406/0_qu202eyc_0_tw5tugmz_2.mp4')
CLEAR_PLAYLIST = ('https://awsvodpkg.iltrovatore.it/local/hls/,'
                  '/nk/content/entry/data/0/406/0_qu202eyc_0_om4n7on0_2,'
                  '/nk/content/entry/data/0/406/0_qu202eyc_0_tw5tugmz_2,'
                  '.mp4.urlset/master.m3u8')


def video_page(**fields):
    """A page whose payload carries the player data of one video, as the site does."""
    return ('<script>self.__next_f.push([1,%s])</script>'
            % json.dumps(json.dumps({'videoData': fields}))).encode('utf-8')


def page_with(player, settings):
    """A page carrying both the video and the player settings the site publishes."""
    return ('<script>self.__next_f.push([1,%s])</script>'
            % json.dumps(json.dumps({'videoData': player, 'playerSettings': settings}))
            ).encode('utf-8')


def clear_page():
    return video_page(path='/otto-e-mezzo/puntate/puntata-del-30-10-2026-398336',
                      drm=False, urlVideo=None,
                      uploadVideo={'cf_remote_url': CLEAR_REMOTE, 'cf_old_entry_id': ''})


THE_EPISODES_DRM_SERVERS = ('com.widevine.alpha|https://licence.example.invalid/widevine;'
                            'com.microsoft.playready|https://licence.example.invalid/playready;'
                            'fairplay|https://licence.example.invalid/fairplay')


def protected_page():
    return video_page(path='/film/passenger-397232', drm=True, drmContentId='667',
                      uploadVideo={'cf_remote_url': '/F100623_20261020100231', 'cf_old_entry_id': ''})


def page_naming_its_own_player_settings():
    """A protected page that says where its license, its token and its CDNs live."""
    return page_with(
        {'path': '/film/passenger-397232', 'drm': True,
         'uploadVideo': {'cf_remote_url': '/F100623_20261020100231', 'cf_old_entry_id': ''}},
        {'abilitaDrm': True, 'drmContentId': '4242',
         'drmLicenseServer': THE_EPISODES_DRM_SERVERS,
         'drmTokenEndpoint': 'https://token.example.invalid/tk.php',
         'hostnameCdn': 'https://clear.example.invalid',
         'hostnameCdnDrm': 'https://drm.example.invalid'})


class Token(object):
    """The token endpoint, answering with the token the license server wants."""

    def __init__(self):
        self.asked = []

    def get(self, url, **kw):
        self.asked.append(url)
        return type('Answer', (object,), {'json': lambda self: {'preAuthToken': 'a-token'}})()


class PlaybackTest(unittest.TestCase):
    def setUp(self):
        harness.install_stubs()
        harness.unload_addon_modules()
        from resources.lib.globals import G
        from resources.lib.playback import drm
        self.G, self.drm = G, drm
        self.token = Token()

    def serve(self, page, answers=None, error=None):
        """The page a test plays, and the token endpoint that answers it."""
        base = {page: answers} if answers is not None else {}
        self.site = Site(base, error)
        return self.site

    def call(self, query, page=None, body=None, error=None):
        """The add-on as Kodi calls it, with the page and the token endpoint served."""
        site = self.serve(page, body, error) if page else Site({}, error)

        def prepare():
            from resources.lib.la7play import client
            from resources.lib.playback import drm
            client.urlopen = site
            drm.requests = self.token
        return harness.run_addon(query, prepare=prepare)

    def test_a_clear_episode_is_played_as_the_hls_playlist_of_its_renditions(self):
        self.call('?mode=tutti_programmi&play=' + EPISODE, EPISODE, clear_page())
        self.assertEqual(len(harness.RESOLVED), 1)
        resolved = harness.RESOLVED[0]
        self.assertTrue(resolved['succeeded'])
        self.assertEqual(resolved['item'].path, CLEAR_PLAYLIST)
        self.assertEqual(resolved['item'].properties, {}, 'a clear stream needs no player')
        self.assertEqual(harness.DIALOGS, [])

    def test_a_protected_episode_is_played_with_the_license_its_token_buys(self):
        self.call('?mode=film&play=' + FILM, FILM, protected_page())
        resolved = harness.RESOLVED[0]
        self.assertTrue(resolved['succeeded'])
        self.assertEqual(resolved['item'].path,
                         'https://d3iki3eydrtvsa.cloudfront.net/F100623_20261020100231'
                         '/DASH/F100623_20261020100231.mpd')
        self.assertEqual(resolved['item'].mimetype, 'application/dash+xml')
        self.assertEqual(resolved['item'].properties['inputstream'], 'inputstream.adaptive')
        self.assertEqual(resolved['item'].properties['inputstream.adaptive.manifest_type'], 'mpd')
        self.assertEqual(resolved['item'].properties['inputstream.adaptive.license_type'],
                         'com.widevine.alpha')
        license_key = resolved['item'].properties['inputstream.adaptive.license_key']
        self.assertTrue(license_key.startswith('https://la7.prod.conax.cloud/widevine/license?'))
        self.assertIn('preAuthorization=a-token', license_key)
        self.assertIn('|R{SSM}|', license_key)
        self.assertEqual(len(self.token.asked), 1)
        self.assertIn('id=667&contentType=VOD', self.token.asked[0])

    def test_a_page_that_names_its_license_server_is_played_with_that_one(self):
        """The site moves its license server and its CDNs without telling anyone: the page says where."""
        self.call('?mode=film&play=' + FILM, FILM, page_naming_its_own_player_settings())
        resolved = harness.RESOLVED[0]
        self.assertEqual(resolved['item'].path,
                         'https://drm.example.invalid/F100623_20261020100231'
                         '/DASH/F100623_20261020100231.mpd')
        license_key = resolved['item'].properties['inputstream.adaptive.license_key']
        self.assertTrue(license_key.startswith('https://licence.example.invalid/widevine?'),
                        license_key)
        # the host header follows the license, it is not a constant of the add-on
        self.assertIn('host=licence.example.invalid', license_key)
        self.assertEqual(len(self.token.asked), 1)
        self.assertTrue(self.token.asked[0].startswith('https://token.example.invalid/tk.php?'))
        self.assertIn('id=4242&contentType=VOD', self.token.asked[0])

    def test_a_clear_episode_is_played_from_the_cdn_the_page_names(self):
        page = page_with(
            {'path': '/otto-e-mezzo/puntate/puntata-del-30-10-2026-398336', 'drm': False,
             'uploadVideo': {'cf_remote_url': CLEAR_REMOTE, 'cf_old_entry_id': ''}},
            {'hostnameCdn': 'https://clear.example.invalid/'})
        self.call('?mode=tutti_programmi&play=' + EPISODE, EPISODE, page)
        self.assertEqual(harness.RESOLVED[0]['item'].path,
                         CLEAR_PLAYLIST.replace('https://awsvodpkg.iltrovatore.it',
                                                'https://clear.example.invalid'))

    def test_a_video_url_the_page_publishes_is_played_as_it_is(self):
        page = video_page(path='/x/video/y-1', urlVideo='https://example.invalid/a.m3u8')
        self.call('?mode=film&play=' + EPISODE, EPISODE, page)
        self.assertEqual(harness.RESOLVED[0]['item'].path, 'https://example.invalid/a.m3u8')

    def test_a_page_that_publishes_no_player_data_is_one_dialog(self):
        page = '<script>self.__next_f.push([1,%s])</script>' % json.dumps(json.dumps({'nothing': 1}))
        items, resolved, dialogs = self.call('?mode=film&play=' + EPISODE, EPISODE, page.encode('utf-8'))
        self.assertEqual(items, [])
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])
        self.assertEqual([entry['succeeded'] for entry in resolved], [False],
                         'Kodi is told the item did not resolve, so the player stops waiting')
        self.assertTrue(harness.LOGS[0].startswith('RivediLA7: film: LookupError: '), harness.LOGS[0])

    def test_a_site_that_does_not_answer_is_one_dialog(self):
        _, resolved, dialogs = self.call('?mode=film&play=' + EPISODE, EPISODE, None, URLError('no route'))
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])
        self.assertEqual([entry['succeeded'] for entry in resolved], [False])

    def test_a_token_the_site_does_not_give_is_one_dialog(self):
        def refuse(url, **kw):
            raise OSError('no token')
        self.token.get = refuse
        _, resolved, dialogs = self.call('?mode=film&play=' + FILM, FILM, protected_page())
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])
        self.assertEqual([entry['succeeded'] for entry in resolved], [False])

    def test_live_plays_the_manifest_of_its_channel(self):
        self.call('?mode=diretta_la7')
        resolved = harness.RESOLVED[0]
        self.assertTrue(resolved['succeeded'])
        self.assertEqual(resolved['item'].path,
                         'https://d15umi5iaezxgx.cloudfront.net/LA7/DRM/DASH/Live.mpd')
        self.assertIn('id=1&contentType=LIVE', self.token.asked[0])

    def test_live_cinema_plays_its_own_manifest(self):
        self.call('?mode=diretta_la7cinema')
        self.assertEqual(harness.RESOLVED[0]['item'].path,
                         'https://d15umi5iaezxgx.cloudfront.net/LA7D/DRM/DASH/Live.mpd')
        self.assertIn('id=2&contentType=LIVE', self.token.asked[0])


if __name__ == '__main__':
    unittest.main()
