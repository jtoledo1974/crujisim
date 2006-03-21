#!/usr/bin/python
#-*- coding:iso8859-15 -*-
# $Id$

# Movimiento de un móvil con velocidad uniforme

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

#############################
# W A R N I N G ! ! !
#
# Do not edit this code. This code is considered old and deprecated
# This module is to be rewriten wholy as Aircraft.py
#
#############################

# Module imports
from MathUtil import *
import sys
import logging
import BADA

# Constants
LEFT = "LEFT"
RIGHT = "RIGHT"

PREACTIVE = "PREACTIVE"
READY = "READY"

# Globals

a = BADA.Atmosphere()
tas_from_cas = a.get_tas_from_cas
cas_from_tas = a.get_cas_from_tas
tas_from_mach = a.get_tas_from_mach
mach_from_tas = a.get_mach_from_tas


wind = [0.0,0.0]

# TODO This is old code still pending to be removed    
def set_global_vars(_punto, _wind, _aeropuertos, _esperas_publicadas,_rwys,_rwyInUse,_procedimientos, _proc_app,_min_sep):
    global punto, wind, aeropuertos, esperas_publicadas,rwys,rwyInUse, procedimientos, proc_app, min_sep
    punto = _punto
    wind = _wind
    aeropuertos = _aeropuertos
    esperas_publicadas = _esperas_publicadas
    rwys = _rwys
    rwyInUse = _rwyInUse
    procedimientos = _procedimientos
    proc_app = _proc_app
    min_sep = _min_sep
    
    
def v(self):
  #Devuelve TAS
    if not self.es_spd_std: # Velocidad mínima manteniedo IAS
        ias_max=cas_from_tas(self.spd_max,self.alt*100)
        tas_max=tas_from_cas(ias_max,self.alt)
        self.ias = cas_from_tas(self.spd, self.alt*100)
        if abs(self.ias_obj-self.ias)>1.:
            self.ias = self.ias_obj
        # return self.ias * (1.0+0.002 *self.alt)
        return tas_from_cas(self.ias, self.alt*100)
    if hasattr(self, "perf"):
        if self.alt<self.cfl: tas = self.perf.get_climb_perf(self.alt)[0] 
        elif self.alt>self.cfl: tas = self.perf.get_descent_perf(self.alt)[0]
        else: tas = self.perf.get_cruise_perf(self.alt)[0]
        return tas      
    
    if self.fl_max > 290.: # Fast moving traffic
        inicio_app = 00.
        trans_tma = 50.
        vel_tma = 150.
    elif self.fl_max > 200.: # Medium speed traffic
        inicio_app = 00.
        trans_tma = 35.
        vel_tma = 80.
    else:
        inicio_app = 00.
        trans_tma = 25.
        vel_tma = 35.
        
    if self.alt<=inicio_app: # Velocidad de aproximación
        return self.spd_app
    elif self.alt<=trans_tma: # Transición entre vel aprox y tma
        p=(self.alt-inicio_app)/(trans_tma - inicio_app)
        return self.spd_app*(1.-p)+self.spd_tma*p
    elif self.alt<=vel_tma: # Transición entre ruta y tma
        p=(self.alt-trans_tma)/(vel_tma - trans_tma)
        ias_std=self.spd_std/(1+0.002*self.fl_max*0.90)
        return self.spd_tma*(1.-p)+ias_std *(1.0+0.002*self.alt)*p
        #    return self.spd_tma
    else:
        ias_std=self.spd_std/(1+0.002*self.fl_max*0.90)
        return min(ias_std * (1+0.002*self.alt),self.spd_max)
        #     p=min((self.alt-vel_tma)/(self.fl_max-vel_tma),1.)
        #     return min(self.spd_max * p + self.spd_tma * (1-p),self.spd_std)
        
    
def f_vert(self):
  # Devuelve factor corrección de velocidad vertical
    q=self.alt/self.fl_max
    if q<.75:
        return 1.0
    elif q<.90:
        return 0.80
    else:
        return 0.60
        
