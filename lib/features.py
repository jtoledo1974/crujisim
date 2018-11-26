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

import logging
import inspect

from . import Route

# Vertical Distance UOM
FL = 'FL'

# Future
standard_library.install_aliases()


class Feature(object):
    """Base class for features"""

    def __str__(self):
        return self.designator if hasattr(self, 'designator') else repr(self)

    def __repr__(self):

        def argrepr(argname):
            value = getattr(self, arg)

            if not hasattr(self, '_strargs') or arg not in self._strargs:
                return repr(value)

            if type(value) not in (list, dict, tuple):
                return str(value)

            if type(value) in (list, tuple, dict):
                return str([str(item) for item in value])

            logging.warning("Unhandled argument type %s for argument %s" % (type(value), value))
            return repr(value)

        # getargspec is deprecated, but the default in python 2
        args, varargs, kwargs, defaults = inspect.getargspec(self.__init__)

        defaults = defaults if defaults is not None else []
        n_defaults = len(defaults)

        attr_list = []
        arglist = args[1:-n_defaults] if n_defaults > 0 else args[1:]

        for arg in arglist:  # Arguments with no default
            attr_list.append("%s" % (argrepr(arg), ))

        for arg, default in zip(args[-n_defaults:], defaults):
            value = getattr(self, arg)
            if value != default:
                attr_list.append("%s=%s" % (arg, argrepr(arg)))

        res = "%s(%s)" % (self.__class__.__name__, ', '.join(attr_list))
        return res


# There are all kind of points defined both in AIXM and Insignia
# This is the bare minimum needed
class Point(Feature):
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


class AirportHeliport(Feature):  # Aerodrome / Heliport

    def __init__(
            self,
            designator,       # ICAO. AIXM allows others. Insignia ICAO_TXT
            pos=None,         # Old crujisim fir files didn't have airport positions
            fieldElev=0,      # Feet. AIXM name. Insignia ELEV_VAL in meters
            runwayDirections=[],
            rwyInUse=None,
            departureRunways=None,
            arrivalRunways=None
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

        self._strargs = ['runwayDirections', 'departureRunways', 'arrivalRunways']

    def get_sid(self, designator):
        return [sid for rwy in self.runwayDirections
                for sid in rwy.stdInstDepartures.values()
                if sid.designator == designator][0]


class RunwayDirection(Feature):

    def __init__(
            self,
            designator,             # AIXM
            trueBearing=None,       # AIXM
            elevationTDZ=None,      # AIXM, Insignia ELEVATIONTDZ (insignia in meters, has to be converted)
            usedRunway=None,        # Pointer to Runway instance
            stdInstDepartures={},
            stdInstArrivals={},
            iap_dict={}
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

        self._strargs = ['stdInstArrivals', 'stdInstDepartures', 'iap_dict']


class Runway(Feature):
    def __init__(self, designator, associatedAirportHeliport):
        self.associatedAirportHeliport = associatedAirportHeliport


class HoldingPattern(Feature):
    # TODO this does not reflect AICM. We need to support the whole
    # procedure_leg in order to do this

    def __init__(
            self,
            holdingPoint,               # AIXM. Point on which the the holding pattern is based.
            inboundCourse=180,          # AIXM. Inbound track of the holding pattern. Insignia has them all as magnetic, so we don't bother to implement anything else for now
            endTime=1,                  # AIXM. For how long to fly on the outbd track in minutes. There are about 163 holding in Insignia with point references. Unsupported by now.
            std_turns=True,             # Standard turns are to the right. TODO Need to change to turnDirection and use a constant. About half in insignia are to the left
            lowerLimit=000,             # AIXM. These four are unused for now
            lowerLimitReference=FL,
            upperLimit=999,
            upperLimitReference=FL):

        assert type(holdingPoint) is Point

        self.holdingPoint = holdingPoint
        self.inboundCourse = inboundCourse
        self.endTime = endTime
        self.std_turns = std_turns
        self.lowerLimit = lowerLimit
        self.lowerLimitReference = lowerLimitReference
        self.upperLimit = upperLimit
        self.upperLimitReference = upperLimitReference


class STAR(Feature):
    # TODO this only covers basic AICM attributes.
    # We need to support the whole procuedure_leg object in order to
    # to support things like SLP and vertical limitations

    def __init__(self, designator, rte):
        self.designator = designator
        self.rte = Route.Route(Route.get_waypoints(rte))
        self.start_fix = designator[: -2]


class SID(Feature):
    # TODO this only covers basic AICM attributes.
    # We need to support the whole procuedure_leg object in order to
    # to support things like SLP and vertical limitations

    def __init__(self, designator, rte):
        self.designator = designator
        self.rte = Route.Route(Route.get_waypoints(rte))
        self.end_fix = designator[: -2]
