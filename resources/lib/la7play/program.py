"""Replays: the days of the TV guide, the replays of a day, a program's week.

The guide of la7play.it publishes the whole week as one page, every program with
the path of its replay, so the days and the episodes are two reads of the same
payload and nothing here scrapes markup. A program page publishes no episode list
at all: its week is that guide filtered on its own path, which is why the guide is
read for both channels. The program page itself is still scraped, and moves here
in the commits that follow.

What holds throughout: one Directory per folder, closed once on every path, and a
failure named by the section that failed.
"""

import datetime
import os
import sys

from urllib.request import Request, urlopen

import xbmc
import xbmcgui

from bs4 import BeautifulSoup

from resources.lib.globals import G
from resources.lib.kodi import dialogs
from resources.lib.kodi.dialogs import AddonError
from resources.lib.kodi.directory import Directory
from resources.lib.la7play import client, payload

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


def repliche(pathname):
    """The replays of one program in the week of the guides, newest day first.

    Returns how many replays were listed: a program the week does not cover is
    listed from its page instead, which is the caller's business.
    """
    added = 0
    page = pathname.rstrip('/')
    seen = set()
    with Directory(content='episodes') as directory:
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


def giorno_label(data):
    """'27-10-2026' in the words of the guide: 'martedi 27 ottobre'."""
    try:
        day, month, year = [int(part) for part in data.split('-')]
        date = datetime.date(year, month, day)
    except (AttributeError, TypeError, ValueError):
        return data
    return '%s %d %s' % (GIORNI_SETTIMANA[date.weekday()], date.day, MESI[date.month - 1])


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


# PAGINA PRINCIPALE
# esempio https://www.la7.it/tgla7 (senza "/rivedila7")
def video_programma_landpage(directory):
    """The top of a program page: the last episode and the carousels."""
    # xbmc.log('LINK GLOBAL_LAND------: '+str(G.LINK),xbmc.LOGINFO)

    # ///// HOME /////
    directory.header('HOME')

    if G.LINK == G.URL_BASE + '/faccia-a-faccia':
        link_landpage = G.URL_BASE + '/facciaafaccia'
        req = Request(link_landpage, headers={'user-agent': G.HEADERS_SET['user-agent']})
    elif G.LINK == G.URL_BASE + '/boss-dei-comici':
        link_landpage = G.URL_BASE + '/il-boss-dei-comici'
        req = Request(link_landpage, headers={'user-agent': G.HEADERS_SET['user-agent']})
    elif G.LINK == G.URL_BASE + '/laria-destate':
        link_landpage = G.URL_BASE + '/lariadestate'
        req = Request(link_landpage, headers={'user-agent': G.HEADERS_SET['user-agent']})
    elif G.LINK == G.URL_BASE + '/tagada-doc':
        link_landpage = G.URL_BASE + '/taga-doc'
        req = Request(link_landpage, headers={'user-agent': G.HEADERS_SET['user-agent']})
    else:
        req = Request(G.LINK, headers={'user-agent': G.HEADERS_SET['user-agent']})
    page = urlopen(req)
    html = BeautifulSoup(page, 'html.parser')

    # VIDEO INIZIALE
    video_iniziale = html.find('div', class_='ultima_puntata')
    #xbmc.log('DATI VIDEO INIZIALE------: '+str(video_iniziale),xbmc.LOGINFO)
    if video_iniziale:
        get_rows_video_landpage_preview(directory, video_iniziale)

    # PUNTATE
    if (html.findAll(text="puntate")) or (html.findAll(text="Guarda ora")) or (html.findAll(text="Tutti i film")):
        # xbmc.log('TEST------: '+str(html.find('div',class_='home-block__content-inner')),xbmc.LOGINFO)
        video_puntate_1r = html.find('div', class_='home-block__content-inner').select('div[class="item"]')
        video_puntate_2r = html.find('section', class_='home-block home-block--oggi-striscia home-block--fixed').find_all('div', class_='item')
        # xbmc.log('TEST------: '+str(video_puntate_2r),xbmc.LOGINFO)
        if video_puntate_1r:
            get_rows_video_landpage(directory, video_puntate_1r)
        if video_puntate_2r:
            get_rows_video_landpage(directory, video_puntate_2r)


