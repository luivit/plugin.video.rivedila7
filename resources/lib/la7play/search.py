"""Search: the site's result page, with its own paging.

A search is opened from the menu, reused when playback stops and reopened when
the site answers with nothing, so the query is kept in a Kodi window property
rather than in this module: the property survives the add-on being called again
for the next page.
"""

from urllib.parse import quote_plus
from urllib.request import Request, urlopen

import xbmc
import xbmcgui

from bs4 import BeautifulSoup

from resources.lib.globals import G
from resources.lib.kodi import dialogs
from resources.lib.kodi.directory import Directory
from resources.lib.playback import streams


def cerca_la7():
    """List the results of one search, page by page."""
    window = xbmcgui.Window(10000)
    url = G.LINK

    # Se un video è appena terminato (Stop), riusa la ricerca salvata senza riaprire la tastiera
    era_in_video = window.getProperty('la7_video_in_corso') == '1'
    window.clearProperty('la7_video_in_corso')

    if era_in_video:
        url = window.getProperty('la7_search_url')

    # Se non c'è URL (nuova ricerca dal menu principale), apre la tastiera
    if not url:
        tastiera = xbmcgui.Dialog()
        testo = tastiera.input("Ricerca nel sito", type=xbmcgui.INPUT_ALPHANUM)
        if not testo:
            Directory().fail()
            return
        query = quote_plus(testo)
        url = f"{G.URL_CERCA_LA7}{query}"
        window.setProperty('la7_search_url', url)
    else:
        window.setProperty('la7_search_url', url)

    try:
        req = Request(url, headers={'user-agent': G.HEADERS_SET['user-agent']})
        page = urlopen(req)
        soup = BeautifulSoup(page, 'html.parser')
    except Exception as e:
        xbmc.log(f'ERRORE RICERCA LA7: {str(e)}', xbmc.LOGERROR)
        Directory().fail()
        return

    rows = soup.find_all('div', class_=lambda c: c and 'views-row' in c)

    # Se non trova risultati: notifica e riapre subito la tastiera
    if not rows:
        dialogs.notify("La ricerca non ha prodotto risultati")
        window.clearProperty('la7_search_url')
        G.LINK = ""
        cerca_la7()
        return

    with Directory() as directory:
        # Elenco dei video trovati
        for row in rows:
            a_tag = row.find('a')
            if not a_tag or not a_tag.get('href'):
                continue

            href = a_tag.get('href').strip()
            video_link = G.URL_BASE + href

            title_div = row.find('div', class_='title')
            titolo = title_div.text.strip() if title_div else "Senza titolo"

            prop_div = row.find('div', class_='property')
            programma = prop_div.text.strip() if prop_div else ""

            data_div = row.find('div', class_='data')
            data_str = data_div.text.strip() if data_div else ""

            label = f"[{data_str}] {titolo}" if data_str else titolo

            thumb = ''
            thumb_div = row.find('div', class_='bg-img')
            if thumb_div and thumb_div.has_attr('data-background-image'):
                thumb = thumb_div.get('data-background-image').strip()
                if thumb.startswith('//'):
                    thumb = 'https:' + thumb

            liStyle = xbmcgui.ListItem(label)
            video_info_tag = liStyle.getVideoInfoTag()
            video_info_tag.setTitle(label)
            if programma or data_str:
                video_info_tag.setPlot(f"{programma} - {data_str}".strip(" -"))

            if thumb:
                liStyle.setArt({'thumb': thumb, 'poster': thumb})
            liStyle.setArt({'fanart': G.FANART_PATH})

            directory.add({"mode": "cerca_la7", "play": video_link}, liStyle, folder=False)

        # Paginazione in fondo
        next_li = soup.find('li', class_='pager-next')
        if next_li and next_li.find('a'):
            next_url = G.URL_BASE + next_li.a.get('href').strip()
            li_next = xbmcgui.ListItem(">> Pagina Successiva")
            li_next.setArt({'fanart': G.FANART_PATH})
            directory.add({"mode": "cerca_la7", "link": next_url}, li_next)


def play_result(video_link):
    """Play one result, and remember that a search is what brought the user there."""
    xbmcgui.Window(10000).setProperty('la7_video_in_corso', '1')
    streams.play_video(video_link, False)
