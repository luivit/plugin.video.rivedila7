"""What a la7play.it page carries in its payload, and how to tell the parts apart.

The site is a Next.js app: the visible HTML is rendered from a React Server
Components payload the page pushes to the client as a series of
`self.__next_f.push([1, "..."])` chunks. The same content is in there as data, so
the add-on reads the payload instead of the markup - one shape to parse instead of
scraping a layout that changes with the design.

Two ways of reading it, because the site uses two:

* `value()` picks one named structure out of the text (the TV guide hands over
  its whole week as the value of a single `"giorno"` key);
* `nodes()` walks an already decoded structure and collects the content nodes in
  it, wherever they are nested (a hub page keeps its content in slots).

A third reader, `page_nodes()`, reads a whole page: the cards of a listing are not
nested under one key, so that one listing cannot be read by name.

What a node is, and how the add-on tells a folder from a playable item, is site
knowledge and therefore lives here too: a node with a stream is an item, a node
whose path has more than one segment is a category.
"""

import json

# the call every page makes to hand a chunk of its payload to the client
RSC_PUSH = 'self.__next_f.push('


def decode(html):
    """The payload of a page, all of its chunks as one text."""
    chunks = []
    position = 0
    while True:
        position = html.find(RSC_PUSH, position)
        if position < 0:
            return ''.join(chunks)
        start = position + len(RSC_PUSH)
        end = _bracketed(html, start)
        try:
            chunk = json.loads(html[start:end])
        except ValueError:
            chunk = []
        # a chunk is [1, "payload"]; a chunk that is anything else carries no text
        if len(chunk) > 1 and isinstance(chunk[1], str):
            chunks.append(chunk[1])
        position = end


def value(text, key):
    """The JSON value of the first `"key":` in a payload, or None."""
    position = text.find('"%s":' % key)
    if position < 0:
        return None
    start = position + len(key) + 3
    while start < len(text) and text[start] in ' \t':
        start += 1
    try:
        return json.loads(text[start:_value_end(text, start)])
    except ValueError:
        return None


def nodes(content, found=None, seen=None):
    """The content nodes of a decoded structure, deepest first order kept."""
    if found is None:
        found, seen = [], set()
    if isinstance(content, dict):
        path = node_path(content)
        if path.startswith('/') and node_title(content) and path not in seen:
            seen.add(path)
            found.append(content)
        for item in content.values():
            nodes(item, found, seen)
    elif isinstance(content, list):
        for item in content:
            nodes(item, found, seen)
    return found


def page_nodes(html):
    """The content nodes of one page, read from the payload text of that page.

    A page does not carry its items under a key: every card of a list is a
    component reference of its own, so this is the one place in the add-on that
    reads the flight text line by line instead of by name. It exists for the one
    listing no query answers - the cards of a category page - and is used by the
    fallback of the archive, not by the sections that read data.
    """
    found = []
    seen = set()
    for line in decode(html).split('\n'):
        _, _, body = line.partition(':')
        try:
            content = json.loads(body)
        except ValueError:
            continue
        for node in nodes(content):
            path = node_path(node)
            if path not in seen:
                seen.add(path)
                found.append(node)
    return found


def node_path(node):
    """The path of a node on the site, empty when it has none."""
    return node.get('path') or node.get('pathname') or ''
def node_title(node):
    """The title of a node, stripped; the site spells it three ways."""
    return (node.get('titolo') or node.get('title') or node.get('nome') or '').strip()


def is_playable(node):
    """True when the node is something the player can open.

    A node is playable when it publishes a stream (an uploaded video or a URL of
    its own), or when its path is one of the shapes the site uses for an episode:
    an episode of a program, the archive page of a program, a film.
    """
    path = node_path(node)
    return bool(node.get('uploadVideo') or node.get('urlVideo')
                or '/puntate/' in path or path.startswith('/film/'))


def is_category(path):
    """True when the path names a category of a page rather than the page itself.

    `/otto-e-mezzo` is a program, `/otto-e-mezzo/puntate` is one of its categories.
    """
    return path.strip('/').count('/') >= 1


def is_ancestor(path, pathname):
    """True when `path` is `pathname` itself or one of its parents."""
    path = path.rstrip('/')
    return bool(path) and (pathname == path or pathname.startswith(path + '/'))


def _bracketed(text, start):
    """End of the [...] value that starts at `start`, closing bracket included."""
    depth = 0
    in_string = False
    escaped = False
    end = start
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
        elif char == '[':
            depth += 1
        elif char == ']':
            depth -= 1
            if depth == 0:
                return end + 1
        end += 1
    return end


def _value_end(text, start):
    """End of the JSON value that starts at `start`, its last character included."""
    depth = 0
    in_string = False
    escaped = False
    end = start
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
        elif char in ']},':
            if depth == 0:
                # a scalar ends where the structure around it closes
                return end
            if char in ']}':
                depth -= 1
                if depth == 0:
                    return end + 1
        end += 1
    return end
