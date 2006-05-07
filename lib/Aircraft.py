#!/usr/bin/python
#-*- coding:iso8859-15 -*-
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

# Module imports
from ConfigParser import ConfigParser
from MathUtil import *
from math import pi, tan
import sys
import logging
from datetime import timedelta
import BADA
import Route
import TLPV  # This is used as an optimization in set_route. Could be removed

# Constants
CALLSIGN_FILE = "Callsigns.txt"
LEFT = "LEFT"
RIGHT = "RIGHT"

# TODO These will be taken out of here and into TLPV
PREACTIVE = "PREACTIVE"
READY = "READY"

# Phases of flight
LOADING  = "LOADING"  # Internal status before the aircraft is 'ready to fly'
GROUND   = "GROUND"   #
TAKEOFF  = "TAKEOFF"
FLYING   = "FLYING"   #
LANDED   = "LANDED"
INACTIVE = "INACTIVE" # Prior to the aircraft entering the first route point

# Subphases of flight
#Flying
COASTING = "COASTING" # After the aircraft reached its final waypoint and it's coasting along

# Globals

a = BADA.Atmosphere()
tas_from_cas = a.get_tas_from_cas
cas_from_tas = a.get_cas_from_tas
tas_from_mach = a.get_tas_from_mach
mach_from_tas = a.get_mach_from_tas

# TODO Wind should be a properperty of the Atmosphere object
# and we would probably like to model the wind gradient and
# the wind direction backing with raising altitude
wind = [0.0,0.0]

callsigns = {}  # Callsign database

# GTA.py sets fir as a module global

# Load the callsign database

def load_callsigns():
    global callsigns
    cf = ConfigParser()
    try: cf.readfp(open(CALLSIGN_FILE, "r"))
    except: cf.readfp(open("../"+CALLSIGN_FILE, "r"))
    callsigns = {}
    for cs, rcs in cf.items('Callsigns'):
        callsigns[cs.upper()] = rcs.upper()

load_callsigns()

def get_radio_callsign(cs):
    global callsigns
    try: rc = callsigns[cs.strip("*")[:3]]
    except:
        rc = ''
        logging.debug("No radio callsign for "+cs)
        callsigns[cs.strip("*")[:3]]=''
    return rc

    
def v(self):
    """Returns the target TAS to acquire"""
    #Devuelve TAS
    if not self.std_speed: # Velocidad mínima manteniedo IAS
        try: return tas_from_cas(self.tgt_ias, self.lvl*100)
        except:
            logging.error("Error setting standard TAS for %s"%self.callsign, exc_info=True)
            return 250.
    if self.perf.bada:
        if self.lvl<self.cfl: tas = self.perf.get_climb_perf(self.lvl)[0] 
        elif self.lvl>self.cfl: tas = self.perf.get_descent_perf(self.lvl)[0]
        else: tas = self.perf.get_cruise_perf(self.lvl)[0]
        return tas      
    
    # TODO we should delete all the following. We should simply have equivalents for
    # all known aircraft to the BADA models
    
    if self.perf.max_fl > 290.: # Fast moving traffic
        inicio_app = 00.
        trans_tma = 50.
        vel_tma = 150.
    elif self.perf.max_fl > 200.: # Medium speed traffic
        inicio_app = 00.
        trans_tma = 35.
        vel_tma = 80.
    else:
        inicio_app = 00.
        trans_tma = 25.
        vel_tma = 35.
        
    if self.lvl<=inicio_app: # Velocidad de aproximación
        return self.perf.app_tas
    elif self.lvl<=trans_tma: # Transición entre vel aprox y tma
        p=(self.lvl-inicio_app)/(trans_tma - inicio_app)
        return self.perf.app_tas*(1.-p)+self.perf.tma_tas*p
    elif self.lvl<=vel_tma: # Transición entre ruta y tma
        p=(self.lvl-trans_tma)/(vel_tma - trans_tma)
        ias_std=self.perf.cruise_tas/(1+0.002*self.perf.max_fl*0.90)
        return self.perf.tma_tas*(1.-p)+ias_std *(1.0+0.002*self.lvl)*p
        #    return self.perf.tma_tas
    else:
        ias_std=self.perf.cruise_tas/(1+0.002*self.perf.max_fl*0.90)
        return min(ias_std * (1+0.002*self.lvl),self.perf.max_tas)
        #     p=min((self.lvl-vel_tma)/(self.perf.max_fl-vel_tma),1.)
        #     return min(self.perf.max_tas * p + self.perf.tma_tas * (1-p),self.perf.cruise_tas)
        
    
def f_vert(self):
  # Devuelve factor corrección de velocidad vertical
    # TODO Probably this is unneeded now that we have a the BADA summary table
    q=self.lvl/self.perf.max_fl
    if q<.75:
        return 1.0
    elif q<.90:
        return 0.80
    else:
        return 0.60
    

                
                
