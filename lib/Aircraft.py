#!/usr/bin/python
# -*- coding:utf-8 -*-
# $Id$
#
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

"""Contains the Aircraft class, which models an aircraft flying a given route
and following ATC commands"""
from builtins import zip
from builtins import str
from builtins import range
from builtins import object

# Module imports
from configparser import ConfigParser
from .MathUtil import *

from math import pi, tan, asin
import codecs
import logging
from datetime import timedelta

from . import AIS
from . import BADA
from . import Route
from . import TLPV  # This is used as an optimization in set_route. Could be removed
from . import LNAV

# Constants
from . import CALLSIGN_FILE

LEFT = "LEFT"
RIGHT = "RIGHT"

# TODO These will be taken out of here and into TLPV
PREACTIVE = "PREACTIVE"
READY = "READY"

# Phases of flight

# Currently only using CRUISE to mean FLYING. The others will be of use when we implement
# a proper VNAV and BADA performance calculations
LOADING = "0-LOADING"  # Internal status before the aircraft is 'ready to fly'
INACTIVE = "0b-INACTIVE"  # Prior to the aircraft entering the first route point
GROUND = "1-GROUND"   #
TAKEOFF = "2-TAKEOFF"
INITIAL_CLIMB = "3-INITIAL_CLIMB"
CLIMB = "4-CLIMB"
CRUISE = "5-CRUISE"
DESCENT = "6-DESCENT"
APPROACH = "7-APPROACH"
LANDED = "8-LANDED"

# Subphases of flight
# Flying
# After the aircraft reached its final waypoint and it's coasting along
COASTING = "COASTING"

# LNAV and VNAV
from .LNAV import NAV, APP, RWY, LOC, LOC_CAPTURE, HOLD, HDG, TRK, HDG_FIX, INT_RDL, ORBIT

# Globals

a = BADA.Atmosphere()
tas_from_cas = a.get_tas_from_cas
cas_from_tas = a.get_cas_from_tas
tas_from_mach = a.get_tas_from_mach
mach_from_tas = a.get_mach_from_tas

# TODO Wind should be a properperty of the Atmosphere object
# and we would probably like to model the wind gradient and
# the wind direction backing with raising altitude
wind = [0.0, 0.0]

callsigns = {}  # Callsign database

# GTA.py sets fir as a module global

# Load the callsign database


def load_callsigns():
    global callsigns
    cf = ConfigParser()
    f = codecs.open(CALLSIGN_FILE, "r", "utf8")
    cf.read_file(f)
    f.close()
    callsigns = {}
    for cs, rcs in cf.items('Callsigns'):
        callsigns[cs.upper()] = rcs.upper()


load_callsigns()


def get_radio_callsign(cs):
    global callsigns
    try:
        rc = callsigns[cs.strip("*")[:3]]
    except Exception:
        rc = ''
        logging.debug("No radio callsign for " + cs)
        callsigns[cs.strip("*")[:3]] = ''
    return rc


def v(self):
    """Returns the target TAS to acquire"""
    # Devuelve TAS
    if not self.std_speed:  # Velocidad mínima manteniedo IAS
        try:
            return tas_from_cas(self.tgt_ias, self.lvl * 100)
        except Exception:
            logging.error("Error setting standard TAS for %s" %
                          self.callsign, exc_info=True)
            return 250.
    if self.perf.bada:
        if self.lvl is not None:
            lvl = self.lvl
        else:
            lvl = 0  # In python 2 None acts as 0 when compared. Not in python 3
        if lvl < self.cfl:
            tas = self.perf.get_climb_perf(lvl)[0]
        elif lvl > self.cfl:
            tas = self.perf.get_descent_perf(lvl)[0]
        else:
            tas = self.perf.get_cruise_perf(lvl)[0]
        return tas

    # TODO we should delete all the following. We should simply have equivalents for
    # all known aircraft to the BADA models

    if self.perf.max_fl > 290.:  # Fast moving traffic
        inicio_app = 00.
        trans_tma = 50.
        vel_tma = 150.
    elif self.perf.max_fl > 200.:  # Medium speed traffic
        inicio_app = 00.
        trans_tma = 35.
        vel_tma = 80.
    else:
        inicio_app = 00.
        trans_tma = 25.
        vel_tma = 35.

    if self.lvl <= inicio_app:  # Velocidad de aproximación
        return self.perf.app_tas
    elif self.lvl <= trans_tma:  # Transición entre vel aprox y tma
        p = (self.lvl - inicio_app) / (trans_tma - inicio_app)
        return self.perf.app_tas * (1. - p) + self.perf.tma_tas * p
    elif self.lvl <= vel_tma:  # Transición entre ruta y tma
        p = (self.lvl - trans_tma) / (vel_tma - trans_tma)
        ias_std = self.perf.cruise_tas / (1 + 0.002 * self.perf.max_fl * 0.90)
        return self.perf.tma_tas * (1. - p) + ias_std * (1.0 + 0.002 * self.lvl) * p
        #    return self.perf.tma_tas
    else:
        ias_std = self.perf.cruise_tas / (1 + 0.002 * self.perf.max_fl * 0.90)
        return min(ias_std * (1 + 0.002 * self.lvl), self.perf.max_tas)
        #     p=min((self.lvl-vel_tma)/(self.perf.max_fl-vel_tma),1.)
        # return min(self.perf.max_tas * p + self.perf.tma_tas *
        # (1-p),self.perf.cruise_tas)


