"""The add-on entry point: Kodi's arguments become one call into the add-on.

Nothing is listed, parsed or played here. This module owns exactly two things:
the parameters Kodi passes on every invocation (they end up in the globals), and
the single place where an unexpected AddonError is turned into one dialog.
"""

from resources.lib.globals import G
from resources.lib.kodi.dialogs import AddonError, report
from resources.lib.la7play import catalog, program, search
from resources.lib.playback import drm, streams


def dispatch():
    """Route the mode Kodi asked for to the module that implements it."""
    if G.MODE == "diretta_la7":
        drm.play_dirette(G.URL_LIVE_LA7, True)

    elif G.MODE == "diretta_la7cinema":
        drm.play_dirette(G.URL_LIVE_LA7CINEMA, True)

    elif G.MODE == "rivedi_la7":
        if G.PLAY == "":
            if G.GIORNO == "":
                program.rivedi(G.URL_RIVEDILA7, 'rivedila7.jpg')
            else:
                program.rivedi_giorno()
        else:
            streams.play_video(G.PLAY, False)

    elif G.MODE == "rivedi_la7cinema":
        if G.PLAY == "":
            if G.GIORNO == "":
                program.rivedi(G.URL_RIVEDILA7CINEMA, 'direttalivela7cinema.jpg')
            else:
                program.rivedi_giorno()
        else:
            streams.play_video(G.PLAY, False)

    elif G.MODE == "tutti_programmi":
        if G.PLAY == "":
            if G.LINK == "":
                catalog.programmi_lettera()
            else:
                program.video_programma()
        else:
            streams.play_video(G.PLAY, False)

    elif G.MODE == "la7_prime":
        if G.PLAY == "":
            if G.LINK == "":
                catalog.programmi_la7prime()
            else:
                program.video_programma()
        else:
            streams.play_video(G.PLAY, False)

    elif G.MODE == "cerca_la7":
        if G.PLAY == "":
            search.cerca_la7()
        else:
            search.play_result(G.PLAY)

    else:
        catalog.show_root_menu()


def run(argv):
    """ Addon entry point """
    G.init_globals(argv)

    if G.PARAMS.get("page", "") == "":
        G.PAGENUM = 0
    else:
        G.PAGENUM = int(G.PARAMS.get("page", ""))

    try:
        dispatch()
    except AddonError as error:
        report(error)
