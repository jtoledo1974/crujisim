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

"""Contains all aeronautical information: Airports, routes, points, procedures, etc."""

from __future__ import print_function
from __future__ import absolute_import
from future import standard_library
from builtins import zip
from builtins import range
from builtins import object

import logging
import os
import re
import codecs
import configparser
import fnmatch
from stat import *

# Application imports
from .MathUtil import *
from .AIXM import Point, AirportHeliport, Hold, RWY_DIRECTION, SID, STAR

standard_library.install_aliases()

# TODO the whole FIR object should be rewritten
# The file format should probably be switched to an XML file that more closely follows
# the internal structure of the information, and the FIR model should structure
# its information using more ideas from the Aeronautical Information Conceptual Model
# See http://www.eurocontrol.int/ais/aixm/aicm40/
# We might even want to consider whether we want to implement AIXM fully,
# although AIXM does not support ATC procedures, which we need to save

# All fir elements should be turned into classes, just as the Hold is now


name = ""       # Name is used to verify that it matches an exercise file
file = ""       # Filename from which information is loaded

points = {}     # All points known

# Dictionary of points relative to another. Format: [RELATIVE_POINT
# NAME]:[POINT_NAME],[RADIAL],[DISTANCE]
routes = []             # List of points defining standard routes within the FIR
airways = []            # List of airways... just for displaying on map
tmas = []               # List of points defining TMAs
local_maps = {}         # Dictionary of local maps
aerodromes = {}         # Dictionary of AirportHeliport features
holds = []              # List of published holds (See Hold class)
procedimientos = {}     # Standard procedures (SIDs and STARs)

# Definition of the approach procedure is extremely confusing. Looking forward to substituting it for the
# proper AIXM structure
# iaps = {'IAF_NAME': (initial_app_points, ILS_info, MAP_points)}
# initial_app_points = [((x, y), POINT_NAME, '', altitude), ]  # List of points that connect IAF to IF
# ILS_info = [(x_llz_antenna, y_llz_antenna), (llz_radial + 180.) % 360., antena_rwy_thresh_dist, gs_angle, rwy_elevation]
# MAP_points = [(x, y), POINT_NAME, '', altitude), ]
iaps = {}

deltas = []
sectors = []  # List of sector names
_sector_sections = {}  # Section name of each secto
boundaries = {}  # List of boundary points for each sector
min_sep = {}  # Minimum radar separation for each sector
auto_departures = {}  # Whether there are autodepartures for each sector
fijos_impresion = {}
fijos_impresion_secundarios = {}
local_maps_order = []
# TODO: ADs should be a class on its own, with attributes
# like elevation, rwys, which sector has to approve a departure if any,
# etc.
local_ads = {}
release_required_ads = {}

routedb = None

mod_lists = ['routes', 'airways', 'tmas', 'holds', 'deltas', 'sectors', 'local_maps_order']
mod_dicts = ['points', 'local_maps', 'aerodromes', 'procedimientos', 'iaps', '_sector_sections',
             'boundaries', 'min_sep', 'auto_departures', 'fijos_impresion', 'fijos_impresion_secundarios',
             'local_ads', 'release_required_ads']
mod_other = ['name', 'routedb', 'file']


def get_AIS_data():
    """Returns all the data held by the module. It's used to pass it on to clients, and for editing exercises"""
    res = {}
    for item in mod_lists + mod_dicts + mod_other:
        res[item] = globals()[item]
    return res


def set_AIS_data(AIS_data):
    """Returns all the data held by the module. It's used to pass it on to clients, and for editing exercises"""
    all_globals = globals()
    for item, value in AIS_data.iteritems():
        all_globals[item] = value


def clear_variables():
    # Testing uses initializes AIS more than once. Variables have to be reset.

    for item in mod_lists:
        assert item in globals()
        globals()[item] = []

    for item in mod_dicts:
        assert item in globals()
        globals()[item] = {}

    for item in mod_other:
        assert item in globals()
        globals()[item] = None


