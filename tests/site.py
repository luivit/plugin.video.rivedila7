"""The site, answered offline: fixtures in, urlopen answers out.

Every section reaches la7play.it through `la7play.client`, and `client` makes one
urlopen call, so replacing that call with a lookup is enough to walk a section
without a network. A request a test did not plan for is a test bug, not an empty
answer: it raises instead of quietly returning nothing.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))


class Answer(object):
    """What urlopen returns: something with read()."""

    def __init__(self, body):
        self.body = body

    def read(self, size=-1):
        return self.body


def fixture(name):
    """One file of tests/fixtures, as the bytes urlopen would return."""
    with open(os.path.join(HERE, 'fixtures', name), encoding='utf-8') as open_fixture:
        return open_fixture.read().encode('utf-8')


class Site(object):
    """urlopen, answering by a substring of the URL it was given."""

    def __init__(self, answers=None, error=None):
        self.answers = answers or {}
        self.error = error
        self.asked = []

    def __call__(self, request, timeout=None):
        self.asked.append(request.full_url)
        if self.error is not None:
            raise self.error
        # the longest key that matches wins, so a test can answer one page of a
        # listing apart from the listing itself
        matches = [match for match in self.answers if match in request.full_url]
        if not matches:
            raise AssertionError('a request this test did not expect: %s' % request.full_url)
        return Answer(self.answers[max(matches, key=len)])
