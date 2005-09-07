#!/usr/bin/python
#-*- coding:"iso8859-15" -*-
import warnings
warnings.filterwarnings('ignore','.*',DeprecationWarning)
from StripSeries import StripSeries
from ConfigParser import *
from avion import *
import glob
from Tkinter import *
import banner

def tpv(): 
  global h_inicio,fir_elegido,sector_elegido,ejercico_elegido

  def eleccion_ejercicio():
    [fir_elegido , sector_elegido , ejercicio_elegido , imprimir_fichas] = banner.seleccion_usuario()
    return (fir_elegido , sector_elegido , ejercicio_elegido , imprimir_fichas)
  
  h_inicio=0.
  fir_elegido,sector_elegido,ejercicio_elegido=[],[],[]
  imprimir_fichas=False
  #Elección del fir,sector y ejercicio
  (fir_elegido,sector_elegido,ejercicio_elegido,imprimir_fichas)=eleccion_ejercicio()
  print 'Total escogido: ',fir_elegido,sector_elegido,ejercicio_elegido
  punto = []
  ejercicio = []
  rutas = []
  limites = []
  incidencias = []
  tmas = []
  deltas = []
  # Lectura de los datos del FIR
  config=ConfigParser()
  config.readfp(open(fir_elegido[1]))
  # Puntos del FIR
  lista=config.items('PUNTOS')
  for (nombre,coord) in lista:
    print 'Leyendo punto ',nombre.upper(),
    (x,y)=coord.split(',')
    x=float(x)
    y=float(y)
    punto.append([nombre.upper(),(x,y)])
    print '...ok'
  # Rutas del FIR
  lista=config.items('RUTAS')
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
  if config.has_section('TMAS'):
    lista=config.items('TMAS')
    for (num,aux) in lista:
      print 'Leyendo tma ',num,
      linea=aux.split(',')
      aux2=()
      for p in linea:
        for q in punto:
          if p==q[0]:
            aux2=aux2+q[1]
      tmas.append([aux2])
  # Deltas del FIR
  if config.has_section('DELTAS'):
    lista=config.items('DELTAS')
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
        d.set_spd(spd)
        d.set_std_spd()
        ias=spd/(1.+0.002*d.rfl)
        d.set_ias(ias)
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
    # Ahora incluimos las performances del avión
    if config.has_option('performances',d.get_kind()):
      aux=config.get('performances',d.get_kind()).split(',')
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
      if not d.vfp:
        estimadas.append(t)
        last_point = True
    # Cálculo de la estimada ajustada
    for i in range(len(ruta)):
      if ruta[i][1]==fijo:
        desfase=hora-estimadas[i]
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
    d.set_spd(spd)
    d.set_std_spd()
    d.set_ias(ias)
    d.set_initial_t(desfase)
    d.set_hist_t(desfase)
    d.set_position(pos)
    d.set_initial_heading()
    hist=[]
    d.set_campo_eco(d.route[-1][1][0:3])
    for dest in ['LEMD','LEPP','LEBB','LESA','LEAS','LEST','LEZG','LEBG']:
      if d.destino==dest:
        d.set_campo_eco(dest[2:4])
    for i in range(5):
      hist.append(d.pos)
    d.set_hist(hist)
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
            ss.draw_flight_data(callsign=a.name, prev_fix=prev, fix=fijo, next_fix=next, prev_fix_est=prev_t, fix_est=fijo_t, next_fix_est=next_t, model=a.tipo, wake=a.estela, responder="C", speed=a.spd, origin=a.origen, destination=a.destino, fl=str(int(a.rfl)), cfl=str(int(a.cfl)),cssr="----", route=ruta, rules="")
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
              ss.draw_flight_data(callsign=a.name, prev_fix=prev, fix=fijo, next_fix=next, prev_fix_est=prev_t, fix_est=fijo_t, next_fix_est=next_t, model=a.tipo, wake=a.estela, responder="C", speed=a.spd, origin=a.origen, destination=a.destino, fl=str(int(a.rfl)), cfl=str(int(a.cfl)),cssr="----", route=ruta, rules="")
      
  ss.save() 
  
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
    visual.mainloop()


  return [punto,ejercicio,rutas,limites,deltas,tmas,h_inicio]
