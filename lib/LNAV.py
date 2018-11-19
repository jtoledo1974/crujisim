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

"""
Outputs desired course track for an LNAV mode
All functions are passed the aircraft instance a
"""

import logging

# Module imports
from .MathUtil import pr, rp, r, sgn, relative_angle

from . import LEVELS_PER_HOUR_TO_FPM, FEET_TO_LEVELS, NM_TO_LEVELS
from .Route import WayPoint, Route

fir = None   # Set by GTA.__init__

# LNAV MODES (somewhat modeled after airbus guidance managed and selected modes)
# See http://www.aviaddicts.com/wiki/a330:flight_guidance_modes, for example

# Managed
NAV = "NAV"
APP = "APP NAV"  # Not used yet, for navigation from IAF to IF
RWY = "RWY"  # Not used yet
LOC = "LOC"  # LOC AND LOC* are implemented using int_rdl functionality
LOC_CAPTURE = "LOC*"
HOLD = "HOLD"

# Selected
HDG = "HDG"
TRK = "TRK"  # Not used
HDG_FIX = "HDG<FIX"  # Follow heading after fix. Probably never used
INT_RDL = "INT_RDL"  # Intercept a radial
ORBIT = "ORBIT"


# JTC 2018-10 This is still all spaghetti code. I moved LNAV methods here, but it still has
# to be properly compartmentalized. Way too many obscure vect, to_do_aux,
# etc. references, and wind_drift corrections should probably be done outside of this


def fpr(a, wind_drift):
    """Follow flight plan route"""
    a.vect = a.get_bearing_to_next()
    # wind_drift correction
    return a.vect[1] - wind_drift


def hdg(a):
    """Fly heading"""
    tgt_hdg = a.to_do_aux[0]

    a.vect = rp((2.0 * a.ground_spd, tgt_hdg))
    rel_a = relative_angle(tgt_hdg, a.hdg)

    # When the turn direction is forced, we provide an intermediate target heading
    # which is 90 degrees on the direction we have been asked to turn
    if a.to_do_aux[1] == 'DCHA':
        if rel_a > 0.:  # El rumbo está a su izquierda
            return (a.hdg + 90.) % 360.
        else:  # Está a su derecha o ya está en rumbo
            return a.to_do_aux[0]

    elif a.to_do_aux[1] == 'IZDA':
        if rel_a < 0.:  # El rumbo está a su derecha
            return (a.hdg - 90.) % 360.
        else:  # Está a su izquierda o ya está en rumbo
            return a.to_do_aux[0]

    # No forced turn
    return a.to_do_aux[0]


def orbit(a):
    """Orbit on present position"""
    if a.to_do_aux[0] == 'DCHA':
        return (a.hdg + 90.0) % 360.0
    else:
        return (a.hdg - 90.0) % 360.0


def hold(a, wind_drift, t):
    """Fly published holding pattern"""
    if not a.to_do_aux[4] and a.to_do_aux[0] in a.route:
        # Aún no ha llegado a la espera, sigue volando en ruta
        # Punto al que se dirige con corrección de wind_drift
        pos = a.route[0].pos()
        a.vect = rp(r(pos, a.pos))
        # Correción de wind_drift
        return a.vect[1] - wind_drift

    # Está dentro de la espera, entramos bucle de la espera
    a.to_do_aux[4] = True

    # El fijo principal debe estar en la ruta. Si no está se pone
    if not a.to_do_aux[0] in a.route:
        a.route.insert(0, WayPoint(a.to_do_aux[0]))

    # Con esta operación no nos borra el punto de la espera
    a.vect = rp((2.0 * a.ground_spd, a.track))

    if len(a.to_do_aux) == 6:  # Vamos a definir el rumbo objetivo, añadiéndolo al final
        inbd_hdg = (a.to_do_aux[1] - wind_drift) % 360.0

        aux = relative_angle(inbd_hdg, a.hdg)
        if aux > -60.0 and aux < 120.0:  # Entrada directa
            # Rumbo de alejamiento (con corrección de wind_drift)
            target_hdg = (a.to_do_aux[1] + 180.0 - wind_drift) % 360.
        else:
            # Rumbo de alejamiento (con corrección de wind_drift)
            target_hdg = - \
                ((a.to_do_aux[1] + 180.0 - 30.0 *
                  a.to_do_aux[5] - wind_drift) % 360.)
        a.to_do_aux.append(target_hdg)

    target_hdg = a.to_do_aux[6]
    if target_hdg < 0.0:
        target_hdg = -target_hdg
    else:
        if abs(target_hdg - a.hdg) > 60.0:
            target_hdg = (a.hdg + 90.0 * a.to_do_aux[5]) % 360.0

    # Está en el viraje hacia el tramo de alejamiento
    if a.to_do_aux[3] == 0.0 or a.to_do_aux[3] == -10.0:
        if abs(target_hdg - a.hdg) < 1.:  # Ha terminado el viraje
            if a.to_do_aux[3] == -10.0:
                a.to_do_aux[4] = False
                a.to_do_aux[3] = 0.0
                a.to_do_aux.pop(6)
            else:
                a.to_do_aux[3] = t

    # Comprobar tiempo que lleva en alejamiento y al terminar entra en
    # acercamiento
    elif (t > a.to_do_aux[2] + a.to_do_aux[3]):
        a.to_do_aux[3] = -10.0
        a.to_do_aux[6] = a.to_do_aux[1]

    return target_hdg


