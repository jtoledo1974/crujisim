#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""GTAoffline (Generador de Tráfico Aéreo - Air Traffic Generator)
This version of GTA is meant for offline simulations"""


# System imports
import datetime
import logging
import os

from .GTA import GTA
from .Aircraft import Aircraft

LEFT = "IZDA"
RIGHT = "DCHA"
ECON = "ECON"


class GTAoffline(GTA):

    def __init__(self, conf=None, exc_file="", refresh_time=5., stop_after_minutes=0,
                 step_callback=None):

        assert(stop_after_minutes > 0)
        assert(step_callback is None or callable(step_callback))

        super(GTAoffline, self).__init__(conf, exc_file, refresh_time)
        self.stopping_time = self.t +\
            datetime.timedelta(minutes=stop_after_minutes)
        if step_callback:
            self.step_callback = step_callback

    def start(self):
        """Run the simulation at full speed, since we are offline"""
        while self.cont:
            try:
                self.timer()
            except Exception:
                logging.error("Error in GTAoffline.timer", exc_info=True)

    def exit(self):
        """Stops execution of the GTA. Called in testing, for instance"""
        self.cont = False
        super(GTAoffline, self).exit()

    def step_callback(self, gta):
        """This function is substituted by the one given by the module that initialized the GTA"""
        pass

    def advance_time(self):
        """Advances time. Return the number of seconds that passed"""
        # If there was a timelimit, stop
        if self.stopping_time < self.t:
            self.cont = False

        self.t += datetime.timedelta(seconds=self.refresh_time)

        self.step_callback(self)  # Function set by the holder of the GTA instance

        delta = self.refresh_time
        return delta  # Used by calculate_qnh


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("FILE", help="Run excercise FILE", metavar="FILE")
    args = parser.parse_args()

    os.chdir("../")

    # Full logging goes to 'crujisim.log'
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        filename='crujisim.log',
                        filemode='w')
    logger = logging.getLogger()
    # Important log messeges go to the console as well
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter('%(levelname)-6s %(message)s'))
    logger.addHandler(console)

    gta = GTAoffline(exc_file=args.FILE, stop_after_minutes=60)
    gta.start()
