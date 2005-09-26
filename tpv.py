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

# Module imports
import warnings
warnings.filterwarnings('ignore','.*',DeprecationWarning)
from StripSeries import StripSeries
from ConfigParser import *
from avion import *
import glob
from Tkinter import *
from Tix import *
import Image
import ImageTk
import PngImagePlugin
import sys

# Constants
IMGDIR='./img/'
CRUJISIMICO=IMGDIR+'crujisim.ico'

def set_seleccion_usuario(seleccion_usuario):
	global g_seleccion_usuario
	g_seleccion_usuario = seleccion_usuario

def calc_eto(d):
    # Cálculo del tiempo entre fijos
    estimadas=[0.0]
    last_point=False
    t=0.
    n_puntos=len(d.route)
    inc_t=15./60./60.
    while not last_point:
      t=t+inc_t
      d.next(t)
      if len(d.route)<n_puntos:
        estimadas.append(t)
        n_puntos=len(d.route)
      if not d.to_do == 'fpr':
        estimadas.append(t)
        last_point = True
    return estimadas
	
def tpv():
  global h_inicio,fir_elegido,sector_elegido,ejercico_elegido, g_seleccion_usuario,rwyInUse

  h_inicio=0.
  imprimir_fichas=False
  #Elección del fir,sector y ejercicio
  [fir_elegido,sector_elegido,ejercicio_elegido,imprimir_fichas] = g_seleccion_usuario
  print 'Total escogido: ',fir_elegido,sector_elegido,ejercicio_elegido
  punto = []
  ejercicio = []
  rutas = []
  limites = []
  incidencias = []
  tmas = []
  deltas = []
  aeropuertos = []
  esperas_publicadas = []
  rwys = {}
  rwyInUse = {}
  procedimientos= {}
  proc_app={}
  auto_depatures = True
  min_sep = 8.0
  local_maps = {}
  # Lectura de los datos del FIR
  config=ConfigParser()
  config.readfp(open(fir_elegido[1]))
  # Puntos del FIR
  lista=config.items('puntos')
  for (nombre,coord) in lista:
    print 'Leyendo punto ',nombre.upper(),
    (x,y)=coord.split(',')
    x=float(x)
    y=float(y)
    punto.append([nombre.upper(),(x,y)])
    print '...ok'
  # Rutas del FIR
  lista=config.items('rutas')
  for (num,aux) in lista:
    print 'Leyendo ruta ',num,
    linea=aux.split(',')
    aux2=()
    for p in linea:
      for q in punto:
        if p==q[0]:
          aux2=aux2+q[1]
    rutas.append([aux2])
  # Tma del FIR
  if config.has_section('tmas'):
    lista=config.items('tmas')
    for (num,aux) in lista:
      print 'Leyendo tma ',num,
      linea=aux.split(',')
      aux2=()
      for p in linea:
        for q in punto:
          if p==q[0]:
            aux2=aux2+q[1]
      tmas.append([aux2])
  # Mapas locales
  try:
    local_map_string = config.get('mapas_locales', 'mapas')
    local_map_sections = local_map_string.split(',')
    for map_section in local_map_sections:
      if config.has_section(map_section):
	map_name = config.get(map_section, 'nombre')
	map_items = config.items(map_section)
	print "Map items:", map_items
	# Store map name and graphical objects in local_maps dictionary (key: map name)
	map_objects = []
	for item in map_items:
	  print item[0].lower()
	  if item[0].lower() != 'nombre':
	    map_objects.append(item[1].split(','))
	local_maps[map_name] = map_objects
  except:
    print "Exception processing local maps"
  # Aeropuertos del FIR
  if config.has_section('aeropuertos'):
    lista=config.items('aeropuertos')
    aeropuertos = []
    for (num,aux) in lista:
      print 'Leyendo aeropuertos ',num,
      for a in aux.split(','):
        aeropuertos.append(a)
      print aeropuertos
  # Esperas publicadas
  if config.has_section('esperas_publicadas'):
    lista=config.items('esperas_publicadas')
    esperas_publicadas = []
    for (fijo,datos) in lista:
      print 'Leyendo espera de ',fijo,
      (rumbo,tiempo_alej,lado) = datos.split(',')
      rumbo,tiempo_alej,lado = float(rumbo),float(tiempo_alej),lado.upper()
      esperas_publicadas.append([fijo.upper(),rumbo,tiempo_alej,lado])
      print rumbo,tiempo_alej
  # Lectura de las pistas de los aeropuertos con procedimientos
  if config.has_section('aeropuertos_con_procedimientos'):
    lista=config.items('aeropuertos_con_procedimientos')
    for (airp,total_rwys) in lista:
      rwys[airp.upper()] = total_rwys
      rwyInUse[airp.upper()] = total_rwys.split(',')[0] # La primera pista es la preferente
  # En caso de haber más de una pista en algún aeropuerto, nos da a elegir la pista en uso
  ask_tag = False
  for airp in rwys.keys():
    if len(rwys[airp].split(','))>1:
      ask_tag = True
      break
  if ask_tag:
	  rwy_chg = Tk()
	  txt_titulo = Label (rwy_chg, text = 'ESPECIFIQUE PISTA(S) EN USO')
	  txt_titulo.grid(column=0,row=0,columnspan=2)
	  line = 1
	  com_airp=[['',0]]
	  for airp in rwys.keys():
	    com_airp.append([airp,0.0])
	    txt_airp = Label (rwy_chg, text = airp.upper())
	    txt_airp.grid(column=0,row=line,sticky=W)
	    com_airp[line][1] = ComboBox (rwy_chg, bg = 'white',editable = True)
	    num = 0
	    for pista in rwys[airp].split(','):
	      com_airp[line][1].insert(num,pista)
	      if pista == rwyInUse[airp]:
		com_airp[line][1].pick(num)
	      num=num+1
	    com_airp[line][1].grid(column=1,row=line,sticky=W)
	    line=line+1
	  but_acept = Button(rwy_chg,text='Aceptar')
	  but_acept.grid(column=0,row=line,columnspan=2)
	  def close_rwy_chg(e=None,window=rwy_chg):
	    global rwyInUse
	    com_airp.pop(0)
	    for [airp,num] in com_airp:
	      print 'Pista en uso de ',airp,' es ahora: ',num.cget('value'),'. Cambiando los procedimientos'
	      rwyInUse[airp] = num.cget('value')
	      window.destroy()
	  but_acept['command']= close_rwy_chg
	  window_width = rwy_chg.winfo_reqwidth()
	  window_height = rwy_chg.winfo_reqheight()
	  screen_width = rwy_chg.winfo_screenwidth()
	  screen_height = rwy_chg.winfo_screenheight()
	  px = (screen_width - window_width) / 2
	  py = (screen_height - window_height) / 2
	  rwy_chg.wm_geometry("+%d+%d" % (px,py))
	  rwy_chg.mainloop()

  
  # Lectura de los procedimientos SID y STAR
  for aerop in rwys.keys():
    for pista in rwys[aerop].split(','):
      # Procedimientos SID
      sid = {}
      lista = config.items('sid_'+pista)
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
      lista = config.items('star_'+pista)
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
      procs_app=config.items('app_'+pista)
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
  if config.has_section('deltas'):
    lista=config.items('deltas')
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
  aux2=config.get(sector_elegido[1],'limites').split(',')
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
  if config.has_option(sector_elegido[1],'min_sep'):
    min_sep=float(config.get(sector_elegido[1],'min_sep'))
  else:
    incidencias.append(('No encontrada separación en sector '+config.get(sector_elegido[1],'nombre')+'. Se asumen 8 NM de separación mínima.'))
    print 'No encontrada separación en sector '+config.get(sector_elegido[1],'nombre')+'. Se asumen 8 NM de separación mínima.'
    min_sep = 8.0
    
  # Despegues automáticos o manuales
  if config.has_option(sector_elegido[1],'auto_departure'):
    aux2=config.get(sector_elegido[1],'auto_departure').upper()
    if aux2 == 'AUTO':
      auto_departures = True
    elif aux2 == 'MANUAL':
      auto_departures = False
    else:
      incidencias.append(('Valor para despegues manual/automático para sector '+config.get(sector_elegido[1],'nombre')+' debe ser "AUTO" o "MANUAL". Se asume automático'))
      print 'Valor para despegues manual/automático para sector '+config.get(sector_elegido[1],'nombre')+' debe ser "AUTO" o "MANUAL". Se asume automático'
      auto_departures = True
  else:
    incidencias.append(('Valor para despegues manual/automático para sector '+config.get(sector_elegido[1],'nombre')+' no encontrado. Se asume automático'))
    print 'Valor para despegues manual/automático para sector '+config.get(sector_elegido[1],'nombre')+' no encontrado. Se asume automático'
    auto_departures = True
  
  # Fijos de impresión primarios
  fijos_impresion=[]
  aux2=config.get(sector_elegido[1],'fijos_de_impresion').split(',')
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
  if config.has_option(sector_elegido[1],'fijos_de_impresion_secundarios'):
    aux2=config.get(sector_elegido[1],'fijos_de_impresion_secundarios').split(',')
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
  
  aux=config.sections()
  for a in aux:
    config.remove_section(a)

  # Lectura del fichero de performances
  config.readfp(open('Modelos_avo.txt','r'))
  
  # Ahora se crean los planes de vuelo del ejercicio
  print 'Leyendo archivo ',ejercicio_elegido[1]
  config.readfp(open(ejercicio_elegido[1],'r'))
  hora = config.get('datos','hora_inicio')
  if hora=='':
    incidencias.append('No hay hora de inicio en ejercicio')
    print 'No hay hora de inicio'
    return    
  h_inicio = float(hora[0:2])*60.*60.+ float(hora[3:5])*60.
  if config.has_option('datos','viento'):
    [rumbo,intensidad] = config.get('datos','viento').split(',')
    intensidad,rumbo = float (intensidad),(float(rumbo)+180.0)%360.0
    wind = [intensidad,rumbo] #[intensidad * sin(rumbo), -intensidad * cos (rumbo)]
  else:
    wind = [0.0 , 0.0]
  # Inicialización de variables en avión.py
  set_canvas_info(1.0,1.0,1.0,1.0,1.0)
  set_global_vars(punto, wind, aeropuertos, esperas_publicadas,rwys,rwyInUse,procedimientos,proc_app,min_sep)

  aviones = config.items('vuelos')
  for (nombre,resto) in aviones:
    print 'Leyendo avión ',nombre.upper(),'...',
    auxi=False
    lista=resto.split(',')
    d=Airplane()
    d.set_callsign(nombre.upper())
    d.set_kind(lista[0])
    d.set_wake(lista[1])
    d.set_origin(lista[2])
    d.set_destination(lista[3])
    d.set_rfl(float(lista[4]))

    cfl = float(lista[5])
    d.set_cfl(float(lista[4]))
    d.pfl=d.cfl
    ruta=[]
    for p in lista[6:]:
      if len(p)==15:
        alt=float(p[8:11])
        d.set_alt(alt)
        spd=float(p[12:15])
        d.set_filed_tas(spd)
        ias=spd/(1.+0.002*d.rfl)
        d.set_std_spd()
        fijo=fijo_ant
        hora=float(p[1:3])+float(p[3:5])/60.+float(p[5:7])/60/60
        d.set_initial_t(0.)  #
        d.set_hist_t(0.) #
      elif len(p)>10 and p[0]=='H':
        incidencias.append(d.get_callsign()+': Grupo HhhmmssFfffVvvv no está comleto')
        print 'Grupo HhhmmssFfffVvvv no está completo'
        auxi=True
        return
      else:
        punto_esta=False
        for q in punto:
          if p==q[0]:
            ruta.append([q[1],q[0],'00:00'])
            fijo_ant=q[0]
            punto_esta=True
        if not punto_esta:
          incidencias.append(d.get_callsign()+': Punto ' + p + ' no encontrado')
          print 'Punto ',p,' no encontrado'
          auxi=False
      if auxi:
        print 'ok'
    # Ahora incluimos las performances del avión
    if d.get_wake() == 'H':
      d.turn = 2.4 * 60. * 60.
    elif d.get_wake() == 'L':
      d.turn = 3.75 * 60. * 60.
    else:
      d.turn = 3.0 * 60. * 60.
    kind_aux =d.get_kind()
    while kind_aux[0].isdigit():
      kind_aux = kind_aux[1:]
    if config.has_option('performances',kind_aux):
      aux=config.get('performances',kind_aux).split(',')
      d.fl_max = float(aux[1])
      d.rate_climb_max = float(aux[2])/100.*60.
      d.rate_climb_std = float(aux[3])/100.*60.
      d.rate_desc_max = float(aux[4])/100.*60.
      d.rate_desc_std = float(aux[5])/100.*60.
      d.spd_std = float(aux[6])
      d.spd_max = float(aux[7])
      d.spd_tma = float(aux[8])
      d.spd_app = float(aux[9])
    else:
      incidencias.append(d.get_callsign()+': No tengo parámetros del modelo ' + d.get_kind() + '. Usando datos estándar')
      print 'No tengo parámetros del modelo ',d.get_kind(),'. Usando datos estándar'
      if config.has_option('performances','estandar'+d.estela.upper()):
        aux=config.get('performances','estandar'+d.estela.upper()).split(',')
        d.fl_max = float(aux[1])
        d.rate_climb_max = float(aux[2])/100.*60.
        d.rate_climb_std = float(aux[3])/100.*60.
        d.rate_desc_max = float(aux[4])/100.*60.
        d.rate_desc_std = float(aux[5])/100.*60.
        d.spd_std = float(aux[6])
        d.spd_max = float(aux[7])
        d.spd_tma = float(aux[8])
        d.spd_app = float(aux[9])
    # Cálculo de la estimada al primer punto
    d.route = ruta
    pos=ruta[0][0]
    print 'Antes del recálculo',fijo,hora,ruta
    d.set_position(pos)
    for i in range(5):
      d.hist.append(ruta[0][0])
    route=[]
    for a in ruta:
      route.append(a)
    route.pop(0)
    d.set_route(route)
    d.set_initial_heading()
    estimadas = calc_eto(d)
    print 'Estimadas en primera vuelta', estimadas
    # Cálculo de la estimada ajustada
    for i in range(len(ruta)):
      if ruta[i][1]==fijo:
        desfase=hora-estimadas[i]
        break
    aux=[]
    for i in range(len(ruta)):
      eto=desfase+estimadas[i]
      h=int(eto)
      m=int((eto*60.+0.5)-h*60.)
      aux.append([ruta[i][0],ruta[i][1],'%02d:%02d'%(h,m)])
    aux.pop(0)
    d.set_route(aux)
    d.set_alt(alt)
    d.set_cfl(cfl)
    d.spd = 0.0
    d.set_std_spd()
    d.set_initial_t(desfase)
    d.set_hist_t(desfase)
    d.set_position(pos)
    d.set_initial_heading()
    # Recálculo para el caso de que al aplicar las SIDs o STARs cambien los puntos de la ruta
    # Mantendremos la eto sobre el primer punto de la ruta
    fijo = ruta [0][1]
    hora = d.t
    d.set_initial_t(0.0)
    print 'Después del recálculo',fijo,hora,ruta
    d.route = ruta
    d.set_se_pinta(False)   # Some previous function has incorrectly set this to True
                            # We need it to be false so that SID and STARs are
                            # added correctly
    complete_flight_plan(d)
    ruta = d.route
    pos=ruta[0][0]
    d.set_position(pos)
    for i in range(5):
      d.hist.append(ruta[0][0])
    route=[]
    for a in ruta:
      route.append(a)
    route.pop(0)
    d.set_route(route)
    d.set_initial_heading()
    estimadas = calc_eto(d)
    print 'Estimadas en segunda vuelta: ',estimadas
    # Cálculo de la estimada ajustada
    for i in range(len(ruta)):
      if ruta[i][1]==fijo:
        desfase=hora-estimadas[i]
	break
    aux=[]
    for i in range(len(ruta)):
      eto=desfase+estimadas[i]
      h=int(eto)
      m=int((eto*60.+0.5)-h*60.)
      aux.append([ruta[i][0],ruta[i][1],'%02d:%02d'%(h,m)])
    aux.pop(0)
    d.set_route(aux)
    d.set_alt(alt)
    d.set_cfl(cfl)
    d.spd = 0.0
    d.set_std_spd()
    d.set_initial_t(desfase)
    d.set_hist_t(desfase)
    d.set_position(pos)
    d.set_initial_heading()
    
    hist=[]
    d.set_campo_eco(d.route[-1][1][0:3])
    for dest in aeropuertos:
      if d.destino==dest:
        d.set_campo_eco(dest[2:4])
    for i in range(5):
      hist.append(d.pos)
    d.set_hist(hist)
    d.set_app_fix()
    ejercicio.append(d)
    print 'ok'
  # Cálculo de hora aparición y ordenamiento
  orden=[]
  for s in range(len(ejercicio)):
    a=ejercicio[s]
    aux = True
    a.t_impresion=48.
    for i in range(len(a.route)):
      for fijo in fijos_impresion:
        if a.route[i][1]==fijo:
          t_impresion=float(a.route[i][2][0:2])+float(a.route[i][2][3:5])/60.
          if a.t_impresion > t_impresion:
            a.t_impresion=t_impresion
            auxiliar = (a.route[i][2],s)
            aux = False
    for i in range(len(a.route)):
      for fijo in fijos_impresion_secundarios:
        if a.route[i][1]==fijo:
          t_impresion=float(a.route[i-1][2][0:2])+float(a.route[i-1][2][3:5])/60.
          if a.t_impresion > t_impresion:
            a.t_impresion=t_impresion
            auxiliar = (a.route[i][2],s)
            aux = False
    if aux:
      incidencias.append('El avión ' + a.get_callsign() + ' no tiene fichas de impresión en el sector, pero se crea ficha')
      print 'El avión ',a.get_callsign(),' no tiene fichas de impresión en el sector, pero se crea ficha'
      auxiliar = (a.route[int(len(a.route)/2)][2],s)
    orden.append(auxiliar)
  orden.sort()
  # Manejo de la impresión de fichas
  #if imprimir_fichas==1:     
  if True:
    parseraux=ConfigParser()
    parseraux.readfp(open(ejercicio_elegido[1],'r'))
    if parseraux.has_option('datos','comentario'):
      name = parseraux.get('datos','comentario')
    else:
      name = ejercicio_elegido[1]
    ss = StripSeries(exercise_name = name, output_file="etiquetas.pdf")
    for (aux,s) in orden:
      a = ejercicio[s]
      # Nombre contiene el indicativo OACI para sacar el callsign
      nombre = ''
      for i in range(len(a.name)):
        if nombre == '' or a.name[i].isalpha():
          nombre=nombre+a.name[i].upper()
        else:
          break
      if config.has_option('indicativos_de_compania',nombre):
        callsign = config.get('indicativos_de_compania',nombre)
      else:
        callsign = ''
      print a.name, nombre, callsign
      ruta=''
      for f in a.route:
        if f[1][0]!='_':
          ruta=ruta+' '+f[1]
      es_secundario = True
      # Fichas en los puntos principales
      for i in range(len(a.route)):
        for fijo in fijos_impresion:
          if a.route[i][1]==fijo:
            es_secundario = False
            if i>0:
              prev=a.route[i-1][1]
              prev_t=a.route[i-1][2][0:2]+a.route[i-1][2][3:5]
            else:
              prev=''
              prev_t=''
            fijo=a.route[i][1]
            fijo_t=a.route[i][2][0:2]+a.route[i][2][3:5]
            if i==len(a.route)-1:
              next=''
              next_t=''
            else:
              next=a.route[i+1][1]
              next_t=a.route[i+1][2][0:2]+a.route[i+1][2][3:5]
            # La variable callsign contiene el indicativo de llamada
            ss.draw_flight_data(callsign=a.name, ciacallsign=callsign, prev_fix=prev, fix=fijo, next_fix=next, prev_fix_est=prev_t, fix_est=fijo_t, next_fix_est=next_t, model=a.tipo, wake=a.estela, responder="C", speed=a.filed_tas, origin=a.origen, destination=a.destino, fl=str(int(a.rfl)), cfl=str(int(a.cfl)),cssr="----", route=ruta, rules="")
      # Si no hay ficha de ningún primario, saca ficha de los secundarios
      if es_secundario:
        for i in range(len(a.route)):
          for fijo in fijos_impresion_secundarios:
            if a.route[i][1]==fijo:
              es_secundario = False
              if i>0:
                prev=a.route[i-1][1]
                prev_t=a.route[i-1][2][0:2]+a.route[i-1][2][3:5]
              else:
                prev=''
                prev_t=''
              fijo=a.route[i][1]
              fijo_t=a.route[i][2][0:2]+a.route[i][2][3:5]
              if i==len(a.route)-1:
                next=''
                next_t=''
              else:
                next=a.route[i+1][1]
                next_t=a.route[i+1][2][0:2]+a.route[i+1][2][3:5]
              # La variable callsign contiene el indicativo de llamada
              ss.draw_flight_data(callsign=a.name, ciacallsign=callsign, prev_fix=prev, fix=fijo, next_fix=next, prev_fix_est=prev_t, fix_est=fijo_t, next_fix_est=next_t, model=a.tipo, wake=a.estela, responder="C", speed=a.filed_tas, origin=a.origen, destination=a.destino, fl=str(int(a.rfl)), cfl=str(int(a.cfl)),cssr="----", route=ruta, rules="")
      
  if not ss.save() :
      while DlgPdfWriteError().result=='retry' and not ss.save():
        pass  
  # Cerrar ficheros
  if len(incidencias) != 0:
    visual = Tk()
    texto = Text(visual, height = 20, width = 80, bg = 'white')
    texto.insert('end','Fichero con datos del FIR: '+ fir_elegido[1]+'\n')
    texto.insert('end','Fichero con ejercicio: ' + ejercicio_elegido[1]+'\n')
    texto.insert('end','\n')
    texto.insert('end','Errores encontrados\n')
    texto.insert('end','-------------------\n')
    for error in incidencias:
      texto.insert('end',error+'\n')
    but_roger = Button (visual, text='Continuar')
    def inicio_ejer(e=None):
      visual.destroy()
    but_roger ['command'] = inicio_ejer
    texto.pack()
    but_roger.pack()
    but_roger.focus_set()
    visual.mainloop()


  return [punto,ejercicio,rutas,limites,deltas,tmas,local_maps,h_inicio,wind,aeropuertos,esperas_publicadas,rwys,procedimientos,proc_app,rwyInUse,auto_departures,min_sep]

