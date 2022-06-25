#!/usr/bin/env python3

# code extracted from /usr/lib/python3/dist-packages/UpdateManager/Core/MyCache.py

# MyCache.py
# -*- Mode: Python; indent-tabs-mode: nil; tab-width: 4; coding: utf-8 -*-
#
#  Copyright (c) 2004-2008 Canonical
#
#  Author: Michael Vogt <mvo@debian.org>
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA

import apt
import apt_pkg
import os
import re
import DistUpgrade.DistUpgradeCache


SYNAPTIC_PINFILE = "/var/lib/synaptic/preferences"

class MyCache(DistUpgrade.DistUpgradeCache.MyCache):

    CHANGELOG_ORIGIN = "Ubuntu"

    def __init__(self, progress, rootdir=None):

        print("initializing")

        apt.Cache.__init__(self, progress, rootdir)
        # save for later
        self.rootdir = rootdir
        # raise if we have packages in reqreinst state
        # and let the caller deal with that (runs partial upgrade)
        # assert len(self.req_reinstall_pkgs) == 0

        print("checking")

        checkset = self.req_reinstall_pkgs
        if len(checkset) > 0:
            print("req_reinstall_pkgs (reqreinst state)")

            for name in checkset:
                print("... " + name)

        # check if the dpkg journal is ok (we need to do that here
        # too because libapt will only do it when it tries to lock
        # the packaging system)
        # assert(not self._dpkgJournalDirty())
        self._dpkgJournalDirty()

        # init the regular cache
        self._initDepCache()
        self.all_changes = {}
        self.all_news = {}

        # on broken packages, try to fix via saveDistUpgrade()
        if self._depcache.broken_count > 0:
            self.saveDistUpgrade()

            print("broken packages")
            for pkg in self._depcache:

                if self._depcache.is_inst_broken(pkg):
                    print("... is_inst_broken " + pkg.name)

                if self._depcache.is_now_broken(pkg):
                    print("... is_now_broken " + pkg.name)

        if self._depcache.del_count > 0:
            print("marked delete packages")
            for pkg in self._depcache:

                if self._depcache.marked_delete(pkg):
                    print("... " + pkg.name)

        # assert (self._depcache.broken_count == 0
        #        and self._depcache.del_count == 0)

        self.saveDistUpgrade()


    def _dpkgJournalDirty(self):
        """
        test if the dpkg journal is dirty
        (similar to debSystem::CheckUpdates)
        """
        d = os.path.dirname(
            apt_pkg.config.find_file("Dir::State::status")) + "/updates"
        for f in os.listdir(d):
            if re.match("[0-9]+", f):
                print("journal dirty " + f)
                # return True
        # return False

    def _initDepCache(self):
        #apt_pkg.config.set("Debug::pkgPolicy","1")
        #self.depcache = apt_pkg.GetDepCache(self.cache)
        #self._depcache = apt_pkg.GetDepCache(self._cache)
        self._depcache.read_pinfile()
        if os.path.exists(SYNAPTIC_PINFILE):
            self._depcache.read_pinfile(SYNAPTIC_PINFILE)
        self._depcache.init()

    def saveDistUpgrade(self):
        """ this functions mimics a upgrade but will never remove anything """
        #self._apply_dselect_upgrade()
        self._depcache.upgrade(True)
        wouldDelete = self._depcache.del_count
        if wouldDelete > 0:
            deleted_pkgs = [pkg for pkg in self if pkg.marked_delete]
            assert wouldDelete == len(deleted_pkgs)
            for pkg in deleted_pkgs:
                print("would delete " + pkg.name)

def main():
    myCache = MyCache(None)
    print("that's all")


if __name__ == "__main__":

    main()
