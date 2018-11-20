#!/usr/bin/python
# -*- coding: utf-8 -*-
# $Id$
# (c) 2018 Juan Toledo toledo@lazaro.es
#
# This file is part of CrujiSim.
#
# CrujiSim is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# CrujiSim is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CrujiSim; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Classes implementing a limited subset of AIXM"""

from __future__ import print_function
from __future__ import absolute_import
from future import standard_library
from builtins import range
from builtins import object

import logging


# Future
standard_library.install_aliases()


class AirportHeliport(object):  # Aerodrome / Heliport

    def __init__(self, code_id, designator='', pos=None, val_elev=0):
        self.code_id = code_id
        self.designator = designator
        self.pos = pos
        self.val_elev = val_elev
        self.rwy_direction_list = []
        self.rwy_in_use = None

    def get_sid(self, txt_desig):
        return [sid for rwy in self.rwy_direction_list
                for sid in rwy.sid_dict.values()
                if sid.txt_desig == txt_desig][0]

    def __repr__(self):
        s = "AD_HP(id: %r, designator:%r, pos:%r, val_elev:%r, %r, %r)" % (
            self.code_id, self.designator, self.pos,
            self.val_elev, self.rwy_direction_list,
            self.rwy_in_use)
        return s


class Association(object):
    """Holds a number of other AIXM objects"""
    def __init__(self, role, max, min):
        self.role = role
        self.max = max
        self.min = min


class RunwayDirection(object):

    def __init__(self, designator, trueBearing, elevationTDZ, usedRunway):
        # designator must have between 2 and 3 characters, of which the first 2
        # may be any digit between 0 and 9. Examples: 09, 09L, 09R, 09C, 09T,
        # etc..
        self.designator = designator
        self.trueBearing = trueBearing
        self.elevationTDZ = elevationTDZ
        self.usedRunway = usedRunway

    def __str__(self):
        return self.designator

    def __repr__(self):
        s = "RWY_DIRECTION(%r, %r, %r, %r" % (
            self.designator, self.trueBearing, self.elevationTDZ, self.usedRunway)
        return s


class Runway(object):
    def __init__(self, designator, associatedAirportHeliport):
        self.associatedAirportHeliport = associatedAirportHeliport


class StandarInstrumentArrival(object):
    # TODO this only covers basic AICM attributes.
    # We need to support the whole procuedure_leg object in order to
    # to support things like SLP and vertical limitations

    def __init__(self, designator, isArrivalFor):
        self.designator = designator

    def __str__(self):
        return self.designator

    def __repr__(self):
        s = "STAR(%r, %s, end_fix: %s)" % (
            self.designator, self.rte, self.start_fix)
        return s


class SID(object):
    # TODO this only covers basic AICM attributes.
    # We need to support the whole procuedure_leg object in order to
    # to support things like SLP and vertical limitations

    def __init__(self, txt_desig, rte):
        self.txt_desig = txt_desig
        self.end_fix = txt_desig[: -2]

    def __str__(self):
        return self.txt_desig

    def __repr__(self):
        s = "SID(%r, %s, end_fix: %s)" % (
            self.txt_desig, self.rte, self.end_fix)
        return s
