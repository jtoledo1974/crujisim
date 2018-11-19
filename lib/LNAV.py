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

import logging

# Module imports
from .MathUtil import pr, rp, r, sgn, relative_angle

from . import LEVELS_PER_HOUR_TO_FPM, FEET_TO_LEVELS, NM_TO_LEVELS
from .Route import WayPoint, Route

fir = None   # Set by GTA.__init__

# JTC 2018-10 This is still all spaghetti code. I moved LNAV methods here, but it still has
# to be properly compartmentalized. Way too many obscure vect, to_do_aux,
# etc. references, and wind_drift corrections should probably be done outside of this


def fpr(f, wind_drift):
    """Follow flight plan route"""
    f.vect = f.get_bearing_to_next()
    # wind_drift correction
    return f.vect[1] - wind_drift


def hdg(f):
    """Fly heading"""
    tgt_hdg = f.to_do_aux[0]

    f.vect = rp((2.0 * f.ground_spd, tgt_hdg))
    rel_a = relative_angle(tgt_hdg, f.hdg)

    # When the turn direction is forced, we provide an intermediate target heading
    # which is 90 degrees on the direction we have been asked to turn
    if f.to_do_aux[1] == 'DCHA':
        if rel_a > 0.:  # El rumbo está a su izquierda
            return (f.hdg + 90.) % 360.
        else:  # Está a su derecha o ya está en rumbo
            return f.to_do_aux[0]

    elif f.to_do_aux[1] == 'IZDA':
        if rel_a < 0.:  # El rumbo está a su derecha
            return (f.hdg - 90.) % 360.
        else:  # Está a su izquierda o ya está en rumbo
            return f.to_do_aux[0]

    # No forced turn
    return f.to_do_aux[0]


def orbit(f):
    """Orbit on present position"""
    if f.to_do_aux[0] == 'DCHA':
        return (f.hdg + 90.0) % 360.0
    else:
        return (f.hdg - 90.0) % 360.0


def hold(f, wind_drift, t):
    """Fly published holding pattern"""
    if not f.to_do_aux[4] and f.to_do_aux[0] in f.route:
        # Aún no ha llegado a la espera, sigue volando en ruta
        # Punto al que se dirige con corrección de wind_drift
        pos = f.route[0].pos()
        f.vect = rp(r(pos, f.pos))
        # Correción de wind_drift
        return f.vect[1] - wind_drift

    # Está dentro de la espera, entramos bucle de la espera
    f.to_do_aux[4] = True

    # El fijo principal debe estar en la ruta. Si no está se pone
    if not f.to_do_aux[0] in f.route:
        f.route.insert(0, WayPoint(f.to_do_aux[0]))

    # Con esta operación no nos borra el punto de la espera
    f.vect = rp((2.0 * f.ground_spd, f.track))

    if len(f.to_do_aux) == 6:  # Vamos a definir el rumbo objetivo, añadiéndolo al final
        inbd_hdg = (f.to_do_aux[1] - wind_drift) % 360.0

        aux = relative_angle(inbd_hdg, f.hdg)
        if aux > -60.0 and aux < 120.0:  # Entrada directa
            # Rumbo de alejamiento (con corrección de wind_drift)
            target_hdg = (f.to_do_aux[1] + 180.0 - wind_drift) % 360.
        else:
            # Rumbo de alejamiento (con corrección de wind_drift)
            target_hdg = - \
                ((f.to_do_aux[1] + 180.0 - 30.0 *
                  f.to_do_aux[5] - wind_drift) % 360.)
        f.to_do_aux.append(target_hdg)

    target_hdg = f.to_do_aux[6]
    if target_hdg < 0.0:
        target_hdg = -target_hdg
    else:
        if abs(target_hdg - f.hdg) > 60.0:
            target_hdg = (f.hdg + 90.0 * f.to_do_aux[5]) % 360.0

    # Está en el viraje hacia el tramo de alejamiento
    if f.to_do_aux[3] == 0.0 or f.to_do_aux[3] == -10.0:
        if abs(target_hdg - f.hdg) < 1.:  # Ha terminado el viraje
            if f.to_do_aux[3] == -10.0:
                f.to_do_aux[4] = False
                f.to_do_aux[3] = 0.0
                f.to_do_aux.pop(6)
            else:
                f.to_do_aux[3] = t

    # Comprobar tiempo que lleva en alejamiento y al terminar entra en
    # acercamiento
    elif (t > f.to_do_aux[2] + f.to_do_aux[3]):
        f.to_do_aux[3] = -10.0
        f.to_do_aux[6] = f.to_do_aux[1]

    return target_hdg


