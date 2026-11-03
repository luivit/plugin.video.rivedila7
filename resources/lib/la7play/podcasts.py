"""Podcasts: the series the site publishes, and the feed that holds the episodes.

la7play.it lists its podcasts but does not serve them: the `/podcast` page is a set of
series cards, and a series links out to the platforms that carry it - Spotify, Apple
Podcasts, Amazon Music. The audio itself is not on the site, and never will be: it lives
in the publisher's RSS feed, and the page already tells us which one, through the Apple
Podcasts link every series carries.

So a series is opened the way any Kodi podcast is: the Apple id in the page's link is
asked to iTunes, which answers with the feed URL, and the feed answers with the episodes -
title, date, duration, picture, and the one thing a player needs, an enclosure URL that
is an mp3. Feeds can hold thousands of episodes, so the feed is read up to the page being
shown and then dropped: only the twenty episodes of a folder page are ever built.

Nothing here is a decision about what a podcast is: it is the site's list, the feed's
episodes, in the order the feed publishes them.
"""

import json
import re
import xml.etree.ElementTree as ElementTree
from email.utils import parsedate_to_datetime
from urllib.error import URLError
from urllib.parse import urlencode

from resources.lib.globals import G
from resources.lib.kodi import items, player
from resources.lib.kodi.dialogs import AddonError
from resources.lib.kodi.directory import Directory
from resources.lib.la7play import client

# the page of the site that lists the series, and the query that says where a feed is
SERIES_PAGE = '/podcast'
LOOKUP = 'https://itunes.apple.com/lookup?'
APPLE_ID = re.compile(r'podcasts\.apple\.com/\S*/id(\d+)')

# how many episodes one folder page shows, and the feed's namespace
PAGE_SIZE = 20
ITUNES = '{http://www.itunes.com/dtds/podcast-1.0.dtd}'

# what a series card calls itself in the page's payload
SERIES_TYPE = 'PodcastSeries'


def serie():
    """The podcasts the site publishes: one folder per series."""
    with Directory() as directory:
        for one in _series():
            directory.add({'mode': G.MODE, 'link': one['apple']},
                          items.entry(one['title'], one['thumb'], one['plot']))


def episodi():
    """The episodes of one podcast, twenty of them, newest first as the feed has them."""
    page = G.PAGENUM or 1
    episodes, more = _episodes(G.LINK, page)
    playable = [episode for episode in episodes if episode['audio']]
    if not playable:
        # a feed with nothing to play is not a folder: it is a failure to report
        raise AddonError(G.MODE, LookupError('the feed of %s publishes no audio' % G.LINK))
    with Directory(content='episodes') as directory:
        for episode in playable:
            directory.add({'mode': G.MODE, 'play': episode['audio']}, _item(episode),
                          folder=False, unique=True)
        if more:
            directory.add({'mode': G.MODE, 'link': G.LINK, 'page': str(page + 1)},
                          items.next_page())


def play(url):
    """Play one episode: the enclosure the feed publishes is an mp3 Kodi plays itself."""
    player.resolve(url, mime='audio/mpeg')


def _item(episode):
    """One episode of a series, as the folder shows it."""
    title = episode['data'] + ' ' + episode['title'] if episode['data'] else episode['title']
    return items.entry(title, episode['thumb'], episode['plot'])


def _series():
    """The series cards of the podcast page, each with the id that finds its feed."""
    try:
        html = client.fetch_html(G.URL_PLAY_BASE + SERIES_PAGE)
    except client.SiteError as cause:
        raise AddonError(G.MODE, cause)
    found, series = set(), []
    for match in re.finditer(r'\{"@type"\s*:\s*"%s"' % SERIES_TYPE, html):
        try:
            card = json.JSONDecoder().raw_decode(html, match.start())[0]
        except ValueError:
            # a card the page never finished writing: the next one is still a card
            continue
        apple = _apple(card)
        if not apple or apple in found:
            continue
        found.add(apple)
        series.append({'apple': apple,
                       'title': (card.get('name') or '').strip() or apple,
                       'thumb': (card.get('image') or {}).get('url') or '',
                       'plot': (card.get('description') or '').strip()})
    if not series:
        raise AddonError(G.MODE, LookupError('the page publishes no podcast'))
    return series


def _apple(card):
    """The Apple id in a series card, which is what names its feed."""
    found = APPLE_ID.search(' '.join(card.get('sameAs') or []))
    return found.group(1) if found else ''


def _feed(apple_id):
    """The RSS feed of one podcast, from the id the site's page gave."""
    try:
        answer = json.loads(client.fetch_html(LOOKUP + urlencode({'id': apple_id})))
        return answer['results'][0]['feedUrl']
    except client.SiteError as cause:
        raise AddonError(G.MODE, cause)
    except (IndexError, KeyError, TypeError, ValueError) as cause:
        raise AddonError(G.MODE, LookupError('%s has no feed on iTunes' % apple_id))


def _episodes(apple_id, page):
    """One page of a feed's episodes, and whether the episode after it has anything."""
    start = (page - 1) * PAGE_SIZE
    episodes, thumb, seen = [], '', 0
    try:
        for event, element in ElementTree.iterparse(client.stream(_feed(apple_id)),
                                                    events=('end',)):
            if element.tag == ITUNES + 'image' and not thumb:
                thumb = element.get('href') or ''
            if element.tag != 'item':
                continue
            seen += 1
            if seen > start + PAGE_SIZE:
                return episodes, True
            if seen > start:
                episodes.append(_episode(element, thumb))
            # a feed is read for the page it is asked about: the rest is dropped
            element.clear()
    except (OSError, URLError) as cause:
        raise AddonError(G.MODE, cause)
    except ElementTree.ParseError as cause:
        raise AddonError(G.MODE, cause)
    return episodes, False


def _episode(element, thumb):
    """One item of a feed, as the add-on shows and plays it."""
    enclosure = element.find('enclosure')
    image = element.find(ITUNES + 'image')
    return {'title': (element.findtext('title') or '').strip(),
            'audio': (enclosure.get('url') if enclosure is not None else '') or '',
            'data': _date(element.findtext('pubDate') or ''),
            'plot': (element.findtext(ITUNES + 'summary') or element.findtext('description') or '').strip(),
            'thumb': (image.get('href') if image is not None else '') or thumb}


def _date(published):
    """The date of an episode as an Italian folder shows it, or '' when it has none."""
    try:
        return parsedate_to_datetime(published).strftime('%d/%m/%Y')
    except (TypeError, ValueError):
        return ''