def init(fir_file):
    """Initialize AIS data"""

    clear_variables()

    global file
    file = fir_file

    firdef = configparser.ConfigParser(inline_comment_prefixes=(';',))
    with codecs.open(fir_file, 'r', 'utf8') as f:
        firdef.read_file(f)

    # FIR name
    global name
    name = firdef.get('datos', 'nombre')

    # Puntos del FIR
    # logging.debug('Points')
    lista = firdef.items('puntos')
    rel_points = {}
    for (pointName, coord) in lista:
        pointName = pointName.upper()
        coord_lista = coord.split(',')

        if len(coord_lista) == 2:
            (x, y) = coord.split(',')
            x, y = float(x), float(y)
            points[pointName] = Point(pointName, (x, y))

        elif len(coord_lista) == 3:  # if len coord is 3, the point is defined referenced to another
            (baseName, x, y) = coord.split(',')
            x, y = float(x), float(y)
            rel_points[pointName.upper()] = [baseName.upper(), (x, y)]

    if len(rel_points) > 0:
        # If at least one relative point has been read we should try to convert it to
        # cartessian coordinates
        scan_again = True
        while scan_again:
            scan_again = False
            for relative_point_name in rel_points:
                # First check if the new relative point already exists
                if relative_point_name not in points:
                    # The point does not exist, lets try if I can ad it
                    # To do so I have to check if the base points exists
                    base_point_name = rel_points[relative_point_name][0]
                    base_point_coordinates = points[base_point_name].pos
                    if len(base_point_coordinates) > 0:
                        # Exists, so lets make the conversion to
                        # cartesian's and add the point to the list
                        (x, y) = pr(rel_points[
                            relative_point_name][1])
                        (x, y) = (
                            x + base_point_coordinates[0], y + base_point_coordinates[1])

                        points[relative_point_name] = Point(relative_point_name, (x, y))
                        scan_again = True

    # FIR Routes
    lista = firdef.items('rutas')
    for (num, aux) in lista:
        linea = aux.split(',')
        routes.append([points[p].pos for p in linea])

    # FIR Airways
    lista = firdef.items('aerovias')
    for (num, aux) in lista:
        linea = aux.split(',')
        airways.append([points[p].pos for p in linea])

    # FIR TMAs
    if firdef.has_section('tmas'):
        lista = firdef.items('tmas')
        for (num, aux) in lista:
            linea = aux.split(',')
            tmas.append([points[p].pos for p in linea])

    # Local maps
    if firdef.has_section('mapas_locales'):
        local_map_string = firdef.get('mapas_locales', 'mapas')
        local_map_sections = local_map_string.split(',')
        for map_section in local_map_sections:
            if firdef.has_section(map_section):
                map_name = firdef.get(map_section, 'nombre')
                map_items = firdef.items(map_section)
                local_maps_order.append(map_name)
                # Store map name and graphical objects in local_maps
                # dictionary (key: map name)
                map_objects = []
                for item in map_items:
                    # logging.debug (item[0].lower())
                    if item[0].lower() != 'nombre':
                        map_objects.append(item[1].split(','))
                local_maps[map_name] = map_objects

    # FIR aerodromes
    if firdef.has_section('aeropuertos'):
        lista = firdef.items('aeropuertos')
        for (num, aux) in lista:
            for a in aux.split(','):
                aerodromes[a] = AirportHeliport(a)
    if firdef.has_section('elevaciones'):
        elev_list = firdef.items('elevaciones')[0][1].split(",")
        for ad, elev in zip(list(aerodromes.keys()), elev_list):
            aerodromes[ad].fieldElev = int(elev)

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
            holds.append(
                Hold(fijo.upper(), rumbo, tiempo_alej, std_turns))

    # IFR Runways
    if firdef.has_section('aeropuertos_con_procedimientos'):
        lista = firdef.items('aeropuertos_con_procedimientos')
        for (airp, total_rwys) in lista:
            ad = aerodromes[airp.upper()]
            for rwy in total_rwys.split(','):
                ad.rwy_direction_list.append(
                    RWY_DIRECTION(rwy.upper()[4: ]))
            # First runway if the preferential
            ad.rwy_in_use = ad.rwy_direction_list[0]

    # SID and STAR procedures
    for ad, rwy_direction in ((ad, rwy) for ad in aerodromes.values()
                              for rwy in ad.rwy_direction_list):
        pista = ad.designator + rwy_direction.txt_desig
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
    for pista in (ad.designator + rwy.txt_desig
                  for ad in aerodromes.values()
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
                    for q in points:
                        if dato == points[q].designator:
                            points_app.append(
                                [points[q].pos, points[q].designator, '', float(altitud)])
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
            for q in points:
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
                for q in points:
                    if dato == q[0]:
                        points_map.append([q[1], q[0], '', float(altitud)])
                        punto_esta = True
                if not punto_esta:
                    logging.warning(
                        'Punto ' + dato + ' no encontrado en procedimiento app_' + pista + ' MAP')
                    # Guardamos los procedimientos
            iaps[fijo.upper()] = (points_app, llz_data, points_map)
    # logging.debug ('Lista de procedimientos de
    # aproximación'+str(iaps)

    # Deltas del FIR
    if firdef.has_section('deltas'):
        lista = firdef.items('deltas')
        for (num, aux) in lista:
            # logging.debug ('Leyendo delta '+str(num))
            linea = aux.split(',')
            deltas.append([points[p].pos for p in linea])

    # Sector characteristics
    for section in firdef.sections():
        if section[0: 6] == 'sector':
            sector_name = firdef.get(section, 'nombre')
            sectors.append(sector_name)
            _sector_sections[sector_name] = section
            boundaries[sector_name] = []
            fijos_impresion[sector_name] = []
            fijos_impresion_secundarios[sector_name] = []
            local_ads[sector_name] = []
            release_required_ads[sector_name] = []

    # Load data for each of the sectors
    for (sector, section) in _sector_sections.items():

        # Límites del sector
        aux2 = firdef.get(section, 'limites').split(',')
        for a in aux2:
            auxi = True
            for q in points:
                if a == q[0]:
                    boundaries[sector].append(q[1])
                    auxi = False
            if auxi:
                logging.warning(
                    'En límite de sector no encontrado el points ' + a)

         # Build TWO LOCAL MAPS: One with sectors limits, and the other with the transparency
                # Separación mínima del sector
        if firdef.has_option(section, 'min_sep'):
            min_sep[sector] = float(firdef.get(section, 'min_sep'))
        else:
            logging.debug('No encontrada separación en sector ' +
                          sector + '. Se asumen 8 NM de separación mínima.')
            min_sep[sector] = 8.0

        # Despegues automáticos o manuales
        if firdef.has_option(section, 'auto_departure'):
            aux2 = firdef.get(section, 'auto_departure').upper()
            if aux2 == 'AUTO':
                auto_departures[sector] = True
            elif aux2 == 'MANUAL':
                auto_departures[sector] = False
            else:
                logging.debug('Valor para despegues manual/automático para sector ' +
                              sector + ' debe ser "AUTO" o "MANUAL". Se asume automático')
                auto_departures[sector] = True
        else:
            logging.debug('Valor para despegues manual/automático para sector ' +
                          sector + ' no encontrado. Se asume automático')
            auto_departures[sector] = True

        # Fijos de impresión primarios
        aux2 = firdef.get(section, 'fijos_de_impresion').split(',')
        for a in aux2:
            auxi = True
            for q in points:
                if a == q[0]:
                    fijos_impresion[sector].append(q[0])
                    auxi = False
            if auxi:
                logging.warning('No encontrado el fijo de impresión ' + a)
        # Fijos de impresión secundarios
        if firdef.has_option(section, 'fijos_de_impresion_secundarios'):
            aux2 = firdef.get(
                section, 'fijos_de_impresion_secundarios').split(',')
            for a in aux2:
                auxi = True
                for q in points:
                    if a == q[0]:
                        fijos_impresion_secundarios[
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
        local_ads[sector] = ads

        # Release required ADs
        try:
            ads = firdef.get(section, 'release_required_ads').split(',')
        except:
            ads = []
        release_required_ads[sector] = ads

    # Load the route database which correspond to this FIR
    global routedb
    from . import Exercise
    try:
        routedb = Exercise.load_routedb(os.path.dirname(file))
    except:
        logging.warning("Unable to load route database from " +
                        os.path.dirname(file) + ". Using blank db")


def get_point_coordinates(point_name):
    if point_name in coords:
        return coords[point_name]
    elif re.match("X([-+]?(\d+(\.\d*)?|\d*\.\d+))Y([-+]?(\d+(\.\d*)?|\d*\.\d+))", point_name.upper()):
        v = re.match(
            "X([-+]?(\d+(\.\d*)?|\d*\.\d+))Y([-+]?(\d+(\.\d*)?|\d*\.\d+))", point_name.upper()).groups()
        return (float(v[0]), float(v[3]))
    else:
        raise RuntimeError('Point %s not found in %s' %
                           (point_name, file))


def ad_has_ifr_rwys(designator):
    return designator in aerodromes \
        and len(aerodromes[designator].rwy_direction_list) > 0


def init_by_name(path, name):
    """Given a directory, initialize with the first file that has a matching name"""
    for root, dirnames, filenames in os.walk(path):
        for filename in fnmatch.filter(filenames, '*.fir'):

            # TODO this check should not really have to parse every fir file.fir
            # Exercises should match the name of the FIR filename.
            fir_file = (os.path.join(root, filename))
            firdef = configparser.ConfigParser(inline_comment_prefixes=(';',))
            with codecs.open(fir_file, 'r', 'utf8') as f:
                firdef.read_file(f)

            # FIR name
            if firdef.get('datos', 'nombre') == name:
                init(fir_file)
                assert len(aerodromes) > 1


pos = get_point_coordinates

