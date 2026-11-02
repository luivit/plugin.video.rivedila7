"""The catalogue: the root menu, and the programs the site publishes.

The programs page is a hub whose carousels are its groups, and `allPrograms` is
the flat index behind it: two queries, so the list cannot drift from the page the
site serves and there is nothing to scrape.

A program is a folder whose path is the one the site gives it, in the order the
site publishes it: no per-program exception to keep up to date, and no config
file to grow. Nothing here builds a Kodi URL by hand or closes a directory - items
go through a Directory, and a failure leaves as an AddonError naming the section.
"""

import os

import xbmcplugin

from resources.lib.globals import G
from resources.lib.kodi import items
from resources.lib.kodi.dialogs import AddonError
from resources.lib.kodi.directory import Directory
from resources.lib.la7play import client, payload

# the programs page of the site, a hub whose carousels are the groups of programs
PROGRAMMI_HUB = '/programmi'

# the two sections that are one hub page each: films and documentaries
FILM_HUB = '/film'
DOCUMENTARI_HUB = '/documentari'

# the root menu in the order the add-on serves it: mode, label, art, folder, live
ROOT_MENU = (
    ('diretta_la7', 32002, 'direttalivela7.jpg', False, True),
    ('diretta_la7cinema', 32009, 'direttalivela7cinema.jpg', False, True),
    ('rivedi_la7', 32001, 'rivedila7.jpg', True, False),
    ('rivedi_la7cinema', 32004, 'direttalivela7cinema.jpg', True, False),
    ('film', 32013, 'film.jpg', True, False),
    ('documentari', 32014, 'filmfiction.jpg', True, False),
    ('tutti_programmi', 32006, 'programmi.jpg', True, False),
    ('cerca_la7', 32012, 'cerca.png', True, False),
)


def show_root_menu():
    """The root menu: the eight sections of the add-on, nothing else."""
    with Directory() as directory:
        for mode, label, art, folder, live in ROOT_MENU:
            directory.add({'mode': mode}, _item(label, art, bold=True),
                          folder=folder, is_live=live)


def programmi():
    """The programs page: its groups as folders, then the flat A-Z list."""
    with Directory() as directory:
        for name in gruppi():
            directory.add({'mode': G.MODE, 'gruppo': name}, _item(name))
        directory.add({'mode': G.MODE, 'lettera': 'tutti'}, _item(32015))


def gruppo(name):
    """The programs one group of the programs page publishes."""
    with Directory() as directory:
        for slot in _slots():
            if slot.get('titoloCarrello') == name:
                _programs(directory, (slot.get('paginatedItems') or {}).get('items') or [])
                return
        # the group is not on the page any more: fail the folder, never show it empty
        raise AddonError(G.MODE, LookupError(name))


def tutti_programmi():
    """Every program the site's index publishes, in alphabetical order."""
    with Directory(sort_method=xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS) as directory:
        rows = (_query('tutti_programmi', 'allPrograms').get('graphqlTuttiProgrammi') or {}).get('results') or []
        _programs(directory, rows)


def film():
    """The films the site's hub publishes, in the order it publishes them."""
    _hubs('film', FILM_HUB)


def documentari():
    """The documentaries the site's hub publishes."""
    _hubs('documentari', DOCUMENTARI_HUB)


def gruppi():
    """The groups the programs page is organised in, in the page's own order."""
    return [slot['titoloCarrello'] for slot in _slots()]


def _hubs(section, path):
    """One section built on a content hub: the videos its page holds.

    A hub carries its films in a grid and the few it recommends in a carousel, and a
    film can be in both: the grid comes first, the repeats are dropped. The hub page
    is itself a node of its own payload, and a section that opened itself would be a
    folder leading back to where the user already is.
    """
    with Directory() as directory:
        entity = _query(section, 'nsContentHub', {'path': path}).get('route') or {}
        for node in payload.nodes(entity.get('entity') or {}):
            node_path = payload.node_path(node)
            if payload.is_ancestor(node_path, path) or not payload.is_playable(node):
                continue
            title = payload.node_title(node)
            if not title:
                continue
            directory.add({'mode': G.MODE, 'play': G.URL_PLAY_BASE + node_path,
                           'titolo': title, 'thumb': payload.node_thumb(node),
                           'plot': payload.node_plot(node)},
                          items.entry(title, payload.node_thumb(node), payload.node_plot(node)),
                          folder=False, unique=True)


def _slots():
    """The carousels of the programs page that carry programs."""
    route = _query('tutti_programmi', 'nsContentHub', {'path': PROGRAMMI_HUB}).get('route') or {}
    entity = route.get('entity') or {}
    return [slot for slot in entity.get('contentSlots') or []
            if slot.get('titoloCarrello') and (slot.get('paginatedItems') or {}).get('items')]


def _query(section, name, variables=None):
    """One query of the site, or an AddonError naming the section that needed it."""
    try:
        return client.gql(name, variables)
    except client.SiteError as cause:
        raise AddonError(section, cause)


def _programs(directory, rows):
    """Add one folder per program of an answer of the site, deduplicated."""
    for row in rows:
        title = payload.node_title(row)
        path = payload.node_path(row)
        if not title or not path:
            continue
        directory.add({'mode': G.MODE, 'link': G.URL_PLAY_BASE + path},
                      _program_item(row, title), unique=True)


def _program_item(row, title):
    """A program as a folder: its title, its image and the site's own synopsis."""
    return items.entry(title, _image(row), (row.get('occhiello') or '').strip())


def _item(label, art=None, bold=False):
    """One menu entry: a label and an image of the add-on, nothing else."""
    text = G.LANGUAGE(label) if isinstance(label, int) else label
    return items.entry('[B]%s[/B]' % text if bold else text,
                       os.path.join(G.THUMB_PATH, art) if art else '')


def _image(row):
    """The first image a program publishes, as an absolute URL."""
    for field in ('img', 'imgRettangolare', 'programmaImage', 'coverImage', 'scenaImage'):
        value = row.get(field)
        if isinstance(value, dict):
            value = value.get('url')
        # the site ends an empty alternative of the field with '||'
        url = (value or '').split('||')[0].strip()
        if url:
            return url if url.startswith('http') else G.URL_PLAY_BASE + url
    return ''
