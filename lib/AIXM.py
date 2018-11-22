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


def attr_repr(instance, attr_list):
    """Get representation string for attributes that may be null"""
    extra = ''
    for attrib in attr_list:
        value = getattr(instance, attrib)
        if value:
            extra += ", %r=%r" % (attrib, value)
    return extra


# There are all kind of points defined both in AIXM and Insignia
# This is the bare minimum needed
class Point(object):
    def __init__(
        self,
        designator,                 # AIXM DesignatedPoint. Insignia DESIGNATEDPOINT_NAME
        pos,                        # Coordinates
        flyOver=False,              # AIXM SegmentPoint. Insignia DP Procedimiento FLYOVER. Unused
        upperLimitAltitude=None,    # AIXM SegmentLeg. We use this and the following on the point starting the leg
        upperLimitReference=None,
        lowerLimitAltitude=None,
        lowerLimitReference=None,
        altitudeInterpretation=None,
        speedLimit=None,
        speedReference=None,
        speedInterpretation=None
    ):
        self.designator = designator
        self.pos = pos
        self.flyOver = flyOver
        self.upperLimitAltitude = upperLimitAltitude
        self.upperLimitReference = upperLimitReference
        self.lowerLimitAltitude = lowerLimitAltitude
        self.lowerLimitReference = lowerLimitReference
        self.altitudeInterpretation = altitudeInterpretation
        self.speedLimit = speedLimit
        self.speedReference = speedReference
        self.speedInterpretation = speedInterpretation

    def __repr__(self):
        extra = attr_repr(self, ('flyOver', 'upperLimitAltitude', 'lowerLimitAltitude',
                                 'upperLimitReference', 'lowerLimitReference',
                                 'altitudeInterpretation', 'speedLimit',
                                 'speedReference', 'speedInterpretation'))
        return "Point(%r, %r%s)" % (self.designator, self.pos, extra)


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
        self.runwayDirections = []
        self.rwyInUse = None

    def get_sid(self, designator):
        return [sid for rwy in self.runwayDirections
                for sid in rwy.standardInstrumentDepartures.values()
                if sid.designator == designator][0]

    def __repr__(self):
        extra = attr_repr(self, ('pos', 'fieldElev', 'runwayDirections', 'rwyInUse'))
        s = "AirportHeliport(designator:%r%s)" % (
            self.designator, extra)
        return s


class RunwayDirection(object):

    def __init__(
            self,
            designator,         # AIXM
            trueBearing=None,   # AIXM
            elevationTDZ=None,  # AIXM, Insignia ELEVATIONTDZ (insignia in meters, has to be converted)
            usedRunway=None     # Pointer to Runway instance
    ):
        # designator must have between 2 and 3 characters, of which the first 2
        # may be any digit between 0 and 9. Examples: 09, 09L, 09R, 09C, 09T,
        # etc..
        self.designator = designator
        self.trueBearing = trueBearing
        self.elevationTDZ = elevationTDZ
        self.usedRunway = usedRunway

        self.standardInstrumentDepartures = {}
        self.standardInstrumentArrivals = {}
        self.iap_dict = {}

    def __str__(self):
        return self.designator

    def __repr__(self):
        s = ("RunwayDirection(designator=%r%s)" % (
            self.designator,
            attr_repr(self, ('trueBearing', 'elevationTDZ', 'usedRunway',
                             'standardInstrumentArrivals', 'standardInstrumentDepartures',
                             'iap_dict'))))
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

    def __init__(self, designator, rte):
        self.designator = designator
        self.end_fix = designator[: -2]

    def __str__(self):
        return self.designator

    def __repr__(self):
        s = "SID(%r, %s, end_fix: %s)" % (
            self.designator, self.rte, self.end_fix)
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


class STAR(object):
    # TODO this only covers basic AICM attributes.
    # We need to support the whole procuedure_leg object in order to
    # to support things like SLP and vertical limitations

    def __init__(self, designator, rte):
        self.designator = designator
        self.rte = Route.Route(Route.get_waypoints(rte))
        self.start_fix = designator[: -2]

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

    def __init__(self, designator, rte):
        self.designator = designator
        self.rte = Route.Route(Route.get_waypoints(rte))
        self.end_fix = designator[: -2]

    def __str__(self):
        return self.designator

    def __repr__(self):
        s = "SID(%r, %s, end_fix: %s)" % (
            self.designator, self.rte, self.end_fix)
        return s

