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
from builtins import object

from . import AIS
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
        speedInterpretation=None,
        role=None                   # Insignia. Currently unsupported and not sure if necessary
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
        self.role = role

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

        # Not in use yet, but they will have to to support LEMD, for example
        self.departureRunways = None    # List of RunwayDirection
        self.arrivalRunways = None      # List of RunwayDirection

    def get_sid(self, designator):
        return [sid for rwy in self.runwayDirections
                for sid in rwy.stdInstDepartures.values()
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

        self.stdInstDepartures = {}
        self.stdInstArrivals = {}
        self.iap_dict = {}

    def __str__(self):
        return self.designator

    def __repr__(self):
        s = ("RunwayDirection(designator=%r%s)" % (
            self.designator,
            attr_repr(self, ('trueBearing', 'elevationTDZ', 'usedRunway',
                             'stdInstArrivals', 'stdInstDepartures',
                             'iap_dict'))))
        return s


class Runway(object):
    def __init__(self, designator, associatedAirportHeliport):
        self.associatedAirportHeliport = associatedAirportHeliport


class Hold(object):
    # TODO this does not reflect AICM. We need to support the whole
    # procedure_leg in order to do this

    def __init__(
            self,
            holdingPoint,               # AIXM. Point on which the the holding pattern is based.
            inbd_track=180,             # Inbound track of the holding pattern
            outbd_time=1,               # For how long to fly on the outbd track
            std_turns=True,             # Standard turns are to the right
            min_FL=000,                 # Mininum FL
            max_FL=999):                # maximun FL at the holding pattern

        assert type(holdingPoint) is Point

        self.holdingPoint = holdingPoint
        self.inbd_track = inbd_track
        self.outbd_time = outbd_time
        self.std_turns = std_turns
        self.min_FL = min_FL
        self.max_FL = max_FL


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

