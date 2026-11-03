"""The add-on entry point: Kodi's arguments become one call into the add-on.

Nothing is listed, parsed or played here. This module owns exactly three things:
the parameters Kodi passes on every invocation (they end up in the globals), the
table that says which function serves which mode, and the single place where a
failure becomes one log line and one dialog.
"""

from resources.lib.globals import G
from resources.lib.kodi import player
from resources.lib.kodi.dialogs import AddonError, report
from resources.lib.la7play import archive, catalog, program, search
from resources.lib.playback import drm, streams


def diretta_la7():
    """Live: the LA7 channel, a fixed manifest and a token."""
    drm.play_live('la7')


def diretta_la7cinema():
    """Live: the cinema channel."""
    drm.play_live('la7cinema')


def film():
    """The films the site publishes: the section, or one film of it."""
    if G.PLAY:
        streams.play_video(G.PLAY)
    else:
        catalog.film()


def documentari():
    """The documentaries the site publishes: the section, or one of them."""
    if G.PLAY:
        streams.play_video(G.PLAY)
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
        streams.play_video(G.PLAY)
    elif G.GIORNO:
        program.giorno()
    else:
        program.giorni(thumb)


def tutti_programmi():
    """The programs page: its groups, the A-Z list, or one program."""
    if G.PLAY:
        streams.play_video(G.PLAY)
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
        search.play_result()
    else:
        search.cerca_la7()


def prefetch():
    """Read the next block of an archive in the background: nothing is shown."""
    archive.prefetch(_pathname())


def root_menu():
    """The root menu, where a new search starts: the remembered one is dropped."""
    search.forget()
    catalog.show_root_menu()


def _pathname():
    """The site path of the page a parameter names."""
    return '/' + G.PLAY[len(G.URL_PLAY_BASE):].strip('/')


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
    'prefetch': prefetch,
}


def dispatch():
    """Serve the mode Kodi asked for; an empty mode is the root menu."""
    MODES.get(G.MODE, root_menu)()


def run(argv):
    """ Addon entry point """
    G.init_globals(argv)

    try:
        dispatch()
    except AddonError as error:
        _refuse()
        report(error)
    except Exception as error:
        # a bug or a section that is not ported yet: still one dialog, never a
        # traceback on the device, and the section that failed names the log line
        _refuse()
        report(AddonError(G.MODE or 'menu', error))


def _refuse():
    """A play that failed has to say so to Kodi, or the player waits for an answer.

    Kodi ignores this during a listing, so it is said on every failure: the call is
    what a play invocation is waiting for, and this is the only place that knows a
    failure happened.
    """
    player.refuse()
