#!/usr/bin/python
# -*- coding:utf-8 -*-

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

"""Outputs desired course track for an LNAV mode"""

from builtins import object
import logging

# Module imports
from . import Route
from .MathUtil import pr, rp, r, sgn

from . import LEVELS_PER_HOUR_TO_FPM, FEET_TO_LEVELS, NM_TO_LEVELS
from .Aircraft import LANDED


# JTC 2018-10 This is still all spaghetti code. I moved LNAV methods here, but it still has
# to be properly compartmentalized. Way too many obscure vect, to_do_aux, etc. references

class Aircraft(object):

    # Heading calculations

    def get_tgt_hdg_fpr(self, wind_drift, t):
        """Follow flight plan route"""
        self.vect = self.get_bearing_to_next()
        # Correción de wind_drift
        return self.vect[1] - wind_drift

    def get_tgt_hdg_hdg(self, wind_drift, t):
        """Fly heading"""
        hdg_obj = self.to_do_aux[0]
        if self.hdg < 180.0 and hdg_obj > self.hdg + 180.0:
            hdg_obj -= 360.0
        elif self.hdg > 180.0 and hdg_obj < self.hdg - 180.0:
            hdg_obj += 360.0
        aux_hdg = self.hdg - hdg_obj
        self.vect = rp((2.0 * self.ground_spd, hdg_obj))
        if self.to_do_aux[1] == 'DCHA':
            if aux_hdg > 0.:  # El rumbo está a su izquierda
                return (self.hdg + 90.) % 360.
            else:  # Está a su derecha o ya está en rumbo
                return self.to_do_aux[0]
        elif self.to_do_aux[1] == 'IZDA':
            if aux_hdg < 0.:  # El rumbo está a su derecha
                return (self.hdg - 90.) % 360.
            else:  # Está a su izquierda o ya está en rumbo
                return self.to_do_aux[0]
        else:
            return self.to_do_aux[0]

    def get_tgt_hdg_orbit(self, wind_drift, t):
        """Orbit on present position"""
        if self.to_do_aux[0] == 'DCHA':
            return (self.hdg + 90.0) % 360.0
        else:
            return (self.hdg - 90.0) % 360.0

    def get_tgt_hdg_hold(self, wind_drift, t):
        """Fly published holding pattern"""
        if not self.to_do_aux[4] and self.to_do_aux[0] in self.route:
            # Aún no ha llegado a la espera, sigue volando en ruta
            # Punto al que se dirige con corrección de wind_drift
            self.pto = self.route[0].pos()
            self.vect = rp(r(self.pto, self.pos))
            # Correción de wind_drift
            return self.vect[1] - wind_drift
        else:  # Está dentro de la espera, entramos bucle de la espera
            self.to_do_aux[4] = True
            # El fijo principal debe estar en la ruta. Si no está se pone
            if not self.to_do_aux[0] in self.route:
                self.route.insert(0, Route.WayPoint(self.to_do_aux[0]))
            # Con esta operación no nos borra el punto de la espera
            self.vect = rp((2.0 * self.ground_spd, self.track))
            if len(self.to_do_aux) == 6:  # Vamos a definir el rumbo objetivo, añadiéndolo al final
                r_acerc = (self.to_do_aux[1] - wind_drift) % 360.0
                if self.hdg < 180.0 and r_acerc > self.hdg + 180.0:
                    r_acerc -= 360.0
                elif self.hdg > 180.0 and r_acerc < self.hdg - 180.0:
                    r_acerc += 360.0
                aux = r_acerc - self.hdg
                if aux > -60.0 and aux < 120.0:  # Entrada directa
                    target_hdg = (self.to_do_aux[1] + 180.0 - wind_drift) % 360.  # Rumbo de alejamiento (con corrección de wind_drift)
                else:
                    # Rumbo de alejamiento (con corrección de wind_drift)
                    target_hdg = - \
                        ((self.to_do_aux[1] + 180.0 - 30.0 *
                          self.to_do_aux[5] - wind_drift) % 360.)
                self.to_do_aux.append(target_hdg)
            target_hdg = self.to_do_aux[6]
            if target_hdg < 0.0:
                target_hdg = -target_hdg
            else:
                if abs(target_hdg - self.hdg) > 60.0:
                    target_hdg = (self.hdg + 90.0 * self.to_do_aux[5]) % 360.0
            # Está en el viraje hacia el tramo de alejamiento
            if self.to_do_aux[3] == 0.0 or self.to_do_aux[3] == -10.0:
                if abs(target_hdg - self.hdg) < 1.:  # Ha terminado el viraje
                    if self.to_do_aux[3] == -10.0:
                        self.to_do_aux[4] = False
                        self.to_do_aux[3] = 0.0
                        self.to_do_aux.pop(6)
                    else:
                        self.to_do_aux[3] = t
            # Comprobar tiempo que lleva en alejamiento y al terminar entra en
            # acercamiento
            elif (t > self.to_do_aux[2] + self.to_do_aux[3]):
                self.to_do_aux[3] = -10.0
                self.to_do_aux[6] = self.to_do_aux[1]
        return target_hdg

    def get_tgt_hdg_hdgfix(self, wind_drift, t):
        """Fly a heading after passing a fix"""
        if self.to_do_aux[0] in self.route:
            # Punto al que se dirige con corrección de wind_drift
            self.pto = self.route[0].pos()
            self.vect = rp(r(self.pto, self.pos))
            # Correción de wind_drift
            return self.vect[1] - wind_drift
        else:
            self.vect = rp((2.0 * self.ground_spd, self.track))
            return self.to_do_aux[1]

    def get_tgt_hdg_intercept_radial(self, wind_drift, t):
        """Intercept and follow radial from a point"""
        (rx, ry) = r(Route.WP(self.to_do_aux[0]).pos(), self.pos)
        rdl_actual = rp((rx, ry))[1]
        rdl = self.to_do_aux[1]
        if rdl < 180.0 and rdl_actual > rdl + 180.0:
            rdl_actual = rdl_actual - 360.0
        elif rdl > 180.0 and rdl_actual < rdl - 180.0:
            rdl_actual = rdl_actual + 360.0
        ang_aux = rdl - rdl_actual  # Positivo, el radial estáa la izquierda de posición actual
        (rdlx, rdly) = pr((1.0, self.to_do_aux[1]))
        dist_perp = abs(rx * rdly - ry * rdlx)
        if dist_perp < 0.1:  # Consideramos que estáen el radial
            self.vect = rp((2.0 * self.ground_spd, self.track))
            self.tgt_hdg = self.to_do_aux[1]
            return self.to_do_aux[1] - wind_drift
        elif dist_perp < 0.8:
            self.vect = rp((2.0 * self.ground_spd, self.track))
            self.tgt_hdg = (self.to_do_aux[1] - 20.0 * sgn(ang_aux)) % 360.0
            return (self.to_do_aux[1] - wind_drift - 20.0 * sgn(ang_aux)) % 360.0
        else:
            self.vect = rp((2.0 * self.ground_spd, self.track))
            return (self.tgt_hdg - wind_drift) % 360.0
            # return (self.to_do_aux[1] - wind_drift - 45.0 * sgn(ang_aux))%360.0

    def get_tgt_hdg_app(self, wind_drift, t):
        try:
            (puntos_alt, llz, puntos_map) = fir.iaps[self.iaf]
        except KeyError:
            logging.warning("No IAF found when trying to set course for approach. Keeping current heading")
            return self.hdg
        [xy_llz, rdl, dist_ayuda, pdte_ayuda, alt_pista] = llz
        if len(self.route) == 0:  # Es el primer acceso a app desde la espera. Se añaden los puntos
            for [a, b, c, h] in puntos_alt:
                self.route.append(Route.WayPoint(b))
            wp = Route.WayPoint("_LLZ")
            wp._pos = xy_llz
            self.route.append(wp)
        # An no estáen el localizador, tocamos solamente la altitud y como plan
        # de vuelo
        if len(self.route) > 1:
            if self._map and '_LLZ' not in self.route:  # Ya estáfrustrando
                for [a, b, c, h] in puntos_map:
                    if b == self.route[0].fix:
                        self.cfl = h / 100.
                        self.set_std_rate()
                        break
            else:
                for [a, b, c, h] in puntos_alt:
                    if b == self.route[0].fix:
                        self.cfl = h / 100.
                        break
            # Punto al que se dirige con corrección de wind_drift
            self.pto = self.route[0].pos()
            self.vect = rp(r(self.pto, self.pos))
            # Correción de wind_drift
            return self.vect[1] - wind_drift
        if len(self.route) == 1:  # Interceptar localizador y senda de planeo
            # Ya estáfrustrando hacia el ltimo punto, asimilamos a plan de
            # vuelo normal
            if self._map and '_LLZ' not in self.route:
                self.to_do = 'fpr'
                self.app_auth = False
                self.app_fix = ''
                self._map = False
                # Punto al que se dirige con corrección de wind_drift
                self.pto = self.route[0].pos()
                self.vect = rp(r(self.pto, self.pos))
                # Correción de wind_drift
                return self.vect[1] - wind_drift
            else:
                # Coordenadas relativas a la radioayuda
                (rx, ry) = r(xy_llz, self.pos)
                # Primero intersecta la senda de planeo cuando es inferior.
                # Solamente tocamos el rate de descenso
                dist_thr = rp((rx, ry))[0] - dist_ayuda
                derrota = rp((rx, ry))[1]
                if abs(dist_thr) < 0.50:  # Avión aterrizado
                    # En caso de estar 200 ft por encima, hace MAP o si ya ha
                    # pasado el LLZ
                    height_over_field = self.lvl * 100 - alt_pista
                    if height_over_field > 200. or abs(derrota - rdl) > 90.:
                        logging.debug("%s: height over field is %d at %.1fnm. Executing MAP"
                                      % (self.callsign, height_over_field, dist_thr))
                        self._map = True

                    if self._map:  # Procedimiento de frustrada asignado
                        self.set_std_spd()
                        self.set_std_rate()
                        self.route = Route.Route(
                            [Route.WayPoint(p[1]) for p in puntos_map])
                    else:
                        logging.debug("%s: Landing" % self.callsign)
                        return LANDED

                if self.esta_en_llz:
                    # Interceptación de la senda de planeo. Se ajusta rate descenso y ajuste ias = perf.app_tas
                    # fl_gp = Flight level of the glidepath at the current point
                    fl_gp = (alt_pista * FEET_TO_LEVELS + dist_thr * pdte_ayuda * NM_TO_LEVELS)
                    if fl_gp <= self.lvl:
                        # If above the glidepath
                        self.set_ias(self.perf.app_tas /
                                     (1.0 + 0.002 * self.lvl))
                        self.cfl = alt_pista * FEET_TO_LEVELS
                        rate = ((self.lvl - fl_gp) * 1 +  # Additional vertical speed to capture
                                self.ground_spd * pdte_ayuda) * NM_TO_LEVELS  # Vert speed to descend with the glide
                        # Unidades en ft/min
                        achievable, max_rate = self.set_vertical_rate(rate)

                        if not achievable:
                            self.set_vertical_rate(-max_rate)
                            rate *= LEVELS_PER_HOUR_TO_FPM
                            max_rate *= LEVELS_PER_HOUR_TO_FPM
                            logging.debug("%s: Distance to threshold: %.1fnm, altitude: %dft, glidepath altitude: %dft, gs: %dkts"
                                          % (self.callsign, dist_thr, self.lvl * 100, fl_gp * 100., self.ground_spd))
                            logging.debug("%s: Unable to set approach descent rate %dfpm. Max is %dfpm"
                                          % (self.callsign, rate, max_rate))
                    else:
                        self.set_vertical_rate(0.001)
                        # Ahora el movimiento en planta
                rdl_actual = rp((rx, ry))[1]
                if rdl < 180.0 and rdl_actual > rdl + 180.0:
                    rdl_actual = rdl_actual - 360.0
                elif rdl > 180.0 and rdl_actual < rdl - 180.0:
                    rdl_actual = rdl_actual + 360.0
                ang_aux = rdl - rdl_actual  # Positivo, el radial estáa la izquierda de posición actual
                (rdlx, rdly) = pr((1.0, rdl))
                dist_perp = abs(rx * rdly - ry * rdlx)
                if dist_perp < 0.1:  # Consideramos que estáen el radial
                    if abs(self.lvl - self.cfl) < 002.0:
                        self.esta_en_llz = True
                    self.int_loc = False
                    self.vect = rp((2.0 * self.ground_spd, self.track))
                    return rdl - wind_drift
                elif dist_perp < 0.8:
                    if abs(self.lvl - self.cfl) < 002.0:
                        self.esta_en_llz = True
                    self.int_loc = False
                    self.vect = rp((2.0 * self.ground_spd, self.track))
                    return (rdl - wind_drift - 20.0 * sgn(ang_aux)) % 360.0
                else:
                    if self.int_loc:
                        rdl_actual = self.hdg
                        if rdl < 180.0 and rdl_actual > rdl + 180.0:
                            rdl_actual = rdl_actual - 360.0
                        elif rdl > 180.0 and rdl_actual < rdl - 180.0:
                            rdl_actual = rdl_actual + 360.0
                        # Positivo, el radial estáa la izquierda de posición
                        # actual
                        ang_aux2 = rdl - rdl_actual
                        if ang_aux * ang_aux2 > 0.:
                            return self.tgt_hdg - wind_drift
                        else:
                            self.int_loc = False
                            self.vect = rp((2.0 * self.ground_spd, self.track))
                            self.tgt_hdg = rdl - 45.0 * sgn(ang_aux)
                            return (rdl - wind_drift - 45.0 * sgn(ang_aux)) % 360.0
                    else:
                        self.vect = rp((2.0 * self.ground_spd, self.track))
                        return (rdl - wind_drift - 45.0 * sgn(ang_aux)) % 360.0

    def get_target_heading(self, wind_drift, t):
        """Return target heading for current flight phase"""

        tgt_hdg_functions = {
            "fpr": self.get_tgt_hdg_fpr,
            "hdg": self.get_tgt_hdg_hdg,
            "orbit": self.get_tgt_hdg_orbit,
            "hld": self.get_tgt_hdg_hold,
            "hdg<fix": self.get_tgt_hdg_hdgfix,
            "int_rdl": self.get_tgt_hdg_intercept_radial,
            "app": self.get_tgt_hdg_app
        }

        if self.to_do in tgt_hdg_functions:
            return tgt_hdg_functions[self.to_do](wind_drift, t)
