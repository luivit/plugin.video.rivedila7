"""Everything the user is told: one exception type, one log line, one dialog.

A section that cannot do its job raises AddonError instead of showing its own
dialog, so the wording of a failure lives in one place and the failure is always
logged with the section that produced it. The entry point is the only caller of
report(), which is what makes "never a traceback, never a silent empty folder"
checkable.
"""

import xbmc
import xbmcgui

from resources.lib.globals import G


class AddonError(Exception):
    """A section failed; the entry point turns it into one dialog."""

    def __init__(self, section, cause):
        super(AddonError, self).__init__(
            '%s: %s: %s' % (section, type(cause).__name__, cause))
        self.section = section
        self.cause = cause


def notify(message):
    """A short, non-blocking message (used where a dialog would be an interruption)."""
    xbmcgui.Dialog().notification(G.PLUGIN_NAME, message,
                                  xbmcgui.NOTIFICATION_INFO, 3000)


def ask(label):
    """Ask for a line of text; the empty string when the user cancels."""
    return (xbmcgui.Dialog().input(G.LANGUAGE(label), type=xbmcgui.INPUT_ALPHANUM) or '').strip()


def report(error):
    """Log an AddonError and tell the user, once: the only error dialog there is."""
    xbmc.log('RivediLA7: %s' % error, xbmc.LOGERROR)
    xbmcgui.Dialog().ok(G.PLUGIN_NAME, G.LANGUAGE(32005))
