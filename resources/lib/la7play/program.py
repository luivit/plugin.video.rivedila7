"""Replays: the TV guide days, and a program page with its week and its archive.

Both listings are still scraped from the pages the site renders for a browser;
they move to the payload in the commits that follow. What already holds here is
the lifecycle: one Directory per folder, closed once, failures through a dialog
and never as a traceback.
"""

import os
import sys

from urllib.request import Request, urlopen

import xbmc
import xbmcgui

from bs4 import BeautifulSoup

from resources.lib.globals import G
from resources.lib.kodi import dialogs
from resources.lib.kodi.directory import Directory


def rivedi(url, thumb):
    """The days the guide offers for a channel."""
    with Directory() as directory:
        req = Request(url, headers={'user-agent': G.HEADERS_SET['user-agent']})
        page = urlopen(req)
        html = BeautifulSoup(page, 'html.parser')
        G.GIORNO = html.find('div', class_='block block-system').find_all('div', class_=['item item--menu-guida-tv', 'item item--menu-guida-tv active'])
        # xbmc.log('GIORNO----------: '+str(G.GIORNO),xbmc.LOGINFO)
        if G.GIORNO:
            for div in reversed(G.GIORNO):
                date_day = div.find('div', class_='giorno-numero').text.strip()
                date_month = div.find('div', class_='giorno-mese').text.strip()
                date_row_week = div.find('div', class_='giorno-text').text.strip()
                a = div.a.get('href').strip()
                liStyle = xbmcgui.ListItem(date_row_week + " " + date_day + " " + date_month, offscreen=True)
                liStyle.setArt({'thumb': os.path.join(G.THUMB_PATH, thumb), 'fanart': G.FANART_PATH})
                directory.add({"mode": G.MODE, "giorno": a}, liStyle)


def rivedi_giorno():
    """The replays of one day of the guide."""
    with Directory(content='episodes') as directory:
        req = Request(G.URL_BASE + G.GIORNO, headers={'user-agent': G.HEADERS_SET['user-agent']})
        page = urlopen(req)
        html = BeautifulSoup(page, 'html.parser')
        guida_tv = html.find(id="content_guida_tv_rivedi").find_all('div', class_='item item--guida-tv')
        if guida_tv:
            for div in guida_tv:
                orario = div.find('div', class_='orario').contents[0].strip()
                nome = div.find('div', class_='property').text.strip()
                thumb = 'https:' + div.find('div', class_='bg-img lozad').get('data-background-image')
                plot = div.find('div', class_='occhiello').text.strip()
                if div.a:
                    urll = div.a.get('href').strip()
                    # xbmc.log('------LINK------: '+str(urll),xbmc.LOGINFO)
                    liStyle = xbmcgui.ListItem(orario + " " + nome, offscreen=True)
                    liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
                    liStyle.setInfo('video', {'plot': plot})
                    directory.add({"mode": G.MODE, "play": urll, "titolo": nome, "thumb": thumb, "plot": plot}, liStyle, folder=False)


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
