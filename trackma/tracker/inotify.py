# This file is part of Trackma.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


import inotify.adapters
import inotify.constants

from trackma import utils
from trackma.tracker import inotifyBase


class inotifyTracker(inotifyBase.inotifyBase):
    name = 'Tracker (inotify)'

    def observe(self, config, watch_dirs):
        # Note that this lib uses bytestrings for filenames and paths.
        self.msg.info('Using inotify.')

        self.msg.debug('Checking if there are open players...')
        opened = self._proc_poll()
        if opened:
            self._proc_open(*opened)

        self.msg.debug('Watching the following paths: ' + ','.join(watch_dirs))

        mask = (inotify.constants.IN_OPEN
                | inotify.constants.IN_CLOSE
                | inotify.constants.IN_CREATE
                | inotify.constants.IN_MOVE
                | inotify.constants.IN_DELETE)

        i = inotify.adapters.InotifyTrees(list(watch_dirs), mask=mask)

        try:
            for event in i.event_gen():
                if not self.active:
                    return

                if event is not None:
                    # With inotifyx impl., only the event type was used,
                    # such that it only served to poll lsof when an
                    # open or close event was received.
                    (header, types, path, filename) = event
                    if 'IN_ISDIR' not in types:
                        # If the file is gone, we remove from library
                        if ('IN_MOVED_FROM' in types
                                or 'IN_DELETE' in types):
                            self._emit_signal('removed', path, filename)
                        # Otherwise we attempt to add it to library
                        # Would check for IN_MOVED_TO or IN_CREATE but no need
                        else:
                            self._emit_signal('detected', path, filename)

                        if 'IN_OPEN' in types:
                            self._proc_open(path, filename)
                        elif ('IN_CLOSE_NOWRITE' in types
                              or 'IN_CLOSE_WRITE' in types):
                            self._proc_close(path, filename)
                elif self.last_state != utils.Tracker.NOVIDEO and not self.last_updated:
                    # Default blocking duration is 1 second
                    # This will count down like inotifyx impl. did
                    self.update_show_if_needed(
                        self.last_state, self.last_show_tuple)
        finally:
            self.msg.info('Tracker has stopped.')
            # inotify resource is cleaned-up automatically
