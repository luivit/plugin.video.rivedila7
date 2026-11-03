"""What the add-on reads out of a la7play.it payload.

The two fixtures are real answers from the site (see tests/fixtures/capture.py):
the payload of a program page, and the payload of the TV guide with its day list
cut down to three days. They are what keeps these tests honest - a hand-written
payload would only prove that the parser agrees with the person who wrote both.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from tests import harness


def fixture(name):
    with open(os.path.join(HERE, 'fixtures', name), encoding='utf-8') as open_fixture:
        return open_fixture.read()


def push(payload):
    """A page that carries one push chunk, as the site does."""
    return '<script>self.__next_f.push([1,%s])</script>' % json.dumps(payload)


class PayloadTest(unittest.TestCase):
    def setUp(self):
        harness.install_stubs()
        harness.unload_addon_modules()
        from resources.lib.la7play import payload
        self.payload = payload

    def test_the_payload_of_a_page_is_read_whole(self):
        text = self.payload.decode(fixture('page-programma.html'))
        self.assertTrue(text.startswith('1:"$Sreact.fragment"'), text[:40])
        self.assertIn('"path":"/otto-e-mezzo"', text)

    def test_a_page_without_payload_gives_nothing(self):
        self.assertEqual(self.payload.decode(''), '')
        self.assertEqual(self.payload.decode('<html><body>no payload here</body></html>'), '')

    def test_chunks_are_concatenated_in_the_order_they_are_pushed(self):
        html = push('one\n') + push('two\n')
        self.assertEqual(self.payload.decode(html), 'one\ntwo\n')

    def test_a_bracket_inside_a_string_does_not_end_the_chunk(self):
        self.assertEqual(self.payload.decode(push('closing ] bracket')), 'closing ] bracket')

    def test_an_unterminated_chunk_is_dropped_not_raised(self):
        # a page cut in half is a truncated answer, not a reason to crash
        html = 'self.__next_f.push([1,"truncated'
        self.assertEqual(self.payload.decode(html), '')

    def test_a_chunk_that_carries_no_text_carries_nothing(self):
        self.assertEqual(self.payload.decode('self.__next_f.push([0])'), '')
        self.assertEqual(self.payload.decode('self.__next_f.push([1,42])'), '')
        self.assertEqual(self.payload.decode('self.__next_f.push(not json)'), '')

    def test_a_named_value_is_read_out_of_the_guide_payload(self):
        text = self.payload.decode(fixture('page-guida-la7.html'))
        giorni = self.payload.value(text, 'giorno')
        self.assertIsInstance(giorni, list)
        self.assertEqual(len(giorni), 3)
        self.assertEqual([giorno['@attributes']['data'] for giorno in giorni],
                         ['25-10-2026', '26-10-2026', '27-10-2026'])
        self.assertEqual([len(giorno['programma']) for giorno in giorni], [3, 3, 3])
        self.assertTrue(giorni[0]['programma'][0]['pathname'].startswith('/omnibus/'))

    def test_a_value_is_the_json_value_of_its_key(self):
        self.assertEqual(self.payload.value('{"k":"v","n":2}', 'k'), 'v')
        self.assertEqual(self.payload.value('{"k":"v","n":2}', 'n'), 2)
        self.assertEqual(self.payload.value('{"k": [1, {"a": "},"}]}', 'k'), [1, {'a': '},'}])
        self.assertIsNone(self.payload.value('{"k":1}', 'missing'))
        self.assertIsNone(self.payload.value('{"k":', 'k'))

    def test_the_nodes_of_a_decoded_answer_are_collected_deep(self):
        answer = json.loads(fixture('gql-nodePage.json'))
        found = self.payload.nodes(answer)
        self.assertEqual([(self.payload.node_path(node), self.payload.node_title(node))
                          for node in found], [('/otto-e-mezzo', 'Otto e mezzo')])

    def test_a_node_needs_a_path_on_the_site_and_a_title(self):
        content = {'a': [{'path': '/kept', 'titolo': 'Kept'},
                         {'path': '/kept', 'titolo': 'Kept twice'},
                         {'pathname': '/kept-by-pathname', 'title': 'By pathname'},
                         {'path': '/no-title'},
                         {'titolo': 'no path'},
                         {'path': 'relative', 'titolo': 'not on the site'}],
                   'b': {'nested': {'path': '/nested', 'nome': 'Nested'}}}
        found = self.payload.nodes(content)
        self.assertEqual([self.payload.node_path(node) for node in found],
                         ['/kept', '/kept-by-pathname', '/nested'])
        self.assertEqual([self.payload.node_title(node) for node in found],
                         ['Kept', 'By pathname', 'Nested'])

    def test_an_episode_is_playable_and_a_hub_is_not(self):
        for node in ({'uploadVideo': {'cf_remote_url': '/x'}},
                     {'urlVideo': 'https://example/stream.m3u8'},
                     {'path': '/otto-e-mezzo/puntate/puntata-del-30-10-2026-398336'},
                     {'path': '/film/passenger-397232'}):
            self.assertTrue(self.payload.is_playable(node), node)
        # a category is a folder of the add-on, even the one named after the archive
        for node in ({'path': '/otto-e-mezzo'},
                     {'path': '/otto-e-mezzo/rivedila7'},
                     {'path': '/documentari/la-conferenza-di-wannsee-395887'},
                     {}):
            self.assertFalse(self.payload.is_playable(node), node)

    def test_a_program_is_the_page_and_a_category_is_below_it(self):
        self.assertFalse(self.payload.is_category('/otto-e-mezzo'))
        self.assertTrue(self.payload.is_category('/otto-e-mezzo/puntate'))
        self.assertTrue(self.payload.is_category('/otto-e-mezzo/video/il-punto-di-pagliaro'))
        self.assertFalse(self.payload.is_category('/'))
        self.assertFalse(self.payload.is_category(''))

    def test_a_parent_of_the_page_is_not_its_content(self):
        self.assertTrue(self.payload.is_ancestor('/otto-e-mezzo', '/otto-e-mezzo'))
        self.assertTrue(self.payload.is_ancestor('/otto-e-mezzo', '/otto-e-mezzo/puntate'))
        self.assertFalse(self.payload.is_ancestor('/otto-e-mezzo/puntate', '/otto-e-mezzo'))
        self.assertFalse(self.payload.is_ancestor('/otto-e-mezzo', '/otto-e-mezzogiorno'))
        self.assertFalse(self.payload.is_ancestor('/', '/otto-e-mezzo'))
        self.assertFalse(self.payload.is_ancestor('', '/otto-e-mezzo'))


if __name__ == '__main__':
    unittest.main()
