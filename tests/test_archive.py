"""The archive of a category: replays kept on disk, clips read off their page.

A program's replays are an archive the site pages twenty at a time; read on every call
it would be thirty requests before the folder appears, so what has been read is kept and
a block of a hundred episodes is fetched per read. A clip listing is shallow and is read
page by page. What is checked here is that decision: which source, how much is read, when
the store is trusted, and what is asked of Kodi so the next block is there before the
user reaches it.
"""

import json
import os
import sys
import unittest

from urllib.error import HTTPError

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from tests import harness
from tests.site import Site

PROGRAM = 'https://www.la7play.it/otto-e-mezzo'
REPLAYS = PROGRAM + '/puntate'
CLIPS = PROGRAM + '/video'

PAGE_SIZE = 20


def listing_page(*cards):
    """A page whose payload lists the cards a test names, in the order given."""
    lines = ['%x:%s' % (position, json.dumps(one)) for position, one in enumerate(cards)]
    return ('<script>self.__next_f.push([1,%s])</script>' % json.dumps('\n'.join(lines))).encode('utf-8')


def card(title, path):
    """One card of a listing, with a picture and a text, as the site renders it."""
    return {'title': title, 'path': path,
            'uploadVideo': {'cf_thumbnail_url': 'https://images.la7play.it/video/%s.jpg' % path.strip('/')},
            'body': {'plainValue': 'Il testo di %s' % title}}


def refused(url):
    """The answer the site gives to a page it will not serve."""
    return HTTPError(url, 503, 'Service Temporarily Unavailable', {}, None)


def replays(count, prefix='puntata'):
    """The site's answers for `count` pages of an archive, twenty replays each."""
    answers = {}
    for page in range(1, count + 1):
        cards = [card('%s %d' % (prefix, (page - 1) * PAGE_SIZE + position),
                      '/otto-e-mezzo/puntate/%s-%d' % (prefix, (page - 1) * PAGE_SIZE + position))
                 for position in range(PAGE_SIZE)]
        answers[REPLAYS if page == 1 else '%s?page=%d' % (REPLAYS, page)] = listing_page(*cards)
    # the site answers an empty page past the end of the archive, whatever the number
    answers[REPLAYS + '?page=%d' % (count + 1)] = listing_page()
    return answers


