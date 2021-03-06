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
"""Classes useful for dealing with Exercise files"""

import logging
import os
from stat import *
import cPickle
import zlib
from ConfigParser import ConfigParser

# CONSTANTS
CACHE_VERSION = 9
MAPPING_FILE_NAME = "exercises-passes.dat"

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
        if f[-4:]!=".eje" and f!=MAPPING_FILE_NAME: continue
        date = os.stat(os.path.join(d,f))[ST_MTIME]
        if date>recent:
            recent=date

    # Find whether a cache file exists or if it's older than the most recent exercise
    cache = os.path.join(d,".cache")
    if not reload and os.access(cache,os.F_OK|os.R_OK) and os.stat(cache)[ST_MTIME]>recent:
        try:
            c = open(cache,"rb")
            version,le,routes = cPickle.loads(zlib.decompress(c.read()))
            if version==CACHE_VERSION:
                exercises += le
                return exercises
            else:
                logging.info("Cache file "+cache+" is version "+str(version)+", different than currently supported version "+str(CACHE_VERSION))
            c.close()
        except:
            logging.warning("Unable to load cache file: "+cache)
    else:
        logging.info("Cache file "+cache+" not found, not readable or stale")

    # Load data for all excercises in the directory
    logging.info("Rebuilding cache file...")
    le = []  #
    
    # Load the mapping file for the directory in case it exists
    mapping = Mapping(os.path.join(d,MAPPING_FILE_NAME))
    
    # RouteDB for this particular directory
    routes = RouteDB()
    
    for f in [f for f in os.listdir(d) if f[-4:]==".eje"]:
        f = os.path.join(d,f)
        try:
            e=Exercise(f)
        except:
            logging.warning("Unable to read exercise "+f)
            continue

        def append_exercise(e):
            for f in e.flights.values():
                routes.append(f.route,f.adep,f.ades)
            del(e.flights)
            le.append(e)
        
        # If we have DA,U,E data, then we can use the mapping file
        # to add all the actual passes implemented by this exercise
        try:
            for (course,phase,day,pass_no,shift) in mapping.exercises[(e.da,e.usu,e.ejer)]:
                ne=e.copy()
                # Don't delete the file just yet because it's currently required
                #del(ne.file)  # The copy is not based on any file
                ne.course,ne.phase,ne.day,ne.pass_no,ne.shift=course,phase,day,pass_no,shift
                append_exercise(ne)
            if (e.course,e.phase,e.day,e.pass_no) not in mapping.exercises[(e.da,e.usu,e.ejer)]:
                # This should be an error, but since we are not really dealing with these,
                # right now it's just distracting
                logging.debug("The exercise reported to be C-P-D-P "+str((e.course,e.phase,e.day,e.pass_no))+\
                              " but it's not shown on the mappings for DA-U-E "+str((e.da,e.usu,e.ejer)))
        except:
            # Since we didn't find mappings, we use the exercises own.
            append_exercise(e)
        
    exercises += le
    cache = open(cache,'wb')  # Cache used to be the file name, now the file object
    cache.write(zlib.compress(cPickle.dumps((CACHE_VERSION,le,routes))))
    cache.close
            
    return exercises    

def load_routedb(dir):
    """Loads the routedb stored in the cache file of an exercise directory
    
    This function does not verify that the cache file is not stale, so
    a call to load_exercises should be done before calling this function"""
    cachefile = os.path.join(dir,'.cache')
    cache = open(cachefile,'rb')
    version,le,routedb = cPickle.loads(zlib.decompress(cache.read()))
    return routedb
    
