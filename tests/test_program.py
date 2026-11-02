"""A program page: its week of replays, the categories it publishes, its items.

The fixtures are the site's own answers: the `nodePage` query of a real program
(its submenu, in the site's order) and the page of one of its categories (the
cards it renders). The week comes from the guide, so the test writes that payload
instead of using the captured guide: the fixture of the guide is another program's
week, and a test that reads two files to find one item is a test that hides its
own assumptions.
"""

import json
import os
import sys
import unittest
import urllib.parse

from urllib.error import URLError

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from tests import harness
from tests.site import Site, fixture

PROGRAM = 'https://www.la7play.it/otto-e-mezzo'
CATEGORY = PROGRAM + '/puntate'
GUIDE = 'https://www.la7play.it/guida-tv-rivedi/la7'
GUIDE_CINEMA = 'https://www.la7play.it/guida-tv-rivedi/la7-cinema'
NODE_PAGE = '/api/gql/' + 'e9d39e6838f7f588'   # nodePage


def guide_page(*pathnames):
    """A guide page whose single day publishes the replays a test names."""
    programme = [{'titolo': 'Puntata del %d' % n, 'pathname': path}
                 for n, path in enumerate(pathnames)]
    days = [{'@attributes': {'data': '01-11-2026'}, 'programma': programme}]
    return ('<script>self.__next_f.push([1,%s])</script>' % json.dumps(json.dumps({'giorno': days}))
            ).encode('utf-8')


def listing_page(*cards):
    """A page whose payload lists the cards a test names, in the order given."""
    lines = ['%x:%s' % (position, json.dumps(one)) for position, one in enumerate(cards)]
    return ('<script>self.__next_f.push([1,%s])</script>' % json.dumps('\n'.join(lines))).encode('utf-8')


def card(title, path):
    """One card of a listing, with a picture and a text, as the site renders it."""
    return {'title': title, 'path': path,
            'uploadVideo': {'cf_thumbnail_url': 'https://images.la7play.it/video/%s.jpg' % path.strip('/')},
            'body': {'plainValue': 'Il testo di %s' % title}}


REPLAY = '/otto-e-mezzo/puntate/puntata-del-31-10-2026-398400'


