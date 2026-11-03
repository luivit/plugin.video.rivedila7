"""An archive kept on disk, so a folder can be paged without re-reading the year.

A program's replays go back years - Piazzapulita's last page is November 2014 - and the
site gives them twenty at a time. Reading them all on every call would be thirty
requests before the folder appears, so what has been read is kept: a listing page per
line, in the add-on's profile directory, together with the page the next read continues
from.

The store knows nothing about the site: it holds a dictionary and gives it back. What
is stale is a question of time, and `stale()` answers it so that one place decides how
long an archive is worth trusting.
"""

import json
import os
import time

from resources.lib.globals import G

# where the archives live, below the profile directory Kodi gives the add-on
DIRECTORY = 'archives'

# how long an archive is trusted before the next folder page re-reads it: a program
# publishes a new episode a day at most, and a stale first page is what the user would
# see first
TTL = 6 * 3600


def load(pathname):
    """What was read of one archive, or {} when nothing was."""
    try:
        with open(_path(pathname), encoding='utf-8') as open_archive:
            stored = json.load(open_archive)
    except (OSError, ValueError):
        return {}
    return stored if isinstance(stored, dict) and isinstance(stored.get('nodes'), list) else {}


def save(pathname, stored):
    """Keep one archive for the calls that come after this one."""
    stored = dict(stored, updated=time.time())
    directory = os.path.join(G.PROFILE_PATH, DIRECTORY)
    try:
        if not os.path.isdir(directory):
            os.makedirs(directory)
        with open(_path(pathname), 'w', encoding='utf-8') as write_archive:
            json.dump(stored, write_archive)
    except OSError:
        # a cache that cannot be written is not a failure to report: the next call
        # reads the site again, which is what would have happened anyway
        return stored
    return stored


def forget(pathname):
    """Drop one archive: the next call starts from the newest episode again."""
    try:
        os.remove(_path(pathname))
    except OSError:
        pass


def stale(stored):
    """True when an archive is old enough to read again from the top."""
    return time.time() - float(stored.get('updated') or 0) > TTL


def _path(pathname):
    """The file of one archive: its path, made into a name."""
    name = pathname.strip('/').replace('/', '-') or 'archive'
    return os.path.join(G.PROFILE_PATH, DIRECTORY, name + '.json')