def hdgfix(f, wind_drift):
    """Fly a heading after passing a fix"""
    if f.to_do_aux[0] in f.route:
        # Punto al que se dirige con corrección de wind_drift
        f.vect = rp(r(f.route[0].pos(), f.pos))
        # Correción de wind_drift
        return f.vect[1] - wind_drift
    else:
        f.vect = rp((2.0 * f.ground_spd, f.track))
        return f.to_do_aux[1]


def intercept_radial(f, wind_drift):
    """Intercept and follow radial from a point"""
    (rx, ry) = r(WayPoint(f.to_do_aux[0]).pos(), f.pos)
    current_radial = rp((rx, ry))[1]
    tgt_radial = f.to_do_aux[1]

    aux = relative_angle(current_radial, tgt_radial)
    (rdlx, rdly) = pr((1.0, f.to_do_aux[1]))
    dist_perp = abs(rx * rdly - ry * rdlx)

    if dist_perp < 0.1:  # Consideramos que está en el radial
        f.vect = rp((2.0 * f.ground_spd, f.track))
        f.tgt_hdg = f.to_do_aux[1]
        return f.to_do_aux[1] - wind_drift

    elif dist_perp < 0.8:
        f.vect = rp((2.0 * f.ground_spd, f.track))
        f.tgt_hdg = (f.to_do_aux[1] - 20.0 * sgn(aux)) % 360.0
        return (f.to_do_aux[1] - wind_drift - 20.0 * sgn(aux)) % 360.0

    else:
        f.vect = rp((2.0 * f.ground_spd, f.track))
        return (f.tgt_hdg - wind_drift) % 360.0
        # return (f.to_do_aux[1] - wind_drift - 45.0 * sgn(ang_aux))%360.0


