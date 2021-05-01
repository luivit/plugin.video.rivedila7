import re
import os
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib.request
import urllib.parse
from urllib.request import Request, urlopen
import html5lib
import time
import requests
import inputstreamhelper
from bs4 import BeautifulSoup

from resources.lib.globals import G

# Tutte queste variabili sono da spostare in globals
# Se sono variabili statiche come gli url possono stare all'interno della classe GlobalVariables
# altrimenti vanno all'interno del metodo 'init_globals'

#INIT --
# queste variabili prima erano state definite in modo errato a livello header del file, ma a fine modulo
# inoltre erano (e sono) in conflitto con variabili dei metodi locali
# vanno spostate su globals e riassegnate correttamente nei vari punti del codice
mode = ''
giorno = ''
play = ''
titolo_global = ''
thumb_global = ''
plot_global = ''
link_global = ''
#END --

url_base = "https://www.la7.it"
url_base_la7d = "https://www.la7.it/la7d"
url_live_la7 = "https://www.la7.it/dirette-tv"
url_live_la7d = "https://www.la7.it/live-la7d"
url_tgla7d = "https://tg.la7.it/listing/tgla7d"
url_rivedila7 = "https://www.la7.it/rivedila7/0/la7"
url_rivedila7d = "https://www.la7.it/rivedila7/0/la7d"
url_programmi = "https://www.la7.it/programmi"
url_programmila7d = "https://www.la7.it/programmi-la7d"
url_tutti_programmi = "https://www.la7.it/tutti-i-programmi"
url_teche_la7 = "https://www.la7.it/i-protagonisti"
url_la7_prime = "https://www.la7.it/la7prime"

headers_set = {
    'host_token': 'pat.la7.it',
    'host_license': 'la7.prod.conax.cloud',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36',
    'accept': '*/*',
    'accept-language': 'en,en-US;q=0.9,it;q=0.8',
    'dnt': '1',
    'te': 'trailers',
    'origin': 'https://www.la7.it',
    'referer': 'https://www.la7.it/',
}

pagenum = 0
list_programmi = []
#list_puntate = []
tg_cronache = False
filtro_cronache = 'TG LA7 Cronache'
omnibus_news = False
filtro_omnibus = 'Omnibus News'
fanart_path = os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources', 'fanart.jpg')
thumb_path = os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources', 'images')


