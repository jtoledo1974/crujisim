#!/usr/bin/python
#-*- coding:iso8859-15 -*-
# $Id$
# (c) 2005 CrujiMaster (crujisim@yahoo.com)
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
"""Classes useful for dealing with Exercise files"""

import logging
import os
from stat import *
import pickle
from ConfigParser import ConfigParser

def load_exercises(path, reload=False):
    
    exercises = []
    
    # Walk each subdirectory looking for cached information. If stale,
    # recalculate statistics
    for d in os.listdir(path):
        d = os.path.join(path,d)
        mode = os.stat(d)[ST_MODE]
        if not S_ISDIR(mode) or d[-4:]==".svn": continue
        exercises += load_exercises(d,reload)

    # Find the date of the oldest .eje file in the directory
    d = path
    logging.debug("Searching for exercises in directory "+str(d))
    recent = 0
    for f in os.listdir(d):
        if f[-4:]!=".eje": continue
        date = os.stat(os.path.join(d,f))[ST_MTIME]
        if date>recent:
            recent=date

    # Find whether a cache file exists or if it's older than the most recent exercise
    cache = os.path.join(d,".cache")
    if not reload and os.access(cache,os.F_OK|os.R_OK) and os.stat(cache)[ST_MTIME]>recent:
        try:
            c = open(cache,"r")
            le = pickle.loads(c.read())
            exercises += le
            return exercises
        except:
            logging.warning("Unable to load cache file: "+cache)
            raise

    # Load data for all excercises in the directory
    logging.info("No cache file found ("+cache+"). Reload="+str(reload)+" Rebuilding...")
    le = []  #
    for f in [f for f in os.listdir(d) if f[-4:]==".eje"]:
        f = os.path.join(d,f)
        try:
            e=Exercise(f)
        except:
            logging.warning("Unable to read exercise "+f)
            continue
        exc = {}
        exc["file"]=f
        exc["fir"]=e.fir
        exc["sector"]=e.sector
        exc["comment"]=e.comment
        exc["n_flights"]=e.n_flights
        le.append(exc)
        
    exercises += le
    cache = open(cache,'w')  # Cache used to be the file name, now the file object
    cache.write(pickle.dumps(le))
    cache.close
            
    return exercises    
    
class Exercise:
    """All data representing a single exercise"""
    def __init__(self,file):
        self.file=file
        exc = ConfigParser()
        exc.readfp(open(file,"r"))
        self.fir=exc.get('datos','fir')
        self.sector=exc.get('datos','sector')
        try: self.da = exc.get('datos','da')
        except: self.da = ""
        try: self.usu = exc.get('datos','usu')
        except: self.usu = ""
        try: self.ejer = exc.get('datos','ejer')
        except: self.ejer = ""
        try: self.ejer = exc.get('datos','ejer')
        except: self.ejer = ""
            
        try:
            self.comment = exc.get('datos','comentario')
        except:
            self.comment = file
        try:
            self.n_flights = len(exc.options('vuelos'))        
            flightopts = exc.options('vuelos')
        except:
            logging.warning("Unable to read any flights from "+file)
        self.flights={}
        for flightopt in flightopts:
            try: self.flights[flightopt.upper()]=Flight(flightopt,exc.get('vuelos',flightopt))
            except:
                logging.warning("Unable to read flight "+flightopt+" from "+file)
        

class Flight:
    """All data related to a specific flight within an Exercise"""
    def __init__(self, callsign, data):
        """Construct a flight instance
        
        Instantiation arguments:
        callsign -- Flight code (eg: IBE231)
        data -- The flight data as is on the Exercise file
        """
        
        self.callsign=callsign.upper()
        self._data=data
        self.orig=self.orig()
        self.dest=self.dest()
        self.route=self.route()
        
    def orig(self):
        """Return the departing aerodrome"""
        data=self._data.split(',')
        return data[2]
        
    def dest(self):
        """Return the destination aerodrome"""
        data=self._data.split(',')
        return data[3]
        
    def route(self):
        """Return a list of route points"""
        data=self._data.split(',')
        route = ''
        for fix in data[6:]:
            if len(fix)<7:
                route = route + fix.upper() + ','
        route = route[:-1]
        return route


if __name__=='__main__':
    #Exercise("../pasadas\APP-RadarBasico\21-Fase-1-Día-01-M-TMA Madrid-1.eje"
    logging.getLogger('').setLevel(logging.DEBUG)
    e=load_exercises("../pasadas")
    #print str(e)
    