def hdgfix(a, wind_drift):
    """Fly a heading after passing a fix"""
    if a.to_do_aux[0] in a.route:
        # Punto al que se dirige con corrección de wind_drift
        a.vect = rp(r(a.route[0].pos(), a.pos))
        # Correción de wind_drift
        return a.vect[1] - wind_drift
    else:
        a.vect = rp((2.0 * a.ground_spd, a.track))
        return a.to_do_aux[1]


def intercept_radial(a, wind_drift):
    """Intercept and follow radial from a point"""
    (rx, ry) = r(WayPoint(a.to_do_aux[0]).pos(), a.pos)
    current_radial = rp((rx, ry))[1]
    tgt_radial = a.to_do_aux[1]

    aux = relative_angle(current_radial, tgt_radial)
    (rdlx, rdly) = pr((1.0, a.to_do_aux[1]))
    dist_perp = abs(rx * rdly - ry * rdlx)

    if dist_perp < 0.1:  # Consideramos que está en el radial
        a.vect = rp((2.0 * a.ground_spd, a.track))
        a.tgt_hdg = a.to_do_aux[1]
        return a.to_do_aux[1] - wind_drift

    elif dist_perp < 0.8:
        a.vect = rp((2.0 * a.ground_spd, a.track))
        a.tgt_hdg = (a.to_do_aux[1] - 20.0 * sgn(aux)) % 360.0
        return (a.to_do_aux[1] - wind_drift - 20.0 * sgn(aux)) % 360.0

    else:
        a.vect = rp((2.0 * a.ground_spd, a.track))
        return (a.tgt_hdg - wind_drift) % 360.0
        # return (a.to_do_aux[1] - wind_drift - 45.0 * sgn(ang_aux))%360.0