class Exercise:
    """All data representing a single exercise"""
    def __init__(self,file=None):
        if file:
            self.load(file)
            return

        self.file = self.fir = self.sector = self.start_time = self.shift = ""
        self.da = self.usu = self.ejer = self.course = self.phase = self.day = self.pass_no = None
        self.wind_azimuth = self.wind_knots = 0
        self.oldcomment = self.comment = ""        
        
        self.flights = {}        
        
    def load(self,file):
        import re

        self.file=file
        exc = ConfigParser()
        exc.readfp(open(file,"r"))
        self.fir=exc.get('datos','fir')
        self.sector=exc.get('datos','sector')
        self.start_time=exc.get('datos','hora_inicio')
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
        try: (self.wind_azimuth,self.wind_knots) = [int(x) for x in exc.get('datos','viento').split(",")]
        except: self.wind_azimuth,self.wind_knots=0,0
        
        # The old comment format was in fact used to present exercises
        # in the old MainMenu.py, so we need to maintain it
        # It actually has more information than a real comment
        try: self.oldcomment = exc.get('datos','comentario')
        except: self.oldcomment = os.path.basename(file)
        # If the file doesn't have an actual new comment attr yet, use the old one.
        try: self.comment = exc.get('datos','comment')
        except: self.comment = self.oldcomment
        
        self.load_flights(exc)
        
        # Attempt to calculate course,phase,day,pass_no,and shift
        if self.course==self.phase==self.day==self.pass_no==None and self.shift=="":
            formats = []
            file = os.path.basename(file)
            # fr=format regular expression, fm=format mapping
            fr = "(\d+)-Fase-(\d+)-D.a-(\d+)-Pasada-(\d+)-([mtMT])-(.*).eje"
            fm = {"course":1,"phase":2,"day":3,"pass_no":4,"shift":5}
            formats.append((fr,fm))
            fr = "(\d+)-Fase-(\d+)-D.a-(\d+)-([mtMT])-([^-]+)-(\d+).eje"
            fm = {"course":1,"phase":2,"day":3,"shift":4,"pass_no":6}
            formats.append((fr,fm))
            #20-Fase-3-D�a-04-M-Domingo-4-2055h.ej
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
                    continue

        # Attempt to extract only the useful comment:
        formats = []
        comment = self.comment
        #20-Fase-1-D�a-02-T-Toledo-1-1020h(29)
        fr = "\d+-Fase-\d+-D.a-\d+-[mtMT]-[^-]+-\d+-\d+h(.*?)(\(.*\))*$"
        fm = {"comment":1}
        formats.append((fr,fm))
        #20-Fase-1-D�a-02-T-Toledo-1(29
        fr = "\d+-Fase-\d+-D.a-\d+-[mtMT]-[^-]+-\d+(.*?)(\(.*\))*$"
        fm = {"comment":1}
        formats.append((fr,fm))
        #23-Fase-2-Dia-3-Pasada-2-M DA33U1E42(29)
        fr = "\d+-Fase-\d+-D.a-\d+-Pasada-\d+-[mtMT] *DA(\d+)US*U*(\d+)EJ*E*(\d+)(.*)\(.*\)"
        fm = {"da":1,"usu":2,"ejer":3,"comment":4}
        formats.append((fr,fm))
        #23-Fase-2-Dia-3-Pasada-2-M (29)
        fr = "\d+ *- *Fase[- ]\d+ *- *D.a[- ]\d+ *- *Pasada[- ]\d+ *- *[mtMT](.*?)(\(.*\))*$"
        fm = {"comment":1}
        formats.append((fr,fm))
        #22 - Fase 1 - Dia 7 - T -Pasada 4(30)
        fr = "\d+ *- *Fase[- ]\d+ *- *D.a[- ]\d+ *- *[mtMT] *- *Pasada[- ]\d+(.*?)(\(.*\))*$"
        fm = {"comment":1}
        formats.append((fr,fm))
        for r,m in formats:
            match=re.match(r,comment)
            try:
                for attrib,index in m.items():
                    if attrib in ("da","usu","ejer"):
                        if self.__dict__[attrib]==None:
                            self.__dict__[attrib]=int(match.group(index))
                    else:
                        self.__dict__[attrib]=match.group(index).strip()
                break
            except:
                continue

    def load_flights(self,exc):
        """Load flights from exercise config parser instance exc"""
        file = self.file
        flightops = ()
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
                logging.warning("Unable to read flight "+str(flightopt).upper()+" from "+str(file))
                logging.debug("Exception data follows",exc_info=True)
                
    def reload_flights(self):
        """Make sure flights are loaded fresh from the exercise file"""
        try: del(self.flights)
        except: pass
        try:
            exc = ConfigParser()
            exc.readfp(open(self.file,"r"))
            self.load_flights(exc)
        except:
            self.flights = {}
            logging.exception("Unable to reload flights for exercise")

    def add_flight(self, f):
        next = self.next_flight_id()
        self.flights[next]=f

    def next_flight_id(self):
        try:
            return max(self.flights.keys())+1
        except:
            return 0

    def save(self,file):
        self.file = file
        try:
            exc = ConfigParser()
            exc.readfp(open(self.file,"r"))
        except:
            logging.info("Unable to open exercise for reading prior to saving")
        
        try: exc.add_section('datos')
        except: pass
        for field in ("fir","sector","shift","da","usu","ejer","course",
                      "phase", "day", "pass_no","comment"):
            exc.set('datos',field, getattr(self,field))
        # Old field formats
        exc.set('datos','comentario',self.oldcomment)
        exc.set('datos','hora_inicio',self.start_time)
        exc.set('datos','viento',"%03d"%self.wind_azimuth+","+"%02d"%self.wind_knots)
        
        try: exc.add_section('vuelos')
        except: pass
        for f in self.flights.values():
            exc.set('vuelos',f.callsign,f.get_config_string())

        exc.write(open(self.file,"w"))        
            
    def copy(self):
        e = Exercise()
        e.__dict__=self.__dict__.copy()
        e.flights=self.flights.copy()
        for f in e.flights.keys():
            e.flights[f]=e.flights[f].copy()
        return e

    def __eq__(self,other):
        try:
            for (sa,sv) in self.__dict__.items():
                if sa=='flights': continue
                if getattr(other,sa)!=sv:
                    logging.debug(sa+" differs when comparing exercises ( "+str(sv)+" "+str(type(sv))+" != "+str(getattr(other,sa))+" "+str(type(getattr(other,sa)))+" )")
                    return False
            for f in self.flights.values():
                f2 = [f2 for f2 in other.flights.values() if f2.callsign==f.callsign][0]
                if f!=f2:
                    return False
            for f2 in other.flights.values():
                f = [f for f in self.flights.values() if f.callsign==f2.callsign][0]
                if f!=f2:
                    return False
        except:
            return False
        return True

    def __ne__(self,other):
        return not self.__eq__(other)

