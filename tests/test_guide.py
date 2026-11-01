"""The TV guide: the days it offers, the replays of a day, a program's week.

The fixture is the guide of LA7 as the site serves it (see
tests/fixtures/capture.py), cut to three days of three programs: the shapes are the
site's, the size is not. The guide is also the only place a program's week exists -
its page publishes no episode list - so `repliche` is tested here too, before the
program pages that call it exist.
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

GUIDE = 'https://www.la7play.it/guida-tv-rivedi/la7'
GUIDE_CINEMA = 'https://www.la7play.it/guida-tv-rivedi/la7-cinema'


def guide_page(days):
    """A page whose payload carries the days a test wants the guide to publish."""
    return ('<script>self.__next_f.push([1,%s])</script>' % json.dumps(json.dumps({'giorno': days}))
            ).encode('utf-8')


def day(data, *pathnames):
    """One day of a guide, as the site publishes it."""
    return {'@attributes': {'data': data},
            'programma': [{'titolo': 'Titolo %d' % n, 'pathname': path} for n, path in enumerate(pathnames)]}


class GuideTest(unittest.TestCase):
    def setUp(self):
        harness.install_stubs()
        harness.unload_addon_modules()
        from resources.lib import plugin
        from resources.lib.globals import G
        from resources.lib.kodi import dialogs
        from resources.lib.la7play import client, program
        self.plugin, self.G, self.dialogs = plugin, G, dialogs
        self.client, self.program = client, program
        self.serve()

    def serve(self, answers=None, error=None):
        """The answers the guide asks for: the site's, or the ones a test gives it."""
        if answers is None:
            answers = {GUIDE: fixture('page-guida-la7.html'),
                       GUIDE_CINEMA: fixture('page-guida-la7.html')}
        self.site = Site(answers, error)
        self.client.urlopen = self.site

    def entering(self, mode='rivedi_la7', giorno=''):
        """The globals of one add-on call, as Kodi makes it."""
        query = '?mode=%s' % mode + ('&giorno=%s' % giorno if giorno else '')
        self.G.init_globals(['plugin://plugin.video.rivedila7/', '1', query])

    def call(self, query):
        """The add-on as Kodi calls it, with the site's answers in place."""
        def prepare():
            from resources.lib.la7play import client
            client.urlopen = self.site
        return harness.run_addon(query, prepare=prepare)

    @staticmethod
    def params(item):
        return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(item['url']).query))

    def test_the_guide_offers_its_days_newest_first(self):
        self.entering()
        self.program.giorni('rivedila7.jpg')
        self.assertEqual([item['label'] for item in harness.ITEMS],
                         ['martedi 27 ottobre', 'lunedi 26 ottobre', 'domenica 25 ottobre'])
        self.assertEqual([self.params(item)['giorno'] for item in harness.ITEMS],
                         ['27-10-2026', '26-10-2026', '25-10-2026'])
        self.assertEqual(self.params(harness.ITEMS[0])['mode'], 'rivedi_la7')
        self.assertEqual(harness.ITEMS[0]['item'].art['thumb'],
                         os.path.join(harness.ADDON_PATH, 'resources', 'images', 'rivedila7.jpg'))
        self.assertEqual(harness.ENDINGS, [{'succeeded': True}])

    def test_a_day_lists_the_replays_it_publishes(self):
        self.entering(giorno='26-10-2026')
        self.program.giorno()
        self.assertEqual([item['label'] for item in harness.ITEMS],
                         ['07:00 Omnibus ST.27', '07:40 TG La7 Edizione Delle 7.30',
                          '07:55 Omnibus Meteo ST.2026'])
        first = harness.ITEMS[0]
        self.assertFalse(first['folder'])
        self.assertEqual(self.params(first), {
            'mode': 'rivedi_la7',
            'play': 'https://www.la7play.it/omnibus/puntate/puntata-del-26-10-2026-397839',
            'titolo': 'Omnibus ST.27',
            'thumb': 'https://images.la7play.it/media/c/h6f1bf590/guidatv/LA7/omnibus-st-27-programma-c07cced3.jpg/omnibus-st-27/640x360.webp',
            'plot': first['item'].info['plot']})
        self.assertTrue(first['item'].info['plot'].startswith('Programma quotidiano'))

    def test_the_cinema_channel_reads_its_own_guide(self):
        self.entering('rivedi_la7cinema')
        self.program.giorni('direttalivela7cinema.jpg')
        self.assertEqual(self.site.asked, [GUIDE_CINEMA])

    def test_a_day_without_a_replay_is_not_offered(self):
        self.serve({GUIDE: guide_page([day('25-10-2026', '/omnibus/puntate/one'),
                                       day('26-10-2026', ''),
                                       day('27-10-2026')])})
        self.entering()
        self.program.giorni('rivedila7.jpg')
        self.assertEqual([item['label'] for item in harness.ITEMS], ['domenica 25 ottobre'])

    def test_a_guide_with_nothing_to_replay_is_one_dialog(self):
        self.serve({GUIDE: guide_page([day('25-10-2026'), day('26-10-2026', '')])})
        items, _, dialogs = self.call('?mode=rivedi_la7')
        self.assertEqual(items, [])
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])
        self.assertEqual(harness.ENDINGS, [{'succeeded': False}])
        self.assertTrue(harness.LOGS[0].startswith('RivediLA7: rivedi_la7: LookupError: '),
                        harness.LOGS[0])

    def test_a_day_the_guide_does_not_publish_is_a_dialog_not_an_empty_folder(self):
        self.entering(giorno='01-01-1999')
        with self.assertRaises(self.dialogs.AddonError) as raised:
            self.program.giorno()
        self.assertEqual(raised.exception.section, 'rivedi_la7')
        self.assertEqual(harness.ITEMS, [])
        self.assertEqual(harness.ENDINGS, [{'succeeded': False}])

    def test_a_site_that_does_not_answer_is_one_dialog(self):
        self.serve(error=URLError('no route'))
        _, _, dialogs = self.call('?mode=rivedi_la7cinema')
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])
        self.assertTrue(harness.LOGS[0].startswith('RivediLA7: rivedi_la7cinema: SiteError: '),
                        harness.LOGS[0])

    def test_a_programs_week_is_the_guide_filtered_on_its_own_path(self):
        self.entering()
        added = self.program.repliche('/omnibus')
        self.assertEqual(added, 3)
        self.assertEqual([item['label'] for item in harness.ITEMS],
                         ['martedi 27 ottobre Omnibus ST.27',
                          'lunedi 26 ottobre Omnibus ST.27',
                          'domenica 25 ottobre Omnibus ST.27'])
        self.assertEqual(len({self.params(item)['play'] for item in harness.ITEMS}), 3)
        self.assertTrue(all(not item['folder'] for item in harness.ITEMS))
        self.assertEqual(harness.ENDINGS, [{'succeeded': True}])

    def test_a_day_listed_by_both_guides_is_one_replay(self):
        self.entering()
        # both channels answered with the same guide: the week must not double it
        self.assertEqual(self.program.repliche('/omnibus-meteo'), 3)
        self.assertEqual(len(harness.ITEMS), 3)

    def test_a_program_whose_name_starts_the_same_takes_no_replay(self):
        self.entering()
        self.assertEqual(self.program.repliche('/omni'), 0)
        self.assertEqual(harness.ITEMS, [])
        self.assertEqual(harness.ENDINGS, [{'succeeded': True}])

    def test_a_programs_week_that_the_guide_does_not_cover_is_empty(self):
        self.entering()
        self.assertEqual(self.program.repliche('/propaganda-live'), 0)

    def test_a_day_is_named_the_way_the_guide_names_it(self):
        self.assertEqual(self.program.giorno_label('25-10-2026'), 'domenica 25 ottobre')
        self.assertEqual(self.program.giorno_label('01-01-2026'), 'giovedi 1 gennaio')
        self.assertEqual(self.program.giorno_label('31-12-2026'), 'giovedi 31 dicembre')
        for unusable in ('', 'domani', None, '01-13-2026'):
            self.assertEqual(self.program.giorno_label(unusable), unusable)


if __name__ == '__main__':
    unittest.main()
