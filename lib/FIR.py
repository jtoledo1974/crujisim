#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Information regarding a Flight Information Region"""
from __future__ import print_function
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import zip
from builtins import range
from builtins import object

import logging
import os
import re
import codecs
from stat import *

# Application imports
from .MathUtil import *
from . import Route

# TODO the whole FIR object should be rewritten
# The file format should probably be switched to an XML file that more closely follows
# the internal structure of the information, and the FIR model should structure
# its information using more ideas from the Aeronautical Information Conceptual Model
# See http://www.eurocontrol.int/ais/aixm/aicm40/
# We might even want to consider whether we want to implement AIXM fully,
# although AIXM does not support ATC procedures, which we need to save

# All fir elements should be turned into classes, just as the Hold is now


class FIR(object):
    """FIR information and processess"""

    def __init__(self, fir_file):
        """Create a FIR instance"""

        self.file = fir_file

        def pos(self, p):                   # TODO Used to be a method alias, but object couldn't be pickled
            # Need to find a better way of doing this.
            self.get_point_coordinates(p)

        Route.fir = self

        # List of geo coordinates of points [ POINT_NAME, (X, Y)]
        self.points = []
        self.coords = {}  # Dictionary with point coordinates
        # Dictionary of points relative to another. Format: [RELATIVE_POINT
        # NAME]:[POINT_NAME],[RADIAL],[DISTANCE]
        self.rel_points = {}
        self.routes = []  # List of points defining standard routes within the FIR
        self.airways = []  # List of airways... just for displaying on map
        self.tmas = []  # List of points defining TMAs
        self.local_maps = {}  # Dictionary of local maps
        self.aerodromes = {}  # Dictionary of AD_HP objects
        self.holds = []  # List of published holds (See Hold class)
        self.procedimientos = {}  # Standard procedures (SIDs and STARs)

        # Definition of the approach procedure is extremely confusing. Looking forward to substituting it for the
        # proper AIXM structure
        # iaps = {'IAF_NAME': (initial_app_points, ILS_info, MAP_points)}
        # initial_app_points = [((x, y), POINT_NAME, '', altitude), ]  # List of points that connect IAF to IF
        # ILS_info = [(x_llz_antenna, y_llz_antenna), (llz_radial + 180.) % 360., antena_rwy_thresh_dist, gs_angle, rwy_elevation]
        # MAP_points = [(x, y), POINT_NAME, '', altitude), ]
        self.iaps = {}

        self.deltas = []
        self.sectors = []  # List of sector names
        self._sector_sections = {}  # Section name of each sector
        self.boundaries = {}  # List of boundary points for each sector
        self.min_sep = {}  # Minimum radar separation for each sector
        self.auto_departures = {}  # Whether there are autodepartures for each sector
        self.fijos_impresion = {}
        self.fijos_impresion_secundarios = {}
        self.local_maps_order = []
        # TODO: ADs should be a class on its own, with attributes
        # like elevation, rwys, which sector has to approve a departure if any,
        # etc.
        self.local_ads = {}
        self.release_required_ads = {}

        import configparser
        firdef = configparser.ConfigParser(inline_comment_prefixes=(';',))
        with codecs.open(fir_file, 'r', 'utf8') as f:
            firdef.read_file(f)

        # FIR name
        self.name = firdef.get('datos', 'nombre')

        # Puntos del FIR
        # logging.debug('Points')
        lista = firdef.items('puntos')
        for (nombre, coord) in lista:
            coord_lista = coord.split(',')
            if len(coord_lista) == 2:
                (x, y) = coord.split(',')
                x = float(x)
                y = float(y)
                self.points.append([nombre.upper(), (x, y)])
                self.coords[nombre.upper()] = (x, y)
            elif len(coord_lista) == 3:  # if len coord is 3, the point is defined referenced to another
                (nombre_base, x, y) = coord.split(',')
                x = float(x)
                y = float(y)
                self.rel_points[nombre.upper()] = [nombre_base.upper(), (x, y)]
        if len(self.rel_points) > 0:
            # If at least one relative point has been read we should try to convert it to
            # cartessian coordinates
            scan_again = True
            while scan_again:
                scan_again = False
                for relative_point_name in self.rel_points:
                    # First check if the new relative point already exists
                    dummy = [p[0]
                             for p in self.points if p[0] == relative_point_name]
                    if len(dummy) == 0:
                        # The point does not exist, lets try if I can ad it
                        # To do so I have to check if the base points exists
                        base_point_name = self.rel_points[
                            relative_point_name][0]
                        base_point_coordinates = [
                            p[1] for p in self.points if p[0] == base_point_name]
                        if len(base_point_coordinates) > 0:
                            # Exists, so lets make the conversion to
                            # cartesian's and add the point to the list
                            (x, y) = pr(self.rel_points[
                                relative_point_name][1])
                            (x, y) = (
                                x + base_point_coordinates[0][0], y + base_point_coordinates[0][1])
                            self.points.append([relative_point_name, (x, y)])
                            self.coords[relative_point_name] = (x, y)
                            scan_again = True

        # FIR Routes
        lista = firdef.items('rutas')
        for (num, aux) in lista:
            linea = aux.split(',')
            aux2 = ()
            for p in linea:
                for q in self.points:
                    if p == q[0]:
                        aux2 = aux2 + q[1]
            self.routes.append([aux2])

        # FIR Airways
        lista = firdef.items('aerovias')
        for (num, aux) in lista:
            linea = aux.split(',')
            self.airways.append([self.coords[p] for p in linea])
        # FIR TMAs
        if firdef.has_section('tmas'):
            lista = firdef.items('tmas')
            for (num, aux) in lista:
                linea = aux.split(',')
                self.tmas.append([self.coords[p] for p in linea])
        # Local maps
        if firdef.has_section('mapas_locales'):
            local_map_string = firdef.get('mapas_locales', 'mapas')
            local_map_sections = local_map_string.split(',')
            for map_section in local_map_sections:
                if firdef.has_section(map_section):
                    map_name = firdef.get(map_section, 'nombre')
                    map_items = firdef.items(map_section)
                    self.local_maps_order.append(map_name)
                    # Store map name and graphical objects in local_maps
                    # dictionary (key: map name)
                    map_objects = []
                    for item in map_items:
                        # logging.debug (item[0].lower())
                        if item[0].lower() != 'nombre':
                            map_objects.append(item[1].split(','))
                    self.local_maps[map_name] = map_objects
        # FIR aerodromes
        if firdef.has_section('aeropuertos'):
            lista = firdef.items('aeropuertos')
            for (num, aux) in lista:
                for a in aux.split(','):
                    self.aerodromes[a] = AD_HP(a)
        if firdef.has_section('elevaciones'):
            elev_list = firdef.items('elevaciones')[0][1].split(",")
            for ad, elev in zip(list(self.aerodromes.keys()), elev_list):
                self.aerodromes[ad].val_elev = int(elev)
        # Published holding patterns
        if firdef.has_section('esperas_publicadas'):
            lista = firdef.items('esperas_publicadas')
            for (fijo, datos) in lista:
                (rumbo, tiempo_alej, lado) = datos.split(',')
                rumbo, tiempo_alej, lado = float(
                    rumbo), float(tiempo_alej), lado.upper()
                if lado == 'D':
                    std_turns = True
                else:
                    std_turns = False
                self.holds.append(
                    Hold(fijo.upper(), rumbo, tiempo_alej, std_turns))
        # IFR Runways
        if firdef.has_section('aeropuertos_con_procedimientos'):
            lista = firdef.items('aeropuertos_con_procedimientos')
            for (airp, total_rwys) in lista:
                ad = self.aerodromes[airp.upper()]
                for rwy in total_rwys.split(','):
                    ad.rwy_direction_list.append(
                        RWY_DIRECTION(rwy.upper()[4: ]))
                # First runway if the preferential
                ad.rwy_in_use = ad.rwy_direction_list[0]
        # SID and STAR procedures
        for ad, rwy_direction in ((ad, rwy) for ad in self.aerodromes.values()
                                  for rwy in ad.rwy_direction_list):
            pista = ad.code_id + rwy_direction.txt_desig
            # SID
            lista = firdef.items('sid_' + pista)
            for (sid_desig, sid_points) in lista:
                sid_desig = sid_desig.upper()
                rwy_direction.sid_dict[sid_desig] = SID(sid_desig, sid_points)
            # Procedimientos STAR
            lista = firdef.items('star_' + pista)
            for (star_desig, star_points) in lista:
                star_desig = star_desig.upper()
                rwy_direction.star_dict[star_desig] = STAR(
                    star_desig, star_points)

        # Instrument Approach Procedures
        for pista in (ad.code_id + rwy.txt_desig
                      for ad in self.aerodromes.values()
                      for rwy in ad.rwy_direction_list):
            # Procedimientos aproximación
            procs_app = firdef.items('app_' + pista)
            for [fijo, lista] in procs_app:
                lista = lista.split(',')
                # logging.debug (str(pista)+'Datos APP '+str(fijo)+' son
                # '+str(lista))
                points_app = []
                for i in range(0, len(lista), 2):
                    dato = lista[i]
                    altitud = lista[i + 1]
                    if dato == 'LLZ':
                        break
                    else:
                        punto_esta = False
                        for q in self.points:
                            if dato == q[0]:
                                points_app.append(
                                    [q[1], q[0], '', float(altitud)])
                                punto_esta = True
                        if not punto_esta:
                            logging.warning(
                                'Punto ' + dato + ' no encontrado en procedimiento app_' + pista + ' APP')
                llz_data = []
                nombre_ayuda = lista[i + 1]
                rdl_ayuda = float(lista[i + 2])
                dist_ayuda = float(lista[i + 3])
                pdte_ayuda = float(lista[i + 4])
                alt_pista = float(lista[i + 5])
                for q in self.points:
                    if lista[i + 1] == q[0]:
                        llz_data = [q[1], (rdl_ayuda + 180.) %
                                    360., dist_ayuda, pdte_ayuda, alt_pista]
                        break
                if llz_data == []:
                    logging.warning(
                        'Localizador no encontrado en procedimiento app_' + pista + ' APP')
                    # Ahora vamos a por los puntos de la frustrada
                points_map = []
                lista = lista[i + 7: ]
                # logging.debug ('Resto para MAp: '+str(lista))
                for i in range(0, len(lista), 2):
                    dato = lista[i]
                    altitud = lista[i + 1]
                    punto_esta = False
                    for q in self.points:
                        if dato == q[0]:
                            points_map.append([q[1], q[0], '', float(altitud)])
                            punto_esta = True
                    if not punto_esta:
                        logging.warning(
                            'Punto ' + dato + ' no encontrado en procedimiento app_' + pista + ' MAP')
                        # Guardamos los procedimientos
                self.iaps[fijo.upper()] = (points_app, llz_data, points_map)
        # logging.debug ('Lista de procedimientos de
        # aproximación'+str(self.iaps)

        # Deltas del FIR
        if firdef.has_section('deltas'):
            lista = firdef.items('deltas')
            for (num, aux) in lista:
                # logging.debug ('Leyendo delta '+str(num))
                linea = aux.split(',')
                self.deltas.append([self.coords[p] for p in linea])

        # Sector characteristics

        for section in firdef.sections():
            if section[0: 6] == 'sector':
                sector_name = firdef.get(section, 'nombre')
                self.sectors.append(sector_name)
                self._sector_sections[sector_name] = section
                self.boundaries[sector_name] = []
                self.fijos_impresion[sector_name] = []
                self.fijos_impresion_secundarios[sector_name] = []
                self.local_ads[sector_name] = []
                self.release_required_ads[sector_name] = []

        # Load data for each of the sectors
        for (sector, section) in self._sector_sections.items():

            # Límites del sector
            aux2 = firdef.get(section, 'limites').split(',')
            for a in aux2:
                auxi = True
                for q in self.points:
                    if a == q[0]:
                        self.boundaries[sector].append(q[1])
                        auxi = False
                if auxi:
                    logging.warning(
                        'En límite de sector no encontrado el self.points ' + a)

             # Build TWO LOCAL MAPS: One with sectors limits, and the other with the transparency
                    # Separación mínima del sector
            if firdef.has_option(section, 'min_sep'):
                self.min_sep[sector] = float(firdef.get(section, 'min_sep'))
            else:
                logging.debug('No encontrada separación en sector ' +
                              sector + '. Se asumen 8 NM de separación mínima.')
                self.min_sep[sector] = 8.0

            # Despegues automáticos o manuales
            if firdef.has_option(section, 'auto_departure'):
                aux2 = firdef.get(section, 'auto_departure').upper()
                if aux2 == 'AUTO':
                    self.auto_departures[sector] = True
                elif aux2 == 'MANUAL':
                    self.auto_departures[sector] = False
                else:
                    logging.debug('Valor para despegues manual/automático para sector ' +
                                  sector + ' debe ser "AUTO" o "MANUAL". Se asume automático')
                    self.auto_departures[sector] = True
            else:
                logging.debug('Valor para despegues manual/automático para sector ' +
                              sector + ' no encontrado. Se asume automático')
                auto_departures[sector] = True

            # Fijos de impresión primarios
            fijos_impresion = []
            aux2 = firdef.get(section, 'fijos_de_impresion').split(',')
            for a in aux2:
                auxi = True
                for q in self.points:
                    if a == q[0]:
                        self.fijos_impresion[sector].append(q[0])
                        auxi = False
                if auxi:
                    logging.warning('No encontrado el fijo de impresión ' + a)
            # Fijos de impresión secundarios
            if firdef.has_option(section, 'fijos_de_impresion_secundarios'):
                aux2 = firdef.get(
                    section, 'fijos_de_impresion_secundarios').split(',')
                for a in aux2:
                    auxi = True
                    for q in self.points:
                        if a == q[0]:
                            self.fijos_impresion_secundarios[
                                sector].append(q[0])
                            auxi = False
                    if auxi:
                        logging.warning(
                            'No encontrado el fijo secundario de impresión ' + a)
            else:
                logging.debug(
                    'No hay fijos de impresión secundarios (no hay problema)')

            # Local ADs
            try:
                ads = firdef.get(section, 'local_ads').split(',')
            except:
                ads = []
            self.local_ads[sector] = ads

            # Release required ADs
            try:
                ads = firdef.get(section, 'release_required_ads').split(',')
            except:
                ads = []
            self.release_required_ads[sector] = ads

        # Load the route database which correspond to this FIR
        from . import Exercise
        try:
            self.routedb = Exercise.load_routedb(os.path.dirname(self.file))
        except:
            logging.warning("Unable to load route database from " +
                            os.path.dirname(self.file) + ". Using blank db")

    def get_point_coordinates(self, point_name):
        if point_name in self.coords:
            return self.coords[point_name]
        elif re.match("X([-+]?(\d+(\.\d*)?|\d*\.\d+))Y([-+]?(\d+(\.\d*)?|\d*\.\d+))", point_name.upper()):
            v = re.match(
                "X([-+]?(\d+(\.\d*)?|\d*\.\d+))Y([-+]?(\d+(\.\d*)?|\d*\.\d+))", point_name.upper()).groups()
            return (float(v[0]), float(v[3]))
        else:
            raise RuntimeError('Point %s not found in %s' %
                               (point_name, self.file))

    def ad_has_ifr_rwys(self, code_id):
        return code_id in self.aerodromes \
            and len(self.aerodromes[code_id].rwy_direction_list) > 0