def app(f, wind_drift):
    try:
        (puntos_alt, llz, puntos_map) = fir.iaps[f.iaf]
    except KeyError:
        logging.warning(
            "No IAF found when trying to set course for approach. Keeping current heading")
        return f.hdg

    [xy_llz, llz_radial, dist_ayuda, pdte_ayuda, alt_pista] = llz
    if len(f.route) == 0:  # Es el primer acceso a app desde la espera. Se añaden los puntos
        for [a, b, c, h] in puntos_alt:
            f.route.append(WayPoint(b))
        wp = WayPoint("_LLZ")
        wp._pos = xy_llz
        f.route.append(wp)

    # An no está en el localizador, tocamos solamente la altitud y como plan
    # de vuelo
    if len(f.route) > 1:
        if f._map and '_LLZ' not in f.route:  # Ya estáfrustrando
            for [a, b, c, h] in puntos_map:
                if b == f.route[0].fix:
                    f.cfl = h / 100.
                    f.set_std_rate()
                    break
        else:
            for [a, b, c, h] in puntos_alt:
                if b == f.route[0].fix:
                    f.cfl = h / 100.
                    break
        # Punto al que se dirige con corrección de wind_drift
        f.pto = f.route[0].pos()
        f.vect = rp(r(f.pto, f.pos))
        # Correción de wind_drift
        return f.vect[1] - wind_drift

    if len(f.route) == 1:  # Interceptar localizador y senda de planeo
        # Ya estáfrustrando hacia el último punto, asimilamos a plan de
        # vuelo normal
        if f._map and '_LLZ' not in f.route:
            f.to_do = 'fpr'
            f.app_auth = False
            f.app_fix = ''
            f._map = False
            # Punto al que se dirige con corrección de wind_drift
            f.pto = f.route[0].pos()
            f.vect = rp(r(f.pto, f.pos))
            # Correción de wind_drift
            return f.vect[1] - wind_drift
        else:
            # Coordenadas relativas a la radioayuda
            (rx, ry) = r(xy_llz, f.pos)
            # Primero intersecta la senda de planeo cuando es inferior.
            # Solamente tocamos el rate de descenso
            dist_thr = rp((rx, ry))[0] - dist_ayuda
            derrota = rp((rx, ry))[1]
            if abs(dist_thr) < 0.50:  # Avión aterrizado
                # En caso de estar 200 ft por encima, hace MAP o si ya ha
                # pasado el LLZ
                height_over_field = f.lvl * 100 - alt_pista
                if height_over_field > 200. or abs(derrota - llz_radial) > 90.:
                    logging.debug("%s: height over field is %d at %.1fnm. Executing MAP"
                                  % (f.callsign, height_over_field, dist_thr))
                    f._map = True

                if f._map:  # Procedimiento de frustrada asignado
                    f.set_std_spd()
                    f.set_std_rate()
                    f.route = Route([WayPoint(p[1]) for p in puntos_map])
                else:
                    logging.debug("%s: Landing" % f.callsign)
                    # Prevents cyclic imports
                    from .Aircraft import LANDED
                    return LANDED

            # TODO THIS IS ALL VNAV, REALLY ##########
            if f.esta_en_llz:
                # Interceptación de la senda de planeo. Se ajusta rate descenso y ajuste ias = perf.app_tas
                # fl_gp = Flight level of the glidepath at the current point
                fl_gp = (alt_pista * FEET_TO_LEVELS +
                         dist_thr * pdte_ayuda * NM_TO_LEVELS)
                if fl_gp <= f.lvl:
                    # If above the glidepath
                    f.set_ias(f.perf.app_tas / (1.0 + 0.002 * f.lvl))
                    f.cfl = alt_pista * FEET_TO_LEVELS
                    rate = ((f.lvl - fl_gp) * 1 +  # Additional vertical speed to capture
                            f.ground_spd * pdte_ayuda) * NM_TO_LEVELS  # Vert speed to descend with the glide
                    # Unidades en ft/min
                    achievable, max_rate = f.set_vertical_rate(rate)

                    if not achievable:
                        f.set_vertical_rate(-max_rate)
                        rate *= LEVELS_PER_HOUR_TO_FPM
                        max_rate *= LEVELS_PER_HOUR_TO_FPM
                        logging.debug("%s: Distance to threshold: %.1fnm, altitude: %dft, glidepath altitude: %dft, gs: %dkts"
                                      % (f.callsign, dist_thr, f.lvl * 100, fl_gp * 100., f.ground_spd))
                        logging.debug("%s: Unable to set approach descent rate %dfpm. Max is %dfpm"
                                      % (f.callsign, rate, max_rate))
                else:
                    f.set_vertical_rate(0.001)
                    # Ahora el movimiento en planta

            current_radial = rp((rx, ry))[1]
            ang_aux = relative_angle(current_radial, llz_radial)

            (rdlx, rdly) = pr((1.0, llz_radial))
            dist_perp = abs(rx * rdly - ry * rdlx)

            if dist_perp < 0.1:  # Consideramos que estáen el radial
                if abs(f.lvl - f.cfl) < 002.0:
                    f.esta_en_llz = True
                f.int_loc = False
                f.vect = rp((2.0 * f.ground_spd, f.track))
                return llz_radial - wind_drift

            elif dist_perp < 0.8:
                if abs(f.lvl - f.cfl) < 002.0:
                    f.esta_en_llz = True
                f.int_loc = False
                f.vect = rp((2.0 * f.ground_spd, f.track))
                return (llz_radial - wind_drift - 20.0 * sgn(ang_aux)) % 360.0

            else:
                if f.int_loc:
                    current_radial = f.hdg
                    if llz_radial < 180.0 and current_radial > llz_radial + 180.0:
                        current_radial = current_radial - 360.0
                    elif llz_radial > 180.0 and current_radial < llz_radial - 180.0:
                        current_radial = current_radial + 360.0

                    # Positivo, el radial estáa la izquierda de posición
                    # actual
                    ang_aux2 = llz_radial - current_radial
                    if ang_aux * ang_aux2 > 0.:
                        return f.tgt_hdg - wind_drift
                    else:
                        f.int_loc = False
                        f.vect = rp((2.0 * f.ground_spd, f.track))
                        f.tgt_hdg = llz_radial - 45.0 * sgn(ang_aux)
                        return (llz_radial - wind_drift - 45.0 * sgn(ang_aux)) % 360.0

                else:
                    f.vect = rp((2.0 * f.ground_spd, f.track))
                    return (llz_radial - wind_drift - 45.0 * sgn(ang_aux)) % 360.0


def get_target_heading(f, wind_drift, t):
    """Return target heading for current flight phase"""

    tgt_hdg_functions = {
        "fpr": (fpr, wind_drift),
        "hdg": (hdg,),
        "orbit": (orbit,),
        "hld": (hold, wind_drift, t),
        "hdg<fix": (hdgfix, wind_drift),
        "int_rdl": (intercept_radial, wind_drift),
        "app": (app, wind_drift)
    }

    if f.to_do in tgt_hdg_functions:
        function = tgt_hdg_functions[f.to_do][0]
        args = [f] + list(tgt_hdg_functions[f.to_do][1:])
        return function(*args)
