#!/usr/bin/python
#-*- coding:iso8859-15 -*-
# $Id$
# (c) 2005 CrujiMaster (crujisim@crujisim.cable.nu)
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
"""Tratamiento Local de Planes de Vuelo / Local Flight Plan Processing"""
from past.builtins import cmp
from builtins import range
from builtins import object

import logging
import random
import datetime

from . import AIS
from . import Route
from . import MathUtil
from . import StripSeries

# random.seed(0)  # So that we can replicate the squawks created

# Constants
PENDING = 0  # Pending
COORDINATED = 1  # Coordinated
PREACTIVE = 2  # Preactive
ACTIVE = 3  # Active


def sector_intersections(route):
    """Given a fp, add waypoints in the intersections of the route with
    the FIR sectors"""
    rte_orig = route[:]

    # Remove previous TLPV waypoints
    for wp in (wp for wp in rte_orig[:] if wp.type == Route.TLPV):
        rte_orig.remove(wp)

    n_added = 0  # Number of added intersections
    for i in range(len(rte_orig) - 1):
        xpoints = []
        for name, boundary in AIS.boundaries.items():
            xp_list = MathUtil.get_entry_exit_points(
                rte_orig[i].pos(), rte_orig[i + 1].pos(), boundary)
            for xp in xp_list:
                xp.append(name)
            xpoints += xp_list
        # Sort according to distance to the first waypoint
        xpoints.sort(key=lambda x: x[2])
        for xp in xpoints:
            wp = Route.WayPoint("X%fY%f" %
                                (xp[1][0], xp[1][1]), type=Route.TLPV)
            if xp[0] == MathUtil.ENTRY:
                wp.sector_entry = xp[3]
            else:
                wp.sector_exit = xp[3]
            route = route[:i + 1 + n_added] + \
                Route.Route([wp]) + route[i + 1 + n_added:]
            n_added += 1

    # If the first point in the route is within a known sector, make sure we
    # note it.
    for sector, boundary in AIS.boundaries.items():
        if MathUtil.point_within_polygon(route[0].pos(), boundary):
            route[0].sector_entry = sector
            n_added += 1

    if not n_added:
        logging.warning("No sector entry points found in %s" % str(route))

    return route  # Eliminates redundancy


def get_exit_ades(flight):
    """Given an Aircraft or a flight plan returns either a the first three letters of the last waypoint
    local to the FIR, or the last two letters of the adep local to the FIR"""
    if flight.ades in AIS.aerodromes:
        return flight.ades[2:]
    # Else
    fet = None
    # If it's a TLPV flight plan and fir_exit_t is already calculated:
    if hasattr(flight, 'fir_exit_t') and flight.fir_exit_t:
        fet = flight.fir_exit_t
    else:
        try:
            fet = max([wp.eto for wp in flight.route if wp.sector_exit])
        except:
            fir_exit_t = None
    if fet:
        exit_wp = [wp for wp in flight.route if wp.eto >=
                   fet and wp.type == Route.WAYPOINT][0]
        return exit_wp.fix[:3]
    else:
        logging.debug("Unable to find exit or ades for %s" % flight.callsign)
        return flight.campo_eco


