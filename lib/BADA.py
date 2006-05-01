#!/usr/bin/env python
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

"""This module handles aircraft data from Eurocontrol's BADA (Database of aircraft data)"""

import re
import logging
from math import *
import ConfigParser

equiv = {}

# Constants
AIRCRAFT_FILE = "Modelos_avo.txt"  # It's loaded in the global config parser acft_cp
BADA_FILE = "bada.txt"

def load_equiv():
    global equiv
    cp = acft_cp
    for e, tl in cp.items('equivalences'):
        for t in tl.split(","):
            if t!="": equiv[t.upper()]=e.upper()

# TODO We are currently loading data from two diferent files, and
# use an equivalence list only for BADA
# The equivalence list should be use for both, and the format of
# AIRCRAFT_FILE should be cleaned up

class Performance:
    """Performance data for a specific aircraft type
    
    Data is loaded both from the AIRCRAFT_FILE file and
    the BADA file."""
    # Crujisim.py loads basic performance data for all known
    # aircraft to be used on the exercise editor
    def __init__(self, type, aircraft_file = AIRCRAFT_FILE,
                 use_bada=True, bada_file=BADA_FILE):

        # Look for the type in the AIRCRAFT_FILE
        cp = acft_cp  # acft_cp is global
        type = type.lower()
        try: data=cp.get("performances", type)
        except:
            raise(type.upper()+" not found in "+AIRCRAFT_FILE)
            return

        self.type = type.upper()
        data = data.split(',')
        self.wtc = data[0][0].upper()  # Only the first letter
        self.max_fl = int(data[1])
        # TODO We should really store this with its natural units, that is, fpm
        self.max_roc = float(data[2])/100*60  # levels per hour
        self.std_roc = float(data[3])/100*60
        self.max_rod = float(data[4])/100*60
        self.std_rod = float(data[5])/100*60
        self.cruise_tas = int(data[6])  # Knots
        self.max_tas = int(data[7])
        self.tma_tas = int(data[8])
        self.app_tas = int(data[9])   
        self.bada = False  # Initially consider BADA info is not available
        
        if not use_bada: return
        
        try: f = open(bada_file,"r")
        except: raise("Unable to open bada file while loading perfomance data")

        # This here just for reference of the attributes this class has        
        self.climb_cas_low = self.climb_cas_high = self.climb_mach = None
        self.cruise_cas_low = self.cruise_cas_high = self.cruise_mach = None
        self.descent_cas_low = self.descent_cas_high = self.descent_mach = None
        self.mass_low = self.mass_nominal = self.mass_high = None
        self.altitude_max = None
        
        # The index for each table are the flight levels for which there is info
        self.cruise_tas_table = {}
        self.cruise_ff_low_table = {}
        self.cruise_ff_nominal_table = {}
        self.cruise_ff_high_table = {}
        self.climb_tas_table ={}
        self.climb_roc_low_table={}
        self.climb_roc_nominal_table={}
        self.climb_roc_high_table={}
        self.climb_ff_table = {}
        self.descent_tas_table={}
        self.descent_rod_table={}
        self.descent_ff_table={}

        # Check whether the type exists in the database
        type = type.upper()
        while (True):
            h=f.readline()
            d=f.readline()
            if (h=="" or d==""):
                logging.warning("Aircraft type %s not found in BADA. Please add to equiv list."%type)
                return
            master = re.match(".*Type: ([^_ ]+)", h).group(1)
            # equiv is global
            if type == master or (equiv.has_key(type) and equiv[type]==master):
                self.type = type
                break;

        l=re.match(".*climb - (.*) cruise", d).group(1)  # 250/300 0.79 low - 104400
        v = re.match("(.*)/(.*) (.*) low[ -]+(.*)",l).groups()
        (self.climb_cas_low, self.climb_cas_high, self.climb_mach, self.mass_low) = \
         (int(v[0]), int(v[1]), float(v[2]), int(v[3]))
        l=re.match(".*cruise - (.*) descent", d).group(1)  # 250/310 0.79 nominal - 140000 Max Alt. [ft]: 41000
        v = re.match("(.*)/(.*) (.*) nominal[ -]+(.*) Max Alt. .*: (.*)",l).groups()
        (self.cruise_cas_low, self.cruise_cas_high, self.cruise_mach, self.mass_nominal, self.altitude_max) = \
         (int(v[0]), int(v[1]), float(v[2]), int(v[3]), int(v[4]))
        
        l=re.match(".*descent - (.*?) =", d).group(1)  # 250/300 0.79 high - 104400
        v = re.match("(.*)/(.*) (.*) high[ -]+(.*)",l).groups()
        (self.descent_cas_low, self.descent_cas_high, self.descent_mach, self.mass_high) = \
         (int(v[0]), int(v[1]), float(v[2]), int(v[3]))
        
        t=re.match(".* nom =* (.*) =*.*", d).group(1)  # Data table
        cont = True
        while (cont):
            try: l=re.match(" *(.*?\|.*?\|.*?\|.*?\|.*?\|.*?\|).*", t).group(1)  # 0| | 157 2210 1990 1620 270.3 | 131 760 97.2 | | |
            except: break
            try: fl = int(re.match("(\d+) *|.*", l).group(1))
            except: break
            # l is either of the following formats
            # 10 | | 129 2650 2750 2270 104.6 | 114 880 19.4 | | |
            # 140 | 306 20.0 21.4 26.6 | 330 3890 3410 2490 75.1 | 342 1810 18.6 | | |
            try:
                v = re.match("(\d+) *\| (\d+) (\d+\.*\d*) (\d+\.*\d*) (\d+\.*\d*) \| (\d+) (\d+) (\d+) (\d+) (\d+\.*\d*) \| (\d+) (\d+) (\d+\.*\d*) .*", l).groups()
                (self.cruise_tas_table[fl], self.cruise_ff_low_table[fl],
                 self.cruise_ff_nominal_table[fl], self.cruise_ff_high_table[fl],
                 self.climb_tas_table[fl], self.climb_roc_low_table[fl],
                 self.climb_roc_nominal_table[fl], self.climb_roc_high_table[fl],
                 self.climb_ff_table[fl], self.descent_tas_table[fl],
                 self.descent_rod_table[fl], self.descent_ff_table[fl]) = \
                  (int(v[1]), float(v[2]), float(v[3]), float(v[4]), 
                   int(v[5]), int(v[6]), int(v[7]), int(v[8]), float(v[9]),
                   int(v[10]), int(v[11]), float(v[12]) )
            except:
                try:
                    v = re.match("(\d+) *\|.*?\| (\d+) (\d+) (\d+) (\d+) (\d+\.*\d*) \| (\d+) (\d+) (\d+\.*\d*) .*", l).groups()
                    (self.climb_tas_table[fl], self.climb_roc_low_table[fl],
                     self.climb_roc_nominal_table[fl], self.climb_roc_high_table[fl],
                     self.climb_ff_table[fl], self.descent_tas_table[fl],
                     self.descent_rod_table[fl], self.descent_ff_table[fl]) = \
                      (int(v[1]), int(v[2]), int(v[3]), int(v[4]), float(v[5]), int(v[6]),
                       int(v[7]), float(v[8]) )
                except:
                    logging.warning ("Unable to read data from table line "+str(l), exc_info=True)
            t=t[len(l)+1:]
        
        f.close()
        self.max_fl = self.altitude_max / 100.
        self.bada = True  # Mark the fact that BADA info is available

    def get_cruise_perf(self, level):
        #return (self.interpolate(self.cruise_tas_table, level),
        #        self.interpolate(self.cruise_ff_low_table, level),
        #        self.interpolate(self.cruise_ff_nominal_table, level),
        #        self.interpolate(self.cruise_ff_high_table, level))
        return (self.interpolate(self.cruise_tas_table, level),
                0,
                0,
                0)
    def get_climb_perf(self, level):
        #return (self.interpolate(self.climb_tas_table, level),
        #        self.interpolate(self.climb_roc_low_table, level),
        #        self.interpolate(self.climb_roc_nominal_table, level),
        #        self.interpolate(self.climb_roc_high_table, level),
        #        self.interpolate(self.climb_ff_table, level))
        return (self.interpolate(self.climb_tas_table, level),
                0,
                self.interpolate(self.climb_roc_nominal_table, level),
                0,
                0)
    def get_descent_perf(self, level):
        #return (self.interpolate(self.descent_tas_table, level),
        #        self.interpolate(self.descent_rod_table, level),
        #        self.interpolate(self.descent_ff_table, level))
        return (self.interpolate(self.descent_tas_table, level),
                self.interpolate(self.descent_rod_table, level),
                0)

    def interpolate(self, dict, level):
        if level < min(dict.keys()): return dict[min(dict.keys())]
        if level > max(dict.keys()): return dict[max(dict.keys())]
        if level in dict.keys(): return dict[level]
        m_level = max([l for l in dict.keys() if l<level])
        M_level = min([l for l in dict.keys() if l>level])
        ratio = (float(level)-m_level)/(M_level-m_level)
        low, high = dict[m_level], dict[M_level]
        return low*(1-ratio)+high*ratio

