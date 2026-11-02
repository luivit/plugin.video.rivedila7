"""Replays, program pages and categories: what the site publishes, as folders.

Three listings live here, and each reads the site's data rather than its markup:

* the TV guide - one page carrying the whole week - gives the days of a replay
  section, the replays of one day, and a program's week (`repliche`);
* a program page gives its week and the categories the site publishes for it: the
  page itself carries no episode list, its submenu carries the categories;
* a category of a program gives the cards one page of it renders.

A category is one of two things, and `archive.py` owns both: a program's replays
are read whole from the archive query, newest first, while a listing of clips is
read off its page and paged with `?page=N`. Either way a folder here is only the
rendering: the items are rendered, the retrieval is not this module's business.

What holds throughout: one Directory per folder, closed once on every path, and a
failure named by the section that failed.
"""

import datetime
import os

import xbmcgui

from resources.lib.globals import G
from resources.lib.kodi.dialogs import AddonError
from resources.lib.kodi.directory import Directory
from resources.lib.la7play import archive, client, payload

GIORNI_SETTIMANA = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato', 'domenica']
MESI = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio',
        'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']


def giorni(thumb):
    """The days of the channel's guide that still have a replay, newest first."""
    with Directory() as directory:
        days = [day for day in _guide(G.MODE, _guida_url()) if _has_replay(day)]
        if not days:
            # a guide with nothing to replay is not a folder: it is a failure to report
            raise AddonError(G.MODE, LookupError('the guide publishes no replay'))
        for day in reversed(days):
            item = xbmcgui.ListItem(giorno_label(day['data']), offscreen=True)
            item.setArt({'thumb': os.path.join(G.THUMB_PATH, thumb), 'fanart': G.FANART_PATH})
            directory.add({'mode': G.MODE, 'giorno': day['data']}, item)


def giorno():
    """The replays one day of the guide publishes."""
    with Directory(content='episodes') as directory:
        day = next((day for day in _guide(G.MODE, _guida_url()) if day['data'] == G.GIORNO), None)
        if day is None:
            raise AddonError(G.MODE, LookupError(G.GIORNO))
        for programma in day['programma']:
            if _path(programma):
                orario = (programma.get('ora') or '').strip()
                params, item = _episode(programma, orario + ' ' + _title(programma))
                directory.add(params, item, folder=False, unique=True)


def repliche(directory, pathname):
    """Add a program's replays from the week of the guides, newest day first.

    Returns how many were added: a program the week does not cover is listed from
    its page instead, which is the caller's business.
    """
    added = 0
    page = pathname.rstrip('/')
    seen = set()
    for url in (G.URL_RIVEDILA7, G.URL_RIVEDILA7CINEMA):
        for day in reversed(_guide(G.MODE, url)):
            for programma in day['programma']:
                path = _path(programma)
                # a program owns the replays below its page, not the ones of a
                # program whose name merely starts the same way
                if path == page or path in seen or not payload.is_ancestor(page, path):
                    continue
                seen.add(path)
                params, item = _episode(programma, giorno_label(day['data']) + ' ' + _title(programma))
                directory.add(params, item, folder=False)
                added += 1
    return added


def pagina():
    """The program page the add-on was asked for: a program, or a category of one."""
    pathname = _pathname()
    with Directory(content='episodes') as directory:
        if payload.is_category(pathname):
            _items(directory, pathname)
        else:
            _program(directory, pathname)


def sezioni(pathname):
    """The categories a program page publishes, in the order the site lists them.

    A program is a hub: its page publishes a submenu, and every entry of it says
    what the category holds. An entry the site keeps in a CMS section is not
    offered - the site has no page of those videos this add-on can list.
    """
    try:
        answer = client.gql('nodePage', {'path': pathname.strip('/')})
    except client.SiteError as cause:
        raise AddonError(G.MODE, cause)
    entity = (answer.get('route') or {}).get('entity') or {}
    categories = []
    for voce in entity.get('vociSottomenu') or []:
        category = _categoria(pathname, voce)
        if category and category not in categories:
            categories.append(category)
    return categories


def giorno_label(data):
    """'27-10-2026' in the words of the guide: 'martedi 27 ottobre'."""
    try:
        day, month, year = [int(part) for part in data.split('-')]
        date = datetime.date(year, month, day)
    except (AttributeError, TypeError, ValueError):
        return data
    return '%s %d %s' % (GIORNI_SETTIMANA[date.weekday()], date.day, MESI[date.month - 1])


def _program(directory, pathname):
    """A program page: the week of its replays, then the categories it publishes."""
    replays = repliche(directory, pathname)
    categories = sezioni(pathname)
    for category in categories:
        directory.add({'mode': G.MODE, 'link': G.URL_PLAY_BASE + category['path']},
                      _folder(category['label']))
    if not replays and not categories:
        # a page with nothing to open is a failure to report, not an empty folder
        # to walk into
        raise AddonError(G.MODE, LookupError('%s publishes no replay and no category' % pathname))