class TLPV(object):
    """Keeps track of flight plans in the system"""
    # TODO in order to keep the implementation simple there cannot be two
    # flightplans sharing the same callsign

    def __init__(self, exercise_name=''):
        self.squawks = []  # List of xpndr codes already assigned
        self.flightplans = []  # List of known flightplans
        self.exercise_name = exercise_name
        pass

    def create_fp(self, callsign, type, adep, ades, rfl, ecl, rte,
                  eobt=None, next_wp=None, next_wp_eto=None,
                  init=True):
        """Creates a new flight plan
        Either the eobt or (next_wp and eto) are mandatory in order to calculate estimates"""

        fp = FlightPlan(callsign, type, adep, ades, rfl, ecl, rte,
                        eobt=eobt, next_wp=next_wp, next_wp_eto=next_wp_eto)
        self.flightplans.append(fp)

        # Assign a squawk code
        fp.squawk = self.get_squawk()

        # Calculate intersections with sectors
        #fp.route = sector_intersections(fp.route)

        # Save sector entry times for each flight plan
        for wp in fp.route:
            if wp.sector_entry and wp.sector_entry not in fp.sector_entry_t:
                fp.sector_entry_t[wp.sector_entry] = wp.eto

        # As there is not yet support for a proper FIR boundary in AIS.py,
        # we define the first sector entry time as the FIR entry time
        try:
            fp.fir_entry_t = min(fp.sector_entry_t.values())
        except:
            fp.fir_entry_t = None
        if fp.ades not in AIS.aerodromes:
            try:
                fp.fir_exit_t = max(
                    [wp.eto for wp in fp.route if wp.sector_exit])
            except:
                fp.fir_exit_t = None
        else:  # Ades is local
            fp.fir_exit_t = None

        return fp

    def get_squawk(self):
        """Returns a random available squawk code"""
        # NOTE In python, the int literal 010 is interpreted in octal,
        # that is, 010 (octal) equals 8 (decimal)
        # TODO this would be inefficient if we had lots of flights,
        # but should do by now considering how little flights we are dealing
        # with
        while True:
            r = random.randint(0o100, 0o6777)  # Between 0100 and 6777 octal
            if r in self.squawks or r in range(0o2000, 0o2777):
                continue
            else:
                break
        return r

    def start(self):
        """Initialize TLPV"""
        # Calculate flight strip print times
        pass
        for sector in AIS.sectors:
            fpl = [fp for fp in self.flightplans if sector in fp.sector_entry_t]
            for fp in fpl:
                fp.fs_print_t[sector] = fp.sector_entry_t[
                    sector] - datetime.timedelta(minutes=10)

    def get_sector_flightstrips(self, sector):
        """Returns a list of FlightStripData objects containing all flight strips for the sector"""

        name = self.exercise_name

        fs_list = []

        fpl = [fp for fp in self.flightplans if sector in fp.sector_entry_t]
        fpl.sort(lambda p, q: cmp(p.fs_print_t[sector], q.fs_print_t[sector]))
        for a in fpl:

            # Flight Strip creation

            # First we determine whether this flight will pass any of the
            # primary flight strip printing points. If it doesn't, then
            # it will use the secondary flight strip printing points instead
            current_printing_fixes = AIS.fijos_impresion_secundarios[sector]
            at_least_one_strip_printed = False
            for i in range(len(a.route)):
                for fix in AIS.fijos_impresion[sector]:
                    if a.route[i].fix == fix:
                        current_printing_fixes = AIS.fijos_impresion[sector]

            route = ''
            for wp in [wp for wp in a.route if wp.type == Route.WAYPOINT]:
                route += wp.fix + ' '

            def format_t(t): return '%02d%02d' % (t.hour, t.minute)

            # Common data
            cfd = StripSeries.FlightStripData()
            cfd.callsign = a.callsign
            cfd.exercice_name = name
            cfd.ciacallsign = a.radio_callsign
            cfd.model = a.type
            cfd.wake = a.wake
            cfd.speed = "%04d" % a.filed_tas
            cfd.responder = "C"
            cfd.origin = a.adep
            cfd.destination = a.ades
            cfd.fl = "%d" % a.rfl
            # If the plane departs from a local airport, cfl is not printed
            if a.adep in AIS.local_ads[sector]:
                cfd.cfl = ""
            else:
                cfd.cfl = "%d" % a.ecl

            cfd.cssr = "%04o" % a.squawk
            cfd.route = route
            cfd.rules = ""
            cfd.print_time = format_t(a.fs_print_t[sector])
            try:
                cfd.eobt = format_t(a.eobt)
            except:
                cfd.eobt = ''

            # Print a coord flight strip if it's a departure from an AD we have
            # to release
            if a.adep in AIS.local_ads[sector]:
                fd = cfd.copy()
                fd.fs_type = "coord"
                fs_list.append(fd)

            # Print a flight strip for every route point which is any of the
            # current_printing_fixes

            if a.adep in AIS.local_ads[sector]:
                prev = a.adep
                prev_t = format_t(a.eobt)
            else:
                prev = prev_t = ''
            for i in range(len(a.route)):
                if i >= 1 and a.fir_entry_t and a.route[i - 1].eto < a.fir_entry_t:
                    prev = 'ENTRAD'
                    prev_t = format_t(a.route[i].eto)
                elif i >= 1 and a.route[i - 1].type not in (Route.TLPV, Route.FMS):
                    prev = a.route[i - 1].fix
                    prev_t = format_t(a.route[i - 1].eto)

                if a.route[i].fix in current_printing_fixes:
                  # Main flight strip fix
                    fijo = a.route[i].fix
                    t = a.route[i].eto
                    fijo_t = '%02d%02d' % (t.hour, t.minute)
                    # Find next printable waypoint
                    try:
                        j = i + 1
                        while True:
                            if a.route[j].type == Route.WAYPOINT:
                                next = a.route[j].fix
                                next_t = format_t(a.route[j].eto)
                                break
                            j += 1
                    except:
                        next = ''
                        next_t = ''
                    if next == '' and a.ades in AIS.local_ads[sector]:
                        # Printing fix is last route point and adep is local
                        next = a.ades
                        next_t = ''
                    elif i < len(a.route) - 1 and a.fir_exit_t and a.route[i + 1].eto > a.fir_exit_t:
                        # Next waypoint marks FIR exit
                        next = 'SALIDA'
                        next_t = format_t(a.route[i + 1].eto)

                    fd = cfd.copy()
                    fd.prev_fix = prev
                    fd.fix = fijo
                    fd.next_fix = next
                    fd.prev_fix_est = prev_t
                    fd.fix_est = fijo_t
                    fd.next_fix_est = next_t
                    fd.ecl = "%d" % a.ecl
                    fs_list.append(fd)

        return fs_list

    def exit(self):
        self.flightplans = []
        self.squawks = []

    def __del__(self):
        logging.debug("TLPV.__del__")


