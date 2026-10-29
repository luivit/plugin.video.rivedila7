import base64
import json
import os
import sys
import time
import re
import datetime
import requests
import inputstreamhelper
from html import unescape

import urllib.parse
from urllib.request import Request, urlopen

import xbmc
import xbmcgui
import xbmcplugin

from bs4 import BeautifulSoup
from resources.lib.globals import G


def show_root_menu():
    xbmcgui.Window(10000).clearProperty('la7_search_url')

    """ Show the plugin root menu """
    li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32002) + '[/B]', offscreen=True)
    li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'direttalivela7.jpg'), 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": "diretta_la7"}, li_style, folder=False, is_live=True)
    li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32009) + '[/B]', offscreen=True)
    li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'direttalivela7cinema.jpg'), 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": "diretta_la7cinema"}, li_style, folder=False, is_live=True)
    li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32011) + '[/B]', offscreen=True)
    li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'direttalivela7eventi.jpg'), 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": "diretta_la7eventi"}, li_style, folder=False, is_live=True)
    li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32001) + '[/B]', offscreen=True)
    li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'rivedila7.jpg'), 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": "rivedi_la7"}, li_style)
    li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32004) + '[/B]', offscreen=True)
    li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'direttalivela7cinema.jpg'), 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": "rivedi_la7cinema"}, li_style)
    li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32010) + '[/B]', offscreen=True)
    li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'la7prime.jpg'), 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": "la7_prime"}, li_style)
    li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32007) + '[/B]', offscreen=True)
    li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'tgmeteo.jpg'), 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": "tg_meteo"}, li_style)
    li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32006) + '[/B]', offscreen=True)
    li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'programmi.jpg'), 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": "tutti_programmi"}, li_style)
    li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32008) + '[/B]', offscreen=True)
    li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'techela7.jpg'), 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": "teche_la7"}, li_style)
    li_style = xbmcgui.ListItem('[B]' + G.LANGUAGE(32012) + '[/B]', offscreen=True)
    li_style.setArt({'thumb': os.path.join(G.THUMB_PATH, 'cerca.png'), 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": "cerca_la7"}, li_style)

    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def add_directory_item_nodup(parameters, li, title='', folder=True, is_live=False):
    if not title:
        title = G.TITOLO
    if title in G.LIST_PROGRAMMI:
        # xbmc.log('PROGRAMMA DUPLICATO', xbmc.LOGINFO)
        pass
    else:
        url = G.PLUGIN_URL + '?' + urllib.parse.urlencode(parameters)
        if is_live:
            url += '&_l=.pvr'  # disabilita per le dirette la richiesta di riprendere il video dall'ultima volta
        # xbmc.log('LIST------: '+str(url),xbmc.LOGINFO)
        if not folder:
            li.setInfo('video', {})
            li.setProperty('isPlayable', 'true')
        return xbmcplugin.addDirectoryItem(handle=G.PLUGIN_HANDLE, url=url, listitem=li, isFolder=folder)


def get_html(url):
    req = Request(url, headers={'user-agent': G.HEADERS_SET['user-agent']})
    return urlopen(req).read().decode(errors='replace')


def next_flight_data(html):
    # le pagine di la7play.it (Next.js) contengono i dati in blocchi self.__next_f.push([1,"..."])
    data = ''
    for m in re.finditer(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html):
        data += json.loads('"' + m.group(1) + '"')
    return data


def json_object_at(text, marker):
    # decodifica l'oggetto JSON che inizia con marker (o subito dopo, se marker e' una chiave)
    pos = text.find(marker)
    if pos < 0:
        return None
    if not marker.startswith('{'):
        pos = text.find('{', pos + len(marker))
    return json.JSONDecoder().raw_decode(text, pos)[0]


def json_string(text, key):
    # primo valore stringa (non null) della chiave nel payload
    m = re.search(r'"%s":"((?:[^"\\]|\\.)*)"' % key, text)
    return json.loads('"' + m.group(1) + '"') if m else ''


def guida_tv(url):
    # guida tv di la7play.it: lista di giorni, ognuno con la sua lista di programmi
    data = json_object_at(next_flight_data(get_html(url)), '{"@attributes":{"canale"')
    giorni = data.get('giorno', []) if data else []
    if isinstance(giorni, dict):
        giorni = [giorni]
    return giorni


def programmi_giorno(giorno):
    programmi = giorno.get('programma', [])
    if isinstance(programmi, dict):
        programmi = [programmi]
    return programmi


def titolo_in_onda(url_guida):
    adesso = time.time()
    try:
        for giorno in guida_tv(url_guida):
            for programma in programmi_giorno(giorno):
                inizio = int(programma['timestamp'])
                if inizio <= adesso < inizio + int(programma['durata']):
                    return programma['titolo']
    except Exception as e:
        xbmc.log('EXCEP TITOLO IN ONDA: ' + str(e), xbmc.LOGINFO)
    return ''


def get_drm_token(endpoint, content_id, content_type):
    headers_tok = {
        'user-agent': G.HEADERS_SET['user-agent'],
        'accept': G.HEADERS_SET['accept'],
        'accept-language': G.HEADERS_SET['accept-language'],
        'origin': G.HEADERS_SET['origin'],
        'referer': G.HEADERS_SET['referer'],
    }
    params = {'id': content_id, 'contentType': content_type, 'v': str(int(time.time() * 1000))}
    response = requests.get(endpoint or G.URL_DRM_TOKEN, params=params, headers=headers_tok).json()
    return response.get('preAuthToken') or response.get('token') or response.get('auth')


def play_drm(mpdurl, pre_auth_token, titolo=''):
    headers_lic = {
        'host': G.HEADERS_SET['host_license'],
        'user-agent': G.HEADERS_SET['user-agent'],
        'accept': G.HEADERS_SET['accept'],
        'accept-language': G.HEADERS_SET['accept-language'],
        'preAuthorization': pre_auth_token,
        'origin': G.HEADERS_SET['origin'],
        'referer': G.HEADERS_SET['referer'],
    }
    pre_lic = '&'.join(['%s=%s' % (name, value) for (name, value) in headers_lic.items()])
    # xbmc.log('LICENSE1------: '+str(pre_lic),xbmc.LOGINFO)

    tsatmp = str(int(time.time()))
    license_url = G.KEY_WIDEVINE + '?d=%s' % tsatmp
    lic_url = '%s|%s|R{SSM}|' % (license_url, pre_lic)
    # xbmc.log('LICENSE2------: '+str(lic_url),xbmc.LOGINFO)
    is_helper = inputstreamhelper.Helper(G.DRM_PROTOCOL, drm=G.DRM)
    if is_helper.check_inputstream():
        listitem = xbmcgui.ListItem(offscreen=True)
        listitem.setPath(mpdurl)
        if titolo:
            listitem.setInfo('video', {'plot': titolo, 'title': titolo})
        listitem.setProperty("inputstream", is_helper.inputstream_addon)
        listitem.setProperty("inputstream.adaptive.manifest_type", G.DRM_PROTOCOL)
        listitem.setProperty("inputstream.adaptive.license_type", G.DRM)
        listitem.setProperty("inputstream.adaptive.license_key", lic_url)
        listitem.setMimeType('application/dash+xml')
        xbmcplugin.setResolvedUrl(G.PLUGIN_HANDLE, True, listitem)
    else:
        xbmcplugin.endOfDirectory(G.PLUGIN_HANDLE, succeeded=False)


def play_dirette(url, live):
    xbmc.log('PLAY DIRETTE', xbmc.LOGINFO)
    #xbmc.log('PAGE DIRETTE-----: '+str(url),xbmc.LOGINFO)

    try:
        player = next_flight_data(get_html(url))
        if url == G.URL_LIVE_LA7EVENTI:
            mpdurl = G.URL_MPD_LA7EVENTI
        else:
            # "mainLiveUrl": "<dash .mpd>|<hls .m3u8>"
            mpdurl = json_string(player, 'mainLiveUrl').split('|')[0].strip()
        pre_auth_token = get_drm_token(json_string(player, 'drmTokenEndpoint'), json_string(player, 'drmContentId'), 'LIVE')
    except Exception as e:
        xbmc.log('EXCEP DIRETTA: ' + str(e), xbmc.LOGINFO)
        mpdurl = ''
        pre_auth_token = ''
    #xbmc.log('URL VIDEO MPD-----: '+str(mpdurl),xbmc.LOGINFO)
    if not mpdurl or not pre_auth_token:
        xbmcgui.Dialog().ok(G.PLUGIN_NAME, G.LANGUAGE(32005))
        xbmcplugin.setResolvedUrl(G.PLUGIN_HANDLE, False, xbmcgui.ListItem(offscreen=True))
        return

    titolo_diretta = ''
    if live:
        if url == G.URL_LIVE_LA7:
            titolo_diretta = titolo_in_onda(G.URL_RIVEDILA7)
        elif url == G.URL_LIVE_LA7CINEMA:
            titolo_diretta = titolo_in_onda(G.URL_RIVEDILA7CINEMA)
        elif url == G.URL_LIVE_LA7EVENTI:
            titolo_diretta = 'LA7 Eventi Live'
        #xbmc.log('TITOLO DIRETTA-----: '+str(titolo_diretta),xbmc.LOGINFO)

    play_drm(mpdurl, pre_auth_token, titolo_diretta)


def play_video_la7play(html):
    # pagina video di la7play.it: i dati del file sono in "uploadVideo"
    player = next_flight_data(html)
    video = json_object_at(player, '"uploadVideo":')
    if not video or not video.get('cf_remote_url'):
        return ''
    remote_url = video['cf_remote_url']
    drm = re.search(r'"drm":(true|false)', player)
    if drm and drm.group(1) == 'true' and '"abilitaDrm":true' in player:
        nome = remote_url.lstrip('/').split('/')[-1]
        mpdurl = json_string(player, 'hostnameCdnDrm').rstrip('/') + '/' + nome + '/DASH/' + nome + '.mpd'
        pre_auth_token = get_drm_token(json_string(player, 'drmTokenEndpoint'), json_string(player, 'drmContentId'), 'VOD')
        play_drm(mpdurl, pre_auth_token, G.TITOLO)
        return None

    # stesso schema del player del sito: <cdn>/local/hls/,<file1>,<file2>,.mp4.urlset/master.m3u8
    cdn = (json_string(player, 'hostnameCdn') or G.URL_CDN_VOD).rstrip('/')
    files = (remote_url if remote_url.startswith('/') else '/' + remote_url).replace('.mp4', '')
    if not video.get('cf_old_entry_id'):
        nk = []
        for f in files.split(','):
            f = f.strip()
            if f and not f.startswith('/nk/'):
                f = '/nk' + f if f.startswith('/') else '/nk/' + f
            nk.append(f)
        files = ','.join(nk)
    return cdn + '/local/hls/,' + files + ',.mp4.urlset/master.m3u8'


def play_video(page_video, live):
    xbmc.log('PLAY VIDEO', xbmc.LOGINFO)
    #xbmc.log('PAGE VIDEO-----: '+str(page_video),xbmc.LOGINFO)

    # regex1 = 'vS = "(.*?)"'
    regex2 = r'\.net/i/.*?content/(.*?)(?:\.mp4)'
    regex3 = 'm3u8: "(.*?)"'
    # regex4 = '  <iframe src="(.*?)"'

    req = Request(page_video, headers={'user-agent': G.HEADERS_SET['user-agent']})
    page = urlopen(req).read()
    html = page.decode('utf-8', errors='ignore')
    if 'self.__next_f.push' in html:
        link_video = play_video_la7play(html)
        if link_video is None:
            return
    elif live:
        return
        # if re.findall(regex1, html):
        # xbmc.log('REGEX1-----: '+str(re.findall(regex1, html)),xbmc.LOGINFO)
        #     link_video = re.findall(regex1, html)[0]
    else:
        if re.findall(regex2, html):
            # xbmc.log('REGEX2-----: '+str(re.findall(regex2, html)),xbmc.LOGINFO)
            link_video = 'https://awsvodpkg.iltrovatore.it/local/hls/,/content/' + re.findall(regex2, html)[0] + '.mp4.urlset/master.m3u8'
            # xbmc.log('LINK2-----: '+str(link_video),xbmc.LOGINFO)
        # elif re.findall(regex5, html) or re.findall(regex5, html):
        #     xbmc.log('REGEX5-----: '+str(re.findall(regex5, html)),xbmc.LOGINFO)
        #     link_video = 'https://awsvodpkg.iltrovatore.it/local/hls/,/content/' + re.findall(regex5, html)[0] + '_1.mp4.urlset/master.m3u8'
        #     xbmc.log('LINK5-----: '+str(link_video),xbmc.LOGINFO)
        elif re.findall(regex3, html):
            # xbmc.log('REGEX3-----: '+str(re.findall(regex3, html)),xbmc.LOGINFO)
            link_video = re.findall(regex3, html)[0]
            # xbmc.log('LINK3-----: '+str(link_video),xbmc.LOGINFO)
        # video .mp4 dal Cerca
        elif re.findall(r'mp4["\']?\s*:\s*["\'](https?://[^"\']+\.mp4)["\']', html):
            link_video = re.findall(r'mp4["\']?\s*:\s*["\'](https?://[^"\']+\.mp4)["\']', html)[0]

        else:
            # xbmc.log('DECODIFICA DRM',xbmc.LOGINFO)
            play_dirette(page_video, False)
            return

    listitem = xbmcgui.ListItem(G.TITOLO, offscreen=True)
    listitem.setInfo('video', {'Title': G.TITOLO})
    if G.THUMB != "":
        listitem.setArt({'thumb': G.THUMB})
    listitem.setInfo('video', {'plot': G.PLOT})
    if link_video == '':
        xbmc.log('RivediLA7: NO VIDEO LINK', xbmc.LOGINFO)
        xbmcgui.Dialog().ok(G.PLUGIN_NAME, G.LANGUAGE(32005))
        xbmcplugin.setResolvedUrl(G.PLUGIN_HANDLE, False, listitem)
        return
    if '.m3u8' in link_video:
        listitem.setProperty('inputstream', 'inputstream.adaptive')
        listitem.setProperty('inputstream.adaptive.manifest_type', 'hls')

    listitem.setPath(link_video)
    xbmcplugin.setResolvedUrl(G.PLUGIN_HANDLE, True, listitem)


GIORNI_SETTIMANA = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
MESI = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']


def rivedi(url, thumb):
    giorni = guida_tv(url)
    # xbmc.log('GIORNO----------: '+str(giorni),xbmc.LOGINFO)
    for giorno in reversed(giorni):
        # i giorni futuri della guida non hanno ancora video da rivedere
        if not any(p.get('pathname') for p in programmi_giorno(giorno)):
            continue
        data = giorno['@attributes']['data']
        giorno_num, mese, anno = [int(x) for x in data.split('-')]
        date_row_week = GIORNI_SETTIMANA[datetime.date(anno, mese, giorno_num).weekday()]
        liStyle = xbmcgui.ListItem(date_row_week + " " + str(giorno_num) + " " + MESI[mese - 1], offscreen=True)
        liStyle.setArt({'thumb': os.path.join(G.THUMB_PATH, thumb), 'fanart': G.FANART_PATH})
        add_directory_item_nodup({"mode": G.MODE, "giorno": data}, liStyle)
    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def rivedi_giorno(url):
    for giorno in guida_tv(url):
        if giorno['@attributes']['data'] != G.GIORNO:
            continue
        for programma in programmi_giorno(giorno):
            if not programma.get('pathname'):
                continue
            orario = programma.get('ora', '')
            nome = programma.get('titolo', '').strip()
            thumb = programma.get('immagine_scena') or programma.get('immagine_programma') or ''
            plot = programma.get('sinossi', '').strip()
            urll = G.URL_BASE_LA7PLAY + programma['pathname']
            # xbmc.log('------LINK------: '+str(urll),xbmc.LOGINFO)
            liStyle = xbmcgui.ListItem(orario + " " + nome, offscreen=True)
            liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
            liStyle.setInfo('video', {'plot': plot})
            liStyle.setProperty('isPlayable', 'true')
            url2 = G.PLUGIN_URL + '?' + urllib.parse.urlencode({"mode": G.MODE, "play": urll, "titolo": nome, "thumb": thumb, "plot": plot})
            xbmcplugin.addDirectoryItem(handle=G.PLUGIN_HANDLE, url=url2, listitem=liStyle, isFolder=False)

    xbmcplugin.setContent(G.PLUGIN_HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def process_program_data(dati, config):
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
        add_directory_item_nodup({"mode": G.MODE, "link": link}, liStyle, titolo)

        if titolo not in G.LIST_PROGRAMMI:
            G.LIST_PROGRAMMI.append(titolo)

def gql_query(query_hash, variables=None):
    # API GraphQL di la7play.it (query persistite): /api/gql/<hash>/<variabili JSON in base64url>
    url = G.URL_GQL + query_hash
    if variables:
        js = json.dumps(variables, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        url += '/' + base64.urlsafe_b64encode(js.encode('utf8')).decode().rstrip('=')
    req = Request(url, headers={'user-agent': G.HEADERS_SET['user-agent'], 'accept': 'application/json'})
    return json.loads(urlopen(req).read().decode()).get('data') or {}


def programmi_lettera():
    data = gql_query(G.GQL_TUTTI_PROGRAMMI)
    programmi = (data.get('graphqlTuttiProgrammi') or {}).get('results') or []

    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)

    for programma in programmi:
        if programma.get('pathname') in config['exclusions'] or not programma.get('properti'):
            continue
        titolo = programma.get('titolo', '').strip()
        liStyle = xbmcgui.ListItem(titolo, offscreen=True)
        thumb = (programma.get('img') or '').split('||')[0]
        if thumb:
            liStyle.setArt({'thumb': thumb})
        liStyle.setArt({'fanart': G.FANART_PATH})
        plot = unescape(re.sub(r'<[^>]+>', '', programma.get('occhiello') or '')).strip()
        liStyle.setInfo('video', {'plot': plot})
        # le puntate si filtrano per nome della property in minuscolo
        add_directory_item_nodup({"mode": G.MODE, "link": programma['properti'].lower()}, liStyle, titolo)
        G.LIST_PROGRAMMI.append(titolo)

    xbmcplugin.addSortMethod(G.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS)
    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def programmi_la7prime():
    titolo = 'Tutti i Film'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    link = G.URL_FILM
    thumb = os.path.join(G.THUMB_PATH, 'film.jpg')
    liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": G.MODE, "link": link}, liStyle, titolo)

    titolo = 'Non Classificati'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    link = 'non classificati'
    thumb = os.path.join(G.THUMB_PATH, 'filmfiction.jpg')
    liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": G.MODE, "link": link}, liStyle, titolo)

    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def programmi_lettera_teche_la7():
    req_teche = Request(G.URL_TECHE_LA7, headers={'user-agent': G.HEADERS_SET['user-agent']})
    page_teche = urlopen(req_teche)
    html_teche = BeautifulSoup(page_teche, 'html.parser')
    
    teche_la7 = html_teche.find_all('div', class_='list-item')

    if teche_la7:
        for dati in teche_la7:
            if not dati.find('a'):
                continue
            
            titolo_div = dati.find('div', class_='titolo')
            if titolo_div:
                nomicognomi = titolo_div.text.strip()
                cognominomi = " ".join(reversed(nomicognomi.split(" ")))
                
                url_trovato = dati.a.get('href').strip()
                bio_link = G.URL_BASE + url_trovato

                liStyle = xbmcgui.ListItem(cognominomi)
                
                video_info_tag = liStyle.getVideoInfoTag()
                video_info_tag.setTitle(cognominomi)
                
                thumb = ''
                try:
                    thumb_div = dati.find('div', class_='image-bg lozad')
                    if thumb_div and thumb_div.has_attr('data-background-image'):
                        thumb = thumb_div.get('data-background-image')
                except Exception:
                    pass
                
                if thumb:
                    liStyle.setArt({'thumb': thumb})
                
                liStyle.setArt({'fanart': G.FANART_PATH})
                
                add_directory_item_nodup({"mode": G.MODE, "link": bio_link}, liStyle, cognominomi)

        xbmcplugin.addSortMethod(G.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS)
        xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def mostra_biografia():
    plot = "Biografia non disponibile."
    titolo = "Biografia"
    try:
        req_bio = Request(G.LINK, headers={'user-agent': G.HEADERS_SET['user-agent']})
        page_bio = urlopen(req_bio)
        html_bio = BeautifulSoup(page_bio, 'html.parser')

        bio_element = html_bio.find('div', class_='field-name-field-biografia')
        if bio_element:
            plot = ' '.join(bio_element.text.split()).strip()

        titolo_element = html_bio.find('h1') or html_bio.find('div', class_='titolo')
        if titolo_element:
            titolo = titolo_element.text.strip()

    except Exception as e:
        xbmc.log(f'ERRORE ESTRAZIONE BIOGRAFIA da {G.LINK}: {str(e)}', xbmc.LOGWARNING)
        plot = f"Errore durante il caricamento: {str(e)}"

    xbmcgui.Dialog().textviewer(titolo, plot)
    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=False)


def programmi_lettera_tg_meteo():
    # link = nome della property su la7play.it (vedi video_programma_la7play)
    titolo = 'TG LA7'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    link = 'tgla7'
    thumb = os.path.join(G.THUMB_PATH, 'tgla7.jpg')
    liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": G.MODE, "link": link}, liStyle, titolo)

    titolo = 'TG Digital'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    link = G.URL_TGDIGITAL
    thumb = os.path.join(G.THUMB_PATH, 'tgdigital.jpg')
    liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": G.MODE, "link": link}, liStyle, titolo)

    titolo = 'Edicola'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    link = 'omnibus edicola'
    thumb = os.path.join(G.THUMB_PATH, 'omnibusnews.jpg')
    liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": G.MODE, "link": link}, liStyle, titolo)

    titolo = 'Omnibus Meteo'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    link = 'omnibus meteo'
    thumb = os.path.join(G.THUMB_PATH, 'omnibusmeteo.jpg')
    liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": G.MODE, "link": link}, liStyle, titolo)

    titolo = 'Meteo della Sera'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    link = 'meteo della sera'
    thumb = os.path.join(G.THUMB_PATH, 'meteodellasera.jpg')
    liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
    add_directory_item_nodup({"mode": G.MODE, "link": link}, liStyle, titolo)

    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def cerca_la7():
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
            xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=False)
            return
        url = G.URL_CERCA_LA7 + '?' + urllib.parse.urlencode({'query': testo})
        window.setProperty('la7_search_url', url)
    else:
        window.setProperty('la7_search_url', url)

    # su la7play.it i risultati sono nel payload della pagina: {"groups":[{"contentType":..., "hits":[...]}]}
    # la ricerca "tutti" restituisce anche i programmi, quella "video" i primi 20 video (non c'e' paginazione)
    hits = []
    try:
        for tipo in ('', 'video'):
            data = json_object_at(next_flight_data(get_html(url + ('&type=' + tipo if tipo else ''))), '{"groups":')
            for group in (data or {}).get('groups', []):
                if group.get('contentType') == ('video' if tipo else 'property'):
                    hits += group.get('hits') or []
    except Exception as e:
        xbmc.log(f'ERRORE RICERCA LA7: {str(e)}', xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=False)
        return

    # Se non trova risultati: notifica e riapre subito la tastiera
    if not hits:
        xbmcgui.Dialog().notification("Cerca La7", "La ricerca non ha prodotto risultati", xbmcgui.NOTIFICATION_INFO, 3000)
        window.clearProperty('la7_search_url')
        G.LINK = ""
        cerca_la7()
        return

    for hit in hits:
        if not hit.get('url'):
            continue
        titolo = (hit.get('title') or '').strip() or "Senza titolo"
        thumb = hit.get('imageUrl') or ''
        plot = (hit.get('excerpt') or '').strip()

        # Programmi: aprono l'elenco delle puntate (vedi video_programma_la7play)
        if hit.get('contentType') == 'property':
            label = '[B]' + titolo + '[/B]'
            liStyle = xbmcgui.ListItem(label, offscreen=True)
            liStyle.setArt({'thumb': thumb, 'poster': thumb, 'fanart': G.FANART_PATH})
            liStyle.setInfo('video', {'plot': plot})
            add_directory_item_nodup({"mode": "tutti_programmi", "link": titolo.lower()}, liStyle, label)
            continue

        programma = (hit.get('propertyName') or '').strip()
        data_str = ''
        if hit.get('publishedAt'):
            data_str = '.'.join(reversed(hit['publishedAt'][:10].split('-')))
        label = f"[{data_str}] {titolo}" if data_str else titolo
        if programma and programma.lower() not in titolo.lower():
            label += ' - ' + programma

        liStyle = xbmcgui.ListItem(label, offscreen=True)
        video_info_tag = liStyle.getVideoInfoTag()
        video_info_tag.setTitle(label)
        video_info_tag.setPlot(plot or f"{programma} - {data_str}".strip(" -"))
        if hit.get('duration'):
            video_info_tag.setDuration(int(hit['duration']))
        if thumb:
            liStyle.setArt({'thumb': thumb, 'poster': thumb})
        liStyle.setArt({'fanart': G.FANART_PATH})

        add_directory_item_nodup({"mode": "cerca_la7", "play": G.URL_BASE_LA7PLAY + hit['url']}, liStyle, label, folder=False)

    xbmcplugin.setContent(G.PLUGIN_HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


# PAGINA PRINCIPALE
# esempio https://www.la7.it/tgla7 (senza "/rivedila7")
def video_programma_landpage():
    # xbmc.log('LINK GLOBAL_LAND------: '+str(G.LINK),xbmc.LOGINFO)

    # ///// HOME /////
    xbmcplugin.addDirectoryItem(handle=G.PLUGIN_HANDLE, url='', listitem=xbmcgui.ListItem("[B][COLOR blue]" + 'HOME' + "[/COLOR][/B]", offscreen=True))

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
        get_rows_video_landpage_preview(video_iniziale)

    # PUNTATE    
    if (html.findAll(text="puntate")) or (html.findAll(text="Guarda ora")) or (html.findAll(text="Tutti i film")):
        # xbmc.log('TEST------: '+str(html.find('div',class_='home-block__content-inner')),xbmc.LOGINFO)
        video_puntate_1r = html.find('div', class_='home-block__content-inner').select('div[class="item"]')
        video_puntate_2r = html.find('section', class_='home-block home-block--oggi-striscia home-block--fixed').find_all('div', class_='item')
        # xbmc.log('TEST------: '+str(video_puntate_2r),xbmc.LOGINFO)
        if video_puntate_1r:
            get_rows_video_landpage(video_puntate_1r)
        if video_puntate_2r:
            get_rows_video_landpage(video_puntate_2r)

    xbmcplugin.setContent(G.PLUGIN_HANDLE, 'episodes')


# PUNTATE DI UN PROGRAMMA su la7play.it, G.LINK = nome della property (es. "otto e mezzo")
def video_programma_la7play():
    data = gql_query(G.GQL_PUNTATE, {'property': G.LINK, 'page': G.PAGENUM + 1, 'pageSize': 20, 'stagione': None, 'sortDirection': 'DESC'})
    listing = data.get('filteredNodeReplicasListing') or {}
    puntate = listing.get('nodes') or []
    for puntata in puntate:
        if not puntata.get('path'):
            continue
        titolo = (puntata.get('title') or '').strip()
        timestamp = (puntata.get('dataMessaInOnda') or puntata.get('created') or {}).get('timestamp')
        data_puntata = '[I] - (' + time.strftime('%d.%m.%Y %H:%M', time.localtime(timestamp)) + ')[/I]' if timestamp else ''
        video = puntata.get('uploadVideo') or {}
        thumb = (video.get('thumbnailDefault') or {}).get('url') or video.get('cf_thumbnail_url') or ''
        link = G.URL_BASE_LA7PLAY + puntata['path']
        liStyle = xbmcgui.ListItem(titolo + data_puntata, offscreen=True)
        liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
        liStyle.setInfo('video', {'plot': titolo})
        add_directory_item_nodup({"mode": G.MODE, "play": link, "titolo": titolo + data_puntata, "thumb": thumb, "plot": titolo}, liStyle, titolo + data_puntata, folder=False)

    if not puntate and G.PAGENUM == 0:
        xbmcgui.Dialog().ok(G.PLUGIN_NAME, G.LANGUAGE(32005))
    pagenext((listing.get('pageInfo') or {}).get('hasNextPage'))

    xbmcplugin.setContent(G.PLUGIN_HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


# FILM su la7play.it (contenuti NodeEventoSingolo nella pagina)
def video_film_la7play():
    player = next_flight_data(get_html(G.LINK))
    trovati = []
    for m in re.finditer(r'\{"__typename":"NodeEventoSingolo"', player):
        film = json.JSONDecoder().raw_decode(player, m.start())[0]
        if not film.get('path') or film.get('id') in trovati:
            continue
        trovati.append(film.get('id'))
        titolo = (film.get('title') or '').strip()
        video = film.get('uploadVideo') or {}
        thumb = (video.get('cf_thumbnail_cover') or {}).get('url') or ''
        link = G.URL_BASE_LA7PLAY + film['path']
        liStyle = xbmcgui.ListItem(titolo, offscreen=True)
        liStyle.setArt({'thumb': thumb, 'poster': thumb, 'fanart': G.FANART_PATH})
        liStyle.setInfo('video', {'plot': titolo})
        add_directory_item_nodup({"mode": G.MODE, "play": link, "titolo": titolo, "thumb": thumb, "plot": titolo}, liStyle, titolo, folder=False)

    xbmcplugin.addSortMethod(G.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS)
    xbmcplugin.setContent(G.PLUGIN_HANDLE, 'movies')
    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


# PAGINA SECONDARIA
# esempio https://www.la7.it/tgla7/rivedila7 (con "/rivedila7")
def video_programma():
    page = ''
    first = None

    if G.LINK == G.URL_FILM:
        video_film_la7play()
        return
    if not G.LINK.startswith('http'):
        video_programma_la7play()
        return

    #xbmc.log('PAGENUM------: '+str(G.PAGENUM),xbmc.LOGINFO)
    if (G.PAGENUM == 0):
        video_programma_landpage()

    if G.LINK != G.URL_TGDIGITAL:
        #xbmc.log('LINK GLOBAL------: '+str(G.LINK),xbmc.LOGINFO)
        req = Request(G.LINK + "/rivedila7", headers={'user-agent': G.HEADERS_SET['user-agent']})
        try:
            page = urlopen(req)
        except Exception as e:
            e = sys.exc_info()[0]
            xbmc.log('EXCEP URL PAGINA SECONDARIA: ' + str(e), xbmc.LOGINFO)
            if xbmcgui.Dialog().ok(G.PLUGIN_NAME, G.LANGUAGE(32005)):
                xbmcplugin.endOfDirectory(G.PLUGIN_HANDLE, succeeded=False)
                return
        html = BeautifulSoup(page, 'html.parser')

        # ///// SETTIMANA /////
        if G.PAGENUM == 0:
            xbmcplugin.addDirectoryItem(handle=G.PLUGIN_HANDLE, url='', listitem=xbmcgui.ListItem("[B][COLOR blue]" + 'SETTIMANA' + "[/COLOR][/B]", offscreen=True))

            # FIRST VIDEO
            if html.find('div', class_='ultima_puntata'):
                first = html.find('div', class_='ultima_puntata')
            elif html.find('div', class_='contenitoreUltimaReplicaLa7d'):
                first = html.find('div', class_='contenitoreUltimaReplicaLa7d')
            elif html.find('div', class_='contenitoreUltimaReplicaNoLuminosa'):
                first = html.find('div', class_='contenitoreUltimaReplicaNoLuminosa')
            else:
                xbmc.log('NO FIRST VIDEO', xbmc.LOGINFO)
                if xbmcgui.Dialog().ok(G.PLUGIN_NAME, G.LANGUAGE(32005)):
                    xbmcplugin.endOfDirectory(G.PLUGIN_HANDLE, succeeded=False)
                    return
            titolo = first.find('div', class_='title_puntata').text.strip()
            # xbmc.log('FIRST VIDEO----: '+str(titolo),xbmc.LOGINFO)
            first_video(first, titolo, True)

            # WEEK VIDEO
            if html.findAll(text=" LA SETTIMANA"):
                video_settimana = html.find('div', class_='home-block__content-carousel container-vetrina').find_all('div', class_='item')
                # xbmc.log('LA SETTIMANA----: '+str(video_settimana),xbmc.LOGINFO)
                if video_settimana:
                    get_rows_video(video_settimana)
            else:
                xbmc.log('NO WEEK VIDEO', xbmc.LOGINFO)

        # ///// ARCHIVIO /////
        if (html.findAll(text="Puntate Cult")) or (html.findAll(text="Tutti i film")):
            xbmcplugin.addDirectoryItem(handle=G.PLUGIN_HANDLE, url='', listitem=xbmcgui.ListItem("[B][COLOR blue]" + 'ARCHIVIO' + "[/COLOR][/B]", offscreen=True))
            
            if (G.LINK == G.URL_BASE + '/chi-sceglie-la-seconda-casa') or (G.LINK == G.URL_BASE + '/lingrediente-perfetto') or (G.LINK == G.URL_BASE + '/una-giornata-particolare'):
                req2 = Request(G.LINK + "/rivedila7", headers={'user-agent': G.HEADERS_SET['user-agent']})
            else:
                req2 = Request(G.LINK + "/rivedila7/archivio?page=" + str(G.PAGENUM), headers={'user-agent': G.HEADERS_SET['user-agent']})
            page2 = urlopen(req2)
            html2 = BeautifulSoup(page2, 'html.parser')
            video_archivio = html2.find('div', class_='view-content clearfix').find_all('div', class_='views-row')
            if video_archivio:
                get_rows_video(video_archivio)
                page = html2.find('li', class_='pager-next')
                pagenext(page)
        else:
            xbmc.log('NO ARCHIVIO VIDEO', xbmc.LOGINFO)

    # TG DIGITAL
    else:
        req = Request(G.LINK + str(G.PAGENUM), headers={'user-agent': G.HEADERS_SET['user-agent']})
        #xbmc.log('URL TGDIGITAL------: '+str(G.LINK + str(G.PAGENUM)),xbmc.LOGINFO)
        page = urlopen(req)
        html = BeautifulSoup(page, 'html.parser')
        video_tgdigital = html.find('div', class_='article-container').find_all('div', class_='tgla7-news')
        if video_tgdigital:
            get_rows_video_tgdigital(video_tgdigital)
            page = html.find('li', class_='pager-next').find('a')
            pagenext(page)

    xbmcplugin.setContent(G.PLUGIN_HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def video_programma_teche_la7():
    # xbmc.log('LINK------: '+str(G.LINK),xbmc.LOGINFO)
    req = Request(G.LINK + "?page=" + str(G.PAGENUM), headers={'user-agent': G.HEADERS_SET['user-agent']})
    page = urlopen(req)
    html = BeautifulSoup(page, 'html.parser')

    if G.PAGENUM == 0:
        # PREVIEW VIDEO
        video_preview = html.find('div', class_='vetrina-protagonista')
        if video_preview:
            get_rows_video_techela7_preview(video_preview)

    # ARCHIVIO VIDEO    
    if html.find('div', class_='view-content clearfix'):
        video_techela7 = html.find('div', class_='view-grouping-content').find_all('div', class_='list-item')
        if video_techela7:
            get_rows_video_techela7(video_techela7)
            page = html.find('li', class_='pager-next')
            pagenext(page)

    xbmcplugin.setContent(G.PLUGIN_HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def first_video(first, titolo, filtro):
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
        add_directory_item_nodup({"mode": G.MODE, "play": link, "titolo": titolo + data, "thumb": thumb, "plot": plot}, liStyle, titolo + data, folder=False)


def video_list(div, titolo, filtro):
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
        add_directory_item_nodup({"mode": G.MODE, "play": link, "titolo": titolo + data, "thumb": thumb, "plot": plot}, liStyle, titolo + data, folder=False)


def get_rows_video(video):
    for div in video:
        titolo = div.find('div', class_='title').text.strip()
        video_list(div, titolo, True)


def get_rows_video_tgdigital(video):
    for div in video:
        titolo = div.find('h4', class_='news-title').text.strip()
        thumb = div.find('div', class_='news-img').find('a').get('style').split("url(")[1].split(")")[0]
        # Cerca il div della descrizione
        descrizione_div = div.find('div', class_='news-descrizione')
        # Estrai il testo solo se il div esiste, altrimenti usa una stringa vuota
        plot = descrizione_div.text.strip() if descrizione_div else ""
        link = G.URL_BASE_TGDIGITAL + div.find('h4', class_='news-title').find('a').get('href')
        liStyle = xbmcgui.ListItem(titolo, offscreen=True)
        liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
        liStyle.setInfo('video', {'plot': plot})
        add_directory_item_nodup({"mode": G.MODE, "play": link, "titolo": titolo, "thumb": thumb, "plot": plot}, liStyle, folder=False)


def get_rows_video_techela7_preview(video):
    # xbmc.log('TEST-----: '+str(video),xbmc.LOGINFO)
    regex5 = 'poster: "(.*?)"'
    html = str(video)

    titolo = video.find('a', class_='title').text.strip()
    data = '[I] - (' + video.find('span', class_='date-display-single').text.strip() + ')[/I]'
    # xbmc.log('DATA-----: '+str(data),xbmc.LOGINFO)
    if re.findall(regex5, html):
        # xbmc.log('REGEX----------: '+str(re.findall(regex5, html)),xbmc.LOGINFO)
        thumb = 'https:' + re.findall(regex5, html)[0]
    else:
        thumb = ''
    plot = video.find('div', class_='description').text.strip()
    link = G.URL_BASE + video.find('a', class_='title').get('href')
    liStyle = xbmcgui.ListItem(titolo + data, offscreen=True)
    liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
    liStyle.setInfo('video', {'plot': plot})
    add_directory_item_nodup({"mode": G.MODE, "play": link, "titolo": titolo + data, "thumb": thumb, "plot": plot}, liStyle, folder=False)


def get_rows_video_techela7(video):
    for div in video:
        titolo = div.find('div', class_='title').text.strip()
        data = '[I] - (' + div.find('div', class_='data').text.strip() + ')[/I]'
        # xbmc.log('DATA-----: '+str(data),xbmc.LOGINFO)
        thumb = 'https:' + div.find('div', class_='bg-img lozad').get('data-background-image')
        plot = ""
        link = G.URL_BASE + div.a.get('href').strip()
        liStyle = xbmcgui.ListItem(titolo + data, offscreen=True)
        liStyle.setArt({'thumb': thumb, 'fanart': G.FANART_PATH})
        liStyle.setInfo('video', {'plot': plot})
        add_directory_item_nodup({"mode": G.MODE, "play": link, "titolo": titolo + data, "thumb": thumb, "plot": plot}, liStyle, folder=False)


def get_rows_video_landpage_preview(video):
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
    add_directory_item_nodup({"mode": G.MODE, "play": link, "titolo": titolo + data, "thumb": thumb, "plot": plot}, liStyle, titolo + data, folder=False)


def get_rows_video_landpage(video):
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
        add_directory_item_nodup({"mode": G.MODE, "play": link, "titolo": titolo + data, "thumb": thumb, "plot": plot}, liStyle, titolo + data, folder=False)


def pagenext(pagenb):
    if pagenb:
        liStyle = xbmcgui.ListItem('[B]' + G.LANGUAGE(32003) + '[/B]', offscreen=True)
        liStyle.setArt({'fanart': G.FANART_PATH})
        add_directory_item_nodup({"mode": G.MODE, "link": G.LINK, "page": G.PAGENUM + 1}, liStyle)


def run(argv):
    """ Addon entry point """
    G.init_globals(argv)

    if G.PARAMS.get("page", "") == "":
        G.PAGENUM = 0
    else:
        G.PAGENUM = int(G.PARAMS.get("page", ""))

    if G.MODE == "diretta_la7":
        play_dirette(G.URL_LIVE_LA7, True)

    elif G.MODE == "diretta_la7cinema":
        play_dirette(G.URL_LIVE_LA7CINEMA, True)

    elif G.MODE == "diretta_la7eventi":
        play_dirette(G.URL_LIVE_LA7EVENTI, True)

    elif G.MODE == "rivedi_la7":
        if G.PLAY == "":
            if G.GIORNO == "":
                rivedi(G.URL_RIVEDILA7, 'rivedila7.jpg')
            else:
                rivedi_giorno(G.URL_RIVEDILA7)
        else:
            play_video(G.PLAY, False)

    elif G.MODE == "rivedi_la7cinema":
        if G.PLAY == "":
            if G.GIORNO == "":
                rivedi(G.URL_RIVEDILA7CINEMA, 'direttalivela7cinema.jpg')
            else:
                rivedi_giorno(G.URL_RIVEDILA7CINEMA)
        else:
            play_video(G.PLAY, False)

    elif G.MODE == "tg_meteo":
        if G.PLAY == "":
            if G.LINK == "":
                programmi_lettera_tg_meteo()
            else:
                video_programma()
        else:
            play_video(G.PLAY, False)

    elif G.MODE == "tutti_programmi":
        if G.PLAY == "":
            if G.LINK == "":
                programmi_lettera()
            else:
                video_programma()
        else:
            play_video(G.PLAY, False)

    elif G.MODE == "la7_prime":
        if G.PLAY == "":
            if G.LINK == "":
                programmi_la7prime()
            else:
                video_programma()
        else:
            play_video(G.PLAY, False)

    elif G.MODE == "teche_la7":
        if G.PLAY == "":
            if G.LINK == "":
                programmi_lettera_teche_la7()
            else:
                mostra_biografia()
        else:
            play_video(G.PLAY, False)

    elif G.MODE == "cerca_la7":
        if G.PLAY == "":
            cerca_la7()
        else:
            xbmcgui.Window(10000).setProperty('la7_video_in_corso', '1')
            play_video(G.PLAY, False)

    else:
        show_root_menu()
