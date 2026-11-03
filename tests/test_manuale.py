"""The manual list: the programs the site forgets, and the sections about the news.

Both are entries a human maintains, so what is checked is not that the site publishes
them - that is the site's business, and a folder fails loudly when it stops - but that
the add-on offers them where a viewer looks for them: news and weather as their own
sections, and a program the index omits reachable from the program list.
"""

import os
import sys
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from tests import harness
from tests.site import Site, fixture

PROGRAM = 'https://www.la7play.it/facciaafaccia'
NODE_PAGE = '/api/gql/' + 'e9d39e6838f7f588'   # nodePage
GUIDE = 'https://www.la7play.it/guida-tv-rivedi/la7'


def empty_guide():
    """A guide page with no programme at all: the categories are what a test checks."""
    return ('<script>self.__next_f.push([1,%s])</script>'
            % '"{\\"giorno\\":[]}"').encode('utf-8')


class ManualeTest(unittest.TestCase):
    def setUp(self):
        harness.install_stubs()
        harness.unload_addon_modules()
        self.serve()

    def serve(self, answers=None):
        base = {NODE_PAGE: fixture('gql-nodePage.json'), GUIDE: empty_guide()}
        base.update(answers or {})
        self.site = Site(base)
        from resources.lib.la7play import client
        client.urlopen = self.site

    def call(self, query):
        def prepare():
            from resources.lib.la7play import client
            client.urlopen = self.site
        return harness.run_addon(query, prepare=prepare)

    @staticmethod
    def params(item):
        return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(item['url']).query))

    def test_the_news_are_a_section_of_their_own(self):
        items, _, dialogs = self.call('?mode=notizie')
        self.assertEqual(dialogs, [])
        self.assertEqual([item['label'] for item in items], ['TG LA7'])
        self.assertEqual(self.params(items[0]),
                         {'mode': 'tutti_programmi', 'link': 'https://www.la7play.it/tgla7'})

    def test_the_weather_is_a_section_of_its_own(self):
        items, _, dialogs = self.call('?mode=meteo')
        self.assertEqual(dialogs, [])
        self.assertEqual([item['label'] for item in items], ['Meteo LA7', 'Omnibus Meteo'])
        self.assertTrue(all(item['folder'] for item in items))

    def test_a_program_the_index_forgets_opens_the_page_the_site_publishes(self):
        items, _, dialogs = self.call('?mode=tutti_programmi&link='
                                      + urllib.parse.quote(PROGRAM, safe=''))
        self.assertEqual(dialogs, [])
        self.assertTrue(items, 'the page publishes its categories')
        self.assertEqual([self.params(item)['link'] for item in items if item['folder']],
                         [PROGRAM + '/puntate', PROGRAM + '/video'])


if __name__ == '__main__':
    unittest.main()