# PAGINA SECONDARIA
# esempio https://www.la7.it/tgla7/rivedila7 (con "/rivedila7")
def video_programma():
    """A program page: the week of replays, then the archive of the program."""
    page = ''
    first = None

    with Directory(content='episodes') as directory:
        #xbmc.log('PAGENUM------: '+str(G.PAGENUM),xbmc.LOGINFO)
        if (G.PAGENUM == 0):
            video_programma_landpage(directory)

        #xbmc.log('LINK GLOBAL------: '+str(G.LINK),xbmc.LOGINFO)
        req = Request(G.LINK + "/rivedila7", headers={'user-agent': G.HEADERS_SET['user-agent']})
        try:
            page = urlopen(req)
        except Exception as e:
            e = sys.exc_info()[0]
            xbmc.log('EXCEP URL PAGINA SECONDARIA: ' + str(e), xbmc.LOGINFO)
            dialogs.show(G.LANGUAGE(32005))
            directory.fail()
            return
        html = BeautifulSoup(page, 'html.parser')

        # ///// SETTIMANA /////
        if G.PAGENUM == 0:
            directory.header('SETTIMANA')

            # FIRST VIDEO
            if html.find('div', class_='ultima_puntata'):
                first = html.find('div', class_='ultima_puntata')
            elif html.find('div', class_='contenitoreUltimaReplicaLa7d'):
                first = html.find('div', class_='contenitoreUltimaReplicaLa7d')
            elif html.find('div', class_='contenitoreUltimaReplicaNoLuminosa'):
                first = html.find('div', class_='contenitoreUltimaReplicaNoLuminosa')
            else:
                xbmc.log('NO FIRST VIDEO', xbmc.LOGINFO)
                dialogs.show(G.LANGUAGE(32005))
                directory.fail()
                return
            titolo = first.find('div', class_='title_puntata').text.strip()
            # xbmc.log('FIRST VIDEO----: '+str(titolo),xbmc.LOGINFO)
            first_video(directory, first, titolo, True)

            # WEEK VIDEO
            if html.findAll(text=" LA SETTIMANA"):
                video_settimana = html.find('div', class_='home-block__content-carousel container-vetrina').find_all('div', class_='item')
                # xbmc.log('LA SETTIMANA----: '+str(video_settimana),xbmc.LOGINFO)
                if video_settimana:
                    get_rows_video(directory, video_settimana)
            else:
                xbmc.log('NO WEEK VIDEO', xbmc.LOGINFO)

        # ///// ARCHIVIO /////
        if (html.findAll(text="Puntate Cult")) or (html.findAll(text="Tutti i film")):
            directory.header('ARCHIVIO')

            if (G.LINK == G.URL_BASE + '/chi-sceglie-la-seconda-casa') or (G.LINK == G.URL_BASE + '/lingrediente-perfetto') or (G.LINK == G.URL_BASE + '/una-giornata-particolare'):
                req2 = Request(G.LINK + "/rivedila7", headers={'user-agent': G.HEADERS_SET['user-agent']})
            else:
                req2 = Request(G.LINK + "/rivedila7/archivio?page=" + str(G.PAGENUM), headers={'user-agent': G.HEADERS_SET['user-agent']})
            page2 = urlopen(req2)
            html2 = BeautifulSoup(page2, 'html.parser')
            video_archivio = html2.find('div', class_='view-content clearfix').find_all('div', class_='views-row')
            if video_archivio:
                get_rows_video(directory, video_archivio)
                page = html2.find('li', class_='pager-next')
                pagenext(directory, page)
        else:
            xbmc.log('NO ARCHIVIO VIDEO', xbmc.LOGINFO)


def first_video(directory, first, titolo, filtro):
    # xbmc.log('FILTRO FIRST: '+ titolo + str(filtro), xbmc.LOGINFO)
    if filtro:
        # xbmc.log('FILTRO TRUE', xbmc.LOGINFO)
        thumblink = first.find('div', class_='holder-bg lozad').get('data-background-image')
        if thumblink.startswith('//'):
            thumb = 'https:' + thumblink
        else:
            thumb = thumblink
        # xbmc.log('THUMB 1------: '+str(thumb),xbmc.LOGINFO)
        data_orig = first.find('div', class_='scritta_ultima').text.strip()
        data = '[I] - (' + data_orig.replace('/', '.') + ')[/I]'
        try:
            plot = first.find('div', class_='occhiello').text.strip()
        except Exception as e:
            e = sys.exc_info()[0]
            xbmc.log('EXCEP PLOT1: ' + str(e), xbmc.LOGINFO)
            plot = ""
        link = G.URL_BASE + first.find('a').get('href')
        liStyle = xbmcgui.ListItem(titolo + data, offscreen=True)
        liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
        liStyle.setInfo('video', {'plot': plot})
        directory.add({"mode": G.MODE, "play": link, "titolo": titolo + data, "thumb": thumb, "plot": plot}, liStyle, folder=False)


