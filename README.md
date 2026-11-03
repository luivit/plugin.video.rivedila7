# LA7-LA7Cinema Kodi plugin

Live TV, the last week of replays, films, documentaries, every on-demand program and
the site's search, for LA7 and LA7 Cinema. Italian only, like the site.

Since 8.0.0 the add-on reads [la7play.it](https://www.la7play.it), the site LA7 moved
to: the listings come from its GraphQL API and from the data its pages carry, not from
the markup of the old la7.it pages. See `CHANGELOG.md` for what that changed.

## What it serves

| Section | |
|---|---|
| LA7 Live · LA7 Cinema Live | DASH + Widevine through `inputstream.adaptive` |
| Replay LA7 · Replay LA7 Cinema | the week of replays the site's TV guide publishes |
| Film · Documentari | the two hubs the site publishes, as data: what they list is what they hold |
| Programmi | the groups of the programs page, and the flat A-Z index |
| Podcast | the series the site lists, played from the RSS feed each one links to |
| Notizie · Meteo | the news and the weather, kept as their own sections |
| Search | the site's own search, 20 results per page, with paging |

A program is a folder of the categories its page publishes ("Replica", "Puntate",
"Clip"). Its replays are an archive that goes back years: it is kept on disk a hundred
episodes at a time and shown twenty at a time, and the block after the one being read is
fetched in the background while the user is still on the page before it. A clip listing
pages with `?page=N`. An item plays the stream the page says it has, or opens the
program it points at; an article from the search is skipped, because there is nothing to
watch in it.

Two lists are kept by hand, in `resources/lib/la7play/manuale.py`, because the site has
them and its own index does not: the programs whose pages answer but that `allPrograms`
omits (`/facciaafaccia`, `/tgla7`), and the entries of the news and weather sections.
Every entry is a path of the site - nothing is invented - so a program that stops
answering fails with the section's name in the dialog.

## Install tips

- You can install this plugin via the official Kodi repository.
- On some Linux distros Kodi comes packaged without the inputstream.adaptive plugin,
  in which case please install it: on Ubuntu, `sudo apt install kodi-inputstream-adaptive`.
- Widevine is installed by `script.module.inputstreamhelper` the first time a
  protected stream is played. Live and part of the on-demand content need it; the
  rest plays as clear HLS.

## Development

```
make test      # offline: the harness rules and every module, against captured site answers
make smoke     # live: walk every section against la7play.it and fail on any dialog
make fixtures  # re-capture the site fixtures the offline tests read
make zip       # the installable ZIP, built from the committed tree
make shipped   # checks the ZIP carries the add-on and not the test suite
make deploy    # install the committed tree into a local Kodi
```

The layout is the architecture, and `resources/lib/kodi/directory.py` is where a Kodi
directory is opened and closed:

```
resources/lib/
  plugin.py            entry point and dispatch: mode -> section, nothing else
  globals.py           configuration only: site, live channels, DRM, query hashes, headers
  kodi/                the only code that touches Kodi
    directory.py       the Directory context manager: the one caller of endOfDirectory
    items.py           the one place a ListItem is built
    player.py          resolve a stream, or refuse it
    background.py      the only place a plugin URL is built: work Kodi runs again, unseen
    dialogs.py         AddonError, one log format, one error dialog
    window.py          the one window property the add-on keeps (the search query)
  la7play/             the site, as data: no Kodi URL is built here, no error shown here
    client.py          GraphQL queries by hash, the page fetch
    payload.py         the RSC payload: node lookups, images, plots, paths
    catalog.py         menu, programs page, the film and documentary hubs
    guide.py           the TV guide: the week of replays
    program.py         a program page and its categories
    archive.py         a category's archive, and the paged listings
    archive_store.py   what has been read of an archive, kept on disk between calls
    podcast.py         the series the site lists and the episode feeds behind them
    manuale.py         the programs the site's index forgets, and the news/weather lists
    search.py          the site's search
  playback/            streams: the player data of a page, and the license it needs
```

Two rules hold the shape together. A module under `la7play/` never builds a Kodi URL by
hand and never shows an error: it returns entries and raises `AddonError(module, cause)`,
which `plugin.report()` turns into one log line and one dialog. And a directory is
opened exactly once, by a `Directory`, closed by it - which is why a failed folder
closes as failed instead of staying empty.

`tests/` holds the harness (Kodi and the site stubbed faithfully enough to run the
add-on offline), the offline suite, and the real site answers the suite reads. The ZIP
carries the add-on only: `tests/`, `design/` and `.github/` are not in it.

GitHub Actions runs `make test` on every push and pull request
(`.github/workflows/tests.yml`), and `make smoke` on a weekly schedule or on demand
(`.github/workflows/smoke.yml`, *Run workflow* in the Actions tab, or
`gh workflow run smoke.yml`) - the live site is not a merge gate. A dispatch can walk a
single section instead: *Run workflow* takes `film --depth 2` and runs `make walk` with it.