def load_types():
    """Loads basic performance information from AIRCRAFT_FILE"""
    types = {}
    cp = acft_cp  # acft_cp is global
    for typename in cp.options('performances'):
        try:
            type = Performance(typename,use_bada=False)
            types[typename.upper()]=type
        except:
            logging.warning("Unable to parse aircraft type "+typename, exc_info=True)
    return types

def load_bada(filename=BADA_FILE):
    """ Given an ascii file containig aircraft performance summary data, return a dictionary
    with the results.
    
    The file is created from the openly published Aircraft Perfomance Summary Data
    pdf file, after having passed it through the unix pdf2text filter. Namely...
    
    $> pdftotext EEC_note_2004_12.pdf
    $> egrep "AC/Type:|^Speeds:" EEC_note_2004_12.txt > bada.txt
    """
    
    f = open(filename)
    bada = {}
    
    while (True):
            
        h=f.readline()
        d=f.readline()
        if (h=="" or d==""): break  # Finished reading the file
        
        type = re.match(".*Type: ([^_ ]+)", h).group(1)
        bada[type]=Performance(type, filename)

    return bada

class Atmosphere:
    def __init__(self, t0=288.15):
        self.t0 = t0  # Temperature at sea level in Kelvins
        self.t0_isa = 288.15  # Isa t0 in Kelvins
        self.rho0_isa = 1.225 # Air density at sea level in kg/m^3
        self.P0_isa = 101320 # Air pressure at sea level in Pa
        pass
    
    def get_tropopause(self):
        """Returns the height of the tropopause in meters"""
        return 11000 + 1000 * (self.t0-self.t0_isa) /6.5
    
    def get_temperature(self, h):
        """Returns the atmosphere's temperature (Kelvins) at a given h (m)"""
        if h > self.get_tropopause(): return 216.65
        else: return self.t0 - 6.5 * h/1000
        
    def get_density(self, h):
        """Returns density in kg/m^3 given a height (m)"""
        t = self.get_temperature(h)
        rho0 = self.rho0_isa * self.t0_isa / self.t0
        if h <= self.get_tropopause():
            return rho0 * (t/self.t0)**4.25864
        else:
            rho_trop = self.get_density(self.get_tropopause())
            return rho_trop * exp(-0.0001577494641342362*(h - self.get_tropopause()))
    
    def get_sound_speed(self, h):
        """Returns the speed of sound in m/s given a height (m)"""
        if h>self.get_tropopause():
            return 295.07
        else:
            return 340.29 * sqrt(self.get_temperature(h)/self.t0_isa)
    
    def get_pressure(self, h):
        """Returns pressure in Pa given a height (m)"""
        t = self.get_temperature(h)
        if h <= self.get_tropopause():
            return self.P0_isa * (t/self.t0)**5.25791
        else:
            P_trop = self.get_pressure(self.get_tropopause())
            return P_trop * exp(-0.0001577494641342362*(h - self.get_tropopause()))

    def get_tas_from_cas(self, cas, h):
        """Returns a TAS (kt), given a CAS (kt) and a height(feet)"""
        cas = 0.514444444 * cas # Turn it into m/s
        h = 0.3048 * h
        
        P = self.get_pressure(h)
        rho = self.get_density(h)
        mu = 1 / 3.5
        aux = (mu*self.rho0_isa*cas**2)/(2*self.P0_isa)
        aux = 1+aux
        aux = aux**(1/mu)
        aux = aux - 1
        aux = 1 + self.P0_isa*aux/P
        aux = aux**mu
        aux = aux - 1
        aux = 2 * P * aux / (mu * rho)
        tas = sqrt(aux)
        tas = tas / 0.514444444  # Turn it into knots
        return tas

    def get_cas_from_tas(self, tas, h):
        """Returns a CAS (kt), given a TAS (kt) and a height(feet)"""
        tas = 0.514444444 * tas  # Turn it into m/s
        h = 0.3048 * h  # Turn it into m
        
        P = self.get_pressure(h)
        rho = self.get_density(h)
        mu = 1 / 3.5
        aux = 1 + mu * rho * tas**2 / (2*P)
        aux = aux ** (1/mu)
        aux = aux - 1
        aux = 1 + P * aux /self.P0_isa
        aux = aux ** mu
        aux = aux - 1
        aux = 2 * self.P0_isa * aux / (mu * self.rho0_isa)
        cas = sqrt(aux)
        cas = cas / 0.514444444  # Turn it into knots
        return cas
    
    def get_tas_from_mach(self, mach, h):
        """returns a TAS speed (Knots), given a MACH number and Height(feet)"""
        h = 0.3048 * h  #Turn it into m
        T = self.get_temperature(h)
        tas = mach * sqrt(1.4 * 287.04 * T)
        tas = tas / 0.514444444 # Turn it into knots
        return tas
    
    def get_mach_from_tas(self,tas, h):
        """returns a MACH number, given a tas (knots) and a Height (feet)"""
        h = h = 0.3048 * h  #Turn it into m
        T = self.get_temperature(h)
        tas = tas * 0.514444444 # Turn into m/s
        mach = tas / sqrt(1.4 * 287.04 * T)
        return mach

# Basic loading
acft_cp = ConfigParser.ConfigParser()
try: acft_cp.readfp(open(AIRCRAFT_FILE, "r"))
except: acft_cp.readfp(open("../"+AIRCRAFT_FILE, "r"))
load_equiv()

        
if __name__=='__main__':
    a = Atmosphere()
    for h in (0, 3000, 6000, a.get_tropopause(), a.get_tropopause()+3000):
        print "Height", h
        print "Density", a.get_density(h)
        print "Pressure", a.get_pressure(h)
        print "Sound speed", a.get_sound_speed(h)
        print "TAS", a.get_tas_from_cas(200, h)
        print "CAS", a.get_cas_from_tas(a.get_tas_from_cas(200, h), h)
        print "MACH", a.get_mach_from_tas(a.get_tas_from_cas(200, h), h)