class FlightPlan(object):

    def __init__(self, callsign, type, adep, ades, rfl, ecl, rte,
                 eobt=None, next_wp=None, next_wp_eto=None,
                 init=True):

        if (next_wp and not next_wp_eto) or (not next_wp and next_wp_eto):
            raise("Unable to calculate flight profile, either the next waypoint or the eto for the next waypoint is missing")
        if not next_wp and not next_wp_eto and not eobt:
            raise(
                "Either the EOBT, or the next waypoint and its ETO are mandatory parameters")

        self.callsign = callsign
        self.radio_callsign = ''
        self.set_callsign(callsign)
        self.adep = adep
        self.ades = ades
        self.type = type
        self.eobt = eobt
        self.rfl = rfl
        self.ecl = ecl
        self.filed_tas = None
        self.route = Route.Route(Route.get_waypoints(rte))
        # Next WP  (in SACTA terminology this is the Entry Point (Punto de
        # Entrada)
        self.next_wp = None
        self.next_wp_eto = None
        self.squawk = None
        self.squawk_alt = None
        self.status = None  # Pending, Coordinated, Preactive, Active
        self.ucs = None  # Which UCS is controlling it
        self.track = None  # If the flight is being tracked through the TDR, this links to the Track
        self.sector_entry_t = {}    # Sector entry times for each of the sectors it traverses
        self.fs_print_t = {}    # Printing time of the flight strips for each sector
        # Time it first enters our FIR (local departures do count)
        self.fir_entry_t = None
        self.fir_exit_t = None  # Time it leaves the FIR (if ever)

    def set_callsign(self, cs):
        from . import Aircraft  # Imported here to prevent a cyclic import
        self.callsign = cs = cs.strip().upper()
        self.radio_callsign = Aircraft.get_radio_callsign(cs)

    # def __del__(self):
    #    logging.debug("FlightPlan.__del__ %s"%self.callsign)