def video_list(directory, div, titolo, filtro):
    if filtro:
        thumblink = div.find('div', class_='bg-img lozad').get('data-background-image')
        if thumblink.startswith('//'):
            thumb = 'https:' + thumblink
        else:
            thumb = thumblink
        # xbmc.log('THUMB 2------: '+str(thumb),xbmc.LOGINFO)
        # subdata=div.find('a').get('href')
        # data='[I] - ('+subdata[24:34]+')[/I]'
        try:
            data_orig = div.find('div', class_='data').text.strip()
            data = '[I] - (' + data_orig.replace('/', '.') + ')[/I]'
        except Exception as e:
            e = sys.exc_info()[0]
            xbmc.log('MANCA DATA: ' + str(e), xbmc.LOGINFO)
            data = ""
        plot = ''
        link = G.URL_BASE + div.find('a').get('href')
        # xbmc.log('TEST------: '+str(data),xbmc.LOGINFO)
        liStyle = xbmcgui.ListItem(titolo + data, offscreen=True)
        liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
        liStyle.setInfo('video', {'plot': plot})
        directory.add({"mode": G.MODE, "play": link, "titolo": titolo + data, "thumb": thumb, "plot": plot}, liStyle, folder=False)


def get_rows_video(directory, video):
    for div in video:
        titolo = div.find('div', class_='title').text.strip()
        video_list(directory, div, titolo, True)


def get_rows_video_landpage_preview(directory, video):
    #xbmc.log('TEST-----: '+str(video),xbmc.LOGINFO)
    titolo = video.find('div', class_='title_puntata').text.strip()
    data = '[I] - (' + video.find('div', class_='scritta_ultima').text.strip() + ')[/I]'
    thumblink = video.find('div', class_='holder-bg lozad arrow-play').get('data-background-image')
    #thumblink = video.find('div', class_='holder-bg lozad').get('data-background-image')

    plot = ""
    if thumblink.startswith('//'):
        thumb = 'https:' + thumblink
    else:
        thumb = thumblink
    try:
        occhiello = video.find('div', class_='occhiello')
        plot = occhiello.text.strip() if occhiello else ""
    except Exception as e:
        e = sys.exc_info()[0]
        xbmc.log('EXCEP PLOT2: ' + str(e), xbmc.LOGINFO)
        try:
            plot = video.find('div', class_='title_puntata').text.strip()
        except Exception as ee:
            ee = sys.exc_info()[0]
            xbmc.log('EXCEP TITLE_PUNTATA: ' + str(ee), xbmc.LOGINFO)
            plot = ""
    link = G.URL_BASE + video.find('a').get('href')
    liStyle = xbmcgui.ListItem(titolo + data, offscreen=True)
    liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
    liStyle.setInfo('video', {'plot': plot})
    directory.add({"mode": G.MODE, "play": link, "titolo": titolo + data, "thumb": thumb, "plot": plot}, liStyle, folder=False)


def get_rows_video_landpage(directory, video):
    # xbmc.log('VIDEO-----: '+str(video),xbmc.LOGINFO)
    for div in video:
        titolo = div.find('div', class_='occhiello').text.strip()
        # xbmc.log('TITOLO-----: '+str(titolo),xbmc.LOGINFO)
        data = '[I] - (' + div.find('div', class_='data').text.strip() + ')[/I]'
        thumblink = div.find('div', class_='bg-img lozad').get('data-background-image')
        if thumblink.startswith('//'):
            thumb = 'https:' + thumblink
        else:
            thumb = thumblink
        plot = ""
        link = G.URL_BASE + div.a.get('href').strip()
        liStyle = xbmcgui.ListItem(titolo + data, offscreen=True)
        liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
        liStyle.setInfo('video', {'plot': plot})
        directory.add({"mode": G.MODE, "play": link, "titolo": titolo + data, "thumb": thumb, "plot": plot}, liStyle, folder=False)


def pagenext(directory, pagenb):
    if pagenb:
        liStyle = xbmcgui.ListItem('[B]' + G.LANGUAGE(32003) + '[/B]', offscreen=True)
        liStyle.setArt({'fanart': G.FANART_PATH})
        directory.add({"mode": G.MODE, "link": G.LINK, "page": G.PAGENUM + 1}, liStyle)
