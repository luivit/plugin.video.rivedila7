"""The Directory contract, which is the reason the class exists.

These tests pin the rule that Kodi does not forgive: the directory is closed once,
after the last item, on every path. The harness drops items added after
endOfDirectory exactly as Kodi does, so a listing that gets this wrong fails here
instead of showing an empty folder on the device.
"""

import os
import sys
import unittest
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests import harness


def init_globals(query='?mode=tutti_programmi'):
    from resources.lib.globals import G
    G.init_globals(['plugin://plugin.video.rivedila7/', '1', query])
    return G


class DirectoryTest(unittest.TestCase):
    def setUp(self):
        harness.install_stubs()
        harness.unload_addon_modules()
        self.g = init_globals()

    def directory(self, **kwargs):
        from resources.lib.kodi.directory import Directory
        return Directory(**kwargs)

    def labels(self):
        return [item['label'] for item in harness.ITEMS]

    def test_items_added_inside_the_block_are_listed(self):
        with self.directory() as directory:
            directory.add({'mode': 'x'}, harness.ListItem('one'))
            directory.add({'mode': 'x'}, harness.ListItem('two'), folder=False)
        self.assertEqual(self.labels(), ['one', 'two'])
        self.assertEqual(harness.ENDINGS, [{'succeeded': True}])
        self.assertEqual(harness.DROPPED, 0)

    def test_the_directory_is_closed_exactly_once(self):
        with self.directory() as directory:
            directory.add({'mode': 'x'}, harness.ListItem('one'))
        self.assertEqual(len(harness.ENDINGS), 1)

    def test_fail_closes_without_a_listing(self):
        directory = self.directory()
        directory.fail()
        self.assertEqual(harness.ENDINGS, [{'succeeded': False}])

    def test_close_after_fail_is_a_no_op(self):
        with self.directory() as directory:
            directory.fail()
        self.assertEqual(harness.ENDINGS, [{'succeeded': False}])

    def test_adding_after_close_is_a_bug_not_a_silent_drop(self):
        directory = self.directory()
        directory.close()
        with self.assertRaises(RuntimeError):
            directory.add({'mode': 'x'}, harness.ListItem('late'))
        self.assertEqual(harness.DROPPED, 0)
        self.assertEqual(self.labels(), [])

    def test_an_exception_closes_the_directory_as_failed(self):
        with self.assertRaises(ValueError):
            with self.directory() as directory:
                directory.add({'mode': 'x'}, harness.ListItem('one'))
                raise ValueError('boom')
        self.assertEqual(harness.ENDINGS, [{'succeeded': False}])

    def test_unique_skips_a_label_the_directory_already_listed(self):
        with self.directory() as directory:
            directory.add({'mode': 'x'}, harness.ListItem('same'), unique=True)
            directory.add({'mode': 'x'}, harness.ListItem('same'), unique=True)
            directory.add({'mode': 'x'}, harness.ListItem('same'))
        self.assertEqual(self.labels(), ['same', 'same'])

    def test_dedupe_does_not_leak_between_two_directories(self):
        with self.directory() as first:
            first.add({'mode': 'x'}, harness.ListItem('same'), unique=True)
        harness.reset_directory()  # a new call means a new directory
        with self.directory() as second:
            second.add({'mode': 'x'}, harness.ListItem('same'), unique=True)
        self.assertEqual(self.labels(), ['same', 'same'])

    def test_a_live_item_keeps_the_pvr_flag(self):
        with self.directory() as directory:
            directory.add({'mode': 'x'}, harness.ListItem('live'), folder=False, is_live=True)
        url = harness.ITEMS[0]['url']
        self.assertTrue(url.endswith('&_l=.pvr'), url)
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)['mode'], ['x'])


if __name__ == '__main__':
    unittest.main()