def app(a, wind_drift):
    try:
        (transition_points, ILS_info, MAP_points) = fir.iaps[a.iaf]
    except KeyError:
        logging.warning("No IAF found when trying to set course for approach. Keeping current heading")
        return a.hdg

    [xy_llz, llz_radial, llz_gs_distance, gs_angle, rwy_elevation] = ILS_info
    if len(a.route) == 0:  # Es el primer acceso a app desde la espera. Se añaden los puntos
        for [point_pos, point_name, void, vertical_constraint] in transition_points:
            a.route.append(WayPoint(point_name))
        wp = WayPoint("_LLZ")
        wp._pos = xy_llz
        a.route.append(wp)

    # An no está en el localizador, tocamos solamente la altitud y como plan
    # de vuelo
    if len(a.route) > 1:
        if a._map and '_LLZ' not in a.route:  # Already executing Missed Approach
            for [point_pos, point_name, void, vertical_constraint] in MAP_points:
                if point_name == a.route[0].fix:
                    a.cfl = vertical_constraint / 100.
                    a.set_std_rate()
                    break
        else:
            for [point_pos, point_name, void, vertical_constraint] in transition_points:
                if point_name == a.route[0].fix:
                    a.cfl = vertical_constraint / 100.
                    break
        # Point towards it is flying, with wind drift correction
        a.vect = rp(r(a.route[0].pos(), a.pos))
        # Correción de wind_drift
        return a.vect[1] - wind_drift

    if len(a.route) == 1:  # Interceptar localizador y senda de planeo
        # Ya estáfrustrando hacia el último punto, asimilamos a plan de
        # vuelo normal
        if a._map and '_LLZ' not in a.route:
            a.lnav_mode = NAV
            a.app_auth = False
            a.app_fix = ''
            a._map = False
            # Punto al que se dirige con corrección de wind_drift
            a.pto = a.route[0].pos()
            a.vect = rp(r(a.pto, a.pos))
            # Correción de wind_drift
            return a.vect[1] - wind_drift
        else:
            # Coordenadas relativas a la radioayuda
            (rx, ry) = r(xy_llz, a.pos)
            # Primero intersecta la senda de planeo cuando es inferior.
            # Solamente tocamos el rate de descenso
            dist_thr = rp((rx, ry))[0] - llz_gs_distance
            derrota = rp((rx, ry))[1]
            if abs(dist_thr) < 0.50:  # Avión aterrizado
                # En caso de estar 200 ft por encima, hace MAP o si ya ha
                # pasado el LLZ
                height_over_field = a.lvl * 100 - rwy_elevation
                if height_over_field > 200. or abs(derrota - llz_radial) > 90.:
                    logging.debug("%s: height over field is %d at %.1fnm. Executing MAP"
                                  % (a.callsign, height_over_field, dist_thr))
                    a._map = True

                if a._map:  # Procedimiento de frustrada asignado
                    a.set_std_spd()
                    a.set_std_rate()
                    a.route = Route([WayPoint(point_pos[1]) for point_pos in MAP_points])
                else:
                    logging.debug("%s: Landing" % a.callsign)
                    # Prevents cyclic imports
                    from .Aircraft import LANDED
                    return LANDED

            # TODO THIS IS ALL VNAV, REALLY ##########
            if a.esta_en_llz:
                # Interceptación de la senda de planeo. Se ajusta rate descenso y ajuste ias = perf.app_tas
                # fl_gp = Flight level of the glidepath at the current point
                fl_gp = (rwy_elevation * FEET_TO_LEVELS +
                         dist_thr * gs_angle * NM_TO_LEVELS)
                if fl_gp <= a.lvl:
                    # If above the glidepath
                    a.set_ias(a.perf.app_tas / (1.0 + 0.002 * a.lvl))
                    a.cfl = rwy_elevation * FEET_TO_LEVELS
                    rate = ((a.lvl - fl_gp) * 1 +  # Additional vertical speed to capture
                            a.ground_spd * gs_angle) * NM_TO_LEVELS  # Vert speed to descend with the glide
                    # Unidades en ft/min
                    achievable, max_rate = a.set_vertical_rate(rate)

                    if not achievable:
                        a.set_vertical_rate(-max_rate)
                        rate *= LEVELS_PER_HOUR_TO_FPM
                        max_rate *= LEVELS_PER_HOUR_TO_FPM
                        logging.debug("%s: Distance to threshold: %.1fnm, altitude: %dft, glidepath altitude: %dft, gs: %dkts"
                                      % (a.callsign, dist_thr, a.lvl * 100, fl_gp * 100., a.ground_spd))
                        logging.debug("%s: Unable to set approach descent rate %dfpm. Max is %dfpm"
                                      % (a.callsign, rate, max_rate))
                else:
                    a.set_vertical_rate(0.001)
                    # Ahora el movimiento en planta

            current_radial = rp((rx, ry))[1]
            ang_aux = relative_angle(current_radial, llz_radial)

            (rdlx, rdly) = pr((1.0, llz_radial))
            dist_perp = abs(rx * rdly - ry * rdlx)

            if dist_perp < 0.1:  # Consideramos que estáen el radial
                if abs(a.lvl - a.cfl) < 002.0:
                    a.esta_en_llz = True
                a.int_loc = False
                a.vect = rp((2.0 * a.ground_spd, a.track))
                return llz_radial - wind_drift

            elif dist_perp < 0.8:
                if abs(a.lvl - a.cfl) < 002.0:
                    a.esta_en_llz = True
                a.int_loc = False
                a.vect = rp((2.0 * a.ground_spd, a.track))
                return (llz_radial - wind_drift - 20.0 * sgn(ang_aux)) % 360.0

            else:
                if a.int_loc:
                    current_radial = a.hdg
                    if llz_radial < 180.0 and current_radial > llz_radial + 180.0:
                        current_radial = current_radial - 360.0
                    elif llz_radial > 180.0 and current_radial < llz_radial - 180.0:
                        current_radial = current_radial + 360.0

                    # Positivo, el radial estáa la izquierda de posición
                    # actual
                    ang_aux2 = llz_radial - current_radial
                    if ang_aux * ang_aux2 > 0.:
                        return a.tgt_hdg - wind_drift
                    else:
                        a.int_loc = False
                        a.vect = rp((2.0 * a.ground_spd, a.track))
                        a.tgt_hdg = llz_radial - 45.0 * sgn(ang_aux)
                        return (llz_radial - wind_drift - 45.0 * sgn(ang_aux)) % 360.0

                else:
                    a.vect = rp((2.0 * a.ground_spd, a.track))
                    return (llz_radial - wind_drift - 45.0 * sgn(ang_aux)) % 360.0


def get_target_heading(a, wind_drift, t):
    """Return target heading for current flight phase"""

    tgt_hdg_functions = {
        NAV: (fpr, wind_drift),
        HDG: (hdg,),
        ORBIT: (orbit,),
        HOLD: (hold, wind_drift, t),
        HDG_FIX: (hdgfix, wind_drift),
        INT_RDL: (intercept_radial, wind_drift),
        LOC_CAPTURE: (app, wind_drift)
    }

    assert a.lnav_mode in tgt_hdg_functions, "Unknown lnav_mode %s" % a.lnav_mode

    function = tgt_hdg_functions[a.lnav_mode][0]
    args = [a] + list(tgt_hdg_functions[a.lnav_mode][1:])
    return function(*args)