class ArchiveSite(Site):
    """A site that answers, and refuses the requests a test names."""

    def __init__(self, answers, fail=None, error=None):
        super(ArchiveSite, self).__init__(answers, error)
        self.fail = fail or {}

    def __call__(self, request, timeout=None):
        for match, cause in self.fail.items():
            if match in request.full_url:
                self.asked.append(request.full_url)
                raise cause
        return super(ArchiveSite, self).__call__(request, timeout)


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        harness.install_stubs()
        harness.reset_profile()
        harness.unload_addon_modules()
        from resources.lib.globals import G
        from resources.lib.kodi.dialogs import AddonError
        from resources.lib.la7play import archive, archive_store, client
        self.G, self.AddonError = G, AddonError
        self.archive, self.store, self.client = archive, archive_store, client
        # the section that names a failure: Kodi sets the mode, a test says it itself
        self.G.init_globals(['plugin://plugin.video.rivedila7/', '1', '?mode=tutti_programmi'])
        self.serve()

    def serve(self, answers=None, fail=None):
        self.site = ArchiveSite(answers if answers is not None else replays(6), fail)
        self.client.urlopen = self.site

    def pages_asked(self):
        return [url for url in self.site.asked if '/puntate' in url]

    def test_the_first_page_of_an_archive_is_its_newest_episodes(self):
        nodes, more = self.archive.items('/otto-e-mezzo/puntate')
        self.assertEqual(len(nodes), PAGE_SIZE, 'one folder page, not the whole archive')
        self.assertTrue(more, 'an archive that goes on offers the page after it')
        self.assertEqual(nodes[0]['path'], '/otto-e-mezzo/puntate/puntata-0')
        self.assertEqual(nodes[-1]['path'], '/otto-e-mezzo/puntate/puntata-19')

    def test_the_first_page_reads_a_hundred_episodes_and_no_more(self):
        self.archive.items('/otto-e-mezzo/puntate')
        self.assertEqual(len(self.pages_asked()), 5, 'a block is a hundred episodes')

    def test_the_page_after_the_first_is_served_without_asking_the_site_again(self):
        self.archive.items('/otto-e-mezzo/puntate')
        asked = len(self.pages_asked())
        nodes, _ = self.archive.items('/otto-e-mezzo/puntate', 2)
        self.assertEqual(nodes[0]['path'], '/otto-e-mezzo/puntate/puntata-20')
        self.assertEqual(len(self.pages_asked()), asked, 'the store answers the second page')

    def test_an_archive_page_past_the_store_reads_the_next_block(self):
        self.archive.items('/otto-e-mezzo/puntate')
        nodes, _ = self.archive.items('/otto-e-mezzo/puntate', 6)
        self.assertEqual(nodes[0]['path'], '/otto-e-mezzo/puntate/puntata-100')
        self.assertIn(REPLAYS + '?page=6', self.site.asked)

    def test_the_archive_ends_where_the_site_stops_publishing_replays(self):
        self.serve(replays(2))
        nodes, more = self.archive.items('/otto-e-mezzo/puntate', 2)
        self.assertEqual(len(nodes), PAGE_SIZE)
        self.assertFalse(more, 'past the last page there is nothing to offer')

    def test_the_last_page_but_one_asks_for_the_next_block_in_the_background(self):
        self.archive.items('/otto-e-mezzo/puntate')
        # a hundred episodes are cached: five pages, and the fourth is the last but one
        self.archive.items('/otto-e-mezzo/puntate', 4)
        self.assertEqual(len(harness.BUILTINS), 1, harness.BUILTINS)
        self.assertTrue(harness.BUILTINS[0].startswith('RunPlugin(plugin://plugin.video.rivedila7/?'),
                        harness.BUILTINS[0])
        self.assertIn('mode=prefetch', harness.BUILTINS[0])

    def test_the_second_to_last_page_asks_for_nothing_a_page_later(self):
        self.archive.items('/otto-e-mezzo/puntate')
        self.archive.items('/otto-e-mezzo/puntate', 5)
        self.assertEqual(harness.BUILTINS, [], 'the last page is not the last but one')

    def test_the_background_call_fills_the_store_and_shows_nothing(self):
        self.archive.items('/otto-e-mezzo/puntate')
        items, _, dialogs = harness.run_addon('?mode=prefetch&play=' + REPLAYS)
        self.assertEqual(items, [], 'a background call lists nothing')
        self.assertEqual(dialogs, [], 'and it never reports')
        self.assertGreater(len(self.store.load('/otto-e-mezzo/puntate')['nodes']), 100,
                           'the block after the first hundred is in the store')

    def test_a_stale_archive_is_read_again_from_the_top(self):
        self.archive.items('/otto-e-mezzo/puntate')
        asked = len(self.pages_asked())
        self.store.TTL = -1      # as an archive read a week ago would be
        try:
            nodes, _ = self.archive.items('/otto-e-mezzo/puntate')
        finally:
            self.store.TTL = 6 * 3600
        self.assertGreater(len(self.pages_asked()), asked, 'a stale archive is read again')
        self.assertEqual(nodes[0]['path'], '/otto-e-mezzo/puntate/puntata-0')

    def test_a_listing_of_clips_never_touches_the_archive(self):
        clips = listing_page(card('La caduta del governo', '/otto-e-mezzo/video/la-caduta-1'),
                             card('Il discorso integrale', '/otto-e-mezzo/video/il-discorso-2'))
        self.serve({CLIPS: clips, CLIPS + '?page=2': listing_page()})
        nodes, _ = self.archive.items('/otto-e-mezzo/video')
        self.assertEqual([n['path'] for n in nodes],
                         ['/otto-e-mezzo/video/la-caduta-1', '/otto-e-mezzo/video/il-discorso-2'])
        self.assertEqual(self.store.load('/otto-e-mezzo/video'), {},
                         'a clip listing is not an archive: nothing is kept')

    def test_an_archive_the_site_does_not_answer_is_one_dialog(self):
        self.serve(fail={REPLAYS: refused(REPLAYS)})
        with self.assertRaises(self.AddonError):
            self.archive.items('/otto-e-mezzo/puntate')

    def test_the_second_page_of_a_listing_is_read_from_the_page(self):
        self.serve({CLIPS: listing_page(card('Prima', '/otto-e-mezzo/video/prima-1')),
                    CLIPS + '?page=2': listing_page(card('Seconda', '/otto-e-mezzo/video/seconda-2')),
                    CLIPS + '?page=3': listing_page()})
        nodes, more = self.archive.items('/otto-e-mezzo/video', 2)
        self.assertEqual([n['title'] for n in nodes], ['Seconda'])
        self.assertFalse(more)


if __name__ == '__main__':
    unittest.main()
