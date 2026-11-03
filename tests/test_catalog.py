"""The catalogue: the root menu, the programs page, and the index behind it.

The answers these tests read are real answers of the site (see
tests/fixtures/capture.py), replayed through `la7play.client`. They are walked the
way Kodi walks them - a mode in, a directory out - so what is asserted is the
folder the device would show, not a helper's return value.
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

MENU = ['[B]string 32002[/B]', '[B]string 32009[/B]', '[B]string 32001[/B]', '[B]string 32004[/B]',
        '[B]string 32013[/B]', '[B]string 32014[/B]', '[B]string 32006[/B]', '[B]string 32016[/B]',
        '[B]string 32017[/B]', '[B]string 32018[/B]', '[B]string 32012[/B]']

MODES = ['diretta_la7', 'diretta_la7cinema', 'rivedi_la7', 'rivedi_la7cinema',
         'film', 'documentari', 'tutti_programmi', 'podcast', 'notizie', 'meteo', 'cerca_la7']

GROUPS = ['Prima serata', 'La giornata', 'La7Play Original', 'Intrattenimento culturale',
          'Le nostre inchieste', 'Viaggia con noi', 'Lifestyle', 'Eventi', 'Teche']


def all_programs(rows):
    """An allPrograms answer carrying the rows a test wants to publish."""
    return json.dumps({'data': {'graphqlTuttiProgrammi': {'results': rows}}}).encode('utf-8')


class CatalogTest(unittest.TestCase):
    def setUp(self):
        harness.install_stubs()
        harness.unload_addon_modules()
        from resources.lib import plugin
        from resources.lib.globals import G
        from resources.lib.kodi import dialogs
        from resources.lib.la7play import catalog, client
        self.plugin, self.G, self.dialogs = plugin, G, dialogs
        self.catalog, self.client = catalog, client
        self.serve()

    def serve(self, rows=None, error=None):
        """The answers the catalogue asks for: the site's, or the ones a test gives it."""
        self.site = Site(error=error)
        if error is None:
            self.site.answers[self.G.GQL_QUERIES['nsContentHub']] = fixture('gql-nsContentHub-programmi.json')
            self.site.answers[self.G.GQL_QUERIES['allPrograms']] = (
                all_programs(rows) if rows is not None else fixture('gql-allPrograms.json'))
        self.client.urlopen = self.site

    def serving_hub(self, name):
        """Answer the hub query of one section with the answer the site gave."""
        self.serve()
        self.site.answers[self.client.query_url('nsContentHub', {'path': '/' + name})] = (
            fixture('gql-nsContentHub-%s.json' % name))

    def entering(self, mode='tutti_programmi'):
        """The globals of one add-on call, as Kodi makes it."""
        self.G.init_globals(['plugin://plugin.video.rivedila7/', '1', '?mode=%s' % mode])

    def call(self, query):
        """The add-on as Kodi calls it, with the site's answers in place."""
        def prepare():
            from resources.lib.la7play import client
            client.urlopen = self.site
        return harness.run_addon(query, prepare=prepare)

    @staticmethod
    def params(item):
        return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(item['url']).query))

    def test_the_root_menu_is_the_eleven_sections_of_the_contract(self):
        self.entering('')
        self.catalog.show_root_menu()
        self.assertEqual([item['label'] for item in harness.ITEMS], MENU)
        self.assertEqual([self.params(item)['mode'] for item in harness.ITEMS], MODES)
        self.assertEqual(harness.ENDINGS, [{'succeeded': True}])

    def test_the_two_live_entries_are_played_not_opened(self):
        self.entering('')
        self.catalog.show_root_menu()
        for item in harness.ITEMS[:2]:
            self.assertFalse(item['folder'])
            self.assertTrue(item['url'].endswith('&_l=.pvr'), item['url'])
            self.assertEqual(item['item'].properties['isPlayable'], 'true')
        for item in harness.ITEMS[2:]:
            self.assertTrue(item['folder'])

    def test_every_entry_of_the_menu_has_a_mode_behind_it(self):
        # the menu is a subset: a mode can also be a call the add-on makes to itself,
        # like the one that fills an archive while the user reads
        self.assertEqual([mode for mode, _label, _art, _folder, _live in self.catalog.ROOT_MENU
                          if mode not in self.plugin.MODES], [])

    def test_the_programs_page_lists_the_groups_and_the_flat_list(self):
        self.entering()
        self.catalog.programmi()
        self.assertEqual([item['label'] for item in harness.ITEMS[:-1]], GROUPS)
        self.assertEqual(self.params(harness.ITEMS[0]),
                         {'mode': 'tutti_programmi', 'gruppo': 'Prima serata'})
        self.assertEqual(harness.ITEMS[-1]['label'], 'string 32015')
        self.assertEqual(self.params(harness.ITEMS[-1]),
                         {'mode': 'tutti_programmi', 'lettera': 'tutti'})

    def test_a_group_lists_the_programs_it_publishes(self):
        self.entering()
        self.catalog.gruppo('Prima serata')
        self.assertEqual([item['label'] for item in harness.ITEMS],
                         ['Otto e mezzo', 'La torre di babele', 'diMartedì'])
        first = harness.ITEMS[0]
        self.assertTrue(first['folder'])
        self.assertEqual(self.params(first), {'mode': 'tutti_programmi',
                                              'link': 'https://www.la7play.it/otto-e-mezzo'})
        self.assertEqual(first['item'].art['thumb'],
                         'https://images.la7play.it/video/0/406/0_qu202eyc_0_35uew99k_2/'
                         'otto-e-mezzo/programma-854x480.webp')
        self.assertEqual(harness.ENDINGS, [{'succeeded': True}])

    def test_the_flat_list_is_the_index_of_the_site_and_the_programs_it_forgets(self):
        self.entering()
        self.catalog.tutti_programmi()
        labels = [item['label'] for item in harness.ITEMS]
        # the site's own index, then the programs whose pages answer but that it does
        # not list (Kodi sorts the folder itself: the order here is the insertion one)
        self.assertEqual(labels[:-2], sorted(labels[:-2], key=str.casefold))
        self.assertEqual(labels[-2:], ['Faccia a Faccia', 'TG LA7'])
        self.assertEqual(len(labels), len(set(labels)), 'a program is listed once')
        self.assertTrue(all(item['folder'] for item in harness.ITEMS))
        self.assertTrue(all(self.params(item)['link'].startswith('https://www.la7play.it/')
                            for item in harness.ITEMS))
        self.assertEqual(harness.ITEMS[0]['item'].info['plot'][:12], 'Piazzapulita')

    def test_a_row_without_a_title_or_a_path_is_not_a_folder(self):
        self.serve(rows=[{'titolo': 'Kept', 'pathname': '/kept'},
                         {'titolo': '', 'pathname': '/no-title'},
                         {'titolo': 'No path'},
                         {'titolo': 'Kept', 'pathname': '/kept'},
                         {'titolo': 'By path', 'path': '/by-path'}])
        self.entering()
        self.catalog.tutti_programmi()
        labels = [item['label'] for item in harness.ITEMS]
        self.assertEqual(labels[:2], ['Kept', 'By path'])
        self.assertNotIn('', labels)
        self.assertEqual(len(labels), 4, 'the two rows and the two programs of the manual list')

    def test_the_film_section_lists_the_films_of_its_hub(self):
        self.serving_hub('film')
        items, _, dialogs = self.call('?mode=film')
        self.assertEqual(dialogs, [])
        self.assertEqual([item['label'] for item in items][:3],
                         ['Passenger', 'Il favoloso mondo di Amélie', 'Destini incrociati'])
        self.assertTrue(all(not item['folder'] for item in items))
        self.assertTrue(all(self.params(item)['play'].startswith('https://www.la7play.it/film/')
                            for item in items))
        self.assertTrue(items[0]['item'].art['thumb'].startswith('https://images.la7play.it/'))
        self.assertEqual(harness.ENDINGS, [{'succeeded': True}])

    def test_a_film_the_hub_recommends_twice_is_listed_once(self):
        self.serving_hub('film')
        items, _, _ = self.call('?mode=film')
        plays = [self.params(item)['play'] for item in items]
        # the hub carries its films in a grid and recommends some of them again
        self.assertEqual(len(plays), len(set(plays)))
        self.assertEqual(len(plays), 16)
        self.assertEqual([item['label'] for item in items].count('Passenger'), 1)

    def test_a_section_does_not_open_the_hub_page_it_lists(self):
        self.serving_hub('film')
        items, _, _ = self.call('?mode=film')
        self.assertNotIn('https://www.la7play.it/film', [self.params(item)['play'] for item in items])

    def test_the_documentary_section_lists_the_documentaries_of_its_hub(self):
        self.serving_hub('documentari')
        items, _, dialogs = self.call('?mode=documentari')
        self.assertEqual(dialogs, [])
        plays = [self.params(item)['play'] for item in items]
        self.assertEqual(len(plays), 17)
        self.assertTrue(all(not item['folder'] for item in items))
        # a documentary lives under its own program as often as under the hub
        self.assertIn('https://www.la7play.it/la-torre-di-babele-doc/puntate/'
                      'puntata-del-27-10-2026-397975', plays)

    def test_a_hub_the_site_does_not_answer_is_one_dialog(self):
        self.serve(error=URLError('no route'))
        items, _, dialogs = self.call('?mode=film')
        self.assertEqual(items, [])
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])
        self.assertEqual(harness.ENDINGS, [{'succeeded': False}])
        self.assertTrue(harness.LOGS[0].startswith('RivediLA7: film: GqlError: '), harness.LOGS[0])

    def test_a_group_the_page_no_longer_publishes_is_a_dialog_not_a_folder(self):
        self.entering()
        with self.assertRaises(self.dialogs.AddonError) as raised:
            self.catalog.gruppo('Gruppo sparito')
        self.assertEqual(raised.exception.section, 'tutti_programmi')
        self.assertEqual(harness.ITEMS, [])
        self.assertEqual(harness.ENDINGS, [{'succeeded': False}])

    def test_a_site_that_does_not_answer_is_one_dialog_and_one_log_line(self):
        self.serve(error=URLError('no route'))
        items, _, dialogs = self.call('?mode=tutti_programmi')
        self.assertEqual(items, [])
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])
        self.assertEqual(harness.ENDINGS, [{'succeeded': False}])
        self.assertEqual(len(harness.LOGS), 1)
        self.assertTrue(harness.LOGS[0].startswith('RivediLA7: tutti_programmi: GqlError: '),
                        harness.LOGS[0])

    def test_the_menu_opens_without_asking_the_site(self):
        self.serve(error=URLError('no route'))
        items, _, dialogs = self.call('?mode=')
        self.assertEqual(len(items), 11)
        self.assertEqual(dialogs, [])
        self.assertEqual(self.site.asked, [])


if __name__ == '__main__':
    unittest.main()
