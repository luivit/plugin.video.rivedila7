"""Regenerate the fixtures in this directory from the live site.

A fixture is a page or an answer the site really returned, saved so the tests can
judge the parsers without a network. That only stays true if the fixtures can be
refreshed: when the site changes and a test fails, run this, look at the diff, and
decide whether the code or the expectation is wrong.

The decoding below is deliberately a second copy of `la7play.payload.decode`: a
fixture produced by the code under test would agree with a broken parser.

Usage:
    python3 tests/fixtures/capture.py            # rewrite every fixture
    python3 tests/fixtures/capture.py --dry-run  # fetch and report, write nothing

What is saved:
    page-programma.html   /otto-e-mezzo, the payload of the page carried by one
                          `self.__next_f.push` script, because the payload is where
                          the page keeps its data
    page-guida-la7.html   /guida-tv-rivedi/la7, same, with the day list cut down to
                          three days of three programs (the real page carries
                          fifteen days and 300+ programs, 700 kB of fixture for
                          the same shapes)
    gql-nodePage.json     the answer of the nodePage query for "otto-e-mezzo"
    gql-allPrograms.json  the flat index of programs behind the programs page
    gql-nsContentHub-programmi.json
                          the programs page as data: its carousels and the few
                          programs of each that are kept (the nine groups are all
                          real, three items each stand in for the rest)

A page fixture is the payload of the page, re-encoded as a single push chunk: the
site sends it in two or three chunks, which is a delivery detail `decode()` folds
away. The trimming rewrites only the `giorno` list, so the fixture keeps the real
shapes of the page around it.
"""

import base64
import json
import os
import sys
import urllib.request

SITE = 'https://www.la7play.it'
HERE = os.path.dirname(os.path.abspath(__file__))
RSC_PUSH = 'self.__next_f.push('

# query name -> persisted hash, as in resources/lib/globals.py
QUERIES = {
    'nodePage': 'e9d39e6838f7f588',
    'allPrograms': 'f7034d55158fc906',
    'nsContentHub': '0f3f2c4225230faf',
}

FIXTURES = [
    # file, kind, what, trimming
    ('page-programma.html', 'page', SITE + '/otto-e-mezzo', None),
    ('page-guida-la7.html', 'page', SITE + '/guida-tv-rivedi/la7',
     {'key': 'giorno', 'days': 3, 'programs': 3}),
    ('gql-nodePage.json', 'gql', {'query': 'nodePage', 'variables': {'path': 'otto-e-mezzo'}}, None),
    ('gql-allPrograms.json', 'gql', {'query': 'allPrograms', 'variables': None}, None),
    ('gql-nsContentHub-programmi.json', 'gql',
     {'query': 'nsContentHub', 'variables': {'path': '/programmi'}}, {'items': 3}),
]


def fetch(url):
    request = urllib.request.Request(url, headers={'user-agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(request, timeout=60).read().decode('utf-8', 'replace')


def payload(html):
    """Concatenate the payloads a page pushes to the client, as one text."""
    parts = []
    pos = 0
    while True:
        pos = html.find(RSC_PUSH, pos)
        if pos < 0:
            return ''.join(parts)
        start = pos + len(RSC_PUSH)
        end, depth, in_string, escaped = start, 0, False, False
        while end < len(html):
            char = html[end]
            if in_string:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == '[':
                depth += 1
            elif char == ']':
                depth -= 1
                if depth == 0:
                    break
            end += 1
        try:
            chunk = json.loads(html[start:end + 1])
        except ValueError:
            chunk = []
        if len(chunk) > 1 and isinstance(chunk[1], str):
            parts.append(chunk[1])
        pos = end


def span(text, key):
    """(start, end) of the JSON value of the first "key": pair, end included."""
    pos = text.find('"%s":' % key)
    if pos < 0:
        return None
    start = pos + len(key) + 3
    while start < len(text) and text[start] in ' \t':
        start += 1
    end, depth, in_string, escaped = start, 0, False, False
    while end < len(text):
        char = text[end]
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in '[{':
            depth += 1
        elif char in ']}':
            depth -= 1
            if depth == 0:
                break
        elif char in ',}' and depth == 0:
            break
        end += 1
    return start, end


def trim(text, key, days, programs):
    """Keep the first days of a list and the first programs of each day."""
    found = span(text, key)
    if found is None:
        raise SystemExit('cannot find "%s" in the payload: did the page change?' % key)
    start, end = found
    kept = json.loads(text[start:end + 1])[:days]
    for day in kept:
        if isinstance(day.get('programma'), list):
            day['programma'] = day['programma'][:programs]
    return text[:start] + json.dumps(kept, separators=(',', ':')) + text[end + 1:]


def gql(query, variables=None):
    url = '%s/api/gql/%s' % (SITE, query)
    if variables is not None:
        encoded = json.dumps(variables, separators=(',', ':'), sort_keys=True).encode('utf-8')
        url += '/' + base64.urlsafe_b64encode(encoded).decode('utf-8').rstrip('=')
    request = urllib.request.Request(url, headers={'user-agent': 'Mozilla/5.0',
                                                   'accept': 'application/json',
                                                   'referer': SITE + '/'})
    return urllib.request.urlopen(request, timeout=60).read().decode('utf-8', 'replace')


def trim_slots(text, items):
    """Keep every carousel of a hub page, and the first items of each."""
    answer = json.loads(text)
    route = (answer.get('data') or {}).get('route') or {}
    for slot in (route.get('entity') or {}).get('contentSlots') or []:
        paginated = slot.get('paginatedItems') or {}
        if isinstance(paginated.get('items'), list):
            paginated['items'] = paginated['items'][:items]
    return json.dumps(answer, separators=(',', ':'))


def build(kind, what, trimming):
    if kind == 'gql':
        body = gql(QUERIES[what['query']], what['variables'])
        return trim_slots(body, trimming['items']) if trimming else body
    body = payload(fetch(what))
    if trimming:
        body = trim(body, trimming['key'], trimming['days'], trimming['programs'])
    return '<script>self.__next_f.push([1,%s])</script>\n' % json.dumps(body)


def main(argv):
    dry_run = '--dry-run' in argv
    for name, kind, what, trimming in FIXTURES:
        body = build(kind, what, trimming)
        path = os.path.join(HERE, name)
        previous = None
        if os.path.exists(path):
            with open(path, encoding='utf-8') as open_previous:
                previous = open_previous.read()
        changed = 'new' if previous is None else ('same' if previous == body else 'changed')
        print('%-24s %8d bytes  %s' % (name, len(body), changed))
        if dry_run or changed == 'same':
            continue
        with open(path, 'w', encoding='utf-8') as open_fixture:
            open_fixture.write(body)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
