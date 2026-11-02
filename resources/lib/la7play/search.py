"""Search: the site's own query, page by page.

The site answers a search with its own grouped result page - a few groups, twenty
hits each - and every hit says what it is: a video, a film, a program page, or an
article. A video or a film plays; a program page opens the program, which is a
folder of its categories. An article is a page of text: it has nothing to watch and
nothing to open, so it is not shown rather than shown as a folder that leads
nowhere.

The query is remembered while the user watches something, because Kodi opens the
folder a video was started from when playback stops: the results come back without
asking again. Opening the search from the menu forgets it, which is what makes that
a new search.
"""

from resources.lib.globals import G
from resources.lib.kodi import dialogs, items, window
from resources.lib.kodi.dialogs import AddonError
from resources.lib.kodi.directory import Directory
from resources.lib.la7play import client

# the query a previous call kept: a search folder is rebuilt after playback stops
MEMBER = 'search'

# how many hits the site answers with in a page
PAGE_SIZE = 20

# the hits that are something to watch, and the hit that is a program to browse
PLAYABLE = ('video', 'film')
PROGRAM = 'property'


def cerca_la7():
    """The results of a search, and the way to the page after them."""
    query = G.QUERY or window.recall(MEMBER) or dialogs.ask(32012)
    if not query:
        # cancelled: the folder closes empty and silent, it does not fail
        with Directory():
            return
    window.remember(MEMBER, query)
    page = max(G.PAGENUM, 1)
    with Directory() as directory:
        # the folder is opened before the site is asked: a failed search closes it
        # with a failure, it does not leave Kodi waiting for an answer
        answer = _search(query, page)
        hits = [hit for hit in answer['hits'] if _listed(hit)]
        for hit in hits:
            params, item = _entry(hit)
            # a program is a folder of its categories, a hit is something to watch
            directory.add(params, item, folder=hit.get('contentType') == PROGRAM, unique=True)
        if hits and page < answer['pages']:
            directory.add({'mode': G.MODE, 'q': query, 'page': str(page + 1)}, items.next_page())


def play_result():
    """Play the hit the user clicked."""
    from resources.lib.playback import streams
    streams.play_video(G.PLAY, False)


def forget():
    """Drop the remembered query: the next search asks for one."""
    window.forget(MEMBER)


def _search(query, page):
    """The hits of one page of the site's answer, and how many pages there are."""
    try:
        answer = client.gql('siteSearch', {'q': query, 'limit': PAGE_SIZE, 'page': page})
    except client.SiteError as cause:
        raise AddonError(G.MODE, cause)
    result = answer.get('siteSearch') or {}
    size = int(result.get('pageSize') or PAGE_SIZE)
    total = int(result.get('total') or 0)
    return {'hits': [hit for group in result.get('groups') or [] for hit in group.get('hits') or []],
            # the site answers totalPages=1 on the first page of every search and the
            # real count from the second page on: what the user can page through is
            # total over pageSize, which both answers agree on
            'pages': -(-total // size)}


def _listed(hit):
    """True for the hits this add-on can do something with."""
    return hit.get('contentType') in PLAYABLE + (PROGRAM,)


def _entry(hit):
    """The item of one hit, and the parameters a click on it carries."""
    title = (hit.get('title') or '').strip()
    path = (hit.get('url') or '').strip()
    thumb = (hit.get('imageUrl') or '').strip()
    plot = (hit.get('excerpt') or hit.get('propertyName') or '').strip()
    if hit.get('contentType') == PROGRAM:
        # a program is a folder of its categories, listed like any other program
        return {'mode': 'tutti_programmi', 'link': G.URL_PLAY_BASE + path}, items.folder(title)
    return {'mode': G.MODE, 'play': G.URL_PLAY_BASE + path, 'titolo': title,
            'thumb': thumb, 'plot': plot}, items.entry(title, thumb, plot)