def f_vert(self):
    # Devuelve factor corrección de velocidad vertical
    # TODO Probably this is unneeded now that we have a the BADA summary table
    q = self.lvl / self.perf.max_fl
    if q < .75:
        return 1.0
    elif q < .90:
        return 0.80
    else:
        return 0.60


class Aircraft(object):

    # All aircraft are uniquely identified. We keep the maximum number used
    # here.
    max_uid = 0

    def __init__(self, callsign, type, adep, ades, cfl, rfl, rte,
                 eobt=None, next_wp=None, next_wp_eto=None, wake_hint=None,
                 init=True):

        if not init:
            return  # The instance will be used as a copy in Aircraft.copy

        if (next_wp and not next_wp_eto) or (not next_wp and next_wp_eto):
            raise("Unable to calculate flight profile, either the next waypoint or the eto for the next waypoint is missing")
        if not next_wp and not next_wp_eto and not eobt:
            raise(
                "Either the EOBT, or the next waypoint and its ETO are mandatory parameters")

        self.no_estimates = False  # If True we skip calculating estimates
        # Used to avoid recursion
        # and avoiding calling sector_intersection
        # which stops the GTA thread for unknown reasons

        self.uid = None  # Unique identifier. Set at the end of the init
        self.callsign = None  # 'IBE767'
        self.radio_callsign = None  # 'IBERIA'
        self.set_callsign(callsign)
        self.type = None  # 'B747'
        self.wake = None  # 'H' Wake turbulence category
        # We can use this to give default perf values if type is unknown
        self.wake_hint = wake_hint
        self.set_type(type)
        self.adep = adep  # 'LEBB'
        self.ades = ades  # 'LEMD'
        self.cfl = cfl   # Cleared Flight Level, the FL the aircraft is climbing/descending towards
        self.rfl = rfl   # Requested Flight Level. As filed in the flight plan
        self.ecl = rfl   # Planned Flight Level.
        # TODO This should not be an aircraft attribute,
        # but rather a TLPV.FlightPlan attribute

        self.pof = LOADING  # Phase of flight
        self.spof = None  # Subphase of flight

        # Time attributes (Datetime instances)
        self.eobt = eobt  # Estimated off block time
        self.next_wp = next_wp
        self.next_wp_eto = next_wp_eto
        self.next_wp_check_t = None  # When to check if waypoint reached
        self.t = None

        self.route = None  # Route object (Route.py)
        self.sid = None  # SID to be flown
        self.star = None  # STAR to be flown
        self.set_route(rte)
        self.log = Route.Route()    # A Route object to keep track of flight progress
        # (0.0,0.0) x,y (Cartesian coordinates in nautical miles)
        self.pos = None
        # This just sets an initial value. The correct value is done on
        # initialize()
        if eobt:
            self.t = self.eobt
        else:
            self.t = self.next_wp_eto
        self.next_wp_check_t = self.t

        self.auto_depart = True  # Whether or not it departs automatically

        self.hdg = None  # Last calculated heading (deg magnetic)
        self.track = None  # Last calculated track (deg magnetic)
        self.tgt_hdg = None  # Target heading to acquire (deg magnetic)
        # TODO we are not currently simulating a transition altitude
        # In order to do so we should keep track of both the altitude and
        # the flight level
        self.lvl = None  # Flight Level
        self.std_rate = True  # Whether the acft will climb/descend using standard rates
        # TODO Notice there is no tgt_rocd. The aircraft changes its rate of climb or descent
        # instantaneously. We might want to revise this.
        # TODO rocd should really be measured in feet per minute
        self.rocd = 0.0   # Rate Of Climb or Descent (flight levels per hour)
        self.tas = 0.0   # True Air Speed (knots)
        self.ground_spd = 0.0   # Ground Speed (knots)
        # TODO We probably don't need this here, but in TLPV (knots)
        self.filed_tas = None
        self.std_speed = True  # Use standard speed for phase of flight
        # Indicated Air Speed (and for our purposes, it's the same as CAS)
        # (knots)
        self.ias = 0.0
        self.tgt_ias = None  # Target IAS to acquire (knots)

        self.lnav_mode = NAV        # LNAV mode
        self.lnav_armed = ""        # LNAV armed mode
        self.to_do_aux = ''
        self.squawk = None  # Mode A transpoder code the aircraft is squawking

        # TLPV calculated fields to support using the Pseudopilot display as a
        # controller
        self.fs_print_t = None
        self.campo_eco = ''
        # IAP related attributes
        self.app_auth = False
        self.iaf = ''
        self._map = False
        self.int_loc = False
        self.esta_en_llz = False
        self.reports = []  # List of things an aircraft should report.
        # [{'time':1.65,'text':'Request climb FL230'},
        #  ,{'time':2.34,'text':'Overflown DGO'}]

        self.pp_pos = None  # Pseudopilot position "piloting" this aircraft
        # TODO atc_pos should be an attribute of a TPV flight, not of the
        # aircraft
        self.atc_pos = None  # UCS controlling this flight
        self.trans_pp_pos = False  # Set to TRUE when ACFT is being transferred by a PP position
        # Set tu TRUE when ACFT is being transferred by a ATC position
        self.trans_atc_pos = False

        if init is True:
            self.initialize()

        Aircraft.max_uid = self.uid = Aircraft.max_uid + 1

    def initialize(self):
        # Init code
        self.std_speed = True
        if not self.next_wp:
            self.pof = GROUND
        else:
            self.pof = CRUISE

        if self.pof == CRUISE:
            self.ground_spd = self.tas = v(self)
            self.lvl = self.cfl
        else:  # GROUND
            self.lvl = AIS.aerodromes[self.adep].fieldElev
            # We need to start up with an initial speed because the
            # accelaration code is not realistic
            self.ground_spd = self.tas = 60.
        self.ias = cas_from_tas(self.tas, self.lvl * 100)

        self.pos = self.route[0].pos
        self.set_app_fix()
        self.track = self.hdg = self.route.get_outbd_track(0)

        # Bearing to the next navigation point, whether a waypoint in the route,
        # or an intermediate point for a capture maneuver
        self.vect = self.get_bearing_to_next()  # Actually (distance, angle)

        self.calc_eto()
        if self.next_wp_eto:
            if self.next_wp not in [wp.fix for wp in self.route]:
                raise "Unable to create flight. Estimate waypoint (%s) not in the route (%s)"
            delta = self.route[self.next_wp].eto - self.next_wp_eto
            for wp in self.route:
                try:
                    wp.eto -= delta
                except Exception:
                    pass
            self.t -= delta

        self.set_campo_eco()

    def __getstate__(self):
        """This function is called by the pickler. We remove the attributes
        that we don't want to send through the wire"""
        odict = self.__dict__.copy()
        try:
            del odict['perf']
        except Exception:
            pass
        return odict

    def __str__(self):
        s = "%s - %s" % (self.callsign, self.pof)
        try:
            s = "%s - %s" % (s, self.route[0])
        except IndexError:
            pass
        return s

    def get_vertical_speed(self):
        """Returns current vertical speed in levels per hour"""
        if self.std_rate and self.pof == CRUISE:
            if self.cfl > self.lvl:
                vs = self.perf.std_roc * f_vert(self)
                if self.perf.bada:
                    vs = self.perf.get_climb_perf(self.lvl)[
                        2] * 60. / 100
            elif self.cfl < self.lvl:
                vs = -min(self.tas / 0.2 / 100. * 60.,
                          self.perf.max_rod * f_vert(self))
                if self.perf.bada:
                    vs = - \
                        self.perf.get_descent_perf(self.lvl)[1] * 60. / 100
            else:   # CFL == LVL
                vs = 0.
            return vs     

        # Vertical speed is not according to model, but fixed. Keep the one we have.
        return self.rocd

    def get_altitude(self, delta_hours):
        """Returns current altitude"""

        self.rocd = self.get_vertical_speed()  # Levels per hour

        delta_levels = self.rocd * delta_hours
        if abs(self.lvl - self.cfl) < abs(delta_levels):
            self.rocd = 0.
            self.std_rate = True
            return self.cfl
        else:
            return self.lvl + delta_levels

    def next(self, t):
        """Advance simulation to time t"""
        global wind
        # logging.debug("%s: %s"% (self.callsign, t))

        # Determine current phase of flight
        try:
            if self.pof == GROUND and t > self.eobt and self.auto_depart:
                self.pof = TAKEOFF
        except TypeError:
            logging.error(
                "Type error when checking phase of flight of %s, assuming departure" % self.callsign)
            self.pof = TAKEOFF

        if t < self.t and self.pof == CRUISE:
            self.pof = INACTIVE
            return

        if t > self.t and self.pof == INACTIVE:
            self.pof = CRUISE

        # With this we make sure that the simulation doesn't advance
        # in steps bigger than 15 seconds
        if (t - self.t) > timedelta(seconds=15):
            ne_backup = self.no_estimates
            self.no_estimates = True
            t2 = self.t + timedelta(seconds=15)
            while (t - self.t) > timedelta(seconds=15) and self.pof != LANDED:
                self.next(t2)
                t2 += timedelta(seconds=15)
            self.no_estimates = ne_backup

        # Delta hours (fractional hours since the last update)
        dh = (t - self.t).seconds / 3600. + \
            (t - self.t).microseconds / 3600. / 1000000

        # New altitude
        self.lvl = self.get_altitude(dh)

        # Iteración para encontrar la posición
        while t >= self.t + timedelta(seconds=1):
            aux_v = v(self)
            inc_v_max = 1.5 * dh * 60. * 60.  # Inc. v = 90kts/min TAS
            if abs(aux_v - self.tas) < inc_v_max or self.tas == 0.:
                self.tas = aux_v
            else:
                self.tas = self.tas + inc_v_max * sgn(aux_v - self.tas)
            if self.tas >= aux_v * .8 and self.pof == TAKEOFF:
                self.pof = CRUISE

            self.ias = cas_from_tas(self.tas, self.lvl * 100)
            (vx, vy) = pr((1.0, self.track))
            (wx, wy) = pr(wind)
            wind_perp = wx * vy - wy * vx
            wind_paral = wx * vx + wy * vy
            self.ground_spd = self.tas + wind_paral

            wind_drift = degrees(asin(wind_perp / self.tas)) if self.tas > 0 else 0
            target_hdg = LNAV.get_target_heading(self, wind_drift, t)

            if target_hdg == LANDED:
                self.pof = LANDED
                return

            if self.hdg < 180.0 and target_hdg > self.hdg + 180.0:
                target_hdg = target_hdg - 360.0
            elif self.hdg > 180.0 and target_hdg < self.hdg - 180.0:
                target_hdg = target_hdg + 360.0

            aux = target_hdg - self.hdg
            rot = self.get_rot() * 60 * 60  # Rate of turn in degrees per hour
            if abs(aux) < rot * dh:
                self.hdg = target_hdg % 360
            else:
                self.hdg = (self.hdg + dh * rot * sgn(aux)) % 360
            self.track = (self.hdg + wind_drift) % 360

            # Distancia recorrida en este inc. de t incluyendo viento
            self.salto = self.ground_spd * dh

            # Ha pasado el punto al que se dirige
            if self.salto > self.vect[0] or self.waypoint_reached():
                # logging.debug("%s: passed %s" % (self.callsign, self.route[0]))
                if len(self.route) == 1:
                    if self.app_auth and AIS.ad_has_ifr_rwys(self.ades):
                        self.lnav_mode in (LOC_CAPTURE, LOC)
                        self.salto = self.tas * dh  # Distancia recorrida en este inc.de t sin viento
                        # Deriva por el viento
                        efecto_viento = (wx * dh, wy * dh)
                        self.t = t

                    # Si el último punto está en la lista de aeropuertos,
                    # orbita sobre él
                    elif self.route[0].fix in AIS.aerodromes:
                        if self.lnav_mode == NAV:  # En caso de que llegue a ese punto en ruta
                            try:
                                ph = [
                                    hold for hold in AIS.holds if hold.fix == self.route[0].fix][0]
                                self.lnav_mode = HOLD
                                if ph.std_turns is True:
                                    turn = 1.0
                                else:
                                    turn = -1.0
                                self.to_do_aux = [ph.fix, ph.inboundCourse,
                                                  timedelta(
                                                      minutes=ph.outbd_time),
                                                  0.0, True, turn]
                            except Exception:
                                pass
                            if len(self.route) == 1:  # En caso contrario, hace una espera de 1 min
                                self.lnav_mode = HOLD
                                self.to_do_aux = [self.route[0], self.hdg, timedelta(
                                    minutes=1), 0.0, True, 1.0]

                        self.salto = self.tas * dh  # Distancia recorrida en este inc.de t sin viento

                        # Deriva por el viento
                        efecto_viento = (wx * dh, wy * dh)
                        self.t = t

                    else:
                        # Aircraft has reached its final waypoint, and its not known
                        # airport, so we just coast along
                        self.lnav_mode = HDG
                        self.to_do_aux = [self.hdg, 'ECON']
                        self.tgt_hdg = self.hdg
                        self.salto = self.tas * dh  # Distancia recorrida en este inc.de t sin viento
                        # Deriva por el viento
                        efecto_viento = (wx * dh, wy * dh)
                        self.t = t
                        self.spof = COASTING
                else:
                    self.salto = self.tas * dh  # Distancia recorrida en este inc.de t sin viento
                    efecto_viento = (wx * dh, wy * dh)  # Deriva por el viento
                    self.t += timedelta(hours=dh)  # Almacenamos el tiempo
                self.log_waypoint()  # Pops the old waypoint, and saves it in the log
                if not self.no_estimates:
                    self.calc_eto()

            else:
                self.salto = self.tas * dh  # Distancia recorrida en este inc.de t sin viento
                efecto_viento = (wx * dh, wy * dh)  # Deriva por el viento
                self.t = t  # Almacenamos el tiempo

            self.pos = s(s(self.pos, pr((self.salto, self.hdg))),
                         efecto_viento)  # Cambiamos la posición
        self.t = t

    def calc_eto(self):
        """Cálculo del tiempo entre fijos"""

        if self.no_estimates:
            return

        last_point = False
        sim = self.copy()
        sim.no_estimates = True
        del sim.log[:]  # Remove previously logged points

        inc_t = timedelta(seconds=15)
        while not last_point:
            t = sim.t + inc_t
            sim.next(t)
            if not sim.lnav_mode == NAV:
                last_point = True

        # Copy the ATOs of the simulated aircraft as our estimates
        for rwp, swp in zip(self.route, sim.log):
            rwp.eto = swp.ato
        return self.route

    def set_callsign(self, cs):
        self.callsign = cs = cs.strip().upper()
        self.radio_callsign = get_radio_callsign(cs)

    def set_route(self, points):
        """Takes a comma or spaced separated list of points and sets and
        replaces the aircraft route"""
        self.route = Route.Route(Route.get_waypoints(points))
        # In order to save processing time, we add the sector intersection
        # waypoints ahead of time, so that when the Aircraft calculates its ETO,
        # there already are ETOs for the TLPV important points as well.
        if not self.no_estimates:
            for wp in [wp for wp in self.route[:] if wp.type == Route.TLPV]:
                self.route.remove(wp)
        self.complete_flight_plan()
        if not self.no_estimates:
            self.route = TLPV.sector_intersections(self.route)
        self.route = self.route.reduce()

    def set_dest(self, ades):
        # TODO we should do proper validation here
        self.ades = ades
        self.set_campo_eco()

    def complete_flight_plan(self):
        """Adds SID and/or STAR to the route if one is published"""

        # TODO should this function be really an Aircraft method?
        # or rather a Route method, or even a FIR method?
        if AIS.ad_has_ifr_rwys(self.ades):  # aplico la STAR que toque
            ad = AIS.aerodromes[self.ades]
            star_list = [star for star in ad.rwyInUse.stdInstArrivals.values()
                         if star.start_fix in self.route]
            if len(star_list) > 0:
                # TODO Currrently if there are more than one STARs beggining at an IAF,
                # we simply pick the first one. There should be a way to favor
                # one or other
                star = star_list[0]
                if self.pof == LOADING:
                    self.route.substitute_after(
                        star.start_fix, star.rte, save=self.next_wp)
                else:
                    self.route.substitute_after(star.start_fix, star.rte)
                self.star = star

        # aplico la SID que toque
        if AIS.ad_has_ifr_rwys(self.adep) and self.pof in (GROUND, LOADING):
            ad = AIS.aerodromes[self.adep]
            sid_list = [sid for sid in ad.rwyInUse.stdInstDepartures.values()
                        if sid.end_fix in self.route]
            if len(sid_list) > 0:
                sid = sid_list[0]
                if self.pof == LOADING:
                    self.route.substitute_before(
                        sid.end_fix, sid.rte, save=self.next_wp)
                else:
                    self.route.substitute_before(sid.end_fix, sid.rte)
                self.sid = sid

        self.route = self.route.reduce()

    def set_type(self, type):
        """Saves the aircraft type and loads performance data"""
        save_type = type
        try:
            while type[0].isdigit():  # Remove number of aircraft if present
                type = type[1:]
        except IndexError:
            logging.error("Unkown type %s for %s. The type code may not be a number" % (
                save_type, self.callsign))
        self.type = type
        try:
            self.perf = BADA.Performance(type)
        except Exception:
            # The previous call only fails if there is no old style performance
            # info for the type
            try:
                std = {'H': 'B743', 'M': 'A320', 'L': 'PA34'}
                std_type = std[self.wake_hint.upper()]
                self.perf = BADA.Performance(std_type)
                logging.warning("No old style performance info for %s (%s). Using %s instead" % (
                    self.callsign, type, std_type))
                self.type = std_type
            except Exception:
                raise "Unable to load perfomance data for "
        self.wake = self.perf.wtc.upper()

    def set_campo_eco(self):
        # TODO This should be part of TLPV.py, and maybe duplicated here for the benefit of the pseudopilot
        # self.campo_eco = self.route[-1].fix[0:3]
        # for ades in AIS.aerodromes:
        #    if self.ades==ades:
        #        self.campo_eco=ades[2:4]
        self.campo_eco = TLPV.get_exit_ades(self)

    def set_ias(self, ias, force=False):
        # TODO This is a very poor approximation to the max ias
        # we are just taking the maximum cruise TAS and trying to guess
        # the maximum IAS from there.
        ias_max = min(cas_from_tas(self.perf.max_tas,
                                   self.lvl * 100), self.perf.tma_tas * 1.1)

        if ias > ias_max and force is False:
            return (False, ias_max)

        self.tgt_ias = float(ias)
        self.std_speed = False
        return (True, None)

    def set_mach(self, mach, force=False):
        lvl = self.lvl * 100
        ias = cas_from_tas(tas_from_mach(mach, lvl), lvl)
        (r, ias_max) = self.set_ias(ias, force)
        if r:
            return (True, None)
        else:
            return (False, mach_from_tas(tas_from_cas(ias_max, lvl), lvl))

    def set_std_spd(self):
        self.std_speed = True
        self.set_ias(cas_from_tas(v(self), self.lvl * 100))

    def set_std_mach(self):
        self.std_speed = True
        self.set_ias(cas_from_tas(v(self), self.lvl * 100))

    def set_cfl(self, lvl):
        if lvl <= self.perf.max_fl:
            self.cfl = lvl
            return (True, None)
        else:
            return (False, self.perf.max_fl)

    def set_ecl(self, ecl):
        # TODO This should be handled in TLPV, not here.
        self.ecl = ecl

    def set_heading(self, hdg, opt='ECON'):
        self.tgt_hdg = hdg
        self.lnav_mode = HDG
        self.to_do_aux = [hdg, opt]
        logging.debug(str((self.lnav_mode, self.to_do_aux)))

    def fly_route(self, route):
        """Introduces a new route, and changes the flight mode to FPR"""
        self.cancel_app_auth()
        self.route = Route.Route(Route.get_waypoints(route))
        self.lnav_mode = NAV
        self.to_do_aux = []
        self.route = TLPV.sector_intersections(self.route)
        self.set_app_fix()
        self.calc_eto()
        self.set_campo_eco()

    def set_vertical_rate(self, rate, force=False):
        """Given a rate in levels per hour, try to set it for the airplane.
        If the given rate is beyond the capabilities of the aircraft then return
        False and the maximum settable rate in levels per hour"""
        self.std_rate = False
        achievable = False
        max_rate = None

        if self.cfl > self.lvl:
            if rate <= self.perf.max_roc * f_vert(self) or force is True:
                self.rocd = rate
                achievable = True
            else:
                max_rate = self.perf.max_roc * f_vert(self)
        else:  # CFL <= LVL
            if abs(rate) <= self.perf.max_rod or force is True:
                self.rocd = -rate
                achievable = True
            else:
                max_rate = self.perf.max_rod

        return (achievable, max_rate)

    def set_app_fix(self):
        self.iaf = 'N/A'
        for wp in reversed(self.route):
            if wp.fix in (iaf.upper() for iaf in AIS.iaps):
                self.iaf = wp.fix
                break

    def set_std_rate(self):
        self.std_rate = True
        if self.rocd > 0:
            self.rocd = self.perf.std_roc * f_vert(self)
        else:
            self.rocd = -self.perf.std_rod

    def get_rot(self):
        """Returns rate of turn in degrees per second"""
        # Rate of turn. See BADA user manual 5.3
        bank_angle = 35  # Bank angle in degrees
        try:
            # Rate of turn in degrees per second
            rot = 9.81 * tan(pi * bank_angle / 180) * \
                180 / (self.tas * .51444) / pi
        except ZeroDivisionError:
            rot = 40
        return rot

    def get_rate_descend(self):
        if hasattr(self, "perf"):
            return self.rocd
        return self.rocd / 60. * 100.

    def get_mach(self):
        # Devuelve el nmero de mach
        return mach_from_tas(self.tas, self.lvl * 100)

    def get_ias_max(self):
        return self.perf.max_tas / (1.0 + 0.002 * self.perf.max_fl)

    def get_sector_entry_fix(self):
        if self.sector_entry_fix is None:
            return ''
        else:
            return self.sector_entry_fix

    def get_bearing_to_next(self):
        # Punto al que se dirige con corrección de wind_drift
        self.coords = self.route[0].pos
        vect = rp(r(self.coords, self.pos))
        return vect

    def set_sector_entry_fix(self, fix):
        self.sector_entry_fix = fix

    def set_sector_entry_time(self, time):
        self.sector_entry_time = time

    def cancel_app_auth(self):
        if self.app_auth:
            self.route = self.route.delete_from(self.iaf)

    # Commands

    def hold(self, fix, inboundCourse=None, outbd_time=None, std_turns=None):
        # If there is a published hold on the fix, use its defaults
        try:
            ph = [hold for hold in AIS.holds if hold.fix == fix][0]
            if inboundCourse is None:
                inboundCourse = ph.inboundCourse
            if outbd_time is None:
                outbd_time = ph.outbd_time
            if std_turns is None:
                std_turns = ph.std_turns
        except Exception:
            logging.debug("No published hold over " + str(fix))
        # Otherwise fill the blanks with defaults
        if inboundCourse is None:
            inboundCourse = self.route.get_inbd_track(fix)
        if outbd_time is None:
            outbd_time = 1  # One minute legs
        if std_turns is None:
            std_turns = True

        if std_turns:
            turn = 1.0
        else:
            turn = -1.0
        self.lnav_mode = HOLD
        self.to_do_aux = [fix, inboundCourse, timedelta(
            minutes=outbd_time), 0.0, False, turn]
        self.cancel_app_auth()

    def hdg_after_fix(self, aux, hdg):
        self.lnav_mode = HDG_FIX
        self.to_do_aux = [aux, hdg]
        self.cancel_app_auth()

    def int_rdl(self, aux, track):
        if self.lnav_mode not in (HDG, TRK):
            self.tgt_hdg = self.hdg
        self.lnav_mode = INT_RDL
        self.to_do_aux = [aux, track]
        self.cancel_app_auth()

    def execute_map(self):
        self._map = True

    def int_ils(self):
        # Se supone que ha sido autorizado previamente
        try:
            (puntos_alt, llz, puntos_map) = AIS.iaps[self.iaf]
        except KeyError:
            logging.warning("No IAF when trying to intercept ILS")
            return

        if self.lnav_mode not in (HDG, TRK):
            self.tgt_hdg = self.hdg

        self.lnav_mode = LOC_CAPTURE
        self.app_auth = True

        [xy_llz, rdl, dist_ayuda, pdte_ayuda, alt_pista] = llz
        wp = Route.WP('_LLZ')
        wp.pos = xy_llz

        self.route = Route.Route([wp])
        self.int_loc = True

        (puntos_alt, llz, puntos_map) = AIS.iaps[self.iaf]
        # En este paso se desciende el tráfico y se añaden los puntos
        logging.debug('Altitud: ' + str(puntos_alt[0][3]))
        self.set_cfl(puntos_alt[0][3] / 100.)
        self.set_std_rate()

    def int_llz(self):
        # Se supone que ha sido autorizado previamente
        try:
            (puntos_alt, llz, puntos_map) = AIS.iaps[self.iaf]
        except KeyError:
            logging.warning("No IAF when trying to intercept LLZ")
            return
        if self.lnav_mode not in (HDG, TRK):
            self.tgt_hdg = self.hdg
        [xy_llz, rdl, dist_ayuda, pdte_ayuda, alt_pista] = llz
        self.lnav_mode = LOC_CAPTURE
        self.to_do_aux = ["X%fY%f" % xy_llz, rdl]

    def orbit(self, turn_direction):
        self.lnav_mode = ORBIT
        if turn_direction == LEFT:
            self.to_do_aux = ['IZDA']
        else:
            self.to_do_aux = ['DCHA']

    def execute_app(self, ades='', iaf=''):
        # TODO Currently we are not checking which destination the
        # user asked for, and just clear for approach to the current
        # destination
        old_iaf = self.iaf

        self.set_app_fix()
        try:
            (puntos_alt, llz, puntos_map) = AIS.iaps[self.iaf]
        except KeyError:
            logging.warning("No IAF when trying to execute approach")
            self.iaf = old_iaf
            return

        self.app_auth = True
        self._map = False
        # En este paso se desciende el tráfico y se añaden los puntos
        logging.debug('Altitud: ' + str(puntos_alt[0][3]))
        self.set_cfl(puntos_alt[0][3] / 100.)
        self.set_std_rate()
        if self.lnav_mode == HOLD:
            pass
        else:
            self.lnav_mode = LOC_CAPTURE  # TODO This is more to do with VNAV at first
            self.route.delete_from(self.iaf)
            self.route.extend([Route.WayPoint(p[1]) for p in puntos_alt])
            wp = Route.WayPoint("_LLZ")
            wp.pos = llz[0]
            self.route.append(wp)
        logging.debug("Autorizado aproximación: " + str(self.route))

    def route_direct(self, fix):
        aux = None
        # Si es un punto intermedio de la ruta, lo detecta
        for i in range(len(self.route)):
            if self.route[i].fix == fix.upper():
                aux = self.route[i:]
        # Si no estáen la ruta, insertamos el punto como n 1
        if aux is None:
            for [nombre, coord] in AIS.points:
                if nombre == fix.upper():
                    aux = [[coord, nombre, '']]
                    for a in self.route:
                        aux.append(a)
        if aux is None:
            # TODO we need to deal with exceptions here the same
            # we do with set_cfl, for instance
            logging.warning('Punto ' + fix.upper() +
                            ' no encontrado al tratar de hacer una ruta directa')
            return

        # This is what actually sets the route
        self.fly_route(aux)

    def depart(self, sid, cfl, t):
        # Ahora se depega el avión y se elimina de la lista
        self.t = t
        # Get the actual sid object, but only if a SID has been given,
        # and we had a previous SID
        if not sid == '' and self.sid:
            sid = AIS.aerodromes[self.adep].get_sid(sid)
            if self.sid:
                self.route.substitute_before(
                    Route.WP(self.sid.end_fix), sid.rte)
            else:
                self.rte = sid.rte + self.rte
        self.cfl = cfl
        self.pof = TAKEOFF
        self.next(t)
        self.calc_eto()

    # Utility

    def log_waypoint(self):
        wp = self.route.pop(0)
        wp.ato = self.t
        self.log.append(wp)

    def copy(self):
        s = self
        acft = Aircraft(s.callsign, s.type, s.adep, s.ades, s.cfl, s.rfl, s.route,
                        eobt=self.eobt, next_wp=self.next_wp,
                        next_wp_eto=self.next_wp_eto, wake_hint=self.wake_hint, init=False)
        acft.__dict__ = self.__dict__.copy()
        acft.no_estimates = True
        acft.route = self.route.copy()
        acft.log = self.log.copy()
        return acft

    def waypoint_reached(self):
        """Uses a hemiplane test to check whether we have gone abeam the next waypoint"""
        # There are times when waypoints will be so close to each other that
        # because of the limited turn performance of the aircraft it may never
        # reach the next waypoint, but rather orbit indefinitely around it.
        # In order to avoid this, besides checking for distance we use a geometrical
        # test to see whether it's not worth trying to pass over the waypoint anymore.
        # We consider a waypoint has been reached when the aircraft is placed in the
        # hemiplane defined by the next waypoint and the waypoint after that.
        # The check is done using the dot product of the leg track, and the vector
        # defined between the next waypoint and the aircraft's position
        # There is a special case. If the route is zig-zagging, the aircraft may start
        # in that hemiplane even before gettting any close to the waypoint,
        # so we also require that in order for the test to be successful, the
        # aircraft must have been in the wrong hemiplane before.
        # Also, it only applies if the aircraft is within 1.5 the turn radius
        # to the waypoint

        # This method is quite expensive. We try to minimize calls by estimating the time
        # to reach and cheking again only after half the time

        if self.t < self.next_wp_check_t or len(self.route) == 0:
            return False  # No need to check.

        # Vector defining the hemiplane
        v1 = pr((1, self.route.get_outbd_track(0)))
        # Vector joining the wp and the aircraft
        v2 = r(self.pos, self.route[0].pos)
        # When the dot product is positive, the aircraft is on the goal
        # hemiplane
        on_goal_hemiplane = dp(v1, v2) > 0

        dist = rp(v2)[0]
        turn_radius = self.tas / (62.8318 * self.get_rot())  # In nautical miles

        # We will check again if at least half the time estimated to reach has passed
        # TODO Should be recalculated if there is a route change, and should be a function of percentage of max_tas
        self.next_wp_check_t = self.t + timedelta(hours=(0.5 * dist / self.tas))

        try:
            reached = not self._prev_on_goal and on_goal_hemiplane and dist < turn_radius * 1.5
        except Exception:
            reached = False

        if reached:
            self._prev_on_goal = None
            logging.debug("%s: %s" % (self.callsign, self.route[0]))
        else:
            self._prev_on_goal = on_goal_hemiplane
        return reached

    # def __del__(self):
    #    logging.debug("Aircraft.__del__ (%s)"%self.callsign)
