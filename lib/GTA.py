#!/usr/bin/python
#-*- coding:iso8859-15 -*-
# $Id$

# (c) 2006 CrujiMaster (crujisim@crujisim.cable.nu)
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

"""GTA (Generador de Tráfico Aéreo - Air Traffic Generator)
This is the main simulation engine to which clients connect"""


# System imports
from time import time, sleep
import logging
import random
import cPickle

import os
import datetime

# Application imports
import Aircraft
import Route
import FIR
from Exercise import Exercise
import TLPV

pickle = cPickle

# Constants
# QNH standard variation mB per second
QNH_STD_VAR = 0.0005


class GTA(object):

    def __init__(self, conf=None, exc_file="", refresh_time=5.):

        self.conf = conf
        self.exercise_file = exc_file
        # I don't remember why, but I believe it was important that
        # the refresh time was a float and not int - JTC
        self.refresh_time = float(refresh_time)

        logging.info("Loading exercise " + exc_file)
        e = Exercise(exc_file)

        # Find the FIR mentioned by the exercise file
        directory = os.path.dirname(os.path.abspath(exc_file))
        fir_list = FIR.load_firs(directory)
        try:
            fir = [fir for fir in fir_list if fir.name == e.fir][0]
        except:
            logging.critical("Unable to load FIR file for " + str(exc_file))
            raise
            return
        self.fir = fir
        Aircraft.fir = fir  # Rather than passing globals
        Route.fir = fir
        TLPV.fir = fir

        self.sector = e.sector
        # TODO wind and qnh should be properties of the atmosphere object
        # and should be variables dependent on location and height in the case
        # of wind
        self.wind = [e.wind_knots, e.wind_azimuth]
        # We have set somewhere else a fixed seed so that squawks are reproducible
        # but we want the qnh to be different in each exercise, so we use
        # getstate and setstate
        st = random.getstate()
        random.seed()
        self.qnh = random.gauss(1013.2, 8)
        # Variation in mB per second.
        self.qnh_var = random.gauss(0, QNH_STD_VAR)
        # Should not be much more than 1mB per 10minutes
        random.setstate(st)

        # Initializes time
        self.cont = True  # Marks when the main loop should exit
        t = datetime.datetime.today()
        self.t = t.replace(t.year, t.month, t.day,
                           int(e.start_time[0:2]),
                           int(e.start_time[3:5]), 0, 0)
        # Copy the datetimeobject
        self.last_update = self.t -\
            datetime.timedelta(seconds=self.refresh_time)

        self.fact_t = 1.0  # Time multiplier
        self.paused = False

        self.tlpv = tlpv = TLPV.TLPV(exc_file)

        # Create the aircraft for each of the flights in the exercise
        self.flights = []
        logging.debug("Loading aircraft")
        for ef in e.flights.values():  # Exercise flights

            # TODO Because the current exercise format cannot distiguish between
            # overflights and departures first we create them all as
            # overflights

            eto = datetime.datetime.today()
            eto = eto.replace(hour=int(ef.eto[:2]), minute=int(
                ef.eto[2:4]), second=int(ef.eto[4:6]))
            logging.debug("Loading %s" % ef.callsign)
            try:
                a = Aircraft.Aircraft(ef.callsign, ef.type, ef.adep, ef.ades,
                                      float(ef.cfl), float(ef.rfl), ef.route,
                                      next_wp=ef.fix, next_wp_eto=eto,
                                      wake_hint=ef.wtc)
            except:
                logging.warning("Unable to load " + ef.callsign, exc_info=True)
                continue

            a.lvl = int(ef.firstlevel)

            # TODO We need to know which of the flights are true departures. We assume that
            # if the aircraft departs from an airfield local to the FIR,
            # the EOBT is the estimate to the first point in the route
            # We substitute the overflight (created using next_wp_eto) with a departure
            # (created using an EOBT)
            if a.adep in fir.aerodromes.keys():
                eobt = a.route[0].eto
                a = Aircraft.Aircraft(a.callsign, a.type, a.adep, a.ades,
                                      a.cfl, a.rfl, a.route, eobt=eobt,
                                      wake_hint=a.wake_hint)
                if not fir.auto_departures[self.sector] \
                        and a.adep in fir.release_required_ads[self.sector]:
                    a.auto_depart = False

            self.flights.append(a)

            # Creates new flight plans from the loaded aircraft
            if a.eobt:
                ecl = a.rfl  # If it's a departure
            else:
                ecl = a.cfl
            fp = tlpv.create_fp(ef.callsign, ef.type, ef.adep, ef.ades,
                                float(ef.rfl), ecl, a.route, eobt=a.eobt,
                                next_wp=a.next_wp, next_wp_eto=a.next_wp_eto)
            a.squawk = fp.squawk  # Set the aircraft's transponder to what the flight plan says
            a.fs_print_t = fp.fs_print_t
            fp.wake = ef.wtc     # Keep the WTC in the exercise file, even if wrong
            fp.filed_tas = int(ef.tas)

        tlpv.start()

    def start(self):
        while self.cont:
            try:
                self.timer()
            except Exception:
                logging.error("Error in GTA.timer", exc_info=True)

            # Thus we make sure that the clock is always up to date.
            sleep(0.5)

    def set_vel_reloj(self, k):
        self.fact_t = k

    def advance_time(self):
        try:
            delta = time() - self.last_timer
        except AttributeError:
            delta = 0
        self.last_timer = time()

        # Si el reloj no está pausado avanzamos el tiempo
        if not self.paused:
            td = datetime.timedelta(seconds=delta * self.fact_t)
            self.t += td

        return delta

    def calculate_qnh(self, delta):
        # Calculate new QNH
        self.qnh = self.qnh + self.qnh_var * delta * self.fact_t

    def advance_flights(self):
        logging.debug(self.t)
        for f in self.flights:
            # logging.debug("Advancing " + f.callsign)
            f.next(self.last_update)

        # Kill flights that have been coasting for 5 minutes
        # Since flights will be deleted, we iterate over a copy of the list
        for f in self.flights[:]:
            if f.spof == Aircraft.COASTING and f.log[-1].ato + datetime.timedelta(minutes=5) < self.t \
                    or f.pof == Aircraft.LANDED:
                self.kill_flight(f)

    def timer(self):
        """Advance the simulation"""

        delta = self.advance_time()

        self.calculate_qnh(delta)

        if (self.t - self.last_update).seconds < self.refresh_time:
            # No further work needed
            return

        self.advance_flights()

        self.last_update = self.t

    def change_rwy_in_use(self, ad_code_id, rwy_direction_desig):
        """Modifies the rwy in use in for the given airport, and
        changes the SID and STAR procedures for the relevant aircraft"""
        try:
            ad = self.fir.aerodromes[ad_code_id]
            rwy_direction = [rwy for rwy in ad.rwy_direction_list
                             if rwy.txt_desig == rwy_direction_desig][0]
        except:
            logging.error("No runway direction %s defined for airport %s" % (ad_code_id, rwy_direction_desig),
                          exc_info=True)
        ad.rwy_in_use = rwy_direction
        for flight in (f for f in self.flights if not f.pp_pos):
            flight.complete_flight_plan()

    def kill_flight(self, f):
        self.flights.remove(f)

    def exit(self):
        self.tlpv.exit()

    def __del__(self):
        logging.debug("GTA.__del__")