class DlgPdfWriteError:

    def __init__(self):
    
        dlg=self.dlg=Tk()
        f1=Frame(dlg)
        f2=Frame(dlg)
        texto=Label(f1,text='Ha sido imposible guardar el archivo de fichas (etiquetas.pdf)\n Es probable que tenga abierto el archivo.')
        photo=ImageTk.PhotoImage(Image.open(IMGDIR+"stock_dialog-warning.png"))
        icono=Label(f1, image=photo)
        icono.photo=photo
        butretry=Button(f2, text='     Reintentar    ', command=self.retry)
        butcancel=Button(f2,text='      Cancelar      ', command=self.cancel)

        f1.grid()
        f2.grid(padx=5, pady=5)
        texto.grid(row=0,column=1, padx=10, pady=5)
        icono.grid(row=0,column=0, padx=10, pady=5)
        butretry.grid(row=0,column=0, padx=10)
        butcancel.grid(row=0,column=1, padx=10)

        if sys.platform.startswith('win'):
                dlg.wm_iconbitmap(CRUJISIMICO)
        dlg.wm_title('Crujisim')

        dlg.protocol("WM_DELETE_WINDOW", self.cancel)
        dlg.focus_set()

        dlg.mainloop()

    def retry(self):
        self.dlg.destroy()
        self.result = 'retry'

    def cancel(self):
        self.dlg.destroy()
        self.result = 'cancel'
