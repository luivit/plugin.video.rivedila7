"""Tests for the harness itself, so its Kodi rules can be trusted.

If these pass, the other tests may use the harness as a judge: a section that adds
items after closing its directory, or that raises a dialog, is really broken on the
device, not only in the harness.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests import harness


class KodiRulesTest(unittest.TestCase):
    def setUp(self):
        harness.install_stubs()

    def test_item_added_after_close_is_dropped(self):
        from xbmcplugin import addDirectoryItem, endOfDirectory
        lister = harness._Lister()
        addDirectoryItem(handle=1, url='plugin://a?x=1',
                         listitem=harness.ListItem('kept'), isFolder=True)
        endOfDirectory(handle=1)
        addDirectoryItem(handle=1, url='plugin://a?x=2',
                         listitem=harness.ListItem('dropped'), isFolder=True)
        labels = [item['label'] for item in harness.ITEMS]
        self.assertIn('kept', labels)
        self.assertNotIn('dropped', labels)
        self.assertEqual(harness.DROPPED, 1)

    def test_dialog_is_recorded(self):
        dialog = harness.Dialog()
        dialog.ok('RivediLA7', 'cannot read the page')
        self.assertEqual(harness.DIALOGS, ['RivediLA7: cannot read the page'])

    def test_a_list_item_reads_its_label_the_way_kodi_does(self):
        """Kodi's ListItem has getLabel() and no `label`: a stub that offered one hid
        a listing that crashed on the device the first time it was opened there."""
        item = harness.ListItem('Puntate')
        self.assertEqual(item.getLabel(), 'Puntate')
        self.assertFalse(hasattr(item, 'label'),
                         'xbmcgui.ListItem has no .label attribute')


class SmokeGateTest(unittest.TestCase):
    def test_smoke_refuses_to_pass_without_sections(self):
        saved = harness.SECTIONS[:]
        del harness.SECTIONS[:]
        try:
            self.assertFalse(harness.smoke(), 'an empty gate must not report success')
        finally:
            harness.SECTIONS.extend(saved)


class AddonRunsTest(unittest.TestCase):
    def test_root_menu_is_not_empty(self):
        items, resolved, dialogs = harness.run_addon('')
        self.assertTrue(items, 'the root menu must list something')
        self.assertEqual(dialogs, [])

    def test_state_does_not_leak_between_calls(self):
        first, _, _ = harness.run_addon('')
        harness.run_addon('?mode=nonexistent')
        second, _, _ = harness.run_addon('')
        self.assertEqual([i['label'] for i in first], [i['label'] for i in second])

    def test_a_mode_that_does_not_exist_falls_back_to_the_menu(self):
        items, _, dialogs = harness.run_addon('?mode=does-not-exist')
        self.assertTrue(items)
        self.assertEqual(dialogs, [])


if __name__ == '__main__':
    unittest.main()