class ProgramTest(unittest.TestCase):
    def setUp(self):
        harness.install_stubs()
        harness.unload_addon_modules()
        from resources.lib import plugin
        from resources.lib.globals import G
        from resources.lib.kodi.dialogs import AddonError
        from resources.lib.la7play import client, program
        self.plugin, self.G, self.AddonError = plugin, G, AddonError
        self.client, self.program = client, program
        self.serve()

    def serve(self, answers=None, error=None):
        """The answers a program page asks for: the site's, or the ones a test gives it."""
        if answers is None:
            answers = {GUIDE: guide_page(REPLAY),
                       GUIDE_CINEMA: guide_page(),
                       NODE_PAGE: fixture('gql-nodePage.json'),
                       CATEGORY: fixture('page-categoria.html')}
        self.site = Site(answers, error)
        self.client.urlopen = self.site

    def call(self, query):
        """The add-on as Kodi calls it, with the site's answers in place."""
        def prepare():
            from resources.lib.la7play import client
            client.urlopen = self.site
        return harness.run_addon(query, prepare=prepare)

    @staticmethod
    def params(item):
        return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(item['url']).query))

    def test_a_program_page_shows_its_week_then_its_categories(self):
        items, _, dialogs = self.call('?mode=tutti_programmi&link=' + urllib.parse.quote(PROGRAM, safe=''))
        self.assertEqual(dialogs, [])
        self.assertEqual([item['label'] for item in items],
                         ['domenica 1 novembre Puntata del 0', 'Puntate', 'Clip'])
        self.assertEqual([item['folder'] for item in items], [False, True, True])
        self.assertEqual(self.params(items[0])['play'], 'https://www.la7play.it' + REPLAY)
        self.assertEqual([self.params(item)['link'] for item in items[1:]],
                         [PROGRAM + '/puntate', PROGRAM + '/video'])
        self.assertEqual(harness.ENDINGS, [{'succeeded': True}])

    def test_the_categories_are_named_the_way_the_site_names_them(self):
        self.call('?mode=tutti_programmi&link=' + urllib.parse.quote(PROGRAM, safe=''))
        labels = [item['label'] for item in harness.ITEMS]
        # "Il Punto di Paolo Pagliaro" is a CMS section: the site has no page of it
        # this add-on can list, so it is not offered rather than offered empty
        self.assertNotIn('Il Punto di Paolo Pagliaro', labels)
        # a podcast is not a category: the site forwards to Spotify and friends
        self.assertNotIn('Podcast', labels)

    def test_a_program_page_reads_data_and_not_its_own_markup(self):
        self.call('?mode=tutti_programmi&link=' + urllib.parse.quote(PROGRAM, safe=''))
        asked = self.site.asked
        self.assertIn(NODE_PAGE, ''.join(asked))
        for request in asked:
            self.assertNotIn(PROGRAM, request, 'the program page was fetched as a page')

    def test_a_program_the_query_does_not_know_keeps_its_week(self):
        self.serve({GUIDE: guide_page(REPLAY), GUIDE_CINEMA: guide_page(),
                    NODE_PAGE: json.dumps({'data': {'route': None}}).encode('utf-8')})
        items, _, dialogs = self.call('?mode=tutti_programmi&link=' + urllib.parse.quote(PROGRAM, safe=''))
        self.assertEqual(dialogs, [])
        self.assertEqual([item['label'] for item in items], ['domenica 1 novembre Puntata del 0'])
        self.assertEqual(harness.ENDINGS, [{'succeeded': True}])

    def test_a_program_page_with_nothing_to_open_is_one_dialog(self):
        self.serve({GUIDE: guide_page(), GUIDE_CINEMA: guide_page(),
                    NODE_PAGE: json.dumps({'data': {'route': None}}).encode('utf-8')})
        items, _, dialogs = self.call('?mode=tutti_programmi&link=' + urllib.parse.quote(PROGRAM, safe=''))
        self.assertEqual(items, [])
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])
        self.assertEqual(harness.ENDINGS, [{'succeeded': False}])
        self.assertTrue(harness.LOGS[0].startswith('RivediLA7: tutti_programmi: LookupError: '),
                        harness.LOGS[0])

    def test_a_category_lists_the_items_its_page_publishes(self):
        self.call('?mode=tutti_programmi&link=' + urllib.parse.quote(CATEGORY, safe=''))
        items = [item for item in harness.ITEMS if not item['folder']]
        plays = [self.params(item)['play'] for item in items]
        self.assertEqual(len(plays), 14)
        self.assertEqual(plays[0], 'https://www.la7play.it/otto-e-mezzo/puntate/puntata-del-30-10-2026-398336')
        self.assertEqual(sorted(set(plays)), sorted(plays), 'a replay is listed once')
        self.assertTrue(all(play.startswith('https://www.la7play.it/otto-e-mezzo/puntate/')
                            for play in plays))
        first = items[0]
        self.assertTrue(first['label'].startswith('Puntata del 30/10/2026'))
        self.assertTrue(first['item'].art['thumb'].startswith('https://images.la7play.it/video/'))

    def test_a_category_does_not_list_the_program_page_it_belongs_to(self):
        self.call('?mode=tutti_programmi&link=' + urllib.parse.quote(CATEGORY, safe=''))
        plays = [self.params(item).get('play') for item in harness.ITEMS]
        self.assertNotIn('https://www.la7play.it/otto-e-mezzo', plays)

    def test_a_category_offers_the_page_after_the_one_it_lists(self):
        second = '/otto-e-mezzo/puntate/puntata-del-1-10-2026-394917'
        self.serve({CATEGORY + '?page=2': listing_page(card('Puntata del 1/10/2026', second)),
                    CATEGORY: fixture('page-categoria.html')})
        self.call('?mode=tutti_programmi&link=' + urllib.parse.quote(CATEGORY, safe=''))
        last = harness.ITEMS[-1]
        self.assertEqual(last['label'], '[B]string 32003[/B]')
        self.assertTrue(last['folder'])
        self.assertEqual(self.params(last), {'mode': 'tutti_programmi', 'link': CATEGORY, 'page': '2'})

    def test_a_later_page_is_asked_for_with_the_sites_own_paging(self):
        second = '/otto-e-mezzo/puntate/puntata-del-1-10-2026-394917'
        self.serve({CATEGORY + '?page=3': listing_page(),
                    CATEGORY + '?page=2': listing_page(card('Puntata del 1/10/2026', second)),
                    CATEGORY: fixture('page-categoria.html')})
        self.call('?mode=tutti_programmi&link=' + urllib.parse.quote(CATEGORY, safe='') + '&page=2')
        self.assertIn(CATEGORY + '?page=2', self.site.asked)
        self.assertEqual([item['label'] for item in harness.ITEMS], ['Puntata del 1/10/2026'])
        self.assertEqual(harness.ITEMS[0]['item'].info['plot'], 'Il testo di Puntata del 1/10/2026')

    def test_a_page_that_repeats_itself_is_not_offered_again(self):
        # the same listing answers every page number: paging would never end, so
        # the next page is offered only when it publishes something this one does not
        self.serve({CATEGORY: fixture('page-categoria.html')})
        self.call('?mode=tutti_programmi&link=' + urllib.parse.quote(CATEGORY, safe=''))
        self.assertNotIn('[B]string 32003[/B]', [item['label'] for item in harness.ITEMS])

    def test_a_category_that_publishes_nothing_is_one_dialog(self):
        self.serve({CATEGORY: guide_page()})   # a payload with no card in it
        items, _, dialogs = self.call('?mode=tutti_programmi&link=' + urllib.parse.quote(CATEGORY, safe=''))
        self.assertEqual(items, [])
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])
        self.assertEqual(harness.ENDINGS, [{'succeeded': False}])

    def test_a_site_that_does_not_answer_is_one_dialog(self):
        self.serve(error=URLError('no route'))
        _, _, dialogs = self.call('?mode=tutti_programmi&link=' + urllib.parse.quote(PROGRAM, safe=''))
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])
        self.assertTrue(harness.LOGS[0].startswith('RivediLA7: tutti_programmi: SiteError: '),
                        harness.LOGS[0])


if __name__ == '__main__':
    unittest.main()
