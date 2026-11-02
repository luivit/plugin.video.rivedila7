"""The archive of a category: one query for the replays, the page for the clips.

A program publishes two kinds of category, and the site answers each in its own way:

* its replays (`/puntate`) come from one query - `filteredNodeReplicas` - which
  answers with the archive of the program, newest first, a hundred nodes at most.
  It refuses a bigger page (503), so the cap is asked for from 100 down to 50 to
  20 before the failure is the failure to report;
* its clips (`/video`) are a listing of cards, which no query answers: the page is
  read (`payload.page_nodes`) and paged with the site's own `?page=N`.

One strategy per listing, stated here because it is the one place both live: an
archive is read whole, a listing is paged, and only a listing offers a next page.

The archive answers for a *program*, not for the category it was asked for: a
program keeps its older replays under another path (`Atlantide` puts them under
`/atlantide/rivedila7/...`), so what is checked is that the archive belongs to the
program at all. A program the query does not know publishes nothing there, and is
listed from its page like any other.
"""

from resources.lib.globals import G
from resources.lib.kodi.dialogs import AddonError
from resources.lib.la7play import client, payload

# the page every program publishes its archive of replays under
REPLICA = '/puntate'

# what the archive query accepts, from the biggest page it answers to the smallest
CAPS = (100, 50, 20)


def items(pathname, page=1):
    """One page of a category, and whether the page after it publishes anything new."""
    if page == 1 and pathname.endswith(REPLICA):
        archived = replicas(pathname)
        if archived:
            return archived, False
    return _listing(pathname, page)


def replicas(pathname):
    """The archive of a program's replays, newest first, empty when it has none."""
    program = '/' + pathname.strip('/').split('/')[0]
    name = _name(program)
    answer, failure = None, None
    for cap in CAPS:
        try:
            answer = client.gql('filteredNodeReplicas', {'path': name, 'value': cap})
            break
        except client.SiteError as cause:
            # the query refuses more than it wants to answer in one go
            failure = cause
    if answer is None:
        raise AddonError(G.MODE, failure)
    nodes = (answer.get('filteredNodeReplicas') or {}).get('nodes') or []
    if not nodes or not payload.is_ancestor(program, payload.node_path(nodes[0])):
        # an archive of another program is no archive of this one
        return []
    playable = [node for node in nodes if payload.is_playable(node)]
    return sorted(playable, key=_air_date, reverse=True)


def _name(program):
    """The name the archive keys a program by: the site's name, not the slug.

    The query takes `Otto e mezzo`, not `otto-e-mezzo`, and answers nothing for the
    wrong spelling. A page the site does not know keeps its slug: the archive will
    answer nothing either, and the listing is the fallback.
    """
    slug = program.strip('/')
    try:
        answer = client.gql('nodePage', {'path': slug})
    except client.SiteError:
        return slug
    entity = (answer.get('route') or {}).get('entity') or {}
    return (entity.get('name') or slug).strip()


def _listing(pathname, page):
    """One page of a listing, and whether the page after it publishes anything new."""
    found = _page(pathname, page)
    paths = set(payload.node_path(node) for node in found)
    # the next page is offered only when it publishes something this one does not:
    # a site that answers the same page for every number would page forever
    return found, any(payload.node_path(node) not in paths for node in _page(pathname, page + 1))


def _page(pathname, page):
    """The items one page of a listing publishes, in the order the site puts them."""
    url = G.URL_PLAY_BASE + pathname
    if page > 1:
        # the site pages a listing with a plain query string
        url += '?page=%d' % page
    try:
        html = client.fetch_html(url)
    except client.SiteError as cause:
        raise AddonError(G.MODE, cause)
    items = []
    for node in payload.page_nodes(html):
        # a listing shows its items: neither itself nor the page it belongs to
        if payload.is_ancestor(payload.node_path(node), pathname):
            continue
        if payload.is_playable(node):
            items.append(node)
    return items


def _air_date(node):
    """The air date of a node as a number, zero when the site gives none."""
    for stamp in (node.get('dataMessaInOnda'), node.get('created')):
        if isinstance(stamp, dict) and stamp.get('timestamp'):
            return int(stamp['timestamp'])
    return 0
