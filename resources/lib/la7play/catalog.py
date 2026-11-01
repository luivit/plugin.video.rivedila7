"""The catalogue: the root menu and the lists of programs the site publishes.

Nothing here talks to Kodi directly: items go through a Directory, so the
listing cannot outlive its folder.
"""

import json
import os
import sys

from urllib.request import Request, urlopen

import xbmc
import xbmcgui
import xbmcplugin

from bs4 import BeautifulSoup

from resources.lib.globals import G
from resources.lib.kodi.directory import Directory


def show_root_menu():
    """The root menu of the add-on."""
    xbmcgui.Window(10000).clearProperty('la7_search_url')

    with Directory() as directory:
        li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32002) + '[/B]', offscreen=True)
        li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'direttalivela7.jpg'), 'fanart': G.FANART_PATH})
        directory.add({"mode": "diretta_la7"}, li_style, folder=False, is_live=True)
        li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32009) + '[/B]', offscreen=True)
        li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'direttalivela7cinema.jpg'), 'fanart': G.FANART_PATH})
        directory.add({"mode": "diretta_la7cinema"}, li_style, folder=False, is_live=True)
        li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32001) + '[/B]', offscreen=True)
        li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'rivedila7.jpg'), 'fanart': G.FANART_PATH})
        directory.add({"mode": "rivedi_la7"}, li_style)
        li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32004) + '[/B]', offscreen=True)
        li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'direttalivela7cinema.jpg'), 'fanart': G.FANART_PATH})
        directory.add({"mode": "rivedi_la7cinema"}, li_style)
        li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32010) + '[/B]', offscreen=True)
        li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'la7prime.jpg'), 'fanart': G.FANART_PATH})
        directory.add({"mode": "la7_prime"}, li_style)
        li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32006) + '[/B]', offscreen=True)
        li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'programmi.jpg'), 'fanart': G.FANART_PATH})
        directory.add({"mode": "tutti_programmi"}, li_style)
        li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32012) + '[/B]', offscreen=True)
        li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'cerca.png'), 'fanart': G.FANART_PATH})
        directory.add({"mode": "cerca_la7"}, li_style)


def programmi_lettera():
    """Both program lists of the site: the curated one and A-Z, minus the mappings."""
    with Directory(sort_method=xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS) as directory:
        req_p = Request(G.URL_PROGRAMMI, headers={'user-agent': G.HEADERS_SET['user-agent']})
        page_p = urlopen(req_p)
        html_p = BeautifulSoup(page_p, 'html.parser')
        programmi = html_p.find(id='container-programmi-list').find_all('div', class_='list-item')
        req_tp = Request(G.URL_TUTTI_PROGRAMMI, headers={'user-agent': G.HEADERS_SET['user-agent']})
        page_tp = urlopen(req_tp)
        html_tp = BeautifulSoup(page_tp, 'html.parser')
        tutti_programmi = html_tp.find_all('div', class_='list-item')

        with open(G.CONFIG_PATH, 'r') as config_file:
            config = json.load(config_file)

        if programmi or tutti_programmi:
            for dati in programmi:
                process_program_data(directory, dati, config)

            for dati in tutti_programmi:
                process_program_data(directory, dati, config)

            # Prog aggiunti manualmente
            programmi = {
                'LA MALA EDUCAXXXION 2': {
                    'url': '/la-mala-educaxxxion',
                    'img': 'https://kdam.iltrovatore.it/p/103/sp/10300/thumbnail/entry_id/0_j0z82ps2/version/100001/type/5/width/600/height/360/quality/100/name/0_j0z82ps2.jpg'
                },
            }
            for programma, program_info in programmi.items():
                titolo = programma
                liStyle = xbmcgui.ListItem(titolo, offscreen=True)
                url_trovato = program_info['url']
                link = G.URL_BASE + url_trovato
                thumb = program_info['img']
                liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
                directory.add({"mode": G.MODE, "link": link}, liStyle, unique=True)


def process_program_data(directory, dati, config):
    """Add one program of the list, unless the config excludes it."""
    if dati.find('a') is None:
        return
    url_trovato = dati.a.get('href').strip()
    # xbmc.log('URL--------: '+str(url_trovato),xbmc.LOGINFO)
    if url_trovato not in config['exclusions']:
        url_trovato = config['mappings'].get(url_trovato, url_trovato)
        titolo = ''
        if dati.find('div', class_='titolo'):
            titolo = dati.find('div', class_='titolo').text.strip()
        if titolo == '':
            titolo = url_trovato.lstrip('/').replace('-', ' ').upper()
        # xbmc.log('TITLE1-----: '+str(titolo),xbmc.LOGINFO)
        liStyle = xbmcgui.ListItem(titolo, offscreen=True)
        link = G.URL_BASE + url_trovato
        # xbmc.log('LINK-----: '+str(link),xbmc.LOGINFO)
        if len(dati) > 0:
            try:
                thumb = dati.find('div', class_='image-bg lozad').get('data-background-image')
            except Exception as e:
                e = sys.exc_info()[0]
                xbmc.log('EXCEP THUMB1: ' + str(e), xbmc.LOGINFO)
                thumb = ''
            if thumb:
                liStyle.setArt({'thumb': thumb})
            else:
                xbmc.log('NO THUMB1', xbmc.LOGINFO)
        liStyle.setArt({'fanart': G.FANART_PATH})
        directory.add({"mode": G.MODE, "link": link}, liStyle, unique=True)


def programmi_la7prime():
    """The three fixed grids of the LA7 Prime section."""
    with Directory() as directory:
        titolo = 'Tutti i Film'
        liStyle = xbmcgui.ListItem(titolo, offscreen=True)
        url_trovato = '/la7-cinema-tutti-i-film'
        link = G.URL_BASE + url_trovato
        thumb = os.path.join(G.THUMB_PATH, 'film.jpg')
        liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
        directory.add({"mode": G.MODE, "link": link}, liStyle, unique=True)

        titolo = 'Film e Fiction'
        liStyle = xbmcgui.ListItem(titolo, offscreen=True)
        url_trovato = '/film-e-fiction'
        link = G.URL_BASE + url_trovato
        thumb = os.path.join(G.THUMB_PATH, 'filmfiction.jpg')
        liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
        directory.add({"mode": G.MODE, "link": link}, liStyle, unique=True)

        titolo = 'Non Classificati'
        liStyle = xbmcgui.ListItem(titolo, offscreen=True)
        url_trovato = '/non-classificati'
        link = G.URL_BASE + url_trovato
        thumb = os.path.join(G.THUMB_PATH, 'filmfiction.jpg')
        liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
        directory.add({"mode": G.MODE, "link": link}, liStyle, unique=True)
