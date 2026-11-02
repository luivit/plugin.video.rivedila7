"""How the add-on asks the site a question, and how it hears "no".

The URL is part of the protocol: a persisted query is asked by its id, its
variables travel as sorted, unpadded base64url JSON, and a wrong encoding is not a
parse error on this side but a 404 on the other. The tests pin the URL, the case
where the site answers something that is not data, and the promise that nothing
here shows a dialog.
"""

import base64
import os
import sys
import unittest

from urllib.error import URLError

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from tests import harness


class _Answer(object):
    """What urlopen returns: something with read()."""

    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body


class _Transport(object):
    """Stands in for urlopen: answers with a body, or fails, and remembers the call."""

    def __init__(self, body=b'', error=None):
        self.body = body
        self.error = error
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return _Answer(self.body)


def fixture(name):
    with open(os.path.join(HERE, 'fixtures', name), encoding='utf-8') as open_fixture:
        return open_fixture.read()


class ClientTest(unittest.TestCase):
    def setUp(self):
        harness.install_stubs()
        harness.unload_addon_modules()
        from resources.lib.la7play import client
        self.client = client
        self.urlopen = client.urlopen

    def tearDown(self):
        self.client.urlopen = self.urlopen

    def transport(self, body=b'', error=None):
        transport = _Transport(body, error)
        self.client.urlopen = transport
        return transport

    def test_a_query_is_asked_by_its_persisted_id(self):
        self.assertEqual(self.client.query_url('allPrograms'),
                         'https://www.la7play.it/api/gql/f7034d55158fc906')

    def test_the_variables_are_the_tail_of_the_url_as_base64url_json(self):
        url = self.client.query_url('nsContentHub', {'path': '/programmi'})
        self.assertEqual(url, 'https://www.la7play.it/api/gql/0f3f2c4225230faf/'
                              'eyJwYXRoIjoiL3Byb2dyYW1taSJ9')
        encoded = url.rsplit('/', 1)[-1]
        self.assertEqual(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)),
                         b'{"path":"/programmi"}')

    def test_the_variables_are_sorted_and_carry_no_padding(self):
        encoded = self.client.query_url('filteredNodeReplicas', {'value': 20, 'path': '/film'}).rsplit('/', 1)[-1]
        self.assertNotIn('=', encoded)
        self.assertEqual(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)),
                         b'{"path":"/film","value":20}')

    def test_a_query_that_is_not_in_the_table_says_so(self):
        with self.assertRaises(self.client.GqlError) as raised:
            self.client.query_url('notAQuery')
        self.assertIn('unknown query', str(raised.exception))

    def test_an_answer_is_reduced_to_its_data(self):
        transport = self.transport(fixture('gql-nodePage.json').encode('utf-8'))
        data = self.client.gql('nodePage', {'path': 'otto-e-mezzo'})
        self.assertEqual(data['route']['entity']['name'], 'Otto e mezzo')
        self.assertEqual(transport.requests[0].full_url,
                         self.client.query_url('nodePage', {'path': 'otto-e-mezzo'}))

    def test_the_site_is_told_who_is_asking(self):
        transport = self.transport(b'{"data":{}}')
        self.client.gql('allPrograms')
        request = transport.requests[0]
        self.assertTrue(request.get_header('User-agent'))
        self.assertEqual(request.get_header('Accept'), 'application/json')
        self.assertEqual(request.get_header('Referer'), 'https://www.la7play.it/')

    def test_an_answer_without_data_is_a_broken_assumption_not_an_empty_list(self):
        for body in (b'{}', b'{"errors":[{"message":"bad hash"}]}', b'{"data":[]}', b'not json'):
            self.transport(body)
            with self.assertRaises(self.client.GqlError):
                self.client.gql('allPrograms')

    def test_an_unreachable_site_names_the_query_and_the_cause(self):
        self.transport(error=URLError('no route'))
        with self.assertRaises(self.client.GqlError) as raised:
            self.client.gql('allPrograms')
        self.assertIn('allPrograms', str(raised.exception))
        self.assertIn('URLError', str(raised.exception))

    def test_a_page_is_returned_as_text(self):
        self.transport('<html>ciao</html>'.encode('utf-8'))
        self.assertEqual(self.client.fetch_html('https://www.la7play.it/film'), '<html>ciao</html>')

    def test_a_page_that_cannot_be_read_is_a_site_error(self):
        self.transport(error=URLError('no route'))
        with self.assertRaises(self.client.SiteError) as raised:
            self.client.fetch_html('https://www.la7play.it/film')
        self.assertIn('https://www.la7play.it/film', str(raised.exception))

    def test_a_query_error_is_a_site_error_too(self):
        self.assertTrue(issubclass(self.client.GqlError, self.client.SiteError))


if __name__ == '__main__':
    unittest.main()
