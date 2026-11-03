"""Podcasts: what the site lists, and what the feed says there is to play.

The site publishes the series and the feed holds the episodes, so both halves are
checked here: the cards of `/podcast` become folders, the Apple id in a card finds the
feed, and the feed's own enclosures are what a folder plays - a podcast is not a stream
the add-on builds.
"""

import json
import os
import sys
import unittest
import urllib.parse

from urllib.error import URLError

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from tests import harness
from tests.site import Site

SERIES_PAGE = 'https://www.la7play.it/podcast'
LOOKUP = 'https://itunes.apple.com/lookup'
FEED = 'https://feeds.example.invalid/otto.xml'
APPLE = '1502081325'


def series_card(name, apple, thumb='https://images.la7play.it/podcast/%s.jpg'):
    card = {'@type': 'PodcastSeries', 'name': name,
            'description': 'Il podcast di %s' % name,
            'image': {'url': thumb % name.lower()},
            'sameAs': ['https://open.spotify.com/show/xxx',
                       'https://podcasts.apple.com/it/podcast/%s/id%s'
                       % (urllib.parse.quote(name.lower()), apple)]}
    return json.dumps(card, separators=(',', ':'))


def series_page(*cards):
    """The podcast page of the site: a card per series, as JSON-LD in the markup."""
    return ('<html><script type="application/ld+json">%s</script></html>'
            % '\n'.join(cards)).encode('utf-8')


def feed(episodes, thumb='https://images.la7play.it/series/otto.jpg'):
    """An RSS feed with the episodes a test names, newest first."""
    items = []
    for number in range(1, episodes + 1):
        day = (number - 1) % 28 + 1
        items.append(
            '<item><title>Puntata %d</title><pubDate>%02d Oct 2026 06:00:00 +0000</pubDate>'
            '<enclosure url="https://audio.example.invalid/puntata-%d.mp3" type="audio/mpeg"/>'
            '<itunes:duration>42:10</itunes:duration>'
            '<itunes:summary>La puntata %d</itunes:summary></item>' % (number, day, number, number))
    return ('<?xml version="1.0" encoding="UTF-8"?><rss '
            'xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"><channel>'
            '<itunes:image href="%s"/>%s</channel></rss>' % (thumb, ''.join(items))).encode('utf-8')


def lookup(feed_url=FEED):
    """What iTunes answers about one podcast: where its feed is."""
    return json.dumps({'results': [{'feedUrl': feed_url}]}).encode('utf-8')


class PodcastTest(unittest.TestCase):
    def setUp(self):
        harness.install_stubs()
        harness.unload_addon_modules()
        self.serve()

    def serve(self, answers=None, error=None):
        base = {SERIES_PAGE: series_page(series_card('Otto e mezzo', APPLE),
                                         series_card('Piazzapulita', '771122')),
                LOOKUP: lookup(),
                FEED: feed(45)}
        base.update(answers or {})
        self.site = Site(base, error)
        from resources.lib.la7play import client
        client.urlopen = self.site

    def call(self, query):
        def prepare():
            from resources.lib.la7play import client
            client.urlopen = self.site
        return harness.run_addon(query, prepare=prepare)

    @staticmethod
    def params(item):
        import urllib.parse
        return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(item['url']).query))

    def test_the_section_lists_the_series_the_page_publishes(self):
        items, _, dialogs = self.call('?mode=podcast')
        self.assertEqual(dialogs, [])
        self.assertEqual([item['label'] for item in items], ['Otto e mezzo', 'Piazzapulita'])
        self.assertEqual(self.params(items[0]), {'mode': 'podcast', 'link': APPLE})

    def test_the_first_page_of_a_feed_is_its_first_twenty_episodes(self):
        items, _, dialogs = self.call('?mode=podcast&link=' + APPLE)
        self.assertEqual(dialogs, [])
        plays = [item for item in items if not item['folder']]
        self.assertEqual(len(plays), 20)
        self.assertEqual(plays[0]['label'], '01/10/2026 Puntata 1')
        self.assertTrue(plays[0]['item'].art['thumb'].startswith('https://images.la7play.it/'),
                        'an episode without its own picture shows the one of its series')
        self.assertEqual(plays[0]['item'].info['plot'], 'La puntata 1')
        self.assertEqual(items[-1]['label'], '[B]string 32003[/B]')

    def test_the_page_after_the_one_listed_is_asked_for(self):
        self.call('?mode=podcast&link=' + APPLE)
        items, _, dialogs = self.call('?mode=podcast&link=' + APPLE + '&page=2')
        self.assertEqual(dialogs, [])
        plays = [item for item in items if not item['folder']]
        self.assertEqual(len(plays), 20)
        self.assertEqual(plays[0]['label'], '21/10/2026 Puntata 21')
        self.assertIn('[B]string 32003[/B]', [item['label'] for item in items],
                      'the feed holds 45 episodes: there is a page after this one')

    def test_an_episode_plays_the_enclosure_the_feed_publishes(self):
        _, resolved, dialogs = self.call('?mode=podcast&play=https://audio.example.invalid/puntata-1.mp3')
        self.assertEqual(dialogs, [])
        self.assertEqual(resolved[0]['item'].path, 'https://audio.example.invalid/puntata-1.mp3')
        self.assertEqual(resolved[0]['item'].mimetype, 'audio/mpeg')

    def test_a_feed_with_no_audio_is_one_dialog(self):
        self.serve({FEED: feed(0)})
        items, _, dialogs = self.call('?mode=podcast&link=' + APPLE)
        self.assertEqual(items, [])
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])

    def test_a_series_without_a_feed_on_itunes_is_one_dialog(self):
        self.serve({LOOKUP: json.dumps({'results': []}).encode('utf-8')})
        items, _, dialogs = self.call('?mode=podcast&link=' + APPLE)
        self.assertEqual(items, [])
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])

    def test_a_site_that_does_not_answer_is_one_dialog(self):
        self.serve(error=URLError('no route'))
        _, _, dialogs = self.call('?mode=podcast')
        self.assertEqual(dialogs, ['RivediLA7: string 32005'])


if __name__ == '__main__':
    unittest.main()