def show_root_menu():
    ''' Show the plugin root menu '''
    liStyle = xbmcgui.ListItem('[B]'+G.LANGUAGE(32002)+'[/B]', offscreen=True)
    liStyle.setArt({ 'thumb': os.path.join(thumb_path, 'direttalivela7.jpg'), 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": "diretta_la7"},liStyle, folder=False)
    liStyle = xbmcgui.ListItem('[B]'+G.LANGUAGE(32009)+'[/B]', offscreen=True)
    liStyle.setArt({ 'thumb': os.path.join(thumb_path, 'direttalivela7d.jpg'), 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": "diretta_la7d"},liStyle, folder=False)   
    liStyle = xbmcgui.ListItem('[B]'+G.LANGUAGE(32001)+'[/B]', offscreen=True)
    liStyle.setArt({ 'thumb': os.path.join(thumb_path, 'rivedila7.jpg'), 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": "rivedi_la7"},liStyle)
    liStyle = xbmcgui.ListItem('[B]'+G.LANGUAGE(32004)+'[/B]', offscreen=True)
    liStyle.setArt({ 'thumb': os.path.join(thumb_path, 'rivedila7d.jpg'), 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": "rivedi_la7d"},liStyle)
    liStyle = xbmcgui.ListItem('[B]'+G.LANGUAGE(32010)+'[/B]', offscreen=True)
    liStyle.setArt({ 'thumb': os.path.join(thumb_path, 'la7prime.jpg'), 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": "la7_prime"},liStyle)
    liStyle = xbmcgui.ListItem('[B]'+G.LANGUAGE(32006)+'[/B]', offscreen=True)
    liStyle.setArt({ 'thumb': os.path.join(thumb_path, 'programmila7la7d.jpg'), 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": "tutti_programmi"},liStyle)
    liStyle = xbmcgui.ListItem('[B]'+G.LANGUAGE(32007)+'[/B]', offscreen=True)
    liStyle.setArt({ 'thumb': os.path.join(thumb_path, 'tgmeteo.jpg'), 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": "tg_meteo"},liStyle) 
    liStyle = xbmcgui.ListItem('[B]'+G.LANGUAGE(32008)+'[/B]', offscreen=True)
    liStyle.setArt({ 'thumb': os.path.join(thumb_path, 'techela7.jpg'), 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": "teche_la7"},liStyle)

    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def addDirectoryItem_nodup(parameters, li, title=titolo_global, folder=True):
    #xbmc.log('LIST PUNTATE------: '+str(list_puntate),xbmc.LOGINFO)
    if title in list_programmi:
        xbmc.log('PROGRAMMA DUPLICATO',xbmc.LOGINFO)
    #elif title in list_puntate:
        #xbmc.log('PUNTATA DUPLICATA',xbmc.LOGINFO)        
    else:
        url = sys.argv[0] + '?' + urllib.parse.urlencode(parameters)
        #xbmc.log('LIST------: '+str(url),xbmc.LOGINFO)
        if not folder:
            li.setInfo('video', {})
            li.setProperty('isPlayable', 'true')
        return xbmcplugin.addDirectoryItem(handle=G.PLUGIN_HANDLE, url=url, listitem=li, isFolder=folder)


def play_dirette(url,live):
    if live:
        if url == url_live_la7:
            url_title = url_base
            regex5 = 'emissioneString\s*=\s*"(.*?)"'
        elif url == url_live_la7d:
            url_title = url_base_la7d
            regex5 = 'emissioneStringLa7d\s*=\s*"(.*?)"'
        #xbmc.log('URL TITLE-----: '+str(url_title),xbmc.LOGINFO)
        
        req = Request(url_title,headers={'user-agent': headers_set['user-agent']})
        page=urlopen(req).read()
        html=page.decode()
        #xbmc.log('REGEX5-----: '+str(re.findall(regex5, html)),xbmc.LOGINFO)
        titolo_diretta=re.findall(regex5, html)[0]
        #xbmc.log('TITOLO DIRETTA-----: '+str(titolo_diretta),xbmc.LOGINFO)

    response = requests.get(url, headers={'user-agent': headers_set['user-agent']},verify=False).content.decode()
    try:
        preurl = re.findall('preTokenUrl = "(.+?)"',response)[0]
    except Exception as e:
        e = sys.exc_info()[0]
        xbmc.log('EXCEP PREURL: '+str(e),xbmc.LOGINFO)
        xbmcplugin.endOfDirectory(G.PLUGIN_HANDLE, succeeded=False)
        return
    response=response.replace("\'",'"')
    mpdurl=re.findall('dash.+?"(.+?)"',response,re.DOTALL)[0]
    headersTok = {
        'host': headers_set['host_token'],
        'user-agent': headers_set['user-agent'],
        'accept': headers_set['accept'],
        'accept-language': headers_set['accept-language'],
        'dnt': headers_set['dnt'],
        'te': headers_set['te'],
        'origin': headers_set['origin'],
        'referer': headers_set['referer'],
    }
    response = requests.get(preurl, headers=headersTok,verify=False).json()
    preAuthToken=response['preAuthToken']
    
    headersLic = {
        'host': headers_set['host_license'],
        'user-agent': headers_set['user-agent'],
        'accept': headers_set['accept'],
        'accept-language': headers_set['accept-language'],
        'preAuthorization': preAuthToken,
        'origin': headers_set['origin'],
        'referer': headers_set['referer'],
    }
    preLic= '&'.join(['%s=%s' % (name, value) for (name, value) in headersLic.items()])
    #xbmc.log('LICENSE1------: '+str(preLic),xbmc.LOGINFO)

    tsatmp=str(int(time.time()))
    license_url= G.KEY_WIDEVINE + '?d=%s'%tsatmp
    lic_url='%s|%s|R{SSM}|'%(license_url,preLic)
    #xbmc.log('LICENSE2------: '+str(lic_url),xbmc.LOGINFO)
    is_helper = inputstreamhelper.Helper(G.DRM_PROTOCOL, drm=G.DRM)
    if is_helper.check_inputstream():
        listitem = xbmcgui.ListItem(offscreen=True)
        listitem.setPath(mpdurl)
        if live:
            #listitem.setLabel(titolo_diretta)
            listitem.setInfo('video', {'plot': titolo_diretta, 'title': titolo_diretta})
            listitem.setProperty('inputstream.adaptive.manifest_update_parameter', 'full') #https://github.com/xbmc/inputstream.adaptive/issues/647
        listitem.setProperty("inputstream", is_helper.inputstream_addon)
        listitem.setProperty("inputstream.adaptive.manifest_type", G.DRM_PROTOCOL)
        listitem.setProperty("inputstream.adaptive.license_type", G.DRM)
        listitem.setProperty("inputstream.adaptive.license_key", lic_url)
        listitem.setProperty("inputstream.adaptive.license_flags", "force_secure_decoder") #https://github.com/xbmc/inputstream.adaptive/issues/638
        listitem.setMimeType('application/dash+xml')
        xbmcplugin.setResolvedUrl(G.PLUGIN_HANDLE, True, listitem)
    else:
        xbmcplugin.endOfDirectory(G.PLUGIN_HANDLE, succeeded=False)


def play_video(page_video,live):
    #xbmc.log('PAGE VIDEO-----: '+str(page_video),xbmc.LOGINFO)
    link_video = ''
    #regex1 = 'vS = "(.*?)"'
    regex2 = '/content/(.*?).mp4'
    regex3 = 'm3u8: "(.*?)"'
    #regex4 = '  <iframe src="(.*?)"'

    req = Request(page_video,headers={'user-agent': headers_set['user-agent']})
    page=urlopen(req).read()
    html=page.decode()
    if live:
        if re.findall(regex1, html):  # <<<< VARIABILE INESISTENTE --------------------------------------------- TO FIX
            # xbmc.log('REGEX1-----: '+str(re.findall(regex1, html)),xbmc.LOGINFO)
            link_video = re.findall(regex1, html)[0]
    else:
        if re.findall(regex2, html):
            #xbmc.log('REGEX2-----: '+str(re.findall(regex2, html)),xbmc.LOGINFO)
            link_video = 'https://awsvodpkg.iltrovatore.it/local/hls/,/content/'+re.findall(regex2, html)[0]+'.mp4.urlset/master.m3u8'
            #xbmc.log('LINK2-----: '+str(link_video),xbmc.LOGINFO)
        elif re.findall(regex3, html):
            #xbmc.log('REGEX3-----: '+str(re.findall(regex3, html)),xbmc.LOGINFO)
            link_video = re.findall(regex3, html)[0]
        else:
            #xbmc.log('DECODIFICA DRM',xbmc.LOGINFO)
            play_dirette(page_video, False)
            return
        # elif re.findall(regex4, html):
        #     #xbmc.log('REGEX4-----: '+str(re.findall(regex4, html)),xbmc.LOGINFO)
        #     iframe = re.findall(regex4, html)[0]
        #     req2 = Request(iframe,headers={'user-agent': headers_set['user-agent']})
        #     page2=urlopen(req2)
        #     html2=page2.read()
        #     if re.findall(regex2, html2):
        #         #xbmc.log('REGEX2-B---: '+str(re.findall(regex2, html)),xbmc.LOGINFO)
        #         link_video = str("https:")+re.findall(regex2, html2)[0]

    listitem = xbmcgui.ListItem(titolo_global, offscreen=True)
    listitem.setInfo('video', {'Title': titolo_global})
    if (thumb_global != ""):
        listitem.setArt({ 'thumb': thumb_global})
    listitem.setInfo('video', { 'plot': plot_global })
    if link_video == '':
        xbmc.log('NO VIDEO LINK',xbmc.LOGINFO)
        xbmcgui.Dialog().ok(G.PLUGIN_NAME, G.LANGUAGE(32005))
        xbmcplugin.setResolvedUrl(G.PLUGIN_HANDLE, False, listitem)
        return
    listitem.setProperty('inputstream','inputstream.adaptive')
    listitem.setProperty('inputstream.adaptive.manifest_type','hls')
    listitem.setPath(link_video)
    xbmcplugin.setResolvedUrl(G.PLUGIN_HANDLE, True, listitem)


def rivedi(url, thumb):
    req = Request(url,headers={'user-agent': headers_set['user-agent']})
    page=urlopen(req)
    html=BeautifulSoup(page,'html5lib')
    giorno=html.find('div',class_='block block-system').find_all('div',class_=['item item--menu-guida-tv','item item--menu-guida-tv active'])
    #xbmc.log('GIORNO----------: '+str(giorno),xbmc.LOGINFO)  
    if giorno:
        for div in reversed(giorno):
            dateDay=div.find('div',class_='giorno-numero').text.strip()
            dateMonth=div.find('div',class_='giorno-mese').text.strip()
            dateRowWeek=div.find('div',class_='giorno-text').text.strip()
            a=div.a.get('href').strip()
            liStyle = xbmcgui.ListItem(dateRowWeek+" "+dateDay+" "+dateMonth, offscreen=True)
            liStyle.setArt({ 'thumb': os.path.join(thumb_path, thumb), 'fanart' : fanart_path })
            addDirectoryItem_nodup({"mode": mode,"giorno": a}, liStyle)
        xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def rivedi_giorno():
    req = Request(url_base+giorno,headers={'user-agent': headers_set['user-agent']})
    page=urlopen(req)
    html=BeautifulSoup(page,'html5lib')
    guida_tv=html.find(id="content_guida_tv_rivedi").find_all('div',class_='item item--guida-tv')
    if guida_tv:
        for div in guida_tv:
            orario=div.find('div',class_='orario').contents[0].strip()
            nome=div.find('div',class_='property').text.strip()
            thumb='https:'+div.find('div',class_='bg-img lozad').get('data-background-image')
            plot=div.find('div',class_='occhiello').text.strip()
            if div.a:
                urll = div.a.get('href').strip()
                #xbmc.log('------LINK------: '+str(urll),xbmc.LOGINFO)
                liStyle = xbmcgui.ListItem(orario+" "+nome, offscreen=True)
                liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
                liStyle.setInfo('video', { 'plot': plot })
                liStyle.setProperty('isPlayable', 'true')
                url2 = sys.argv[0] + '?' + urllib.parse.urlencode({"mode": mode,"play": urll,"titolo": nome,"thumb":thumb,"plot":plot})
                xbmcplugin.addDirectoryItem(handle=G.PLUGIN_HANDLE, url=url2, listitem=liStyle, isFolder=False)

    xbmcplugin.setContent(handle, 'episodes')
    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def programmi_lettera():
    req_p = Request(url_programmi,headers={'user-agent': headers_set['user-agent']})
    page_p=urlopen(req_p)
    html_p=BeautifulSoup(page_p,'html5lib') 
    programmi=html_p.find(id='container-programmi-list').find_all('div',class_='list-item')
    #xbmc.log('PROGRAMMI----------: '+str(programmi),xbmc.LOGINFO)
    req_pd = Request(url_programmila7d,headers={'user-agent': headers_set['user-agent']})
    page_pd=urlopen(req_pd)
    html_pd=BeautifulSoup(page_pd,'html5lib') 
    programmila7d=html_pd.find(id='container-programmi-list').find_all('div',class_='list-item')
    req_tp = Request(url_tutti_programmi,headers={'user-agent': headers_set['user-agent']})
    page_tp=urlopen(req_tp)
    html_tp=BeautifulSoup(page_tp,'html5lib') 
    tutti_programmi=html_tp.find_all('div',class_='list-item')

    if programmi or programmila7d or tutti_programmi:
        for dati in programmi:
            if dati.find('div',class_='titolo'):
                titolo=dati.find('div',class_='titolo').text.strip()
                #xbmc.log('TITLE1-----: '+str(titolo),xbmc.LOGINFO)
                liStyle = xbmcgui.ListItem(titolo, offscreen=True)
                url_trovato=dati.a.get('href').strip()
                #xbmc.log('URL--------: '+str(url_trovato),xbmc.LOGINFO)
                if url_trovato !='/meteola7' and url_trovato !='/meteo-della-sera' and url_trovato !='/tgla7' and url_trovato !='/film' and url_trovato !='/film-e-fiction':
                    if url_trovato == '/facciaafaccia':
                        url_trovato='/faccia-a-faccia'
                    if url_trovato == '/il-boss-dei-comici':
                        url_trovato='/boss-dei-comici'
                    if url_trovato == '/lariadestate':
                        url_trovato='/laria-destate'
                    if url_trovato == '/taga-doc':
                        url_trovato='/tagada-doc'
                    link=url_base+url_trovato
                    #xbmc.log('LINK-----: '+str(link),xbmc.LOGINFO)
                    if(len(dati)>0):
                        try:
                            thumb=dati.find('div',class_='image-bg lozad').get('data-background-image')
                        except Exception as e:
                            e = sys.exc_info()[0]
                            xbmc.log('EXCEP THUMB1: '+str(e),xbmc.LOGINFO)
                            thumb = None
                        if thumb:
                            liStyle.setArt({ 'thumb': thumb})
                        else:
                            xbmc.log('NO THUMB1',xbmc.LOGINFO)     
                    liStyle.setArt({ 'fanart' : fanart_path })
                    addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo)
                    if not titolo in list_programmi:
                        list_programmi.append(titolo)

        for dati in programmila7d:
            if dati.find('div',class_='titolo'):
                titolo=dati.find('div',class_='titolo').text.strip()
                #xbmc.log('TITLE1-----: '+str(titolo),xbmc.LOGINFO)
                liStyle = xbmcgui.ListItem(titolo, offscreen=True)
                url_trovato=dati.a.get('href').strip()
                if url_trovato !='/meteola7' and url_trovato !='/meteo-della-sera' and url_trovato !='/tgla7' and url_trovato !='/film' and url_trovato !='/film-e-fiction':
                    if url_trovato == '/facciaafaccia':
                        url_trovato='/faccia-a-faccia'
                    if url_trovato == '/il-boss-dei-comici':
                        url_trovato='/boss-dei-comici'
                    if url_trovato == '/lariadestate':
                        url_trovato='/laria-destate'
                    if url_trovato == '/taga-doc':
                        url_trovato='/tagada-doc'
                    link=url_base+url_trovato
                    #xbmc.log('LINK-----: '+str(link),xbmc.LOGINFO)
                    if(len(dati)>0):
                        try:
                            thumb=dati.find('div',class_='image-bg lozad').get('data-background-image')
                        except Exception as e:
                            e = sys.exc_info()[0]
                            xbmc.log('EXCEP THUMB2: '+str(e),xbmc.LOGINFO)
                            thumb = None
                        if thumb:
                            liStyle.setArt({ 'thumb': thumb})
                        else:
                            xbmc.log('NO THUMB2',xbmc.LOGINFO)     
                    liStyle.setArt({ 'fanart' : fanart_path })
                    addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo)
                    if not titolo in list_programmi:
                        list_programmi.append(titolo)


        for dati in tutti_programmi:
            if dati.find('div',class_='titolo'):
                titolo=dati.find('div',class_='titolo').text.strip()
                #xbmc.log('TITLE2: '+str(titolo),xbmc.LOGINFO)
                liStyle = xbmcgui.ListItem(titolo, offscreen=True)
                url_trovato=dati.a.get('href').strip()
                #xbmc.log('URL TROVATO-----: '+str(url_trovato),xbmc.LOGINFO)
                if url_trovato !='/meteola7' and url_trovato !='/meteo-della-sera' and url_trovato !='/tgla7' and url_trovato !='/film' and url_trovato !='/film-e-fiction':
                    if url_trovato == '/facciaafaccia':
                        url_trovato='/faccia-a-faccia'
                    if url_trovato == '/il-boss-dei-comici':
                        url_trovato='/boss-dei-comici'
                    if url_trovato == '/lariadestate':
                        url_trovato='/laria-destate'
                    if url_trovato == '/taga-doc':
                        url_trovato='/tagada-doc'
                    link=url_base+url_trovato
                    #xbmc.log('LINK-----: '+str(link),xbmc.LOGINFO)
                    if(len(dati)>0):
                        try:
                            thumb=dati.find('div',class_='image-bg lozad').get('data-background-image')
                        except Exception as e:
                            e = sys.exc_info()[0]
                            xbmc.log('EXCEP THUMB3: '+str(e),xbmc.LOGINFO)
                            thumb = None
                        if thumb:
                            liStyle.setArt({ 'thumb': thumb})
                        else:
                            xbmc.log('NO THUMB3',xbmc.LOGINFO)     
                    liStyle.setArt({ 'fanart' : fanart_path })
                    addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo)

        #Prog aggiunti manualmente
        programmi = {
            'LA MALA EDUCAXXXION 2': {
                'url': '/la-mala-educaxxxion',
                'img': 'https://kdam.iltrovatore.it/p/103/sp/10300/thumbnail/entry_id/0_j0z82ps2/version/100001/type/5/width/600/height/360/quality/100/name/0_j0z82ps2.jpg'
                },           
            'NON CLASSIFICATI': {
                'url': '/non-classificati',
                'img': '',
                },
        }
        for programma, program_info in programmi.items():
            titolo = programma
            liStyle = xbmcgui.ListItem(titolo, offscreen=True)
            url_trovato = program_info['url']
            link = url_base + url_trovato
            thumb = program_info['img']
            liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
            addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo)

        xbmcplugin.addSortMethod(G.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS)
        xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def programmi_la7prime():
    titolo = 'LA7 Prime'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    url_trovato = '/la7prime'
    link = url_base + url_trovato
    thumb = os.path.join(thumb_path, 'la7prime.jpg')
    liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo)

    titolo = 'Film'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    url_trovato = '/film'
    link = url_base + url_trovato
    thumb = os.path.join(thumb_path, 'film.jpg')
    liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo)

    titolo = 'Film e Fiction'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    url_trovato = '/film-e-fiction'
    link = url_base + url_trovato
    thumb = os.path.join(thumb_path, 'filmfiction.jpg')
    liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo)

    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def programmi_lettera_teche_la7():
    req_teche = Request(url_teche_la7,headers={'user-agent': headers_set['user-agent']})
    page_teche=urlopen(req_teche)
    html_teche=BeautifulSoup(page_teche,'html5lib') 
    teche_la7=html_teche.find_all('div',class_='list-item')

    if teche_la7:
        for dati in teche_la7:
            if dati.find('div',class_='titolo'):
                nomicognomi = dati.find('div',class_='titolo').text.strip()
                cognominomi = " ".join( reversed(nomicognomi.split(" ")))              
                liStyle = xbmcgui.ListItem(cognominomi, offscreen=True)
                url_trovato=dati.a.get('href').strip()
                link=url_base+url_trovato
                #xbmc.log('LINK-----: '+str(link),xbmc.LOGINFO)
                if(len(dati)>0):
                    try:
                        thumb='https:'+dati.find('div',class_='image-bg lozad').get('data-background-image')
                    except Exception as e:
                        e = sys.exc_info()[0]
                        xbmc.log('EXCEP THUMB4: '+str(e),xbmc.LOGINFO)
                        thumb = None
                    if thumb:
                        liStyle.setArt({ 'thumb': thumb})
                    else:
                        xbmc.log('NO THUMB4',xbmc.LOGINFO)     
                liStyle.setArt({ 'fanart' : fanart_path })
                addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, cognominomi)

        xbmcplugin.addSortMethod(G.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS)
        xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)
    

def programmi_lettera_tg_meteo():
    titolo = 'TG La7'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    url_trovato = '/tgla7'
    link = url_base + url_trovato
    thumb = os.path.join(thumb_path, 'tgla7.jpg')
    liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo)
    
    titolo = 'TG La7d'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    link = url_tgla7d
    thumb = os.path.join(thumb_path, 'tgla7d.jpg')
    liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo)

    # (rimosso temporaneamente per mancanza di contenuti)
    # titolo = 'TG Cronache'
    # liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    # link = 'flag_tg_cronache'
    # thumb = os.path.join(thumb_path, 'tgcronache.jpg')
    # liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
    # addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo)
    
    titolo = 'Omnibus News'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    link = 'flag_omnibus_news'
    thumb = os.path.join(thumb_path, 'omnibusnews.jpg')
    liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo) 

    titolo = 'Meteo La7'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    url_trovato = '/meteola7'
    link = url_base+url_trovato
    thumb = os.path.join(thumb_path, 'meteola7.jpg')
    liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo)          

    titolo = 'Meteo della Sera'
    liStyle = xbmcgui.ListItem(titolo, offscreen=True)
    url_trovato = '/meteo-della-sera'
    link = url_base+url_trovato
    thumb = os.path.join(thumb_path, 'meteodellasera.jpg')
    liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
    addDirectoryItem_nodup({"mode": mode,"link": link}, liStyle, titolo)  

    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def video_programma():
    global link_global
    global tg_cronache
    global omnibus_news
    #xbmc.log('LINK GLOBAL------: '+str(link_global),xbmc.LOGINFO)
    
    if link_global == 'flag_tg_cronache':
        tg_cronache = True
        link_global = url_base+'/tgla7'
    
    if link_global == 'flag_omnibus_news':
        omnibus_news = True
        link_global = url_base+'/omnibus'

    if (pagenum == 0) and (link_global != url_base+'/film'):
        video_programma_landpage()

    if link_global != url_tgla7d:
        req = Request(link_global+"/rivedila7",headers={'user-agent': headers_set['user-agent']})
        try:
            page=urlopen(req)
        except Exception as e:
            e = sys.exc_info()[0]
            xbmc.log('EXCEP URL: '+str(e),xbmc.LOGINFO)
            if xbmcgui.Dialog().ok(G.PLUGIN_NAME, G.LANGUAGE(32005)):
                exit()
        html=BeautifulSoup(page,'html5lib')

        if pagenum == 0:
            xbmcplugin.addDirectoryItem(handle=G.PLUGIN_HANDLE, url='', listitem=xbmcgui.ListItem("[B][COLOR blue]"+'SETTIMANA'+"[/COLOR][/B]", offscreen=True))
            # FIRST VIDEO
            if html.find('div',class_='ultima_puntata'):
                first = html.find('div',class_='ultima_puntata')
            elif html.find('div',class_='contenitoreUltimaReplicaLa7d'):
                first = html.find('div',class_='contenitoreUltimaReplicaLa7d')
            elif html.find('div',class_='contenitoreUltimaReplicaNoLuminosa'):
                first = html.find('div',class_='contenitoreUltimaReplicaNoLuminosa')
            else:
                xbmc.log('NO FIRST VIDEO',xbmc.LOGINFO)
                if xbmcgui.Dialog().ok(G.PLUGIN_NAME, G.LANGUAGE(32005)):
                    exit()
            titolo = first.find('div',class_='title_puntata').text.strip()
            
            if tg_cronache == True:
                first_video(first, titolo, titolo.find(filtro_cronache) != -1)
            elif omnibus_news == True:
                first_video(first, titolo, titolo.find(filtro_omnibus) != -1)
            elif link_global == url_base+'/tgla7':
                first_video(first, titolo, titolo.find(filtro_cronache) == -1)
            elif link_global == url_base+'/omnibus':
                first_video(first, titolo, titolo.find(filtro_omnibus) == -1)
            else:
                first_video(first, titolo, True)
            #xbmc.log('FIRST VIDEO----: '+str(titolo),xbmc.LOGINFO)

            # WEEK VIDEO
            if html.findAll(text=" LA SETTIMANA"):
                video_settimana = html.find('div',class_='home-block__content-carousel container-vetrina').find_all('div',class_='item')
                #xbmc.log('LA SETTIMANA----: '+str(video_settimana),xbmc.LOGINFO)
                if video_settimana:
                    get_rows_video(video_settimana)
            else:
                xbmc.log('NO WEEK VIDEO',xbmc.LOGINFO)

            if html.findAll(text="Puntate Cult"):
                xbmcplugin.addDirectoryItem(handle=G.PLUGIN_HANDLE, url='', listitem=xbmcgui.ListItem("[B][COLOR blue]"+'ARCHIVIO'+"[/COLOR][/B]", offscreen=True))

        # CULT VIDEO
        if html.findAll(text="Puntate Cult"):
            if (link_global == url_base+'/chi-sceglie-la-seconda-casa') or (link_global == url_base+'/lingrediente-perfetto'):
                req2 = Request(link_global+"/rivedila7",headers={'user-agent': headers_set['user-agent']})
            else:
                req2 = Request(link_global+"/rivedila7/archivio?page="+str(pagenum),headers={'user-agent': headers_set['user-agent']})
            page2 = urlopen(req2)
            html2 = BeautifulSoup(page2,'html5lib')
            video_archivio = html2.find('div',class_='view-content clearfix').find_all('div',class_='views-row')
            if video_archivio:
                get_rows_video(video_archivio)

                if not omnibus_news:
                    page=html2.find('li',class_='pager-next')
                    pagenext(page)
    #Tg La7d
    else:
        req = Request(link_global+"?page="+str(pagenum),headers={'user-agent': headers_set['user-agent']})
        page = urlopen(req)
        html=BeautifulSoup(page,'html5lib')
        video_tgla7d = html.find('div',class_='tgla7-category').find_all('article',class_='tgla7-new clearfix')
        if video_tgla7d:
            get_rows_video_tgla7d(video_tgla7d)
            page=html.find('li',class_='next')
            pagenext(page)
            
    xbmcplugin.setContent(G.PLUGIN_HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)
    
    
def video_programma_teche_la7():
    global link_global

    #xbmc.log('LINK------: '+str(link_global),xbmc.LOGINFO)
    req = Request(link_global+"?page="+str(pagenum),headers={'user-agent': headers_set['user-agent']})
    page = urlopen(req)
    html=BeautifulSoup(page,'html5lib')
    
    if pagenum == 0:
        # PREVIEW VIDEO
        video_preview = html.find('div',class_='vetrina-protagonista')
        if video_preview:
            get_rows_video_techela7_preview(video_preview)

    # ARCHIVIO VIDEO    
    if html.find('div',class_='view-content clearfix'):
        video_techela7 = html.find('div',class_='view-grouping-content').find_all('div',class_='list-item')
        if video_techela7:
            get_rows_video_techela7(video_techela7)
            page=html.find('li',class_='pager-next')
            pagenext(page)
            
    xbmcplugin.setContent(G.PLUGIN_HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def first_video(first, titolo, filtro):
    if filtro:
        thumblink=first.find('div',class_='holder-bg lozad').get('data-background-image')
        if thumblink.startswith('//'):
            thumb='https:'+thumblink
        else:
            thumb=thumblink
        #xbmc.log('THUMB 1------: '+str(thumb),xbmc.LOGINFO)
        data_orig = first.find('div',class_='scritta_ultima').text.strip()
        data = '[I] - ('+data_orig.replace('/', '.')+')[/I]'
        try:
            plot=first.find('div',class_='occhiello').text.strip()
        except Exception as e:
            e = sys.exc_info()[0]
            xbmc.log('EXCEP PLOT1: '+str(e),xbmc.LOGINFO)
            plot=""
        link=url_base+first.find('a').get('href')
        liStyle = xbmcgui.ListItem(titolo+data, offscreen=True)
        liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
        liStyle.setInfo('video', { 'plot': plot })
        addDirectoryItem_nodup({"mode": mode,"play": link,"titolo": titolo+data,"thumb":thumb,"plot":plot}, liStyle, titolo+data, folder=False)
        #if not titolo+data in list_puntate:
            #list_puntate.append(titolo+data)

def video_list(div, titolo, filtro):
    if filtro:
        thumblink=div.find('div',class_='bg-img lozad').get('data-background-image')
        if thumblink.startswith('//'):
            thumb='https:'+thumblink
        else:
            thumb=thumblink
        #xbmc.log('THUMB 2------: '+str(thumb),xbmc.LOGINFO)
        #subdata=div.find('a').get('href')
        #data='[I] - ('+subdata[24:34]+')[/I]'
        try:
            data_orig = div.find('div',class_='data').text.strip()
            data = '[I] - ('+data_orig.replace('/', '.')+')[/I]'
        except Exception as e:
            e = sys.exc_info()[0]
            xbmc.log('EXCEP DATA_1: '+str(e),xbmc.LOGINFO)
            data=""
        plot=''
        link=url_base+div.find('a').get('href')
        #xbmc.log('TEST------: '+str(data),xbmc.LOGINFO)
        liStyle = xbmcgui.ListItem(titolo+data, offscreen=True)
        liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
        liStyle.setInfo('video', { 'plot': plot })
        addDirectoryItem_nodup({"mode": mode,"play": link,"titolo": titolo+data,"thumb":thumb,"plot":plot}, liStyle, titolo+data, folder=False)
        #if not titolo+data in list_puntate:
            #list_puntate.append(titolo+data)

def get_rows_video(video):
    for div in video:
        titolo=div.find('div',class_='title').text.strip()
        #xbmc.log('TITOLO: '+str(titolo.find(filtro_cronache)),xbmc.LOGINFO)
        if tg_cronache == True:
            video_list(div, titolo, titolo.find(filtro_cronache) != -1)
        elif omnibus_news == True:
            video_list(div, titolo, titolo.find(filtro_omnibus) != -1)
        elif link_global == url_base+'/tgla7':
            video_list(div, titolo, titolo.find(filtro_cronache) == -1)
        elif link_global == url_base+'/omnibus':
            video_list(div, titolo, titolo.find(filtro_omnibus) == -1)
        else:
            video_list(div, titolo, True)


def get_rows_video_tgla7d(video):
    for div in video:
        titolo=div.find('div',class_='tgla7-condividi').get('data-title').strip()
        thumb_link=div.find('div',class_='tgla7-img').get('style')
        thumb = thumb_link[22:-1]
        try:
            plot=div.find('div',class_='tgla7-descrizione').text.strip()
        except Exception as e:
            e = sys.exc_info()[0]
            xbmc.log('EXCEP PLOT_TGLA7d: '+str(e),xbmc.LOGINFO)
            plot=""
        link=div.find('div',class_='tgla7-condividi').get('data-share')
        liStyle = xbmcgui.ListItem(titolo, offscreen=True)
        liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
        liStyle.setInfo('video', { 'plot': plot })
        addDirectoryItem_nodup({"mode": mode,"play": link,"titolo": titolo,"thumb":thumb,"plot":plot}, liStyle, folder=False)              


def get_rows_video_techela7_preview(video):
    #xbmc.log('TEST-----: '+str(video),xbmc.LOGINFO)
    regex5 = 'poster: "(.*?)"'
    html=str(video)
        
    titolo=video.find('a',class_='title').text.strip()
    data='[I] - ('+video.find('span',class_='date-display-single').text.strip()+')[/I]'
    #xbmc.log('DATA-----: '+str(data),xbmc.LOGINFO)
    if re.findall(regex5, html):
        #xbmc.log('REGEX----------: '+str(re.findall(regex5, html)),xbmc.LOGINFO)
        thumb = 'https:'+re.findall(regex5, html)[0]
    else:
        thumb=''
    plot=video.find('div',class_='description').text.strip()
    link=url_base+video.find('a',class_='title').get('href')
    liStyle = xbmcgui.ListItem(titolo+data, offscreen=True)
    liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
    liStyle.setInfo('video', { 'plot': plot })
    addDirectoryItem_nodup({"mode": mode,"play": link,"titolo": titolo+data,"thumb":thumb,"plot":plot}, liStyle, folder=False)


def get_rows_video_techela7(video):
    for div in video:
        titolo=div.find('div',class_='title').text.strip()
        data='[I] - ('+div.find('div',class_='data').text.strip()+')[/I]'
        #xbmc.log('DATA-----: '+str(data),xbmc.LOGINFO)
        thumb='https:'+div.find('div',class_='bg-img lozad').get('data-background-image')
        plot=""
        link=url_base+div.a.get('href').strip()
        liStyle = xbmcgui.ListItem(titolo+data, offscreen=True)
        liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
        liStyle.setInfo('video', { 'plot': plot })
        addDirectoryItem_nodup({"mode": mode,"play": link,"titolo": titolo+data,"thumb":thumb,"plot":plot}, liStyle, folder=False)


def video_programma_landpage():
    global link_global
    #xbmc.log('LINK GLOBAL_LAND------: '+str(link_global),xbmc.LOGINFO)
    xbmcplugin.addDirectoryItem(handle=G.PLUGIN_HANDLE, url='', listitem=xbmcgui.ListItem("[B][COLOR blue]"+'HOME'+"[/COLOR][/B]", offscreen=True))

    if link_global == url_base+'/faccia-a-faccia':
        link_landpage=url_base+'/facciaafaccia'
        req = Request(link_landpage,headers={'user-agent': headers_set['user-agent']})
    elif link_global == url_base+'/boss-dei-comici':
        link_landpage=url_base+'/il-boss-dei-comici'
        req = Request(link_landpage,headers={'user-agent': headers_set['user-agent']})
    elif link_global == url_base+'/laria-destate':
        link_landpage=url_base+'/lariadestate'
        req = Request(link_landpage,headers={'user-agent': headers_set['user-agent']})
    elif link_global == url_base+'/tagada-doc':
        link_landpage=url_base+'/taga-doc'
        req = Request(link_landpage,headers={'user-agent': headers_set['user-agent']})
    else:
        req = Request(link_global,headers={'user-agent': headers_set['user-agent']})
    page = urlopen(req)
    html=BeautifulSoup(page,'html5lib')
    
    # FIRT VIDEO
    first_video = html.find('div',class_='ultima_puntata')
    if first_video:
        get_rows_video_landpage_preview(first_video)

    # PUNTATE    
    if (html.findAll(text="puntate")) or (html.findAll(text="Guarda ora")):
        #xbmc.log('TEST------: '+str(html.find('div',class_='home-block__content-inner')),xbmc.LOGINFO)
        video_puntate_1r = html.find('div',class_='home-block__content-inner').select('div[class="item"]')
        video_puntate_2r = html.find('section',class_='home-block home-block--oggi-striscia home-block--fixed').find_all('div',class_='item')
        #xbmc.log('TEST------: '+str(video_puntate_2r),xbmc.LOGINFO)
        if video_puntate_1r:
            get_rows_video_landpage(video_puntate_1r)
        if video_puntate_2r:
            get_rows_video_landpage(video_puntate_2r)
            
    xbmcplugin.setContent(G.PLUGIN_HANDLE, 'episodes')
    #xbmcplugin.endOfDirectory(handle=G.PLUGIN_HANDLE, succeeded=True)


def get_rows_video_landpage_preview(video):
    #xbmc.log('TEST-----: '+str(video),xbmc.LOGINFO)
    titolo = video.find('div',class_='title_puntata').text.strip()
    data='[I] - ('+video.find('div',class_='scritta_ultima').text.strip()+')[/I]'
    thumblink=video.find('div',class_='holder-bg lozad').get('data-background-image')
    if thumblink.startswith('//'):
        thumb='https:'+thumblink
    else:
        thumb=thumblink
    plot=video.find('div',class_='occhiello').text.strip()
    link=url_base+video.find('a').get('href')
    liStyle = xbmcgui.ListItem(titolo+data, offscreen=True)
    liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
    liStyle.setInfo('video', { 'plot': plot })
    addDirectoryItem_nodup({"mode": mode,"play": link,"titolo": titolo+data,"thumb":thumb,"plot":plot}, liStyle, titolo+data, folder=False)
    #if not titolo+data in list_puntate:
        #list_puntate.append(titolo+data)


def get_rows_video_landpage(video):
    #xbmc.log('VIDEO-----: '+str(video),xbmc.LOGINFO)
    for div in video:
        titolo=div.find('div',class_='occhiello').text.strip()
        #xbmc.log('TITOLO-----: '+str(titolo),xbmc.LOGINFO)
        data='[I] - ('+div.find('div',class_='data').text.strip()+')[/I]'
        thumblink=div.find('div',class_='bg-img lozad').get('data-background-image')
        if thumblink.startswith('//'):
            thumb='https:'+thumblink
        else:
            thumb=thumblink
        plot=""
        link=url_base+div.a.get('href').strip()
        liStyle = xbmcgui.ListItem(titolo+data, offscreen=True)
        liStyle.setArt({ 'thumb': thumb, 'fanart' : fanart_path })
        liStyle.setInfo('video', { 'plot': plot })
        addDirectoryItem_nodup({"mode": mode,"play": link,"titolo": titolo+data,"thumb":thumb,"plot":plot}, liStyle, titolo+data, folder=False)
        #if not titolo+data in list_puntate:
            #list_puntate.append(titolo+data)


def pagenext(pagenb):
    if pagenb:
        liStyle = xbmcgui.ListItem('[B]'+G.LANGUAGE(32003)+'[/B]', offscreen=True)
        liStyle.setArt({ 'fanart' : fanart_path })
        addDirectoryItem_nodup({"mode": mode,"link":link_global,"page":pagenum+1}, liStyle)


def run(argv):
    """Addon entry point"""
    # Initialize globals right away to avoid stale values from the last addon invocation.
    # Otherwise Kodi's reuseLanguageInvoker will cause some really quirky behavior!
    # PR: https://github.com/xbmc/xbmc/pull/13814
    G.init_globals(argv)

    mode = str(G.PARAMS.get("mode", ""))
    giorno = str(G.PARAMS.get("giorno", ""))
    play = str(G.PARAMS.get("play", ""))
    titolo_global = str(G.PARAMS.get("titolo", ""))
    thumb_global = str(G.PARAMS.get("thumb", ""))
    plot_global = str(G.PARAMS.get("plot", ""))
    link_global = str(G.PARAMS.get("link", ""))

    if G.PARAMS.get("page", "") == "":
        pagenum = 0
    else:
        pagenum = int(G.PARAMS.get("page", ""))

    if mode=="diretta_la7":
        play_dirette(url_live_la7,True)

    elif mode=="diretta_la7d":
        play_dirette(url_live_la7d,True)

    elif mode=="rivedi_la7":
        if play=="":
            if giorno=="":
                rivedi(url_rivedila7, 'rivedila7.jpg')
            else:
                rivedi_giorno()
        else:
            play_video(play,False)

    elif mode=="rivedi_la7d":
        if play=="":
            if giorno=="":
                rivedi(url_rivedila7d, 'rivedila7d.jpg')
            else:
                rivedi_giorno()
        else:
            play_video(play,False)

    elif mode=="la7_prime":
        if play=="":
            if link_global=="":
                programmi_la7prime()
            else:
                video_programma()
        else:
            play_video(play,False)

    elif mode=="tutti_programmi":
        if play=="":
            if link_global=="":
                programmi_lettera()
            else:
                video_programma()
        else:
            play_video(play,False)

    elif mode=="tg_meteo":
        if play=="":
            if link_global=="":
                programmi_lettera_tg_meteo()
            else:
                video_programma()
        else:
            play_video(play,False)

    elif mode=="teche_la7":
        if play=="":
            if link_global=="":
                programmi_lettera_teche_la7()
            else:
                video_programma_teche_la7()
        else:
            play_video(play,False)

    else:
        show_root_menu()
