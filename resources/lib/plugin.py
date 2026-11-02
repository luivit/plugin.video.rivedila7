"""The add-on entry point: Kodi's arguments become one call into the add-on.

Nothing is listed, parsed or played here. This module owns exactly three things:
the parameters Kodi passes on every invocation (they end up in the globals), the
table that says which function serves which mode, and the single place where a
failure becomes one log line and one dialog.
"""

from resources.lib.globals import G
from resources.lib.kodi.dialogs import AddonError, report
from resources.lib.la7play import catalog, program, search
from resources.lib.playback import drm, streams


def diretta_la7():
    """Live: two channels, two fixed manifests."""
    drm.play_dirette(G.URL_LIVE_LA7, True)


def diretta_la7cinema():
    """Live: the cinema channel."""
    drm.play_dirette(G.URL_LIVE_LA7CINEMA, True)


def film():
    """The films the site publishes: the section, or one film of it."""
    if G.PLAY:
        streams.play_video(G.PLAY, False)
    else:
        catalog.film()


def documentari():
    """The documentaries the site publishes: the section, or one of them."""
    if G.PLAY:
        streams.play_video(G.PLAY, False)
    else:
        catalog.documentari()


def rivedi_la7():
    """LA7 replays: the days of its guide, one day of it, or one episode."""
    _replay('rivedila7.jpg')


def rivedi_la7cinema():
    """LA7 Cinema replays: the days of its guide, one day of it, or one episode."""
    _replay('direttalivela7cinema.jpg')


def _replay(thumb):
    """The three depths of a replay section: the guide, a day, an episode."""
    if G.PLAY:
        streams.play_video(G.PLAY, False)
    elif G.GIORNO:
        program.giorno()
    else:
        program.giorni(thumb)


def tutti_programmi():
    """The programs page: its groups, the A-Z list, or one program."""
    if G.PLAY:
        streams.play_video(G.PLAY, False)
    elif G.LINK:
        program.pagina()
    elif G.GRUPPO:
        catalog.gruppo(G.GRUPPO)
    elif G.LETTERA:
        catalog.tutti_programmi()
    else:
        catalog.programmi()


def cerca_la7():
    """The site's search, or one of its results."""
    if G.PLAY:
        search.play_result(G.PLAY)
    else:
        search.cerca_la7()


# which function serves which mode: the root menu and this table are one thing
MODES = {
    'diretta_la7': diretta_la7,
    'diretta_la7cinema': diretta_la7cinema,
    'rivedi_la7': rivedi_la7,
    'rivedi_la7cinema': rivedi_la7cinema,
    'film': film,
    'documentari': documentari,
    'tutti_programmi': tutti_programmi,
    'cerca_la7': cerca_la7,
}


def dispatch():
    """Serve the mode Kodi asked for; an empty mode is the root menu."""
    MODES.get(G.MODE, catalog.show_root_menu)()


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
    except Exception as error:
        # a bug or a section that is not ported yet: still one dialog, never a
        # traceback on the device, and the section that failed names the log line
        report(AddonError(G.MODE, error))
