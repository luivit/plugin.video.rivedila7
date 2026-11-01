"""One episode page becomes one stream: clear HLS when the page publishes it,
a DRM session when it does not.
"""

import re

from urllib.request import Request, urlopen

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib.globals import G
from resources.lib.kodi import dialogs
from resources.lib.playback import drm


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
    if live:
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
            drm.play_dirette(page_video, False)
            return

    listitem = xbmcgui.ListItem(G.TITOLO, offscreen=True)
    listitem.setInfo('video', {'Title': G.TITOLO})
    if G.THUMB != "":
        listitem.setArt({'thumb': G.THUMB})
    listitem.setInfo('video', {'plot': G.PLOT})
    if link_video == '':
        xbmc.log('RivediLA7: NO VIDEO LINK', xbmc.LOGINFO)
        dialogs.show(G.LANGUAGE(32005))
        xbmcplugin.setResolvedUrl(G.PLUGIN_HANDLE, False, listitem)
        return
    if '.m3u8' in link_video:
        listitem.setProperty('inputstream', 'inputstream.adaptive')
        listitem.setProperty('inputstream.adaptive.manifest_type', 'hls')

    listitem.setPath(link_video)
    xbmcplugin.setResolvedUrl(G.PLUGIN_HANDLE, True, listitem)