def mach_tas(perc):
  # Transforma nmero de mach a IAS
    return perc*600
    
def complete_flight_plan(self):
  # Completa el plan de vuelo con la SID o STAR, si es que hay alguna publicada para origen y destino
    if self.destino in rwys.keys(): # aplico la STAR que toque
        (sid,star) = procedimientos[rwyInUse[self.destino]]
        for i in range(len(self.route)):
            fijo = self.route[i][1]
            if fijo in star.keys():
                self.route = self.route [:i]
                for pto_star in star[fijo][1]:
                    self.route.append(pto_star)
                break
                
    if self.origen in rwys.keys() and not self.is_flying(): # aplico la SID que toque
        (sid,star) = procedimientos[rwyInUse[self.origen]]
        for i in range(len(self.route)):
            fijo = self.route[i][1]
            if fijo in sid.keys():
                aux_ruta = []
                for pto_sid in sid[fijo][1]:
                    aux_ruta.append(pto_sid)
                self.route = aux_ruta + self.route [i+1:]
                break
                
                
def get_hdg_obj(self,deriva,t):
  # Da el rumbo objetivo en función de la demanda
    if self.to_do == 'fpr': # Mantener plan de vuelo
        self.pto=self.route[0][0] #Punto al que se dirige con corrección de deriva
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
    # self.to_do_aux = [[coord,nombre,estim],derrota_acerc, tiempo_alej,Tiempo en alejam. = 0.0,Esta en espera=False/True,giro I=-1.0/D=+1.0]
        if not self.to_do_aux[4] and self.to_do_aux[0] in self.route: # An no ha llegado a la espera, sigue volando en ruta
            self.pto=self.route[0][0] #Punto al que se dirige con corrección de deriva
            self.vect=rp(r(self.pto,self.pos))
            # Correción de deriva
            return self.vect[1] - deriva
        else: # Está dentro de la espera, entramos bucle de la espera
            self.to_do_aux[4] = True
            if not self.to_do_aux[0] in self.route: # El fijo principal debe estar en la ruta. Si no está se pone
                self.route.insert(0,self.to_do_aux[0])
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
            self.pto=self.route[0][0] #Punto al que se dirige con corrección de deriva
            self.vect=rp(r(self.pto,self.pos))
            # Correción de deriva
            return self.vect[1] - deriva
        else:
            self.vect=rp((2.0*self.ground_spd,self.track))
            return self.to_do_aux[1]
    elif self.to_do == 'int_rdl':
        (rx,ry) = r(self.to_do_aux[0],self.pos) # Coordenadas relativas a la radioayuda
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
            self.hold_hdg = self.to_do_aux[1]
            return self.to_do_aux[1] - deriva
        elif dist_perp<0.8:
            self.vect=rp((2.0*self.ground_spd,self.track))
            self.hold_hdg = (self.to_do_aux[1] - 20.0 * sgn(ang_aux))%360.0
            return (self.to_do_aux[1] - deriva - 20.0 * sgn(ang_aux))%360.0
        else:
            self.vect=rp((2.0*self.ground_spd,self.track))
            return (self.hold_hdg - deriva)%360.0
            #       return (self.to_do_aux[1] - deriva - 45.0 * sgn(ang_aux))%360.0
    elif self.to_do == 'app':
        (puntos_alt,llz,puntos_map) = proc_app[self.fijo_app]
        [xy_llz ,rdl, dist_ayuda, pdte_ayuda, alt_pista] = llz
        if len(self.route) == 0: # Es el primer acceso a app desde la espera. Se añaden los puntos
            for [a,b,c,h] in puntos_alt:
                self.route.append([a,b,c])
            self.route.append([xy_llz,'_LLZ',''])
        if len (self.route) > 1: # An no estáen el localizador, tocamos solamente la altitud y como plan de vuelo
            if self._map and [xy_llz,'_LLZ',''] not in self.route: # Ya estáfrustrando
                for [a,b,c,h] in puntos_map:
                    if [a,b,c] == self.route[0]:
                        self.cfl = h/100.
                        break
            else:
                for [a,b,c,h] in puntos_alt:
                    if [a,b,c] == self.route[0]:
                        self.cfl = h/100.
                        break
            self.pto=self.route[0][0] #Punto al que se dirige con corrección de deriva
            self.vect=rp(r(self.pto,self.pos))
            # Correción de deriva
            return self.vect[1] - deriva
        if len(self.route) == 1: # Interceptar localizador y senda de planeo
            if self._map and [xy_llz,'_LLZ',''] not in self.route: # Ya estáfrustrando hacia el ltimo punto, asimilamos a plan de vuelo normal
                self.to_do = 'fpr'
                self.app_auth = False
                self.app_fix = ''
                self._map = False
                self.pto=self.route[0][0] #Punto al que se dirige con corrección de deriva
                self.vect=rp(r(self.pto,self.pos))
                # Correción de deriva
                return self.vect[1] - deriva
            else:
                (rx,ry) = r(xy_llz,self.pos) # Coordenadas relativas a la radioayuda
                # Primero intersecta la senda de planeo cuando es inferior. Solamente tocamos el rate de descenso
                dist_thr = rp((rx,ry))[0]-dist_ayuda
                derrota = rp((rx,ry))[1]
                if abs(dist_thr) < 0.50: # Avión aterrizado
                    if (self.alt-alt_pista/100.)>2.or abs(derrota-rdl)>90.: # En caso de estar 200 ft por encima, hace MAP o si ya ha pasado el LLZ
                        self._map = True 
                    if self._map: # Procedimiento de frustrada asignado
                        self.set_std_spd()
                        self.route = []
                        for [a,b,c,h] in puntos_map:
                            self.route.append([a,b,c])
                    else:
                        logging.debug("Aterrizando el "+str(self.name))
                        self.kill()
                        return 'Dead'
                if self.esta_en_llz: # Interceptación de la senda de planeo. Se ajusta rate descenso y ajuste ias = spd_app
                    fl_gp = (alt_pista/100. + dist_thr * pdte_ayuda * 60.)
                    if fl_gp <= self.alt:
                        self.set_spd(self.spd_app/(1.0+0.002*self.alt))
                        self.cfl = alt_pista/100.
                        rate = ((self.alt - fl_gp)*2.0 + self.ground_spd * pdte_ayuda )
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
                    if abs(self.alt-self.cfl)<002.0:
                        self.esta_en_llz = True
                    self.int_loc = False
                    self.vect=rp((2.0*self.ground_spd,self.track))
                    return rdl - deriva
                elif dist_perp<0.8:
                    if abs(self.alt-self.cfl)<002.0:
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
                            return self.hold_hdg - deriva
                        else:
                            self.int_loc = False
                            self.vect=rp((2.0*self.ground_spd,self.track))
                            self.hold_hdg = rdl- 45.0 * sgn(ang_aux)
                            return (rdl - deriva - 45.0 * sgn(ang_aux))%360.0
                    else:
                        self.vect=rp((2.0*self.ground_spd,self.track))
                        return (rdl - deriva - 45.0 * sgn(ang_aux))%360.0
                        
                        
                        
