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

"""These classes hold information gathered from AIS sources"""

# Initially I intended to model AIXM whole, but it is way
# too cumbersome, and far exceeds the needs of this simulation
# Furthermore, the main source of data will be Insignia,
# the GIS solution of Enaire, which share some attributes with
# AIXM but is way more sparse.
# So the final result is a mixture of the two adapted to our needs
# There will have to be special code to input data from each source
# to these structures

from __future__ import print_function
from __future__ import absolute_import
from future import standard_library
from builtins import range
from builtins import object

import logging

from . import Route

# Future
standard_library.install_aliases()


# There are all kind of points defined both in AIXM and Insignia
# This is the bare minimum needed
class Point(object):
    def __init__(
            self,
            pos,              # Coordinates
            designator,       # AIXM DesignatedPoint. Insignia DESIGNATEDPOINT_NAME
            flyOver=False):   # AIXM SegmentPoint. Insignia DP Procedimiento FLYOVER. Unused
        self.pos = pos
        self.designator = designator
        self.flyOVer = flyOver


class AirportHeliport(object):  # Aerodrome / Heliport

    def __init__(
            self,
            designator,       # ICAO. AIXM allows others. Insignia ICAO_TXT
            pos=None,         # Old crujisim fir files didn't have airport positions
            fieldElev=0       # Feet. AIXM name. Insignia ELEV_VAL in meters
    ):
        # Descriptive
        self.designator = designator
        self.pos = pos
        self.fieldElev = fieldElev

        # Operating
        self.rwy_direction_list = []
        self.rwy_in_use = None

    def get_sid(self, txt_desig):
        return [sid for rwy in self.rwy_direction_list
                for sid in rwy.sid_dict.values()
                if sid.txt_desig == txt_desig][0]

    def __repr__(self):
        s = "AD_HP(designator:%r, pos:%r, fieldElev:%r, %r, %r)" % (
            self.designator, self.pos,
            self.fieldElev, self.rwy_direction_list,
            self.rwy_in_use)
        return s


class RunwayDirection(object):

    def __init__(
            self,
            designator,     # AIXM
            trueBearing,    # AIXM
            elevationTDZ,   # AIXM, Insignia ELEVATIONTDZ (insignia in meters, has to be converted)
            usedRunway):
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


# AIX can have a STAR point at multiple RWY directions
# Insignia has duplicate entries, I believe

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


# TO BE SUBSTITUTED BY THE ONES ABOVE!

# TODO
# There is currently no support for lat/lon coordinates, so we are using
# the non-standard attribute 'pos' to store the cartesian coordinates of objects,
# rather than the aicm standard geo_lat and geo_lon


class Designated_Point(object):

    def __init__(self, designator, pos):
        self.designator = designator
        self.pos = pos


Point = Designated_Point  # Alias for the class


class Hold(object):
    # TODO this does not reflect AICM. We need to support the whole
    # procedure_leg in order to do this

    def __init__(self, fix, inbd_track=180, outbd_time=1, std_turns=True, min_FL=000, max_FL=999):
        self.fix = fix         # The fix on which this hold is based
        self.inbd_track = inbd_track  # Inbound track of the holding pattern
        self.outbd_time = outbd_time  # For how long to fly on the outbd track
        self.std_turns = std_turns   # Standard turns are to the right
        self.min_FL = min_FL        # minimun FL at the holding pattern
        self.max_FL = max_FL        # maximun FL at the holding pattern


class RWY_DIRECTION(object):

    def __init__(self, txt_desig):
        # TXT_DESIG must have between 2 and 3 characters, of which the first 2
        # may be any digit between 0 and 9. Examples: 09, 09L, 09R, 09C, 09T,
        # etc..
        self.txt_desig = txt_desig
        self.sid_dict = {}
        self.star_dict = {}
        self.iap_dict = {}

    def __repr__(self):
        s = "RWY_DIRECTION(%r, %r, %r, %r" % (
            self.txt_desig, self.sid_dict, self.star_dict, self.iap_dict)
        return s


class STAR(object):
    # TODO this only covers basic AICM attributes.
    # We need to support the whole procuedure_leg object in order to
    # to support things like SLP and vertical limitations

    def __init__(self, txt_desig, rte):
        self.txt_desig = txt_desig
        self.rte = Route.Route(Route.get_waypoints(rte))
        self.start_fix = txt_desig[: -2]

    def __str__(self):
        return self.txt_desig

    def __repr__(self):
        s = "STAR(%r, %s, end_fix: %s)" % (
            self.txt_desig, self.rte, self.start_fix)
        return s


class SID(object):
    # TODO this only covers basic AICM attributes.
    # We need to support the whole procuedure_leg object in order to
    # to support things like SLP and vertical limitations

    def __init__(self, txt_desig, rte):
        self.txt_desig = txt_desig
        self.rte = Route.Route(Route.get_waypoints(rte))
        self.end_fix = txt_desig[: -2]

    def __str__(self):
        return self.txt_desig

    def __repr__(self):
        s = "SID(%r, %s, end_fix: %s)" % (
            self.txt_desig, self.rte, self.end_fix)
        return s