def load_firs(path):
    import configparser

    firs = []

    for d in os.listdir(path):
        d = os.path.join(path, d)
        mode = os.stat(d)[ST_MODE]
        if not S_ISDIR(mode) or d[-4: ] == ".svn":
            continue
        firs += load_firs(d)

    for f in [f for f in os.listdir(path) if f[-4: ] == ".fir"]:
        f = os.path.join(path, f)
        try:
            fir = FIR(f)
        except:
            logging.warning("Unable to read FIR file" + f, exc_info=True)
            continue

        firs.append(fir)

    return firs

# TODO
# There is currently no support for lat/lon coordinates, so we are using
# the non-standard attribute 'pos' to store the cartesian coordinates of objects,
# rather than the aicm standard geo_lat and geo_lon


class Designated_Point(object):

    def __init__(self, code_id, pos):
        self.code_id = code_id
        self.pos = pos

Point = Designated_Point  # Alias for the class


class AD_HP(object):  # Aerodrome / Heliport

    def __init__(self, code_id, txt_name='', pos=None, val_elev=0):
        self.code_id = code_id
        self.txt_name = txt_name
        self.pos = pos
        self.val_elev = val_elev
        self.rwy_direction_list = []
        self.rwy_in_use = None

    def get_sid(self, txt_desig):
        return [sid for rwy in self.rwy_direction_list
                for sid in rwy.sid_dict.values()
                if sid.txt_desig == txt_desig][0]

    def __repr__(self):
        s = "AD_HP(id: %r, txt_name:%r, pos:%r, val_elev:%r, %r, %r)" % (
            self.code_id, self.txt_name, self.pos,
            self.val_elev, self.rwy_direction_list,
            self.rwy_in_use)
        return s