def _items(directory, pathname):
    """The items one page of a category publishes, and the way to its next page."""
    page = max(G.PAGENUM, 1)
    nodes, more = archive.items(pathname, page)
    if not nodes:
        raise AddonError(G.MODE, LookupError('%s publishes nothing' % pathname))
    for node in nodes:
        params, item = _node(node)
        directory.add(params, item, folder=False, unique=True)
    if more:
        # only a listing pages: an archive is one query, read whole
        directory.add({'mode': G.MODE, 'link': G.URL_PLAY_BASE + pathname,
                       'page': str(page + 1)}, _next_page())


def _categoria(pathname, voce):
    """The category one entry of a program's submenu names, or None.

    An entry says what it holds, not where it is: a replica archive and a video
    list are the two pages a program publishes under the same names.
    """
    label = (voce.get('titoloVoce') or '').strip()
    if not label or (voce.get('sezione') or {}).get('path'):
        return None
    tipo = (voce.get('tipoDiContenuto') or {}).get('name')
    if tipo == 'Replica':
        return {'path': pathname + '/puntate', 'label': label}
    if tipo == 'Video':
        return {'path': pathname + '/video', 'label': label}
    # an article, or a podcast the site forwards to Spotify and friends
    return None


def _pathname():
    """The site path of the page the add-on was asked for."""
    return '/' + G.LINK[len(G.URL_PLAY_BASE):].strip('/')


def _guida_url():
    """The guide page of the channel the add-on is showing."""
    return G.URL_RIVEDILA7CINEMA if G.MODE == 'rivedi_la7cinema' else G.URL_RIVEDILA7


def _guide(section, url):
    """The days a guide page publishes, oldest first, each with its programs."""
    try:
        text = payload.decode(client.fetch_html(url))
    except client.SiteError as cause:
        raise AddonError(section, cause)
    days = []
    for day in payload.value(text, 'giorno') or []:
        data = (day.get('@attributes') or {}).get('data')
        if data:
            days.append({'data': data, 'programma': day.get('programma') or []})
    return days


def _has_replay(day):
    """A day is worth a folder when one of its programs has a replay."""
    return any(_path(programma) for programma in day['programma'])


def _path(programma):
    """The path of the replay of a program of the guide, or ''."""
    return (programma.get('pathname') or '').strip()


def _title(programma):
    """The title the guide gives a program of the day."""
    return (programma.get('titolo') or '').strip()


def _episode(programma, label):
    """One replay: the item Kodi shows, and where a click on it goes."""
    thumb = programma.get('immagine_programma') or programma.get('immagine_scena') or ''
    plot = (programma.get('sinossi') or '').strip()
    item = xbmcgui.ListItem(label, offscreen=True)
    art = {'fanart': G.FANART_PATH}
    if thumb:
        art['thumb'] = thumb
    item.setArt(art)
    item.setInfo('video', {'plot': plot})
    params = {'mode': G.MODE, 'play': G.URL_PLAY_BASE + _path(programma),
              'titolo': _title(programma), 'thumb': thumb, 'plot': plot}
    return params, item


def _node(node):
    """One item of a category: the item Kodi shows, and what a click on it opens."""
    title = payload.node_title(node)
    thumb = _cover(node)
    plot = _plot(node)
    item = xbmcgui.ListItem(title, offscreen=True)
    art = {'fanart': G.FANART_PATH}
    if thumb:
        art['thumb'] = thumb
    item.setArt(art)
    if plot:
        item.setInfo('video', {'plot': plot})
    params = {'mode': G.MODE, 'play': G.URL_PLAY_BASE + payload.node_path(node),
              'titolo': title, 'thumb': thumb, 'plot': plot}
    return params, item


def _folder(label):
    """A category as Kodi shows it: a folder named the way the site names it."""
    item = xbmcgui.ListItem(label, offscreen=True)
    item.setArt({'fanart': G.FANART_PATH})
    return item


def _next_page():
    """The item that opens the page after the one being listed."""
    item = xbmcgui.ListItem('[B]' + G.LANGUAGE(32003) + '[/B]', offscreen=True)
    item.setArt({'fanart': G.FANART_PATH})
    return item


def _cover(node):
    """The picture of a category item: its scene first, whatever else after."""
    upload = node.get('uploadVideo') or {}
    for image in (upload.get('cf_thumbnail_url'), node.get('smartTvLocandina'),
                  node.get('coverImage'), node.get('scenaImage'), node.get('programmaImage')):
        url = _image(image)
        if url:
            return url
    return ''


def _plot(node):
    """The text a category item publishes about itself, wherever it keeps it."""
    for text in (_text(node.get('body')), _text(node.get('description')),
                 _text(node.get('sinossi'))):
        if text:
            return text
    return ''


def _image(image):
    """The URL of a picture, which the site gives as a string or as a structure."""
    if isinstance(image, str):
        return image
    if isinstance(image, dict):
        return _image(image.get('url'))
    return ''


def _text(value):
    """The string of a text, which the site wraps as plain text or as HTML."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return _text(value.get('plainValue') or value.get('value'))
    return ''