class Flight(object):
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
            self.adep=self.adep()
            self.ades=self.ades()
            self.route=self.route()
            self.fix,self.eto,self.firstlevel,self.tas = self.fix_eto_firstlevel_tas()
            self.wtc=self.wtc()
            self.rfl=self.rfl()
            self.cfl=self.cfl()
            self.type=self.type()
        else:
            self.callsign=""
            self.adep=""
            self.ades=""
            self.route=""
            self.fix=""
            self.eto=""
            self.wtc=""
            self.tas=""
            self.rfl=""
            self.firstlevel=""
            self.cfl=""
            self.type=""
            
    def copy(self):
        n = Flight()
        n.__dict__=self.__dict__.copy()
        return n
        
    def adep(self):
        """Return the departing aerodrome"""
        data=self._data.split(',')
        return data[2]
        
    def ades(self):
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
        import re
        data=self._data.split(',')
        route=data[6:]
        for fix,i in zip(route,range(len(route)-1)):
            m = re.match("H(\d+)F(\d+)V(\d+)",route[i+1])
            if m:
                break
        try:
            eto = m.group(1).ljust(6,"0")  # Make sure it's six chars long, and right pad with zeroes
            firstlevel = m.group(2).rjust(3,"0")
            tas = m.group(3).rjust(3,"0")
        except:
            logging.warning("Unable to extract HFV field in '"+self._data+"'")
            raise
        
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
    
    def get_config_string(self):
        try:
            s = self.type+","+self.wtc+","+self.adep+","+self.ades+","+"%03d"%(int(self.rfl))+","+"%03d"%(int(self.cfl))
            for f in self.route.split(","):
                s += ","+f
                if f==self.fix:
                    s += ",H"+self.eto+"F"+"%03d"%(int(self.firstlevel))+"V"+"%03d"%(int(self.tas))
            return s
        except:
            logging.error("Failure to create config string for "+str(self.callsign))
            raise
    
    def __eq__(self,other):
        try:
            for (sa,sv) in self.__dict__.items():
                if getattr(other,sa)!=sv:
                    logging.debug(sa+" differs when comparing flights ( "+str(sv)+" != "+str(getattr(other,sa))+" )")
                    return False
        except:
            return False
        return True
                
    def __ne__(self,other):
        return not self.__eq__(other)

    def __setattr__(self,name,value):
        """Capture attribute setting so as to force formatting"""
        object.__setattr__(self,name,value) # This actually sets the attributes
        if name=="eto" and len(value)==4:
            object.__setattr__(self,name,value+"00")

class Mapping:
    """Deals with the relationship between the unique exercises and on which day they were scheduled"""
    def __init__(self,mapping_file,exercise_file=None):
        mapping = ConfigParser()
        #dir=os.path.dirname(exercise_file)
        #f=self.mapping_file=os.path.join(dir,)
        f=mapping_file
        try:
            mapping.readfp(open(f))
        except:
            logging.info("Mapping file "+f+" does not exist")
        self.exercises={}
        try:
            for opt in mapping.options('Mappings'):
                try:
                    (da,u,e)=(int(opt[2:4]),int(opt[5:7]),int(opt[8:11]))
                    self.exercises[(da,u,e)]=[]
                    for s in mapping.get('Mappings',opt).split(","):
                        try:
                            (course,phase,day,pass_no, shift)=(int(s[1:3]),int(s[4:5]),int(s[6:8]),int(s[9:10]),s[11:12])
                            self.exercises[(da,u,e)].append((course,phase,day,pass_no,shift))
                        except:
                            logging.warning("Incorrect mapping format "+s+" in mapping file "+f)
                except:
                    logging.warning("Unable to read mapping for excercise "+opt+" in "+f)
        except:
            logging.warning("Section Mappings not found in mapping file "+f)
            
