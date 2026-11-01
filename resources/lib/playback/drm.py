"""DASH + Widevine: the token header, the license request, the play item.

This is the one path that cannot be verified on a Linux Kodi (no Widevine), so it
stays as small as it can: build the license URL, ask inputstream.adaptive to
play the manifest, and say so when it cannot.
"""

import re
import sys
import time

from urllib.request import Request, urlopen

import inputstreamhelper
import requests

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib.globals import G
from resources.lib.kodi.directory import Directory


def play_dirette(url, live):
    xbmc.log('PLAY DIRETTE', xbmc.LOGINFO)
    #xbmc.log('PAGE DIRETTE-----: '+str(url),xbmc.LOGINFO)

    url_title = ''
    regex5 = ''
    titolo_diretta = ''

    if live:
        if url == G.URL_LIVE_LA7:
            url_title = G.URL_BASE
            regex5 = r'var orainonda = ".*\t(.*?)"'
        elif url == G.URL_LIVE_LA7CINEMA:
            url_title = G.URL_BASE
            regex5 = r'var orainondala7d = ".*\t(.*?)"'
        #xbmc.log('URL TITLE-----: '+str(url_title),xbmc.LOGINFO)

        req = Request(url_title, headers={'user-agent': G.HEADERS_SET['user-agent']})
        page = urlopen(req).read()
        html = page.decode(errors='replace')
        #xbmc.log('REGEX5-----: '+str(re.findall(regex5, html)),xbmc.LOGINFO)

        titolo_diretta = re.findall(regex5, html)[0]
        #xbmc.log('TITOLO DIRETTA-----: '+str(titolo_diretta),xbmc.LOGINFO)

    response = requests.get(url, headers={'user-agent': G.HEADERS_SET['user-agent']}, verify=False).content.decode()
    try:
        preurl = re.findall('preTokenUrl = "(.+?)"', response)[0]
    except Exception as e:
        e = sys.exc_info()[0]
        xbmc.log('EXCEP PREURL: ' + str(e), xbmc.LOGINFO)
        Directory().fail()
        return
    response = response.replace("\'", '"')

    mpdurl = re.findall('dash.+?"(.+?)"', response, re.DOTALL)[0]
    #xbmc.log('URL VIDEO MPD-----: '+str(mpdurl),xbmc.LOGINFO)

    headers_tok = {
        'host': G.HEADERS_SET['host_token'],
        'user-agent': G.HEADERS_SET['user-agent'],
        'accept': G.HEADERS_SET['accept'],
        'accept-language': G.HEADERS_SET['accept-language'],
        'dnt': G.HEADERS_SET['dnt'],
        'te': G.HEADERS_SET['te'],
        'origin': G.HEADERS_SET['origin'],
        'referer': G.HEADERS_SET['referer'],
    }
    response = requests.get(preurl, headers=headers_tok, verify=False).json()
    pre_auth_token = response['preAuthToken']

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
        if live:
            # listitem.setLabel(titolo_diretta)
            listitem.setInfo('video', {'plot': titolo_diretta, 'title': titolo_diretta})
        listitem.setProperty("inputstream", is_helper.inputstream_addon)
        listitem.setProperty("inputstream.adaptive.manifest_type", G.DRM_PROTOCOL)
        listitem.setProperty("inputstream.adaptive.license_type", G.DRM)
        listitem.setProperty("inputstream.adaptive.license_key", lic_url)
        listitem.setMimeType('application/dash+xml')
        xbmcplugin.setResolvedUrl(G.PLUGIN_HANDLE, True, listitem)
    else:
        Directory().fail()
