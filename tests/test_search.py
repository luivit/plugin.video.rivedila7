"""Search: the site's own query, its hits, its paging, and what is remembered.

The fixtures are the two first answers the site gave for "manovra": three groups of
hits - a program, videos, articles - and a second page of the same search. What is
tested is which hits become something to open, and how the add-on asks again after
playback without asking the user to type the query a second time.
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

SEARCH = '/api/gql/' + '4da1e384f8a63808'   # siteSearch
ARTICLE = 'https://www.la7play.it/intanto/articolo/'


class SearchTest(unittest.TestCase):
    def setUp(self):
        harness.install_stubs()
        harness.unload_addon_modules()
        harness.WINDOW.clear()
        harness.TYPED = ''
        from resources.lib.globals import G
        from resources.lib.la7play import client, search
        self.G, self.client, self.search = G, client, search
        self.entering('cerca_la7')
        self.serve()

    def entering(self, mode, query=''):
        self.G.init_globals(['plugin://plugin.video.rivedila7/', '1', '?mode=%s' % mode + query])

    def serve(self, answers=None, error=None):
        """The answers the search asks for: the site's, or the ones a test gives it."""
        base = {self.client.query_url('siteSearch', {'q': 'manovra', 'limit': 20, 'page': 1}):
                fixture('gql-siteSearch.json'),
                self.client.query_url('siteSearch', {'q': 'manovra', 'limit': 20, 'page': 2}):
                fixture('gql-siteSearch-page2.json')}
        base.update(answers or {})
        self.site = Site(base, error)
        self.client.urlopen = self.site

    def call(self, query='', typed=''):
        """The add-on as Kodi calls it, with what the user types."""
        harness.TYPED = typed

        def prepare():
            from resources.lib.la7play import client
            client.urlopen = self.site
        return harness.run_addon('?mode=cerca_la7' + query, prepare=prepare)

    @staticmethod
    def params(item):
        return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(item['url']).query))

    @staticmethod
    def hits(items):
        """The items of a page, without the pager that may end it."""
        return [item for item in items if item['label'] != '[B]string 32003[/B]']

    def test_the_results_of_a_search_are_the_hits_of_the_site(self):
        items, _, dialogs = self.call('&q=manovra')
        self.assertEqual(dialogs, [])
        self.assertEqual([item['label'] for item in self.hits(items)],
                         ['Il fattore economico',
                          'Manovra 2027, Giannini: "La manovra del vorrei ma non posso"',
                          'Manovra economica, Guerzoni: \u201cSembra una manovra molto elettorale\u201d',
                          'Manovra, Trovati: "Non abbiamo abolito la Fornero"',
                          'Manovra, il libro dei sogni... infranti',
                          'Vannacci sulla manovra: "Tirata per le bretelle"',
                          'Manovra, tante promesse, poche risorse'])
        self.assertEqual(harness.ENDINGS, [{'succeeded': True}])

    def test_a_video_is_played_and_a_program_is_opened(self):
        items, _, _ = self.call('&q=manovra')
        found = self.hits(items)
        self.assertTrue(found[0]['folder'], 'a program is a folder of its categories')
        self.assertEqual(self.params(found[0]),
                         {'mode': 'tutti_programmi', 'link': 'https://www.la7play.it/il-fattore-economico'})
        self.assertTrue(all(not item['folder'] for item in found[1:]))
        self.assertEqual(self.params(found[1])['play'],
                         'https://www.la7play.it/otto-e-mezzo/video/'
                         'manovra-2027-giannini-la-manovra-del-vorrei-ma-non-posso-15-10-2026-661948')

    def test_an_article_is_not_offered_as_a_folder_that_leads_nowhere(self):
        items, _, _ = self.call('&q=manovra')
        offers = [self.params(item).get('play') or self.params(item).get('link')
                  for item in self.hits(items)]
        self.assertFalse([offer for offer in offers if (offer or '').startswith(ARTICLE)], offers)

    def test_a_search_with_more_pages_offers_the_next_one(self):
        items, _, _ = self.call('&q=manovra')
        last = items[-1]
        self.assertEqual(last['label'], '[B]string 32003[/B]')
        self.assertEqual(self.params(last), {'mode': 'cerca_la7', 'q': 'manovra', 'page': '2'})

    def test_a_search_that_fits_in_one_page_offers_none(self):
        one_page = {'data': {'siteSearch': {
            'total': 3, 'pageSize': 20, 'totalPages': 1,
            'groups': [{'contentType': 'video', 'hits': [
                {'contentType': 'video', 'title': 'Uno', 'url': '/uno/video/uno-1'}]}]}}}
        self.serve({self.client.query_url('siteSearch', {'q': 'manovra', 'limit': 20, 'page': 1}):
                    json.dumps(one_page).encode('utf-8')})
        items, _, _ = self.call('&q=manovra')
        self.assertEqual([item['label'] for item in items], ['Uno'])

    def test_the_page_after_the_one_listed_is_asked_for(self):
        items, _, _ = self.call('&q=manovra&page=2')
        self.assertEqual(len(items), 7)     # six hits of page two, then the pager
        last = items[-1]
        self.assertEqual(last['label'], '[B]string 32003[/B]')
        self.assertEqual(self.params(last), {'mode': 'cerca_la7', 'q': 'manovra', 'page': '3'})

    def test_the_query_the_user_types_is_the_query_the_site_is_asked(self):
        self.call(typed='manovra')
        self.assertEqual(harness.INPUTS, ['string 32012'])
        self.assertIn(SEARCH, self.site.asked[0])

    def test_a_search_the_user_cancels_is_an_empty_folder_and_no_dialog(self):
        items, _, dialogs = self.call(typed='')
        self.assertEqual(items, [])
        self.assertEqual(dialogs, [])
        self.assertEqual(self.site.asked, [])
        self.assertEqual(harness.ENDINGS, [{'succeeded': True}])

    def test_the_query_is_remembered_so_playback_can_come_back_to_it(self):
        self.call(typed='manovra')
        self.assertEqual(harness.INPUTS, ['string 32012'], 'the first search asks for the query')
        # Kodi re-opens the same folder when playback stops: no query in the url
        items, _, dialogs = self.call(typed='')
        self.assertEqual(dialogs, [])
        self.assertEqual(len(self.hits(items)), 7)
        self.assertEqual(harness.INPUTS, [], 'the second call asks nothing: it remembered')

    def test_the_menu_forgets_the_query_so_the_next_search_asks_again(self):
        self.call(typed='manovra')
        menu, _, _ = harness.run_addon('?mode=')
        self.assertEqual(len(menu), 9)
        items, _, _ = self.call(typed='')
        self.assertEqual(items, [])
        self.assertEqual(harness.INPUTS, ['string 32012'], 'a search from the menu asks again')

    def test_a_site_that_does_not_answer_is_one_dialog(self):
        self.serve(error=URLError('no route'))
        items, _, dialogs = self.call('&q=manovra')
        self.assertEqual(items, [])
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])
        self.assertEqual(harness.ENDINGS, [{'succeeded': False}])
        self.assertTrue(harness.LOGS[0].startswith('RivediLA7: cerca_la7: GqlError: siteSearch: '),
                        harness.LOGS[0])


if __name__ == '__main__':
    unittest.main()