def get_hdg_obj(self,deriva,t):
  # Da el rumbo objetivo en función de la demanda
    if self.to_do == 'fpr': # Mantener plan de vuelo
        self.pto=self.route[0].pos() #Punto al que se dirige con corrección de deriva
        self.vect=rp(r(self.pto,self.pos))
        # Correción de deriva
        return self.vect[1] - deriva
    elif self.to_do == 'hdg': # Mantener rumbo
        hdg_obj =  self.to_do_aux[0]
        if self.hdg<180.0 and hdg_obj>self.hdg+180.0:
            hdg_obj -= 360.0
        elif self.hdg>180.0 and hdg_obj<self.hdg-180.0:
            hdg_obj += 360.0
        aux_hdg = self.hdg - hdg_obj
        self.vect=rp((2.0*self.ground_spd,hdg_obj))
        if self.to_do_aux[1] == 'DCHA':
            if aux_hdg > 0.: #El rumbo está a su izquierda
                return (self.hdg+90.)%360.
            else: # Está a su derecha o ya está en rumbo
                return self.to_do_aux[0]
        elif self.to_do_aux[1] == 'IZDA':
            if aux_hdg < 0.: # El rumbo está a su derecha
                return (self.hdg-90.)%360.
            else: # Está a su izquierda o ya está en rumbo
                return self.to_do_aux[0]
        else:
            return self.to_do_aux[0]
    elif self.to_do == 'orbit': # Orbitar en presente posición
        if self.to_do_aux[0] == 'DCHA':
            return (self.hdg + 90.0)%360.0
        else:
            return (self.hdg - 90.0)%360.0
    elif self.to_do == 'hld': #Hacer esperas sobre un punto
        if not self.to_do_aux[4] and self.to_do_aux[0] in self.route:
            # Aún no ha llegado a la espera, sigue volando en ruta
            self.pto=self.route[0].pos() #Punto al que se dirige con corrección de deriva
            self.vect=rp(r(self.pto,self.pos))
            # Correción de deriva
            return self.vect[1] - deriva
        else: # Está dentro de la espera, entramos bucle de la espera
            self.to_do_aux[4] = True
            if not self.to_do_aux[0] in self.route: # El fijo principal debe estar en la ruta. Si no está se pone
                self.route.insert(0,Route.WayPoint(self.to_do_aux[0]))
            self.vect=rp((2.0*self.ground_spd,self.track)) # Con esta operación no nos borra el punto de la espera
            if len(self.to_do_aux)== 6: # Vamos a definir el rumbo objetivo, añadiéndolo al final
                r_acerc = ( self.to_do_aux[1] - deriva) %360.0
                if self.hdg<180.0 and r_acerc>self.hdg+180.0:
                    r_acerc -= 360.0
                elif self.hdg>180.0 and r_acerc<self.hdg-180.0:
                    r_acerc += 360.0
                aux=r_acerc-self.hdg
                if aux > -60.0 and aux < 120.0: # Entrada directa
                    r_obj = (self.to_do_aux[1] + 180.0  - deriva) %360. # Rumbo de alejamiento (con corrección de deriva)
                else:
                    r_obj = -((self.to_do_aux[1] + 180.0  -30.0 * self.to_do_aux[5] - deriva) %360.) # Rumbo de alejamiento (con corrección de deriva)
                self.to_do_aux.append(r_obj)
            r_obj = self.to_do_aux[6]
            if r_obj < 0.0:
                r_obj = -r_obj
            else:
                if abs(r_obj - self.hdg)>60.0: 
                    r_obj = (self.hdg +90.0 * self.to_do_aux[5])%360.0
            if self.to_do_aux[3] == 0.0 or self.to_do_aux[3] == -10.0: # Está en el viraje hacia el tramo de alejamiento
                if abs(r_obj - self.hdg) < 1.: # Ha terminado el viraje
                    if self.to_do_aux[3] == -10.0:
                        self.to_do_aux[4] = False
                        self.to_do_aux[3] = 0.0
                        self.to_do_aux.pop(6)
                    else:
                        self.to_do_aux[3] = t
            elif (t>self.to_do_aux[2] + self.to_do_aux[3]): # Comprobar tiempo que lleva en alejamiento y al terminar entra en acercamiento
                self.to_do_aux[3] = -10.0
                self.to_do_aux[6] = self.to_do_aux[1]
        return r_obj
    elif self.to_do == 'hdg<fix':
        if self.to_do_aux[0] in self.route:
            self.pto=self.route[0].pos() #Punto al que se dirige con corrección de deriva
            self.vect=rp(r(self.pto,self.pos))
            # Correción de deriva
            return self.vect[1] - deriva
        else:
            self.vect=rp((2.0*self.ground_spd,self.track))
            return self.to_do_aux[1]
    elif self.to_do == 'int_rdl':
        (rx,ry) = r(Route.WP(self.to_do_aux[0]).pos(),self.pos) # Coordenadas relativas a la radioayuda
        rdl_actual = rp((rx,ry))[1]
        rdl = self.to_do_aux[1]
        if rdl<180.0 and rdl_actual>rdl+180.0:
            rdl_actual=rdl_actual-360.0
        elif rdl>180.0 and rdl_actual<rdl-180.0:
            rdl_actual=rdl_actual+360.0
        ang_aux=rdl - rdl_actual #  Positivo, el radial estáa la izquierda de posición actual
        (rdlx,rdly)=pr((1.0,self.to_do_aux[1]))
        dist_perp = abs(rx * rdly - ry * rdlx)
        if dist_perp < 0.1: # Consideramos que estáen el radial
            self.vect=rp((2.0*self.ground_spd,self.track))
            self.tgt_hdg = self.to_do_aux[1]
            return self.to_do_aux[1] - deriva
        elif dist_perp<0.8:
            self.vect=rp((2.0*self.ground_spd,self.track))
            self.tgt_hdg = (self.to_do_aux[1] - 20.0 * sgn(ang_aux))%360.0
            return (self.to_do_aux[1] - deriva - 20.0 * sgn(ang_aux))%360.0
        else:
            self.vect=rp((2.0*self.ground_spd,self.track))
            return (self.tgt_hdg - deriva)%360.0
            #       return (self.to_do_aux[1] - deriva - 45.0 * sgn(ang_aux))%360.0
    elif self.to_do == 'app':
        (puntos_alt,llz,puntos_map) = fir.iaps[self.iaf]
        [xy_llz ,rdl, dist_ayuda, pdte_ayuda, alt_pista] = llz
        if len(self.route) == 0: # Es el primer acceso a app desde la espera. Se añaden los puntos
            for [a,b,c,h] in puntos_alt:
                self.route.append(Route.WayPoint(b))
            wp = Route.WayPoint("_LLZ")
            wp._pos = xy_llz
            self.route.append(wp)
        if len (self.route) > 1: # An no estáen el localizador, tocamos solamente la altitud y como plan de vuelo
            if self._map and '_LLZ' not in self.route: # Ya estáfrustrando
                for [a,b,c,h] in puntos_map:
                    if b == self.route[0].fix:
                        self.cfl = h/100.
                        self.set_std_rate()
                        break
            else:
                for [a,b,c,h] in puntos_alt:
                    if b == self.route[0].fix:
                        self.cfl = h/100.
                        break
            self.pto=self.route[0].pos() #Punto al que se dirige con corrección de deriva
            self.vect=rp(r(self.pto,self.pos))
            # Correción de deriva
            return self.vect[1] - deriva
        if len(self.route) == 1: # Interceptar localizador y senda de planeo
            if self._map and '_LLZ' not in self.route: # Ya estáfrustrando hacia el ltimo punto, asimilamos a plan de vuelo normal
                self.to_do = 'fpr'
                self.app_auth = False
                self.app_fix = ''
                self._map = False
                self.pto=self.route[0].pos() #Punto al que se dirige con corrección de deriva
                self.vect=rp(r(self.pto,self.pos))
                # Correción de deriva
                return self.vect[1] - deriva
            else:
                (rx,ry) = r(xy_llz,self.pos) # Coordenadas relativas a la radioayuda
                # Primero intersecta la senda de planeo cuando es inferior. Solamente tocamos el rate de descenso
                dist_thr = rp((rx,ry))[0]-dist_ayuda
                derrota = rp((rx,ry))[1]
                if abs(dist_thr) < 0.50: # Avión aterrizado
                    if (self.lvl-alt_pista/100.)>2.or abs(derrota-rdl)>90.: # En caso de estar 200 ft por encima, hace MAP o si ya ha pasado el LLZ
                        self._map = True 
                    if self._map: # Procedimiento de frustrada asignado
                        self.set_std_spd()
                        self.set_std_rate()
                        self.route = Route.Route([Route.WayPoint(p[1]) for p in puntos_map] )
                    else:
                        logging.debug("Aterrizando el "+str(self.callsign))
                        return LANDED
                if self.esta_en_llz: # Interceptación de la senda de planeo. Se ajusta rate descenso y ajuste ias = perf.app_tas
                    fl_gp = (alt_pista/100. + dist_thr * pdte_ayuda * 60.)
                    if fl_gp <= self.lvl:
                        self.set_ias(self.perf.app_tas/(1.0+0.002*self.lvl))
                        self.cfl = alt_pista/100.
                        rate = ((self.lvl - fl_gp)*2.0 + self.ground_spd * pdte_ayuda )
                        self.set_rate_descend(rate*100.) # Unidades en ft/min
                    else:
                        self.set_rate_descend(0.001)
                        # Ahora el movimiento en planta
                rdl_actual = rp((rx,ry))[1]
                if rdl<180.0 and rdl_actual>rdl+180.0:
                    rdl_actual=rdl_actual-360.0
                elif rdl>180.0 and rdl_actual<rdl-180.0:
                    rdl_actual=rdl_actual+360.0
                ang_aux=rdl - rdl_actual #  Positivo, el radial estáa la izquierda de posición actual
                (rdlx,rdly)=pr((1.0,rdl))
                dist_perp = abs(rx * rdly - ry * rdlx)
                if dist_perp < 0.1: # Consideramos que estáen el radial
                    if abs(self.lvl-self.cfl)<002.0:
                        self.esta_en_llz = True
                    self.int_loc = False
                    self.vect=rp((2.0*self.ground_spd,self.track))
                    return rdl - deriva
                elif dist_perp<0.8:
                    if abs(self.lvl-self.cfl)<002.0:
                        self.esta_en_llz = True
                    self.int_loc = False
                    self.vect=rp((2.0*self.ground_spd,self.track))
                    return (rdl - deriva - 20.0 * sgn(ang_aux))%360.0
                else:
                    if self.int_loc:
                        rdl_actual = self.hdg
                        if rdl<180.0 and rdl_actual>rdl+180.0:
                            rdl_actual=rdl_actual-360.0
                        elif rdl>180.0 and rdl_actual<rdl-180.0:
                            rdl_actual=rdl_actual+360.0
                        ang_aux2=rdl - rdl_actual #  Positivo, el radial estáa la izquierda de posición actual
                        if ang_aux*ang_aux2 > 0.:
                            return self.tgt_hdg - deriva
                        else:
                            self.int_loc = False
                            self.vect=rp((2.0*self.ground_spd,self.track))
                            self.tgt_hdg = rdl- 45.0 * sgn(ang_aux)
                            return (rdl - deriva - 45.0 * sgn(ang_aux))%360.0
                    else:
                        self.vect=rp((2.0*self.ground_spd,self.track))
                        return (rdl - deriva - 45.0 * sgn(ang_aux))%360.0
                        
                        
                        