class RouteDB:
    """A database of routes that are known for a specific FIR"""
    
    def __init__(self):
        self._routes={}
        
    def append(self,route,adep,ades):
        """Append a route together with the adep and ades to the DB of routes"""
        route=route.strip().replace(" ",",")
        if route not in self._routes.keys():
          # We add the route to the database, with a frequency of one, and
          # adding the first pair of adep and ades
            self._routes[route]=(1,[adep+ades])
            # logging.debug("New route: "+route)
        else:
          # If the route already exists, we increment the frequency for the route
          # and if the orig_dest pair is new, add it to the list.
            (frequency,orig_dest_list)=self._routes[route]
            frequency=frequency+1
            if (adep+ades) not in orig_dest_list:
                orig_dest_list.append(adep+ades)
            self._routes[route]=(frequency,orig_dest_list)
            
    def size(self):
        """Return the number of known routes"""
        len(self._routes)
        
    def matching_routes(self,fix_list,adep,ades):
        """Given a list of points, and optional adep and ades airports, return
        a sorted list of possible matching routes"""
        match_routes=self._routes.copy()
        potential_discards=[]
        # Routes must contain the given fixes in the same order
        for route in match_routes.keys():
            i=0
            rs=route.split(',')
            for f in rs:
                if f==fix_list[i]:
                    i=i+1
                    if i==len(fix_list):
                        break;
            # If we have given a list of fixes, and we did not find them all in order,
            # remove the route. But it's OK if the list was empty to begin with
            # (meaning that we DO want to see all the available options).
            if i<len(fix_list) and fix_list[0]<>'':
                del match_routes[route]
                continue
            
            # Remove the route if it has the origin AD as the first route point
            if adep==route.split(",")[0]:
                del match_routes[route]
                continue

            # Mark for discarding routes that neither begin nor end on the
            # given adep and ades
            (f,orig_dest_list)=match_routes[route]
            if adep<>'' or ades<>'':
                for od in orig_dest_list:
                    if not (adep=='' or adep==od[0:4]) and not (ades=='' or ades==od[4:8]):
                        if route not in potential_discards:
                            potential_discards.append(route)
                        break
                            
        # Only discard routes based on adep and ades when it doesn't remove
        # all of our options
        if len(potential_discards)<len(match_routes):
            for d in potential_discards:
                del match_routes[d]
                
        # Out of the remaining routes, we need to sort them first according to whether
        # it is appropriate for the adep-ades pair, and then frequency 
        sorted_routes=[]
        for (route, (frequency, orig_dest_list)) in match_routes.items():
            if (adep+ades) in orig_dest_list:
                # Both origin and ades matches gives the highest score
                matches_orig_dest=2
            else:
                # No matching whatsoever gives the lowest score
                matches_orig_dest=0
                for od in orig_dest_list:
                    if (adep==od[0:4]) or (ades==od[4:8]):
                        # But if either the adep or ades matched we get partial score
                        matches_orig_dest=1
            sorted_routes.append([matches_orig_dest,frequency,route])
        sorted_routes.sort(reverse=True)
        logging.debug(sorted_routes)
        for i in range(len(sorted_routes)):
            sorted_routes[i]=sorted_routes[i][2]
        return sorted_routes        

def hhmmss_to_hhmm(s):
    """Given a string formated as hhmmss return a string formated to hhmm correctly rounded"""
    import datetime
    dt=datetime.datetime.today()    
    dt=dt.replace(hour=int(s[0:2]),minute=int(s[2:4]),second=int(s[4:]))
    dt+=datetime.timedelta(seconds=30)
    return dt.strftime("%H%M")

def export_callsigns(el, filename, reload=True):
    """Creates a tab separated value file containing the callsigns of the
    actual flights used in the exercices"""
    if reload:
        for e in el:
            e.reload_flights()
    
    csl = [f.callsign.strip("*")[:3] for e in el for f in e.flights.values()]
    callsigns = {}
    cp = ConfigParser()
    cp.readfp(open("Modelos_avo.txt"))
    for cs in cp.options("indicativos_de_compania"):
        callsigns[cs.upper()] = cp.get('indicativos_de_compania',cs)
    
    csd = {}
    for cs in csl:
        try:
            csd[cs][0]+=1
        except:
            try:
                csd[cs]=[1,callsigns[cs]]
            except:
                csd[cs]=[1,""]
    
    f=open(filename,"w")
    
    for code, (n, cs) in csd.items():
        f.write(code+"\t"+cs+"\t"+str(n)+"\n")
        

if __name__=='__main__':
    #Exercise("../pasadas\APP-RadarBasico\21-phase-1-D�a-01-M-TMA Madrid-1.eje"
    logging.getLogger('').setLevel(logging.DEBUG)
    e=load_exercises("../pasadas/Ruta-FIRMadrid", reload=True)
    #print str(e)
    
    
    
