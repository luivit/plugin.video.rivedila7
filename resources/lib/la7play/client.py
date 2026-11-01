"""How the add-on asks la7play.it for its content: one request, two shapes.

A list on the site is a persisted GraphQL query: the URL carries the id of the
query and, when it has any, its variables as base64url JSON. A page is HTML with
the data of that page embedded as a React Server Components payload, which is
`payload.py`'s half of the job.

What lives here is the request and its failure: the timeout, the encoding of the
variables, the fact that a query which does not answer with `data` is not an
empty list but a broken assumption about the site. Nothing here knows about Kodi,
directories or the user, so a failure is an exception the caller names - the
section that could not do its work is the one that knows what to say.
"""

import base64
import json

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from resources.lib.globals import G

TIMEOUT = 30

USER_AGENT = {'user-agent': G.HEADERS_SET['user-agent']}


class SiteError(Exception):
    """The site did not answer as documented."""

    def __init__(self, what, cause):
        super(SiteError, self).__init__(
            '%s: %s: %s' % (what, type(cause).__name__, cause))
        self.what = what
        self.cause = cause


class GqlError(SiteError):
    """A persisted query failed: the site changed its ids, or it is unreachable."""


def fetch_html(url):
    """The HTML of one page, decoded."""
    request = Request(url, headers=USER_AGENT)
    try:
        return urlopen(request, timeout=TIMEOUT).read().decode('utf-8', 'replace')
    except (HTTPError, URLError, OSError, ValueError) as cause:
        raise SiteError(url, cause)


def query_url(name, variables=None):
    """The URL of one persisted query, with its variables if it takes any."""
    try:
        query = G.GQL_QUERIES[name]
    except KeyError:
        raise GqlError(name, 'unknown query, not in GQL_QUERIES')
    url = '%s/api/gql/%s' % (G.URL_PLAY_BASE, query)
    if variables is not None:
        # the site takes its variables as sorted, unpadded base64url JSON
        encoded = json.dumps(variables, separators=(',', ':'), sort_keys=True).encode('utf-8')
        url += '/' + base64.urlsafe_b64encode(encoded).decode('utf-8').rstrip('=')
    return url


def gql(name, variables=None):
    """Run one persisted query and return the data object of its answer."""
    url = query_url(name, variables)
    headers = dict(USER_AGENT, accept='application/json', referer=G.URL_PLAY_BASE + '/')
    try:
        answer = json.loads(urlopen(Request(url, headers=headers),
                                    timeout=TIMEOUT).read().decode('utf-8', 'replace'))
    except (HTTPError, URLError, OSError, ValueError) as cause:
        raise GqlError(name, cause)
    if not isinstance(answer, dict) or not isinstance(answer.get('data'), dict):
        raise GqlError(name, 'answer without data')
    return answer['data']