class Aircraft:
    
    max_uid = 0  # All aircraft are uniquely identified. We keep the maximum number used here.

    def __init__(self, callsign, type, adep, ades, cfl, rfl, rte,
                 eobt=None, next_wp=None, next_wp_eto=None, wake_hint = None,
                 init = True):
        
        if not init: return  # The instance will be used as a copy in Aircraft.copy

        if (next_wp and not next_wp_eto) or (not next_wp and next_wp_eto):
            raise("Unable to calculate flight profile, either the next waypoint or the eto for the next waypoint is missing")
        if not next_wp and not next_wp_eto and not eobt:
            raise("Either the EOBT, or the next waypoint and its ETO are mandatory parameters")
        
        self.no_estimates   = False  # If True we skip calculating estimates
                                     # Used to avoid recursion
                                     # and avoiding calling sector_intersection
                                     # which stops the GTA thread for unknown reasons
        
        self.uid            = None  # Unique identifier. Set at the end of the init
        self.callsign       = None  # 'IBE767'
        self.radio_callsign = None  # 'IBERIA'
        self.set_callsign(callsign)
        self.type           = None  # 'B747'
        self.wake           = None  # 'H' Wake turbulence category
        self.wake_hint      = wake_hint  # We can use this to give default perf values if type is unknown
        self.set_type(type)
        self.adep           = adep  # 'LEBB'
        self.ades           = ades  # 'LEMD'
        self.cfl            = cfl   # Cleared Flight Level, the FL the aircraft is climbing/descending towards
        self.rfl            = rfl   # Requested Flight Level. As filed in the flight plan
        self.pfl            = rfl   # Planned Flight Level.
                                    # TODO This should not be an aircraft attribute,
                                    # but rather a TLPV.FlightPlan attribute
        
        self.pof            = LOADING  # Phase of flight
        self.spof           = None  # Subphase of flight
        
        # Time attributes (Datetime instances)
        self.eobt           = eobt  # Estimated off block time
        self.next_wp        = next_wp
        self.next_wp_eto    = next_wp_eto
        self.t              = None

        self.route          = None  # Route object (Route.py)
        self.set_route(rte)
        self.log = Route.Route()    # A Route object to keep track of flight progress
        self.pos            = None  # (0.0,0.0) x,y (Cartesian coordinates in nautical miles)
        # This just sets an initial value. The correct value is done on initialize()
        if eobt: self.t = self.eobt
        else: self.t = self.next_wp_eto
        self.auto_depart    = True  # Whether or not it departs automatically

        self.hdg            = None  # Last calculated heading (deg magnetic)
        self.track          = None  # Last calculated track (deg magnetic)
        self.tgt_hdg        = None  # Target heading to acquire (deg magnetic)
        # TODO we are not currently simulating a transition altitude
        # In order to do so we should keep track of both the altitude and
        # the flight level
        self.lvl            = None  # Flight Level
        self.std_rate       = True  # Whether the acft will climb/descend using standard rates
        # TODO Notice there is no tgt_rocd. The aircraft changes its rate of climb or descent
        # instantaneously. We might want to revise this.
        # TODO rocd should really be measured in feet per minute
        self.rocd           = 0.0   # Rate Of Climb or Descent (flight levels per hour) 
        self.tas            = 0.0   # True Air Speed (knots)
        self.ground_spd     = 0.0   # Ground Speed (knots)
        self.filed_tas      = None  # TODO We probably don't need this here, but in TLPV (knots)
        self.std_speed      = True  # Use standard speed for phase of flight
        self.ias            = 0.0   # Indicated Air Speed (and for our purposes, it's the same as CAS) (knots)
        self.tgt_ias        = None  # Target IAS to acquire (knots)
        self.to_do          = 'fpr'
        self.to_do_aux      = ''
        self.squawk         = None  # Mode A transpoder code the aircraft is squawking
        # TLPV calculated fields to support using the Pseudopilot display as a controller
        self.fs_print_t     = None
        self.campo_eco      = ''
        # IAP related attributes
        self.app_auth       = False
        self.iaf            = ''
        self._map           = False
        self.int_loc        = False
        self.esta_en_llz    = False
        self.reports        = []  # List of things an aircraft should report.
                                  # [{'time':1.65,'text':'Request climb FL230'},
                                  #  ,{'time':2.34,'text':'Overflown DGO'}]
                           
        self.pp_pos = None  # Pseudopilot position "piloting" this aircraft
        # TODO atc_pos should be an attribute of a TPV flight, not of the aircraft
        self.atc_pos = None  # UCS controlling this flight
        self.trans_pp_pos   = False   #Set to TRUE when ACFT is being transferred by a PP position
        self.trans_atc_pos  = False  #Set tu TRUE when ACFT is being transferred by a ATC position

        if init == True: self.initialize()
        
        Aircraft.max_uid = self.uid = Aircraft.max_uid + 1
            
    def initialize(self):
        # Init code
        self.std_speed = True
        if self.callsign=='ZORRO34':
            print "zorro"
        if not self.next_wp: self.pof = GROUND
        else: self.pof = FLYING

        if self.pof == FLYING:
            self.ground_spd = self.tas = v(self)
            self.lvl = self.cfl
        else:  # GROUND
            try: self.lvl = fir.ad_elevations[self.adep]
            except:
                if self.adep in fir.aerodromes:
                    logging.warning("No elevation known for "+self.adep+". Setting initial altitude to 0")
                self.lvl = 0
            # We need to start up with an initial speed because the
            # accelaration code is not realistic
            self.ground_spd = self.tas = 60.  
        self.ias = cas_from_tas(self.tas, self.lvl*100)

        self.pos = self.route[0].pos()
        self.set_app_fix()
        self.track = self.hdg = self.route.get_outbd_track(0)

        self.calc_eto()
        if self.next_wp_eto:
            if self.next_wp not in [wp.fix for wp in self.route]:
                raise("Unable to create flight. Estimate waypoint (%s) not in the route (%s)"%(self.next_wp, self.route))
            delta = self.route[self.next_wp].eto-self.next_wp_eto
            for wp in self.route:
                try: wp.eto -= delta
                except: pass
            self.t -= delta
            
        self.set_campo_eco()

    def __getstate__(self):
        """This function is called by the pickler. We remove the attributes
        that we don't want to send through the wire"""
        odict = self.__dict__.copy()
        try: del odict['perf']
        except: pass
        return odict
    
    def __str__(self):
        return self.callsign
        
    def next(self,t):
        """Advance simulation to time t"""
        global wind
            
        if self.pof == GROUND and t > self.eobt and self.auto_depart:
            self.pof = TAKEOFF
        if t < self.t or self.pof==GROUND:
            if self.pof == FLYING: self.pof = INACTIVE
            return
        if t>self.t and self.pof == INACTIVE:
            self.pof = FLYING

        # With this we make sure that the simulation doesn't advance
        # in steps bigger than 15 seconds
        if (t-self.t)>timedelta(seconds=15):
            ne_backup = self.no_estimates
            self.no_estimates = True
            t2 = self.t + timedelta(seconds=15)
            while (t-self.t)>timedelta(seconds=15):
                self.next(t2)
                t2 += timedelta(seconds=15)
            self.no_estimates = ne_backup
            
        dh = (t-self.t).seconds/3600. + (t-self.t).microseconds/3600./1000000  # Delta hours (fractional hours since the last update)
                
        # Cálculo de la altitud
        if self.cfl>self.lvl and self.pof == FLYING:
            if self.std_rate:
                self.rocd = self.perf.std_roc * f_vert(self)
                if self.perf.bada:
                    self.rocd=self.perf.get_climb_perf(self.lvl)[2] * 60./100
        elif self.cfl<self.lvl and self.pof == FLYING:
            if self.std_rate:
                self.rocd = -min(self.tas/0.2/100.*60.,self.perf.max_rod * f_vert(self))
                if self.perf.bada:
                    self.rocd=-self.perf.get_descent_perf(self.lvl)[1] * 60./100
        else: self.rocd = 0.
        inch=self.rocd*dh
        if abs(self.lvl-self.cfl)<abs(inch):
            self.lvl=self.cfl
            self.rocd =0.
            self.std_rate=True
        else:
            self.lvl=self.lvl+inch
        # Iteración para encontrar la posición
        while t >= self.t + timedelta(seconds=1):
            aux_v = v(self)
            inc_v_max = 1.5 * dh * 60. * 60. #Inc. v = 90kts/min TAS
            if abs(aux_v-self.tas)<inc_v_max or self.tas == 0.:
                self.tas=aux_v
            else:
                self.tas = self.tas + inc_v_max * sgn(aux_v - self.tas)
            if self.tas >= aux_v*.8 and self.pof == TAKEOFF: self.pof = FLYING
            self.ias = cas_from_tas(self.tas, self.lvl*100)
            (vx,vy) = pr((1.0,self.track))
            (wx,wy) = pr(wind)
            wind_perp = wx*vy - wy*vx
            wind_paral = wx * vx + wy * vy
            self.ground_spd = self.tas + wind_paral
            try: deriva = degrees(asin(wind_perp / self.tas))
            except ZeroDivisionError: deriva = 0
            r_obj = get_hdg_obj(self,deriva,t)
            if r_obj == LANDED:
                self.pof, self.spof = GROUND, LANDED
                return
            if self.hdg<180.0 and r_obj>self.hdg+180.0:
                r_obj=r_obj-360.0
            elif self.hdg>180.0 and r_obj<self.hdg-180.0:
                r_obj=r_obj+360.0
            aux=r_obj-self.hdg
            rot = self.get_rot()*60*60  # Rate of turn in degrees per hour
            if abs(aux)<rot*dh:
                self.hdg=r_obj%360
            else:
                self.hdg=(self.hdg+dh*rot*sgn(aux))%360
            self.track = (self.hdg + deriva)%360
            self.salto=(self.ground_spd)*dh # Distancia recorrida en este inc. de t incluyendo viento
            # Ha pasado el punto al que se dirige
            if self.salto>self.vect[0] or self.waypoint_reached():
                if len(self.route)==1:
                    if self.app_auth and self.ades in fir.rwys.keys():
                        self.to_do = 'app'
                        #             (puntos_alt,llz,puntos_map) = iaps[sel.iaf]
                        #             self.to_do_aux = app
                        self.salto=self.tas*dh # Distancia recorrida en este inc.de t sin viento
                        efecto_viento = (wx*dh,wy*dh) # Deriva por el viento
                        self.t = t
                    elif self.route[0].fix in fir.aerodromes: # Si el último punto está en la lista de aeropuertos, orbita sobre él
                        if self.to_do == 'fpr': # En caso de que llegue a ese punto en ruta
                            try:
                                ph = [hold for hold in fir.holds if hold.fix == self.route[0].fix][0]
                                self.to_do = 'hld'
                                if ph.std_turns == True: turn = 1.0
                                else: turn = -1.0
                                self.to_do_aux = [ph.fix, ph.inbd_track,
                                                  timedelta(minutes=ph.outbd_time),
                                                  0.0, True, turn]
                            except: pass
                            if len(self.route)==1: # En caso contrario, hace una espera de 1 min 
                                self.to_do = 'hld'
                                self.to_do_aux = [self.route[0], self.hdg, timedelta(minutes=1), 0.0, True, 1.0]
                        self.salto=self.tas*dh # Distancia recorrida en este inc.de t sin viento
                        efecto_viento = (wx*dh,wy*dh) # Deriva por el viento
                        self.t = t
                    else:
                        # Aircraft has reached its final waypoint, and its not known
                        # airport, so we just coast along
                        self.to_do = 'hdg'
                        self.to_do_aux = [self.hdg,'ECON']
                        self.tgt_hdg=self.hdg
                        self.salto=self.tas*dh # Distancia recorrida en este inc.de t sin viento
                        efecto_viento = (wx*dh,wy*dh) # Deriva por el viento
                        self.t = t
                        self.spof = COASTING
                else:
                    self.salto=self.tas*dh # Distancia recorrida en este inc.de t sin viento
                    efecto_viento = (wx*dh,wy*dh) # Deriva por el viento
                    self.t += timedelta(hours=dh) #Almacenamos el tiempo
                self.log_waypoint()  # Pops the old waypoint, and saves it in the log
                if not self.no_estimates: self.calc_eto()
            else:
                self.salto=self.tas*dh # Distancia recorrida en este inc.de t sin viento
                efecto_viento = (wx*dh,wy*dh) # Deriva por el viento
                self.t=t #Almacenamos el tiempo
            self.pos=s(s(self.pos,pr((self.salto,self.hdg))),efecto_viento) #Cambiamos la posición
        self.t = t

    def calc_eto(self):
        """Cálculo del tiempo entre fijos"""
        
        if self.no_estimates: return
        
        estimadas = [0.0]
        last_point = False
        sim = self.copy()
        sim.no_estimates = True
        del sim.log[:]  # Remove previously logged points

        inc_t = timedelta(seconds=15)
        while not last_point:
            t = sim.t + inc_t
            sim.next(t)
            if not sim.to_do == 'fpr':
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
            for wp in [wp for wp in self.route[:] if wp.type==Route.TLPV]:
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
        # Completa el plan de vuelo con la SID o STAR, si es que hay alguna publicada para adep y destino
        # TODO should this function be really an Aircraft method?
        # or rather a Route method, or even a FIR method?
        if self.ades in fir.rwys.keys(): # aplico la STAR que toque
            (sid,star) = fir.procedimientos[fir.rwyInUse[self.ades]]
            # TODO Currrently if there are more than one STARs beggining at an IAF,
            # we simply pick the first one. There should be a way to favor one or other
            for iaf in star.keys():
                if iaf in self.route:
                    self.route.substitute_after(iaf, [Route.WayPoint(p[1]) for p in star[iaf][1]], save=self.next_wp)
                    
        if self.adep in fir.rwys.keys() and self.pof in (GROUND, LOADING): # aplico la SID que toque
            (sid,star) = fir.procedimientos[fir.rwyInUse[self.adep]]
            for fix in sid.keys():
                if fix in self.route:
                    self.route.substitute_before(fix, [Route.WayPoint(p[1]) for p in sid[fix][1]], save=self.next_wp)
                    
        #if self.adep in fir.aerodromes and self.route[0].fix!=self.adep:
        #    self.route.insert(0, self.adep)
        #
        #if self.ades in fir.aerodromes and self.route[-1].fix!=self.ades:
        #    self.route.append(self.ades)
        
        self.route = self.route.reduce()
            
    def set_type(self, type):
        """Saves the aircraft type and loads performance data"""
        while type[0].isdigit():  # Remove number of aircraft if present
            type = type[1:]
        self.type = type
        try: self.perf = BADA.Performance(type)
        except:
            # The previous call only fails if there is no old style performance
            # info for the type
            try:
                std = {'H':'B743','M':'A320','L':'PA34'}
                std_type = std[self.wake_hint.upper()]
                self.perf = BADA.Performance(std_type)
                logging.warning("No old style performance info for %s (%s). Using %s instead"%(self.callsign,type,std_type))
                self.type = std_type
            except:
                raise("Unable to load perfomance data for "+self.callsign)
        self.wake = self.perf.wtc.upper()
        
    def set_campo_eco(self):
        # TODO This should be part of TLPV.py, and maybe duplicated here for the benefit of the pseudopilot
        #self.campo_eco = self.route[-1].fix[0:3]
        #for ades in fir.aerodromes:
        #    if self.ades==ades:
        #        self.campo_eco=ades[2:4]
        self.campo_eco = TLPV.get_exit_ades(self)
            
    def set_ias(self,ias,force=False):
        self.std_speed = False

        # TODO This is a very poor approximation to the max ias
        # we are just taking the maximum cruise TAS and trying to guess
        # the maximum IAS from there.
        ias_max=min(cas_from_tas(self.perf.max_tas,self.lvl*100), self.perf.tma_tas*1.1)
        tas_max=self.perf.max_tas
        if (ias < ias_max) or (force == True):
            self.tgt_ias = float(ias)
            return (True, None)
        else:
            return (False, ias_max)
        
    def set_mach(self,mach,force=False):
        lvl = self.lvl * 100
        ias = cas_from_tas(tas_from_mach(mach,lvl),lvl)
        (r, ias_max) = self.set_ias(ias,force)
        if r: return (True, None)
        else: return (False, mach_from_tas(tas_from_cas(ias_max, lvl), lvl))
            
    def set_std_spd(self):
        self.std_speed = True
        self.set_ias(cas_from_tas(v(self), self.lvl*100))
        
    def set_std_mach(self):
        self.std_speed = True
        self.set_ias(cas_from_tas(v(self), self.lvl*100))
        
    def set_cfl(self, lvl):
        if lvl <= self.perf.max_fl:
            self.cfl = lvl
            return (True, None)
        else:
            return (False, self.perf.max_fl)
        
    def set_pfl(self, pfl):
        # TODO This should be handled in TLPV, not here.
        self.pfl = pfl
        
    def set_heading(self, hdg, opt):
        self.tgt_hdg = hdg
        self.to_do = 'hdg'
        self.to_do_aux = [hdg,opt]
        logging.debug(str((self.to_do,self.to_do_aux)))
        
    def fly_route(self,route):
        """Introduces a new route, and changes the flight mode to FPR"""
        self.cancel_app_auth()
        self.route = Route.Route(Route.get_waypoints(route))
        self.to_do = 'fpr'
        self.to_do_aux = []
        self.set_app_fix()
        self.calc_eto()
        self.set_campo_eco()
        
    def set_rate_descend(self,rate, force=False):
        self.std_rate=False
        if self.cfl>self.lvl:
            rate = rate/100.*60.
            if rate <= self.perf.max_roc*f_vert(self) or force==True:
                self.rocd = rate
                return (True, None)
            else:
                return (False, self.perf.max_roc*f_vert(self)*100./60)
        else:
            rate = -abs(rate/100.*60.)
            if abs(rate) <= self.perf.max_rod or force==True:
                self.rocd = rate
                return (True, None)
            else:
                return (False, -self.perf.max_rod*100./60)
                
    def set_app_fix(self):
        self.iaf = 'N/A'
        for i in range(len(self.route),0,-1):
            if self.route[i-1].fix in fir.iaps.keys():
                self.iaf = self.route[i-1].fix
                break
                
    def set_std_rate(self):
        self.std_rate = True
        if self.rocd>0:
            self.rocd = self.perf.std_roc * f_vert(self)
        else:
            self.rocd = -self.perf.std_rod
            
    def get_rot(self):
        """Returns rate of turn in degrees per second"""
        # Rate of turn. See BADA user manual 5.3
        bank_angle = 35  # Bank angle in degrees
        try: rot = 9.81*tan(pi*bank_angle/180)*180/(self.tas*.51444)/pi  # Rate of turn in degrees per second
        except ZeroDivisionError: rot = 40
        return rot

    def get_rate_descend(self):
        if hasattr(self, "perf"):
            return self.rocd
        return self.rocd/60.*100.
        
    def get_mach(self):
    # Devuelve el nmero de mach
      return mach_from_tas(self.tas,self.lvl * 100)

    def get_ias_max(self):
        return self.perf.max_tas/(1.0+0.002*self.perf.max_fl)
        
    def get_sector_entry_fix(self):
        if self.sector_entry_fix==None:
            return ''
        else:
            return self.sector_entry_fix
            
    def set_sector_entry_fix(self,fix):
        self.sector_entry_fix=fix
        
    def set_sector_entry_time(self,time):
        self.sector_entry_time=time

    def cancel_app_auth(self):
        if self.app_auth:
            for i in range(len(self.route),0,-1):
                if self.route[i-1].fix == self.iaf:
                    self.route = self.route[:i]
                    break
    
    def hold(self, fix, inbd_track=None, outbd_time=None, std_turns=None):
        # If there is a published hold on the fix, use its defaults
        try:
            ph = [hold for hold in fir.holds if hold.fix == fix][0]
            if inbd_track == None: inbd_track = ph.inbd_track
            if outbd_time == None: outbd_time = ph.outbd_time
            if std_turns  == None: std_turns  = ph.std_turns
        except:
            logging.debug("No published hold over "+str(fix))
        # Otherwise fill the blanks with defaults
        if inbd_track == None: inbd_track = self.route.get_inbd_track(fix)
        if outbd_time == None: outbd_time = 1  # One minute legs
        if std_turns  == None: std_turns = True
        
        if std_turns: turn = 1.0
        else: turn = -1.0
        self.to_do = 'hld'
        self.to_do_aux = [fix, inbd_track, timedelta(minutes=outbd_time), 0.0, False, turn]
        self.cancel_app_auth()
        
    def hdg_after_fix(self, aux, hdg):
        self.to_do = 'hdg<fix'
        self.to_do_aux = [aux, hdg]
        self.cancel_app_auth()
        
    def int_rdl(self, aux, track):
        if self.to_do <> 'hdg':
            self.tgt_hdg = self.hdg
        self.to_do = 'int_rdl'
        self.to_do_aux = [aux, track]
        self.cancel_app_auth()
        
    def execute_map(self):
        self._map = True
        
    def int_ils(self):
        if self.to_do <> 'hdg':
            self.tgt_hdg = self.hdg
        # Se supone que ha sido autorizado previamente
        self.to_do = 'app'
        self.app_auth = True
        (puntos_alt,llz,puntos_map) = fir.iaps[self.iaf]
        [xy_llz ,rdl, dist_ayuda, pdte_ayuda, alt_pista] = llz
        wp = Route.WP('_LLZ')
        wp._pos = xy_llz
        self.route = Route.Route([wp])
        self.int_loc = True
        (puntos_alt,llz,puntos_map) = fir.iaps[self.iaf]
        # En este paso se desciende el tráfico y se añaden los puntos
        logging.debug('Altitud: '+str(puntos_alt[0][3]))
        self.set_cfl(puntos_alt[0][3]/100.)
        self.set_std_rate()

    def int_llz(self):
        if self.to_do <> 'hdg':
            self.tgt_hdg = self.hdg
            # Se supone que ha sido autorizado previamente
        (puntos_alt,llz,puntos_map) = fir.iaps[self.iaf]
        [xy_llz ,rdl, dist_ayuda, pdte_ayuda, alt_pista] = llz
        self.to_do = 'int_rdl'
        self.to_do_aux = ["X%fY%f"%xy_llz, rdl]
        
    def orbit(self, turn_direction):
        self.to_do = 'orbit'
        if turn_direction == LEFT:
            self.to_do_aux = ['IZDA']
        else:
            self.to_do_aux = ['DCHA']
            
    def execute_app(self, ades, iaf):
        # TODO Currently we are not checking which destination the
        # user asked for, and just clear for approach to the current destination
        self.app_auth = True
        self._map = False
        self.iaf = ''
        for i in range(len(self.route),0,-1):
            if self.route[i-1].fix in fir.iaps.keys():
                self.iaf = self.route[i-1].fix
                break
        if self.iaf == '': # No encuentra procedimiento de aprox.
            pass
        (puntos_alt,llz,puntos_map) = fir.iaps[self.iaf]
        # En este paso se desciende el tráfico y se añaden los puntos
        logging.debug('Altitud: '+str(puntos_alt[0][3]))
        self.set_cfl(puntos_alt[0][3]/100.)
        self.set_std_rate()
        if self.to_do == 'hld':
            pass
        else:
            self.to_do = 'app'
            for i in range(len(self.route),0,-1):
                if self.route[i-1].fix == self.iaf:
                    self.route = self.route[:i]
                    break
            self.route.append([Route.WayPoint(p[1]) for p in puntos_alt])
            wp = Route.WayPoint("_LLZ")
            wp._pos = llz[0]
            self.route.append(wp)
        logging.debug("Autorizado aproximación: " +str(self.route))
    
    def route_direct(self, fix):
        aux = None
        # Si es un punto intermedio de la ruta, lo detecta
        for i in range(len(self.route)):
            if self.route[i].fix == fix.upper():
                aux = self.route[i:]
        # Si no estáen la ruta, insertamos el punto como n 1
        if aux == None:
            for [nombre,coord] in self.fir.points:
                if nombre == fix.upper():
                    aux = [[coord,nombre,'']]
                    for a in self.route:
                        aux.append(a)
        if aux == None:
            # TODO we need to deal with exceptions here the same
            # we do with set_cfl, for instance
            logging.warning('Punto '+fix.upper()+' no encontrado al tratar de hacer una ruta directa')
            return

        # This is what actually sets the route
        self.fly_route(aux)
        
        
    def depart(self, sid, cfl, t):
        # Ahora se depega el avión y se elimina de la lista
        self.t = t
        self.t_ficha = t - timedelta(hours=100)  # TODO This does not belong here
        self.cfl = cfl
        self.pof = TAKEOFF
        self.next(t)
        self.calc_eto()
    
    def log_waypoint(self):
        wp = self.route.pop(0)
        wp.ato = self.t
        self.log.append(wp)
    
    def copy(self):
        s = self
        acft = Aircraft(s.callsign, s.type, s.adep, s.ades, s.cfl, s.rfl, s.route,
                        eobt = self.eobt, next_wp = self.next_wp,
                        next_wp_eto = self.next_wp_eto, wake_hint = self.wake_hint, init=False)
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
        # Also, it only applys if the aircraft is within 1.5 the turn radius
        # to the waypoint
        if len(self.route)==0: return False  # No need to check.
        v1 = pr((1, self.route.get_outbd_track(0)))  # Vector defining the hemiplane
        v2 = r(self.pos, self.route[0].pos())  # Vector joining the wp and the aircraft
        on_goal_hemiplane = dp(v1, v2)>0  # When the dot product is positive, the aircraft is on the goal hemiplane
        dist = rp(v2)[0]
        turn_radius = self.tas/(62.8318*self.get_rot())  # In nautical miles
        try: reached = not self._prev_on_goal and on_goal_hemiplane and dist < turn_radius * 1.5
        except: reached = False
        if reached: self._prev_on_goal = None
        else: self._prev_on_goal = on_goal_hemiplane
        return reached
    
    #def __del__(self):
    #    logging.debug("Aircraft.__del__ (%s)"%self.callsign)

if __name__=='__main__':
    pass    
