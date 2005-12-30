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
"""Information regarding a Flight Information Region"""

class FIR:
    """FIR information and processess"""
    
    points=[]   # List of geo coordinates of points
    routes=[]   # List of points defining standard routes within the FIR
    tmas=[]     # List of points defining TMAs
    local_maps={}  # Dictionary of local map lists
    aerodromes=[]  # List of aerodrome codes
    holds=[]    # List of published holds [fix,hdg,time,turns]   
    rwys={}     # IFR rwys of each AD
    rwyInUse={} # Rwy in use at each AD
    
    
    def __init__(self, fir_file):
        """Create a FIR instance"""
        
        import ConfigParser
        import logging
        
        firdef = ConfigParser.ConfigParser()
        firdef.readfp(open(fir_file,'r'))

        # Puntos del FIR
        logging.debug('Points')
        lista=firdef.items('puntos')
        for (nombre,coord) in lista:
            (x,y)=coord.split(',')
            x=float(x)
            y=float(y)
            self.points.append([nombre.upper(),(x,y)])
        # FIR Routes
        lista=firdef.items('rutas')
        for (num,aux) in lista:
            linea=aux.split(',')
            aux2=()
            for p in linea:
                for q in self.points:
                    if p==q[0]:
                      aux2=aux2+q[1]
            self.routes.append([aux2])
        # FIR TMAs
        if firdef.has_section('tmas'):
            lista=firdef.items('tmas')
            for (num,aux) in lista:
                linea=aux.split(',')
                aux2=()
                for p in linea:
                    for q in self.points:
                        if p==q[0]:
                              aux2=aux2+q[1]
                self.tmas.append([aux2])
        # Local maps
        if firdef.has_section('mapas_locales'):
            local_map_string = firdef.get('mapas_locales', 'mapas')
            local_map_sections = local_map_string.split(',')
            for map_section in local_map_sections:
                if firdef.has_section(map_section):
                    map_name = firdef.get(map_section, 'nombre')
                    map_items = firdef.items(map_section)
                    # Store map name and graphical objects in local_maps
                    # dictionary (key: map name)
                    map_objects = []
                    for item in map_items:
                        print item[0].lower()
                        if item[0].lower() != 'nombre':
                            map_objects.append(item[1].split(','))
                    self.local_maps[map_name] = map_objects
        # FIR aerodromes
        if firdef.has_section('aeropuertos'):
            lista=firdef.items('aeropuertos')
            for (num,aux) in lista:
                for a in aux.split(','):
                    self.aerodromes.append(a)
        # Published holding patterns
        if firdef.has_section('esperas_publicadas'):
            lista=firdef.items('esperas_publicadas')
            for (fijo,datos) in lista:
                (rumbo,tiempo_alej,lado) = datos.split(',')
                rumbo,tiempo_alej,lado = float(rumbo),float(tiempo_alej),lado.upper()
                self.holds.append([fijo.upper(),rumbo,tiempo_alej,lado])
        # IFR Runways
        if firdef.has_section('aeropuertos_con_procedimientos'):
            lista=firdef.items('aeropuertos_con_procedimientos')
            for (airp,total_rwys) in lista:
                self.rwys[airp.upper()] = total_rwys
                # First runway if the preferential
                self.rwyInUse[airp.upper()] = total_rwys.split(',')[0]
        # Lectura de los procedimientos SID y STAR
        for aerop in self.rwys.keys():
          for pista in rwys[aerop].split(','):
            # Procedimientos SID
            sid = {}
            lista = firdef.items('sid_'+pista)
            for (nombre_sid,puntos_sid) in lista:
              last_point = puntos_sid.split(',')[-1]
              # Cambiamos el formato de puntos para que se pueda añadir directamente al plan de vuelo
              points_sid = []
              for nombre_punto in puntos_sid.split(','):
                punto_esta=False
                for q in punto:
                  if nombre_punto==q[0]:
                    points_sid.append([q[1],q[0],'00:00'])
                    punto_esta=True
                if not punto_esta:
                  incidencias.append('Punto ' + nombre_punto + ' no encontrado en procedimiento '+ nombre_sid)
                  print 'Punto ',nombre_punto,' no encontrado en procedimiento ', nombre_sid
      #        points_sid.pop(0)
              sid[last_point] = (nombre_sid,points_sid)
            # Procedimientos STAR
            star = {}
            lista = firdef.items('star_'+pista)
            for (nombre_star,puntos_star) in lista:
              last_point = puntos_star.split(',')[0]
              # Cambiamos el formato de puntos para que se pueda añadir directamente al plan de vuelo
              points_star = []
              for nombre_punto in puntos_star.split(','):
                punto_esta=False
                for q in punto:
                  if nombre_punto==q[0]:
                    points_star.append([q[1],q[0],'00:00'])
                    punto_esta=True
                if not punto_esta:
                  incidencias.append('Punto ' + nombre_punto + ' no encontrado en procedimiento '+ nombre_star)
                  print 'Punto ',nombre_punto,' no encontrado en procedimiento ', nombre_star
      #        points_star.pop(-1)
              star[last_point] = (nombre_star,points_star)
            procedimientos[pista] = (sid,star)
        print 'Lista de procedimientos',procedimientos
        print 'Pistas: ',rwys
        print 'Pistas en uso:',rwyInUse
        # Procedimientos de aproximación
        proc_app={}        
        for aerop in rwys.keys():
          for pista in rwys[aerop].split(','):
            # Procedimientos aproximación
            procs_app=firdef.items('app_'+pista)
            for [fijo,lista] in procs_app:
              lista = lista.split(',')
              print pista,'Datos APP ',fijo,' son ',lista
              points_app = []
              for i in range(0,len(lista),2):
                dato = lista[i]
                altitud=lista[i+1]
                if dato == 'LLZ':
                  break
                else:
                  punto_esta=False
                  for q in punto:
                    if dato==q[0]:
                      points_app.append([q[1],q[0],'',float(altitud)])
                      punto_esta=True
                  if not punto_esta:
                    incidencias.append('Punto ' + dato + ' no encontrado en procedimiento app_'+pista+' APP')
                    print 'Punto ',nombre_punto,' no encontrado en procedimiento  app_'+pista+' APP'
              llz_data = []
              nombre_ayuda = lista[i+1]
              rdl_ayuda = float(lista[i+2])
              dist_ayuda = float(lista[i+3])
              pdte_ayuda = float(lista[i+4])
              alt_pista = float(lista[i+5])
              for q in punto:
                if lista[i+1]==q[0]:
                  llz_data = [q[1],(rdl_ayuda + 180.)%360.,dist_ayuda,pdte_ayuda,alt_pista]
                  break
              if llz_data == []:
                incidencias.append('Localizador no encontrado en procedimiento app_'+pista+' APP')
                print 'Localizador no encontrado en procedimiento  app_'+pista+' APP'
              # Ahora vamos a por los puntos de la frustrada        
              points_map = []
              lista = lista [i+7:]
              print 'Resto para MAp: ',lista
              for i in range(0,len(lista),2):
                dato = lista[i]
                altitud=lista[i+1]
                punto_esta=False
                for q in punto:
                  if dato==q[0]:
                    points_map.append([q[1],q[0],'',float(altitud)])
                    punto_esta=True
                if not punto_esta:
                  incidencias.append('Punto ' + dato + ' no encontrado en procedimiento app_'+pista+' MAP')
                  print 'Punto ',nombre_punto,' no encontrado en procedimiento  app_'+pista+' MAP'
              # Guardamos los procedimientos
              proc_app[fijo.upper()]=(points_app,llz_data,points_map)
        print 'Lista de procedimientos de aproximación',proc_app
        
        # Deltas del FIR
        if firdef.has_section('deltas'):
          lista=firdef.items('deltas')
          for (num,aux) in lista:
            print 'Leyendo delta ',num,
            linea=aux.split(',')
            aux2=()
            for p in linea:
              for q in punto:
                if p==q[0]:
                  aux2=aux2+q[1]
            deltas.append([aux2])
        # Límites del sector
        aux2=firdef.get(sector_elegido[1],'limites').split(',')
        for a in aux2:
          auxi=True
          for q in punto:
            if a==q[0]:
              limites.append(q[1])
              auxi=False
          if auxi:
            incidencias.append(('En el límite de sector no encontrado el punto '+a))
            print 'En límite de sector no encontrado el punto ',a
            
        # Separación mínima del sector
        if firdef.has_option(sector_elegido[1],'min_sep'):
          min_sep=float(firdef.get(sector_elegido[1],'min_sep'))
        else:
          incidencias.append(('No encontrada separación en sector '+firdef.get(sector_elegido[1],'nombre')+'. Se asumen 8 NM de separación mínima.'))
          print 'No encontrada separación en sector '+firdef.get(sector_elegido[1],'nombre')+'. Se asumen 8 NM de separación mínima.'
          min_sep = 8.0
          
        # Despegues automáticos o manuales
        if firdef.has_option(sector_elegido[1],'auto_departure'):
          aux2=firdef.get(sector_elegido[1],'auto_departure').upper()
          if aux2 == 'AUTO':
            auto_departures = True
          elif aux2 == 'MANUAL':
            auto_departures = False
          else:
            incidencias.append(('Valor para despegues manual/automático para sector '+firdef.get(sector_elegido[1],'nombre')+' debe ser "AUTO" o "MANUAL". Se asume automático'))
            print 'Valor para despegues manual/automático para sector '+firdef.get(sector_elegido[1],'nombre')+' debe ser "AUTO" o "MANUAL". Se asume automático'
            auto_departures = True
        else:
          incidencias.append(('Valor para despegues manual/automático para sector '+firdef.get(sector_elegido[1],'nombre')+' no encontrado. Se asume automático'))
          print 'Valor para despegues manual/automático para sector '+firdef.get(sector_elegido[1],'nombre')+' no encontrado. Se asume automático'
          auto_departures = True
        
        # Fijos de impresión primarios
        fijos_impresion=[]
        aux2=firdef.get(sector_elegido[1],'fijos_de_impresion').split(',')
        for a in aux2:
          auxi=True
          for q in punto:
            if a==q[0]:
              fijos_impresion.append(q[0])
              auxi=False
          if auxi:
            incidencias.append(('No encontrado fijo de impresión '+a))
            print 'No encontrado el fijo de impresión ',a
        print
        # Fijos de impresión secundarios
        fijos_impresion_secundarios=[]
        if firdef.has_option(sector_elegido[1],'fijos_de_impresion_secundarios'):
          aux2=firdef.get(sector_elegido[1],'fijos_de_impresion_secundarios').split(',')
          for a in aux2:
            auxi=True
            for q in punto:
              if a==q[0]:
                fijos_impresion_secundarios.append(q[0])
                auxi=False
            if auxi:
              incidencias.append(('No encontrado fijo secundario de impresión '+a))
              print 'No encontrado el fijo secundario de impresión ',a
        else:
          print 'No hay fijos de impresión secundarios (no hay problema)'


if __name__ == "__main__":
    FIR('/temp/radisplay/pasadas/Ruta-Convencional/Ruta-Convencional.fir')
    
