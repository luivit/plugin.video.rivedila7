"""The archive of a category: the query for replays, the page for clips.

Two answers of the site, both captured: the archive of one program (the shape it
gives, the newest six of the hundred), and a page of a listing. What is checked
here is the decision between them - which source, asked with what, and what
happens when it answers nothing or refuses.
"""

import base64
import json
import os
import sys
import unittest

from urllib.error import HTTPError

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from tests import harness
from tests.site import Site, fixture

PROGRAM = 'https://www.la7play.it/otto-e-mezzo'
REPLAYS = PROGRAM + '/puntate'
CLIPS = PROGRAM + '/video'
NODE_PAGE = '/api/gql/' + 'e9d39e6838f7f588'          # nodePage
REPLICAS = '/api/gql/' + 'e4ec45c8e38bb081'          # filteredNodeReplicas

ARCHIVE = fixture('gql-filteredNodeReplicas.json')
EMPTY = json.dumps({'data': {'filteredNodeReplicas': {'nodes': [],
                                                      'pageInfo': {'hasNextPage': False}}}}).encode('utf-8')


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
    """The answer the site gives to a query it will not run."""
    return HTTPError(url, 503, 'Service Temporarily Unavailable', {}, None)


def archive_of(*paths):
    """An answer of the archive query that belongs to the paths given."""
    nodes = [{'path': path, 'title': path.rsplit('/', 1)[-1],
              'dataMessaInOnda': {'timestamp': 1000 + position},
              'uploadVideo': {'cf_thumbnail_url': 'https://images.la7play.it/%d.jpg' % position}}
             for position, path in enumerate(paths)]
    return json.dumps({'data': {'filteredNodeReplicas': {'nodes': nodes,
                                                         'pageInfo': {'hasNextPage': False}}}}).encode('utf-8')


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
        harness.unload_addon_modules()
        from resources.lib.globals import G
        from resources.lib.kodi.dialogs import AddonError
        from resources.lib.la7play import archive, client
        self.G, self.AddonError = G, AddonError
        self.archive, self.client = archive, client
        # the section that names a failure: Kodi sets the mode, a test says it itself
        self.G.init_globals(['plugin://plugin.video.rivedila7/', '1', '?mode=tutti_programmi'])
        self.serve()

    def serve(self, answers=None, fail=None):
        if answers is None:
            answers = {NODE_PAGE: fixture('gql-nodePage.json'), REPLICAS: ARCHIVE}
        self.site = ArchiveSite(answers, fail)
        self.client.urlopen = self.site

    def variables(self, name, hash_of):
        """The variables of the one request the add-on made for a query."""
        asked = [url for url in self.site.asked if hash_of in url]
        self.assertEqual(len(asked), 1, asked)
        tail = asked[0].split('/')[-1]
        return json.loads(base64.urlsafe_b64decode(tail + '=' * (-len(tail) % 4)).decode('utf-8'))

    def test_the_archive_of_a_replica_category_is_read_whole_and_newest_first(self):
        from resources.lib.la7play import payload
        nodes, more = self.archive.items('/otto-e-mezzo/puntate')
        self.assertEqual(len(nodes), 6)
        self.assertFalse(more, 'an archive is one query: it has no next page')
        stamps = [payload.node_path(node) for node in nodes]
        self.assertEqual(stamps[0], '/otto-e-mezzo/puntate/puntata-del-30-10-2026-398336')
        self.assertEqual(len(set(stamps)), len(stamps), 'a replay is listed once')

    def test_the_archive_is_asked_for_by_the_programs_name_not_its_slug(self):
        self.archive.items('/otto-e-mezzo/puntate')
        # "otto-e-mezzo" answers nothing: the query keys a program by its site name
        self.assertEqual(self.variables('filteredNodeReplicas', REPLICAS),
                         {'path': 'Otto e mezzo', 'value': 100})

    def test_an_archive_that_refuses_a_hundred_nodes_is_asked_for_fewer(self):
        too_many = self.client.query_url('filteredNodeReplicas', {'path': 'Otto e mezzo', 'value': 100})
        self.serve(fail={too_many: refused(too_many)})
        nodes, _ = self.archive.items('/otto-e-mezzo/puntate')
        self.assertEqual(len(nodes), 6)
        self.assertIn(self.client.query_url('filteredNodeReplicas', {'path': 'Otto e mezzo', 'value': 50}),
                      self.site.asked)

    def test_an_archive_that_answers_for_another_program_is_no_archive(self):
        self.serve({NODE_PAGE: fixture('gql-nodePage.json'),
                    REPLICAS: archive_of('/atlantide/rivedila7/atlantide-1-1-2026-1'),
                    REPLAYS: listing_page(card('Puntata del 30/10/2026', '/otto-e-mezzo/puntate/x-1')),
                    REPLAYS + '?page=2': listing_page()})
        nodes, more = self.archive.items('/otto-e-mezzo/puntate')
        self.assertEqual([n['path'] for n in nodes], ['/otto-e-mezzo/puntate/x-1'])
        self.assertFalse(more)

    def test_a_listing_of_clips_never_asks_the_archive(self):
        clips = listing_page(card('La caduta del governo', '/otto-e-mezzo/video/la-caduta-1'),
                             card('Il discorso integrale', '/otto-e-mezzo/video/il-discorso-2'))
        self.serve({CLIPS: clips, CLIPS + '?page=2': listing_page()})
        nodes, _ = self.archive.items('/otto-e-mezzo/video')
        self.assertEqual([n['path'] for n in nodes],
                         ['/otto-e-mezzo/video/la-caduta-1', '/otto-e-mezzo/video/il-discorso-2'])
        self.assertNotIn(REPLICAS, ''.join(self.site.asked))

    def test_an_archive_the_site_does_not_answer_is_one_dialog(self):
        self.serve({NODE_PAGE: fixture('gql-nodePage.json')}, fail={REPLICAS: refused(REPLICAS)})
        with self.assertRaises(self.AddonError) as failure:
            self.archive.items('/otto-e-mezzo/puntate')
        self.assertIn('filteredNodeReplicas', str(failure.exception))

    def test_the_second_page_of_a_listing_is_read_from_the_page(self):
        self.serve({CLIPS: listing_page(card('Prima', '/otto-e-mezzo/video/prima-1')),
                    CLIPS + '?page=2': listing_page(card('Seconda', '/otto-e-mezzo/video/seconda-2')),
                    CLIPS + '?page=3': listing_page()})
        nodes, more = self.archive.items('/otto-e-mezzo/video', 2)
        self.assertEqual([n['title'] for n in nodes], ['Seconda'])
        self.assertFalse(more)


if __name__ == '__main__':
    unittest.main()