class Airplane:

    def __init__(self):
        self.name='IBE767'
        self.radio_callsign='IBERIA'
        self.tipo='B747'
        self.estela='H'
        self.origen='LEBB'
        self.destino='LEMD'
        self.pos=(0.0,0.0) #x,y
        self.t=0.0 # ltimo tiempo calculado
        self.hdg=400.0 # Último rumbo calculado. Este valor es para saber la primera vez
        self.track = 400.0 # Derrota del avión
        self.hold_hdg=400.0 
        self.alt=350.0 # Altitud
        self.cfl=350.0 # Altitud autorizada
        self.pfl=self.cfl
        self.rfl=self.cfl
        self.fl_max=350.0
        self.rate_climb_max=25.0/60.
        self.rate_climb_std=15.0/60.
        self.rate_desc_max=25.0/60.
        self.rate_desc_std=15.0/60.
        self.es_std=True
        self.rate=0.0 #Tasa de asc/desc.
        self.spd=0.
        self.ground_spd=350.
        self.spd_std=self.spd
        self.spd_max=self.spd
        self.filed_tas = 0.
        self.spd_tma=200.
        self.spd_app=180.
        self.es_spd_std=True
        self.ias=300. # Velocidad indicada
        self.ias_obj = 0.
        # A list containig all the route points [ (coords), nombre, eto_ascii, eto ]
        # ETO is defined as the number of hours since 00:00. Minutes and seconds are fractions of the hour
        self.route=[[(-8.0,10.0),'punto','00:00',0.]]
        self.eobt=None  # Estimated off block time in fractional hours since midnight
        self.turn=3.0*60.*60. #Los mínimos grados por segundo que vira el avión
        self.vfp=True # Vale 1 si via flight plan y 0 si mantiene rumbo
        self.to_do='fpr'
        self.to_do_aux = ''
        self.se_pinta=False
        self.ficha_imprimida=False
        self.t_ficha=0.
        self.t_impresion=0.
        self.campo_eco=''
        self.esta_asumido=False
        self.last_lad = 0
        self.app_auth = False
        self.fijo_app = ''
        self._map = False
        self.int_loc = False
        self.esta_en_llz = False
        self.sector_entry_fix = None  # First route point within our sector
        self.sector_entry_time = None # Estimated ETO over our sector entry point
        self.reports = []  # List of things an aircraft should report.
                           # [{'time':1.65,'text':'Request climb FL230'},
                           #  ,{'time':2.34,'text':'Overflown DGO'}]
            
    def __getstate__(self):
        """This function is called by the pickler. We remove the attributes
        that we don't want to send through the wire"""
        odict = self.__dict__.copy()
        try: del odict['perf']
        except: pass
        return odict
        
    def next(self,t):
        global wind, aeropuertos
        # Devuelve la posición en el tiempo t
        if t<self.t:
            self.se_pinta=False
            return self.se_pinta # Con esto activamos los vuelos a la hora inicial y se dejan
        else:
            self.se_pinta=1
        # Cálculo de la altitud
        if self.cfl>self.alt:
            if self.es_std:
                self.rate = self.rate_climb_std * f_vert(self)
                if hasattr(self, "perf"):
                    self.rate=self.perf.get_climb_perf(self.alt)[2] * 60./100
            else:
                self.rate = min(self.rate_climb_max * f_vert(self),abs(self.rate))
        elif self.cfl<self.alt:
            if self.es_std:
                self.rate = -min(self.spd/0.2/100.*60.,self.rate_desc_max * f_vert(self))
                if hasattr(self, "perf"):
                    self.rate=-self.perf.get_descent_perf(self.alt)[1] * 60./100
            else:
                self.rate = -min(self.rate_desc_max * f_vert(self),abs(self.rate))
        inch=self.rate*(t-self.t)
        if abs(self.alt-self.cfl)<abs(inch):
            self.alt=self.cfl
            self.rate =0.
            self.es_std=True
        else:
            self.alt=self.alt+inch
            # Iteración para encontrar la posición
        while t>=self.t+1./60./60.:
            aux_v = v(self)
            inc_v_max = 1.5 * (t-self.t) * 60. * 60. #Inc. v = 90kts/min TAS
            if abs(aux_v-self.spd)<inc_v_max or self.spd == 0.:
                self.spd=aux_v
            else:
                self.spd = self.spd + inc_v_max * sgn(aux_v - self.spd)
            (vx,vy) = pr((1.0,self.track))
            (wx,wy) = pr(wind)
            wind_perp = wx*vy - wy*vx
            wind_paral = wx * vx + wy * vy
            self.ground_spd = self.spd + wind_paral
            deriva = degrees(asin(wind_perp / self.spd))
            r_obj = get_hdg_obj(self,deriva,t)
            if r_obj == 'Dead':
                return self.se_pinta
            if self.hdg<180.0 and r_obj>self.hdg+180.0:
                r_obj=r_obj-360.0
            elif self.hdg>180.0 and r_obj<self.hdg-180.0:
                r_obj=r_obj+360.0
            aux=r_obj-self.hdg
            if abs(aux)<self.turn*(t-self.t):
                self.hdg=r_obj%360
            else:
                self.hdg=(self.hdg+(t-self.t)*self.turn*sgn(aux))%360
            self.track = (self.hdg + deriva)%360
            self.salto=(self.ground_spd)*(t-self.t) # Distancia recorrida en este inc. de t incluyendo viento
            # Ha pasado el punto al que se dirige
            if self.salto>self.vect[0]:
                if len(self.route)==1:
                    if self.app_auth and self.destino in rwys.keys():
                        self.to_do = 'app'
                        #             (puntos_alt,llz,puntos_map) = proc_app[sel.fijo_app]
                        #             self.to_do_aux = app
                        self.salto=self.spd*(t-self.t) # Distancia recorrida en este inc.de t sin viento
                        efecto_viento = (wx*(t-self.t),wy*(t-self.t)) # Deriva por el viento
                        self.t = t
                        self.route.pop(0)
                    elif self.route[0][1] in aeropuertos: # Si el ltimo punto estáen la lista de aeropuertos, orbita sobre él
                        if self.to_do == 'fpr': # En caso de que llegue a ese punto en ruta
                            self.vfp=False
                            for [fijo_pub,rumbo,tiempo,lado] in esperas_publicadas: # Si hay espera publicada, la usa
                                if fijo_pub == self.route[0][1]:
                                    if lado.upper() == 'I':
                                        aux_lado = -1.0
                                    else:
                                        aux_lado = 1.0
                                    self.to_do = 'hld'
                                    self.to_do_aux = [self.route[0], rumbo, tiempo/60., 0.0, True, aux_lado]
                                    self.route.pop(0)
                                    break
                            if len(self.route)==1: # En caso contrario, hace una espera de 1 min 
                                self.to_do = 'hld'
                                self.to_do_aux = [self.route[0], self.hdg, 1./60., 0.0, True, 1.0]
                                self.route.pop(0)
                        else:
                            self.route.pop(0)
                        self.salto=self.spd*(t-self.t) # Distancia recorrida en este inc.de t sin viento
                        efecto_viento = (wx*(t-self.t),wy*(t-self.t)) # Deriva por el viento
                        self.t = t
                    else:
                        self.vfp=False # Si es el ltimo punto, mantiene el rumbo
                        self.to_do = 'hdg'
                        self.to_do_aux = [self.hdg,'ECON']
                        self.hold_hdg=self.hdg
                        self.salto=self.spd*(t-self.t) # Distancia recorrida en este inc.de t sin viento
                        efecto_viento = (wx*(t-self.t),wy*(t-self.t)) # Deriva por el viento
                        self.t = t  
                else:
                    self.route.pop(0) # Eliminamos el punto ya pasado de la ruta e iteramos
                    perc=self.vect[0]/self.salto
                    self.salto=self.spd*(t-self.t)*perc
                    efecto_viento = p((wx,wy),(t-self.t)*perc) # Deriva por el viento
                    self.t=self.t+(t-self.t)*perc
            else:
                self.salto=self.spd*(t-self.t) # Distancia recorrida en este inc.de t sin viento
                efecto_viento = (wx*(t-self.t),wy*(t-self.t)) # Deriva por el viento
                self.t=t #Almacenamos el tiempo
            self.pos=s(s(self.pos,pr((self.salto,self.hdg))),efecto_viento) #Cambiamos la posición
        return self.se_pinta
    
    def set_initial_heading(self):
        self.pto = self.route[0][0] #Punto al que se dirige
        self.vect = rp(r(self.pto,self.pos))
        self.hdg = self.vect[1]
        self.track = self.vect[1]
        
    def set_coords(self, (x0, y0)):
        self.x0 = x0
        self.y0 = y0
        
    def set_position(self,pos):
        self.pos=pos
        
    def set_callsign(self,name):
        self.name = name
        
    def set_kind(self,tipo):
        self.tipo = tipo
        
    def set_wake(self,wake):
        self.estela = wake.upper()
        
    def get_wake(self):
        return self.estela
        
    def set_origin(self,ori):
        self.origen = ori
        
    def set_destination(self,dest):
        self.destino = dest
        
    def set_alt(self, alt):
        self.alt = alt
        
    def set_spd(self,ias,force=False):
        self.es_spd_std = False
        vel=tas_from_cas(ias, self.alt*100)
        #if float(ias)<1.:
        #    # TODO Substitue with a proper mach calculation
        #    vel = tas_from_mach(float(ias),self.alt*100)
        #    ias = cas_from_tas(vel,self.alt*100)
        
        ias_max=cas_from_tas(self.spd_max,self.alt*100)
        tas_max=self.spd_max
        if (vel < tas_max) or (force == True):
            self.ias_obj = float(ias)
            return True
        else:
            self.ias_obj = ias_max
            return False
        
    def set_mach(self,mach,force=False):
        ias = cas_from_tas(tas_from_mach(mach,self.alt*100),self.alt*100)
        self.set_spd(ias,force)
        
            
    def set_std_spd(self):
        self.es_spd_std = True
        
    def set_std_mach(self):
        self.es_spd_std = True
        
    def set_cfl(self, alt):
        if alt <= self.fl_max:
            self.cfl = alt
            return True
        else:
            self.cfl = self.fl_max
            return False
            
    def set_pfl(self, alt):
        self.pfl = alt
        
    def set_rfl(self,rfl):
        self.rfl = rfl
        
    def set_heading(self, hdg, opt):
        self.hold_hdg = hdg
        self.vfp = False
        self.to_do = 'hdg'
        self.to_do_aux = [hdg,opt]
        logging.debug(self.to_do,self.to_do_aux)
        
    def set_route(self,route):
        self.cancel_app_auth()
        self.route = route
        self.vfp = True
        self.to_do = 'fpr'
        self.to_do_aux = []
        self.set_app_fix()
        
    def set_initial_t(self,t):
        self.t = t
        
    def set_vfp(self,vfp):
        self.vfp = vfp
        self.to_do = 'fpr'
        
    def set_se_pinta(self,opci):
        self.se_pinta = opci
        
    def set_campo_eco(self,eco):
        self.campo_eco = eco
        
    def get_callsign(self):
        return self.name
        
    def get_coords(self):
        return self.pos
        
    def get_cfl(self):
        return self.cfl
        
    def get_pfl(self):
        return self.pfl
        
    def get_origin(self):
        return self.origen
        
    def get_destination(self):
        return self.destino
        
    def get_kind(self):
        return self.tipo
        
    def get_alt(self):
        return self.alt
        
    def get_heading(self):
        return self.hdg
        
    def get_track(self):
        return self.track
        
    def get_ias(self):
        return self.spd/(1.0+0.002*self.alt)
        
    def set_ias(self, ias):
        self.ias = ias
        
    def set_rate_descend(self,rate):
        self.es_std=False
        if self.cfl>self.alt:
            self.rate = rate/100.*60.
            if self.rate <= self.rate_climb_max*f_vert(self):
                return True
            else:
                self.rate = self.rate_climb_max*f_vert(self)
                return False
        else:
            self.rate = -abs(rate/100.*60.)
            if abs(self.rate) <= self.rate_desc_max:
                return True
            else:
                self.rate = -self.rate_desc_max
                return False
                
    def set_app_fix(self):
        self.fijo_app = 'N/A'
        for i in range(len(self.route),0,-1):
            if self.route[i-1][1] in proc_app.keys():
                self.fijo_app = self.route[i-1][1]
                break
                
    def set_std_rate(self):
        self.es_std = True
        if self.rate>0:
            self.rate = self.rate_climb_std * f_vert(self)
        else:
            self.rate = -self.rate_desc_std
            
    def set_filed_tas(self,filed_tas):
        self.filed_tas=filed_tas
        
    def get_filed_tas(self):
        return self.filed_tas
        
    def get_rate_descend(self):
        if hasattr(self, "perf"):
            return self.rate
        return self.rate/60.*100.
        
    def get_speed(self):
        return self.spd
    
    def get_mach(self):
    # Devuelve el nmero de mach
      return mach_from_tas(self.spd,self.alt * 100)

        
    def get_ias_max(self):
        return self.spd_max/(1.0+0.002*self.fl_max)
        
    def get_ground_speed(self):
        return self.ground_spd
        
    def get_eobt(self):
        return self.eobt
        
    def set_eobt(self,eobt):
        self.eobt=eobt
        
    def get_sector_entry_fix(self):
        if self.sector_entry_fix==None:
            return ''
        else:
            return self.sector_entry_fix
            
    def set_sector_entry_fix(self,fix):
        self.sector_entry_fix=fix
        
    def get_sector_entry_time(self):
        return self.sector_entry_time
        
    def set_sector_entry_time(self,time):
        self.sector_entry_time=time

    def cancel_app_auth(self):
        if self.app_auth:
            for i in range(len(self.route),0,-1):
                if self.route[i-1][1] == self.fijo_app:
                    self.route = self.route[:i]
                    break
    
    def hold(self, fix, inbound_track, outbound_time, turn_direction):
        self.vfp = False
        self.to_do = 'hld'
        self.to_do_aux = [fix, inbound_track, outbound_time, 0.0, False, turn_direction]
        self.cancel_app_auth()
        
    def hdg_after_fix(self, aux, hdg):
        self.vfp = False
        self.to_do = 'hdg<fix'
        self.to_do_aux = [aux, hdg]
        self.cancel_app_auth()
        
    def int_rdl(self, aux, track):
        if self.to_do <> 'hdg':
            self.hold_hdg = self.hdg
        self.vfp = False
        self.to_do = 'int_rdl'
        self.to_do_aux = [aux, track]
        self.cancel_app_auth()
        
    def execute_map(self):
        self._map = True
        
    def int_ils(self):
        if self.to_do <> 'hdg':
            self.hold_hdg = self.hdg
            # Se supone que ha sido autorizado previamente
        self.to_do = 'app'
        self.app_auth = True
        (puntos_alt,llz,puntos_map) = fir.proc_app[self.fijo_app]
        [xy_llz ,rdl, dist_ayuda, pdte_ayuda, alt_pista] = llz
        self.route = [[xy_llz,'_LLZ','']]
        self.int_loc = True
        (puntos_alt,llz,puntos_map) = fir.proc_app[self.fijo_app]
        # En este paso se desciende el tráfico y se añaden los puntos
        logging.debug('Altitud: '+str(puntos_alt[0][3]))
        self.set_cfl(puntos_alt[0][3]/100.)
        self.set_std_rate()

    def int_llz(self):
        if self.to_do <> 'hdg':
            self.hold_hdg = self.hdg
            # Se supone que ha sido autorizado previamente
        (puntos_alt,llz,puntos_map) = fir.proc_app[self.fijo_app]
        [xy_llz ,rdl, dist_ayuda, pdte_ayuda, alt_pista] = llz
        self.to_do = 'int_rdl'
        self.to_do_aux = [xy_llz, rdl]
        
    def orbit(self, turn_direction):
        self.to_do = 'orbit'
        if turn_direction == LEFT:
            self.to_do_aux = ['IZDA']
        else:
            self.to_do_aux = ['DCHA']
            
    def execute_app(self, dest, iaf):
        # TODO Currently we are not checking which destination the
        # user asked for, and just clear for approach to the current destination
        self.app_auth = True
        self._map = False
        self.fijo_app = ''
        for i in range(len(self.route),0,-1):
            if self.route[i-1][1] in fir.proc_app.keys():
                self.fijo_app = self.route[i-1][1]
                break
        if self.fijo_app == '': # No encuentra procedimiento de aprox.
            pass
        (puntos_alt,llz,puntos_map) = fir.proc_app[self.fijo_app]
        # En este paso se desciende el tráfico y se añaden los puntos
        logging.debug('Altitud: '+str(puntos_alt[0][3]))
        self.set_cfl(puntos_alt[0][3]/100.)
        self.set_std_rate()
        if self.to_do == 'hld':
            pass
        else:
            self.to_do = 'app'
            for i in range(len(self.route),0,-1):
                if self.route[i-1][1] == self.fijo_app:
                    self.route = self.route[:i]
                    break
            for [a,b,c,h] in puntos_alt:
                self.route.append([a,b,c,0.0])
            self.route.append([llz[0],'_LLZ',''])
        logging.debug("Autorizado aproximación: " +str(self.route))
    
    def route_direct(self, fix):
        aux = None
        # Si es un punto intermedio de la ruta, lo detecta
        for i in range(len(self.route)):
            if self.route[i][1] == fix.upper():
                aux = self.route[i:]
        # Si no estáen la ruta, insertamos el punto como n 1
        if aux == None:
            for [nombre,coord] in self.fir.points:
                if nombre == fix.upper():
                    aux = [[coord,nombre,'']]
                    for a in self.route:
                        aux.append(a)
        # Si no encuentra el punto, fondo en rojo y no hace nada
        if aux == None:
            # TODO we need to deal with exceptions on the networking code
            logging.warning('Punto '+fix.upper()+' no encontrado al tratar de hacer una ruta directa')
            return

        # This is what actually sets the route
        self.set_route(aux)
        
        
    def depart(self, sid, cfl, t):
        if sid.upper() != self.sid.upper():  # self.sid is set in GTA.py
            for [p,(x,y)] in fir.points:
                if p==self.sid[:-2]:
                    break
            for i in range(len(self.route)):
                if self.route[i][1] in sid.upper():
                    self.route = self.route[i+1:]
                    self.route.insert(0,[(x,y),p,''])
                    complete_flight_plan(self)
                    break
        # Ahora se depega el avión y se elimina de la lista
        self.t = t
        self.t_ficha = t-100.
        self.ficha_imprimida = True
        self.cfl = cfl
        self.next(t)        
        
    def se_debe_imprimir(self,t):
      # Definimos cuánto tiempo antes nos sale la ficha y el tiempo de permanencia del mensaje
        permanece=2./60.
        if not self.ficha_imprimida and self.t_impresion<t:
            self.ficha_imprimida=True
            self.t_ficha=t
            return True
        elif t-self.t_ficha<permanece:
            return True
        else:
            return False
            
    def kill(self):
        """Kills aircraft
        
        Currently it just forces the plane not to be painted any more
        """
        self.t=self.t+1000.
        self.se_pinta = False
        
    def is_flying(self):
        return self.se_pinta

class Type:
    """Data related to an aircraft type"""
    def __init__(self,type,data):
        """Create an aircraft type instance from the ICAO code and the
        comma separated list of performance numbers"""        
        self.type = type.upper()
        data = data.split(',')
        self.wtc = data[0][0].upper()  # Only the first letter
        self.max_fl = int(data[1])
        self.max_roc = int(data[2])  # Feet per minute
        self.std_roc = int(data[3])
        self.max_rod = int(data[4])
        self.std_rod = int(data[5])
        self.cruise_tas = int(data[6])  # Knots
        self.max_tas = int(data[7])
        self.tma_tas = int(data[8])
        self.app_tas = int(data[9])   

def load_types(file):
    types = {}
    import ConfigParser
    cp = ConfigParser.ConfigParser()
    cp.readfp(open(file,"r"))
    for typename in cp.options('performances'):
        try:
            type = Type(typename,cp.get('performances',typename))
            types[typename.upper()]=type
        except:
            logging.warning("Unable to parse aircraft type "+typename)
    return types

if __name__=='__main__':
    pass    
