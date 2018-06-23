# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Portions Copyright Buildbot Team Members

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time

from twisted.internet import threads
from twisted.python import log

from buildbot import config
from buildbot.worker import AbstractLatentWorker

try:
    import fabric
except ImportError:
    fabric = None

VM_STATUS_CMD = "sudo vm info openbsd | head -n 4 | tail -n 1 | cut -d':' -f 2 | cut -d' ' -f 2"
RUNNING = "running"

class VMBhyveLatentWorker(AbstractLatentWorker):

    def __init__(self, image, datastore, name, hostname, username,
                 **kwargs):

        if not fabric:
            config.error("The python module 'fabric' is needed to use a "
                         "VMBhyveLatentWorker")

        self.datastore = datastore
        self.name = name
        self.image = image
        self.conn = fabric.Connection(host=hostname, user=username, port=22)
        self.vm_status = ""
        self.timeout = 300

        AbstractLatentWorker.__init__(self, **kwargs)

    def start_instance(self, build):

        provision_str = "vm image provision " + self.image + " " + self.name
        self.conn.sudo(provision_str)
        start_str = "vm start " ++ self.name
        self.conn.sudo(start_str)
        self._wait_for_startup()

    def stop_instance(self, fast=False):

        return threads.deferToThread(
            self._stop_instance)

    def _stop_instance(self):
        stop_str = "yes | vm poweroff " ++ self.name
        destroy_str = "yes | vm destroy " ++ self.name
        self.conn.sudo(stop_str)
        self._wait_for_shutdown()
        self.conn.sudo(destroy_str)

    def _get_status(self):
        info_cmds = "| head -n 4 | tail -n 1 | cut -d':' -f 2 | cut -d' ' -f 2"
        whole_vm = "vm info " + self.name + info_cmds
        self.conn.sudo(whole_vm).stdout

    def _set_status(self):
        if (self._get_status() == 'running\n'):
            self.vm_status = 'running'
        elif self._get_status() == 'stopped\n':
            self.vm_status = 'stopped'

    def _wait_for_startup(self):
        while self.vm_status != 'running':
            time.sleep(20)
            self._set_status()

    def _wait_for_shutdown(self):
        duration = 0
        while (self.vm_status != 'stopped'):   #|| duration < self.timeout
            time.sleep(20)
            self._set_status()
            duration += 20