class Hold(object):
    # TODO this does not reflect AICM. We need to support the whole
    # procedure_leg in order to do this

    def __init__(self, fix, inbd_track=180, outbd_time=1, std_turns=True, min_FL=000, max_FL=999):
        self.fix = fix         # The fix on which this hold is based
        self.inbd_track = inbd_track  # Inbound track of the holding pattern
        self.outbd_time = outbd_time  # For how long to fly on the outbd track
        self.std_turns = std_turns   # Standard turns are to the right
        self.min_FL = min_FL        # minimun FL at the holding pattern
        self.max_FL = max_FL        # maximun FL at the holding pattern


class RWY_DIRECTION(object):

    def __init__(self, txt_desig):
        # TXT_DESIG must have between 2 and 3 characters, of which the first 2
        # may be any digit between 0 and 9. Examples: 09, 09L, 09R, 09C, 09T,
        # etc..
        self.txt_desig = txt_desig
        self.sid_dict = {}
        self.star_dict = {}
        self.iap_dict = {}

    def __repr__(self):
        s = "RWY_DIRECTION(%r, %r, %r, %r" % (
            self.txt_desig, self.sid_dict, self.star_dict, self.iap_dict)
        return s


class STAR(object):
    # TODO this only covers basic AICM attributes.
    # We need to support the whole procuedure_leg object in order to
    # to support things like SLP and vertical limitations

    def __init__(self, txt_desig, rte):
        self.txt_desig = txt_desig
        self.rte = Route.Route(Route.get_waypoints(rte))
        self.start_fix = txt_desig[: -2]

    def __str__(self):
        return self.txt_desig

    def __repr__(self):
        s = "STAR(%r, %s, end_fix: %s)" % (
            self.txt_desig, self.rte, self.start_fix)
        return s


class SID(object):
    # TODO this only covers basic AICM attributes.
    # We need to support the whole procuedure_leg object in order to
    # to support things like SLP and vertical limitations

    def __init__(self, txt_desig, rte):
        self.txt_desig = txt_desig
        self.rte = Route.Route(Route.get_waypoints(rte))
        self.end_fix = txt_desig[: -2]

    def __str__(self):
        return self.txt_desig

    def __repr__(self):
        s = "SID(%r, %s, end_fix: %s)" % (
            self.txt_desig, self.rte, self.end_fix)
        return s


if __name__ == "__main__":
    # FIR('/temp/radisplay/pasadas/Ruta-Convencional/Ruta-Convencional.fir')
    print([fir.file for fir in load_firs('..')])
