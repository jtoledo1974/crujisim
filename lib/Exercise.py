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

# CONSTANTS
CACHE_VERSION = 1

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
            version,le = pickle.loads(c.read())
            if version==CACHE_VERSION:
                exercises += le
                return exercises
            else:
                logging.info("Cache file "+cache+" is version "+str(version)+", different than currently supported version "+str(CACHE_VERSION))
        except:
            logging.warning("Unable to load cache file: "+cache)
    else:
        logging.info("Cache file "+cache+" not found, not readable or stale")

    # Load data for all excercises in the directory
    logging.info("Rebuilding cache file...")
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
        exc["course"]=e.course
        exc["phase"]=e.phase
        exc["day"]=e.day
        exc["pass_no"]=e.pass_no
        exc["shift"]=e.shift
        le.append(exc)
        
    exercises += le
    cache = open(cache,'w')  # Cache used to be the file name, now the file object
    cache.write(pickle.dumps((CACHE_VERSION,le)))
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
        try: self.da = exc.getint('datos','da')
        except: self.da = None
        try: self.usu = exc.getint('datos','usu')
        except: self.usu = None
        try: self.ejer = exc.getint('datos','ejer')
        except: self.ejer = None
        try: self.course = exc.getint('datos','course')
        except: self.course = None
        try: self.phase = exc.getint('datos','phase')
        except: self.phase = None
        try: self.day = exc.getint('datos','day')
        except: self.day = None
        try: self.pass_no = exc.getint('datos','pass_no')
        except: self.pass_no = None
        try: self.shift = exc.get('datos','shift')
        except: self.shift = ""
            
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
        i=0
        for flightopt in flightopts:
            try:
                self.flights[i]=Flight(flightopt,exc.get('vuelos',flightopt))
                i += 1
            except:
                logging.warning("Unable to read flight "+flightopt+" from "+file)
        
        # Attempt to calculate course,phase,day,pass_no,and shift
        if self.course==self.phase==self.day==self.pass_no==None and self.shift=="":
            import re
            formats = []
            file = os.path.basename(file)
            # fr=format regular expression, fm=format mapping
            fr = "(\d+)-Fase-(\d+)-D.a-(\d+)-Pasada-(\d+)-([mtMT])-(.*).eje"
            fm = {"course":1,"phase":2,"day":3,"pass_no":4,"shift":5}
            formats.append((fr,fm))
            fr = "(\d+)-Fase-(\d+)-D.a-(\d+)-([mtMT])-([^-]+)-(\d+).eje"
            fm = {"course":1,"phase":2,"day":3,"shift":4,"pass_no":6}
            formats.append((fr,fm))
            #20-Fase-3-Día-04-M-Domingo-4-2055h.ej
            fr = "(\d+)-Fase-(\d+)-D.a-(\d+)-([mtMT])-([^-]+)-(\d+)-(\d+)h.*.eje"
            fm = {"course":1,"phase":2,"day":3,"shift":4,"pass_no":6}
            formats.append((fr,fm))
            for r,m in formats:
                match=re.match(r,file)
                try:
                    for attrib,index in m.items():
                        if attrib in ["course","phase","day","pass_no"]:
                            self.__dict__[attrib]=int(match.group(index))
                        elif attrib in ["shift"]:
                            self.__dict__[attrib]=match.group(index).upper()
                except:
                    if self.course != None:
                        print "Error aqui"
                    continue
                #print file,self.course,self.phase,self.day,self.pass_no,self.shift
                if self.pass_no == None:
                    print "Error!"
                break
            if self.course==None:
                #print "Could not match file ", file
                pass
            else:
                if self.pass_no == None:
                    print "Error!"
                

class Flight:
    """All data related to a specific flight within an Exercise"""
    def __init__(self, callsign=None, data=None):
        """Construct a flight instance
        
        Instantiation arguments:
        callsign -- Flight code (eg: IBE231)
        data -- The flight data as is on the Exercise file
        """
        
        if callsign and data:
            self.callsign=callsign.upper()
            self._data=data
            self.orig=self.orig()
            self.dest=self.dest()
            self.route=self.route()
            self.fix,self.eto,self.firstlevel,self.tas = self.fix_eto_firstlevel_tas()
            self.wtc=self.wtc()
            self.rfl=self.rfl()
            self.cfl=self.cfl()
            self.type=self.type()
        else:
            self.callsign=""
            self.orig=""
            self.dest=""
            self.route=""
            self.fix=""
            self.eto=""
            self.wtc=""
            self.tas=""
            self.rfl=""
            self.firstlevel=""
            self.cfl=""
            self.type=""
        
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

    def fix_eto_firstlevel_tas(self):
        """Return the fix for which the eto is valid"""
        data=self._data.split(',')
        route=data[6:]
        for fix,i in zip(route,range(len(route)-1)):
            if len(route[i+1])==15:
                break
        s = route[i+1]
        eto = s[1:7]
        firstlevel = s[8:11]
        tas = s[12:]
        
        return fix,eto,firstlevel,tas
        
    def wtc(self):
        """Return the wake turbulence cat"""
        data=self._data.split(',')
        return data[1]
        
    def rfl(self):
        """Return the RFL"""
        data=self._data.split(',')
        return data[4]
        
    def cfl(self):
        """Return the CFL"""
        data=self._data.split(',')
        return data[5]
        
    def type(self):
        """Return the type"""
        data=self._data.split(',')
        return data[0]

def hhmmss_to_hhmm(s):
    """Given a string formated as hhmmss return a string formated to hhmm correctly rounded"""
    import datetime
    dt=datetime.datetime.today()    
    dt=dt.replace(hour=int(s[0:2]),minute=int(s[2:4]),second=int(s[4:]))
    dt+=datetime.timedelta(seconds=30)
    return dt.strftime("%H%M")

if __name__=='__main__':
    #Exercise("../pasadas\APP-RadarBasico\21-phase-1-Día-01-M-TMA Madrid-1.eje"
    logging.getLogger('').setLevel(logging.DEBUG)
    e=load_exercises("../pasadas")
    #print str(e)
    