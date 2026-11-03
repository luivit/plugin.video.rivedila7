"""What the site publishes but its own index forgets, kept by hand and by name.

Two kinds of thing end up here, and both are the same kind of exception:

* programs that answer on the site but are not in `allPrograms` - `/facciaafaccia`
  and `/tgla7` publish a program page with its categories, and the index the
  programs page is built from does not list them, so a folder built from the index
  alone cannot reach them;
* the sections that are about what LA7 says rather than what it airs: the news
  editions and the weather, which the site publishes as programs and which a viewer
  looks for as their own entry.

A list in a module rather than a file next to the add-on: it is versioned with the
code, it can be reviewed in the same diff that uses it, and it is the same for
everybody - a machine cannot end up with a list nobody else has. Every entry is a
path of the site: the add-on never invents a program, and an entry that stops
answering fails like any other folder, with the section's name in the dialog.
"""

from resources.lib.globals import G
from resources.lib.kodi import items
from resources.lib.kodi.directory import Directory

# programs the site's index does not list, though their pages answer
PROGRAMMI = (
    ('/facciaafaccia', 'Faccia a Faccia'),
    ('/tgla7', 'TG LA7'),
)

# the news the site publishes, as a section of its own
NOTIZIE = (
    ('/tgla7', 'TG LA7'),
)

# the weather the site publishes, as a section of its own
METEO = (
    ('/meteola7', 'Meteo LA7'),
    ('/omnibus-meteo', 'Omnibus Meteo'),
)


def programmi():
    """The programs of the manual list, as the folders the site's own list makes."""
    return [{'path': path, 'title': title} for path, title in PROGRAMMI]


def notizie():
    """The news: one folder per program the site publishes about it."""
    _elenco(NOTIZIE)


def meteo():
    """The weather: one folder per program the site publishes about it."""
    _elenco(METEO)


def _elenco(entries):
    """One folder per entry of a list, opened like the program page it names."""
    with Directory() as directory:
        for path, title in entries:
            directory.add({'mode': 'tutti_programmi', 'link': G.URL_PLAY_BASE + path},
                          items.entry(title), unique=True)
