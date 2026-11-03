"""The archive of a category: a program's replays kept on disk, a clip listing paged.

A program publishes two kinds of category, and the site pages both with its own
`?page=N`, twenty items at a time:

* its replays (`/puntate`) are an archive that goes back years - the last page of
  Piazzapulita is from November 2014 - and reading it whole on every call would be
  thirty requests before the folder appears. What has been read is kept in
  `archive_store`, a hundred episodes at a time, so a folder page shows twenty and
  the next hundred is read while the user is still on the page before it;
* its clips (`/video`) are a listing of cards that is shallow: it is read page by
  page and a page is offered only when the next one publishes something new.

Either way a folder offers one page, and the page after it only when there is one. The
archive has one extra rule: when a folder page is the last but one the store can serve,
the block after it is asked for in the background, so the click that reaches it finds
it already there.
"""

from resources.lib.globals import G
from resources.lib.kodi import background
from resources.lib.kodi.dialogs import AddonError
from resources.lib.la7play import archive_store, client, payload

# the page every program publishes its archive of replays under
REPLICA = '/puntate'

# how many items one folder page shows, and how many episodes one read of the site
# adds to an archive: the site gives twenty a page, so a block is five of them
PAGE_SIZE = 20
BLOCK = 100


def items(pathname, page=1):
    """One page of a category, and whether the page after it has anything to show."""
    if pathname.endswith(REPLICA):
        return _archive(pathname, page)
    return _listing(pathname, page)


def prefetch(pathname):
    """Read the next block of an archive into the store; nothing is shown, nothing fails.

    This is the background call `background.later()` asks for: Kodi hands it a plugin
    invocation of its own, and the user is looking at another folder by the time it
    runs. A failure is swallowed on purpose - there is nobody to tell, and the next
    folder page will read the block itself.
    """
    try:
        stored = archive_store.load(pathname)
        if stored and not archive_store.stale(stored) and stored.get('more'):
            archive_store.save(pathname, _read(pathname, stored))
    except AddonError:
        return


def _archive(pathname, page):
    """One page of a program's replays, read from the store a block at a time."""
    stored = archive_store.load(pathname)
    if not stored or archive_store.stale(stored):
        # a stale archive is read again from the top: the newest episode is what a
        # user sees first, and an episode published today must be there
        stored = {'nodes': [], 'page': 1, 'more': True}
    start = (page - 1) * PAGE_SIZE
    while len(stored['nodes']) < start + PAGE_SIZE and stored['more']:
        stored = archive_store.save(pathname, _read(pathname, stored))
    nodes = stored['nodes'][start:start + PAGE_SIZE]
    more = len(stored['nodes']) > start + PAGE_SIZE or bool(stored['more'])
    if _about_to_run_out(stored, page):
        # the user is on the last page the store can serve but one: read the next
        # block now, while reading the page before it
        background.later('prefetch', link=G.URL_PLAY_BASE + pathname)
    return nodes, more


def _about_to_run_out(stored, page):
    """True when the page being shown is the last but one the store can serve."""
    served = len(stored.get('nodes') or [])
    return bool(stored.get('more')) and page * PAGE_SIZE < served <= (page + 1) * PAGE_SIZE


def _read(pathname, stored):
    """One block of an archive: the pages the store has not read yet, up to BLOCK items."""
    nodes = list(stored.get('nodes') or [])
    seen = set(payload.node_path(node) for node in nodes)
    cursor, more, added = int(stored.get('page') or 1), bool(stored.get('more', True)), 0
    while more and added < BLOCK:
        found = _page(pathname, cursor)
        fresh = [node for node in found if payload.node_path(node) not in seen]
        cursor += 1
        if not found or not fresh:
            # the site answered with nothing new: the archive ends here, whether it
            # says so or not
            more = False
            break
        added += len(fresh)
        nodes.extend(fresh)
        seen.update(payload.node_path(node) for node in fresh)
    return {'nodes': nodes, 'page': cursor, 'more': more}


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
