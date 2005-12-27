#!/usr/bin/python
#-*- coding:iso8859-15 -*-

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


from ConfigParser import *
import glob
from Tix import *
import Image
import ImageTk
Image._initialized=2
import banner
import os.path
import Excercise
import logging

#fichero = ''
def ejercicio():
  # En primer lugar escojo el FIR
  global window, ejer, sector, hora_inicio, descrip
  global ruta_escogida,txt_ruta_esc
  global txt_nombre, txt_fir, txt_sector, txt_hora, fichero, txt_coment, txt_viento
  global fir_elegido,fichero_fir
  fires = [x[1] for x in banner.get_fires()]
  config_fir=ConfigParser()
  lista = []
  for a in fires:
    config_fir.readfp(open(a,'r'))
    lista.append([config_fir.get('datos','nombre'),a])
  lista.sort()
  if not ejer.has_section('datos'):
    root = Tk()
    txt_Escoge = Label(root,text='Escoge FIR:')
    lista_fir = Listbox(root)
    for [a,b] in lista:
      lista_fir.insert(END,a)
    def escoge_fir(e=None):
      global fir_elegido,fichero_fir
      [fir_elegido,fichero_fir] = lista[int(lista_fir.curselection()[0])]
      root.destroy()
    txt_Aceptar = Button(root,text='Aceptar',command=escoge_fir)
    txt_Escoge.pack()
    lista_fir.pack()
    txt_Aceptar.pack()  
    root.bind('<Double-1>',escoge_fir)
    
    def set_window_size():
	window_width = root.winfo_reqwidth()
	window_height = root.winfo_reqheight()
	screen_width = root.winfo_screenwidth()
	screen_height = root.winfo_screenheight()
	px = (screen_width - window_width) / 2
	py = (screen_height - window_height) / 2
	root.wm_geometry("+%d+%d" % (px,py))
    root.after_idle(set_window_size)
    
    root.mainloop()
  else:
    for [fir_elegido,fichero_fir] in lista:
      if fir_elegido == ejer.get('datos','fir'):
        break
  print 'Fir escogido: ',fir_elegido
  for a in config_fir.sections():
    config_fir.remove_section(a)
  # Listado con los sectores del fir
  config_fir.readfp(open(fichero_fir,'r'))
  lista_sectores = []
  for l_sector in config_fir.sections():
    if l_sector[0:6]=='sector':
      lista_sectores.append(config_fir.get(l_sector,'nombre'))
  # Ahora ordeno alfabéticamente los sectores
  lista_sectores.sort()
  print lista_sectores
  # Recupero todos los puntos del FIR (solamente nombres)
  puntos = []
  aux_puntos = config_fir.items('puntos')
  for (nombre,coorde) in aux_puntos:
    puntos.append(nombre.upper())
  print puntos
  for a in config_fir.sections():
    config_fir.remove_section(a)

  
  # Ahora creamos la base de datos con las rutas
  sectores = banner.get_sectores(fir_elegido)
  print 'Sectores: ',sectores
  a_extraer = []
  a_extraer_aux = []
  for sect in sectores:
    a_extraer_aux += banner.get_ejercicios(fir_elegido,sect[0])
  for [nombre,fich] in a_extraer_aux:
    a_extraer.append(fich)
  print 'Ejercicios: ',a_extraer
  rutas=RouteDB()
  for e in a_extraer:
    config_fir.readfp(open(e,'r'))
    if config_fir.get('datos','fir') == fir_elegido:
      for (ident,datos) in config_fir.items('vuelos'):
        flight=Excercise.Flight(ident,datos)
        rutas.append(flight.route(), flight.orig(), flight.dest())
      for a in config_fir.sections():
        config_fir.remove_section(a)
  print 'Total de rutas: ',rutas.size()
  # Ahora empezamos introducir el ejercicio
  
  def datos_generales(ventana):
    # Definición de los datos generales
    global fichero
    if  ejer.has_section('datos'):
      fir_elegido = ejer.get('datos','fir')
      sector = ejer.get('datos','sector')
      aux = ejer.get('datos','hora_inicio')
      hora_inicio = aux[0:2]+aux[3:5]
      descrip = ejer.get('datos','comentario')
      if ejer.has_option('datos','viento'):
        viento = ejer.get('datos','viento')
      else:
        ejer.set('datos','viento','')
        viento = '000,00'
    else:
      ejer.add_section('datos')
      ejer.set('datos','fir',fir_elegido)
      ejer.set('datos','sector','')
      ejer.set('datos','hora_inicio','')
      ejer.set('datos','comentario','')
      ejer.set('datos','viento','')
      fichero = ''
      fir_elegido = ''
      sector = ''
      hora_inicio = ''
      descrip = ''
    if fichero == '' or len(fichero.split('-'))<7:
      promo = '0'
      fase = '0'
      dia = '0'
      pasada = '0'
      turno = ''
    else:
      aux = fichero.split('-')
      print 'Desglose del fichero: ',aux
      promo = aux[0]
      fase = aux[2]
      dia = aux[4]
      pasada = aux[6]
      turno = aux[7]
      if not (promo.isdigit() and fase.isdigit() and dia.isdigit() and pasada.isdigit() and turno in ['T','M']):
        promo = '0'
        fase = '0'
        dia = '0'
        pasada = '0'
        turno = ''
        
    
    root = Toplevel(ventana)
    txt_datos = Label (root, text = 'DATOS GENERALES EJERCICIO '+fichero)
    txt_promo = Label(root,text = 'Promoción: ')
    ent_promo = ComboBox(root, bg = 'white', editable = True)
    pick = 2
    for i in range(20,35):
      ent_promo.insert(i-20,i)
      if i == int(promo):
        pick = i-20
    ent_promo.pick(pick)
    txt_fase = Label(root,text = 'Fase: ')
    ent_fase = ComboBox(root, editable = True)
    pick = 0
    for i in range(0,5):
      ent_fase.insert(i,i)
      if i == int(fase):
        pick=i
    ent_fase.pick(pick)
    txt_dia = Label(root,text = 'Dia de la fase: ')
    ent_dia = ComboBox(root, bg = 'white', editable = True)
    pick = 0
    for i in range(1,18):
      ent_dia.insert(i-1,i)
      if i == int(dia):
        pick = i-1
    ent_dia.pick(pick)
    txt_pasada = Label(root,text = 'Pasada: ')
    ent_pasada = ComboBox(root, bg = 'white', editable = True)
    pick = 0
    for i in range(1,5):
      ent_pasada.insert(i-1,i)
#       if i == int(pasada):
#         pick = i-1
    ent_pasada.pick(pick)
    txt_turno = Label(root,text = 'Turno: ')
    ent_turno = ComboBox(root, bg = 'white', editable = True)
    pick = 0
    i=0
    for a in ('T','M'):
      ent_turno.insert(i,a)
      if a == turno:
        pick = i
      i=i+1
    ent_turno.pick(pick)

    txt_sector = Label(root,text = 'Sector: ')
    ent_sector = ComboBox(root, bg = 'white', editable = True)
    pick = 0
    for i in range(len(lista_sectores)):
      ent_sector.insert(i,lista_sectores[i])
      if lista_sectores[i] == sector:
        pick = i
    ent_sector.pick(0)
    txt_hora_inicio = Label (root, text = 'Hora de inicio (hhmm):')
    ent_hora_inicio = Entry (root, width = 8, bg='white')
    ent_hora_inicio.insert(END, hora_inicio)
    txt_descripcion = Label (root, text = 'Descripción adicional ejercicio: ')
    ent_descripcion = Entry (root, width = 40, bg='white')
    ent_descripcion.insert(END, '')
    txt_viento = Label(root, text = 'Viento (rumbo,intensidad):')
    ent_viento = Entry (root, width=10, bg='white')
    ent_viento.insert(END, viento)
    def siguiente(e=None):
      global txt_nombre, txt_fir, txt_sector, txt_hora, fichero, txt_coment, txt_viento
      correcto = True
      viento = ent_viento.get()
      if viento == '' or len(viento.split(',')) ==2:
        if viento == '': viento = '000,00'
        ent_viento['bg'] = 'white'
      else:
        correcto = False
        ent_viento['bg'] = 'red'
        ent_viento.focus_set()
      descrip = ent_descripcion.get()
      hora_inicio = ent_hora_inicio.get()
      if len(hora_inicio) <>4:
        correcto = False
        ent_hora_inicio['bg'] = 'red'
        ent_hora_inicio.focus_set()
      else:
        ent_hora_inicio['bg'] = 'white'
      promo = ent_promo.cget('value')
      fase = ent_fase.cget('value')
      dia = ent_dia.cget('value')
      pasada = ent_pasada.cget('value')
      turno = ent_turno.cget('value')
      sector = ent_sector.cget('value')
      fichero = promo+'-Fase-'+fase+'-Dia-'+dia+'-Pasada-'+pasada+'-'+turno+'-'+sector+'.eje'
      descrip = promo+'-Fase-'+fase+'-Dia-'+dia+'-Pasada-'+pasada+'-'+turno+' '+ent_descripcion.get()
      if correcto: 
        ejer.set('datos','fir',fir_elegido)
        ejer.set('datos','sector',sector)
        ejer.set('datos','hora_inicio',(hora_inicio[0:2]+':'+hora_inicio[2:4]))
        ejer.set('datos','comentario',descrip)
        ejer.set('datos','viento',viento)
        txt_nombre['text'] = 'Fichero: '+fichero
        txt_fir['text'] = 'fir: '+ejer.get('datos','fir')
        txt_sector["text"] = 'sector: '+ejer.get('datos','sector')
        txt_coment['text'] = 'Comentario: '+ejer.get('datos','comentario')
        txt_hora['text'] = 'hora de inicio: '+ejer.get('datos','hora_inicio')
        txt_viento['text'] = 'Viento: '+ejer.get('datos','viento')
        root.destroy()
      
    but_siguiente = Button (root, text='Hecho', command = siguiente)
    root.bind('<Return>',siguiente)
    root.bind('<KP_Enter>',siguiente)
    txt_datos.grid(column=0,row=0,columnspan=2)
    txt_promo.grid(column=0,row=1,sticky='W')
    ent_promo.grid(column=1,row=1,sticky='W')
    txt_fase.grid(column=0,row=2,sticky='W')
    ent_fase.grid(column=1,row=2,sticky='W')
    txt_dia.grid(column=0,row=3,sticky='W')
    ent_dia.grid(column=1,row=3,sticky='W')
    txt_pasada.grid(column=0,row=4,sticky='W')
    ent_pasada.grid(column=1,row=4,sticky='W')
    txt_turno.grid(column=0,row=5,sticky='W')
    ent_turno.grid(column=1,row=5,sticky='W')
    txt_sector.grid(column=0,row=6,sticky='W')
    ent_sector.grid(column=1,row=6,sticky='W')
    txt_hora_inicio.grid(column=0,row=7,sticky='W')
    ent_hora_inicio.grid(column=1,row=7,sticky='W')
    txt_descripcion.grid(column=0,row=8,sticky='W')
    ent_descripcion.grid(column=1,row=8,sticky='W')
    txt_viento.grid(column=0,row=9,sticky='W')
    ent_viento.grid(column=1,row=9,sticky='W')
    but_siguiente.grid(column=1,row=10,sticky='E')
    ent_promo.focus_set()
    def set_window_size():
	window_width = root.winfo_reqwidth()
	window_height = root.winfo_reqheight()
	screen_width = root.winfo_screenwidth()
	screen_height = root.winfo_screenheight()
	px = (screen_width - window_width) / 2
	py = (screen_height - window_height) / 2
	root.wm_geometry("+%d+%d" % (px,py))
    root.after_idle(set_window_size)

    root.mainloop()
  
  
  def entrada(ind,root):
    # Definición de los datos
    global ruta_escogida,txt_ruta_esc, otro_avo,grabar
    
    if ind == 'new':
      ind = ''
      kind = ''
      wake = ''
      origin = ''
      destination = ''
      p_rfl = ''
      p_cfl = ''
      ruta_escogida = ''
      p_alt = ''
      p_spd = ''
      p_fijo = ''
      p_hora = ''
      fijo_ant = ''
      hora_inc = ''
      inc = ''
    else:
      resto = ejer.get('vuelos',ind)
      lista=resto.split(',')
      kind = lista[0].upper()
      wake = lista[1].upper()
      origin = lista[2].upper()
      destination = lista[3].upper()
      p_rfl = lista[4]
      p_cfl = lista[5]    
      ruta_escogida = ''
      for p in lista[6:]:
        if len(p)==15:
          p_alt = p[8:11]
          p_spd = p[12:15]
          p_fijo = fijo_ant.upper()
          p_hora = p[1:7]
        else:
          fijo_ant = p
          if ruta_escogida == '':
            ruta_escogida = p.upper()
          else:
            ruta_escogida += ','+p.upper()
      if ejer.has_section('req') and ejer.has_option('req',ind):
        incidencia=ejer.get('req',ind)
        hora_inc=incidencia[:4]
        inc=incidencia[5:]
        if (inc[0]=='"' and inc[-1]=='"') or (inc[0]=="'" and inc[-1]=="'"):
            inc=inc[1:-1]
      else:
        hora_inc=''
        inc=''
    def definir_ruta(root):
      # Ahora vamos a por las rutas
      frame1 = Toplevel(root)
      txt_pedir_fijo = Label (frame1, text = 'Entre punto(s) de la ruta (separados con ,)')
      ent_pedir_fijo = Entry (frame1, width=7, bg = 'white')
      def seguir(e=None):
        global fijo_ruta
        fijo_ruta = ent_pedir_fijo.get().upper().split(',')
        frame1.destroy()
      but_pedir_fijo = Button (frame1, text='Aceptar', command = seguir)
      frame1.bind('<Return>',seguir)
      frame1.bind('<KP_Enter>',seguir)
      but_pedir_fijo.pack(side='bottom')
      txt_pedir_fijo.pack(side='left')
      ent_pedir_fijo.pack(side='left')
      ent_pedir_fijo.focus_set()
      def set_window_size():
	window_width = root.winfo_reqwidth()
	window_height = root.winfo_reqheight()
	screen_width = root.winfo_screenwidth()
	screen_height = root.winfo_screenheight()
	px = (screen_width - window_width) / 2
	py = (screen_height - window_height) / 2
	frame1.wm_geometry("+%d+%d" % (px,py))
      frame1.after_idle(set_window_size)
      frame1.wait_window()
      
      frame = Toplevel(root)
      txt_fijo_ruta = Label (frame, text = 'Fijo(s) en ruta:')
      ent_fijo_ruta = Label (frame, text = fijo_ruta)
      txt_num_ruta = Label (frame, text = 'Número de la ruta')
      ent_num_ruta = Entry (frame, width = 2, bg='white')
      ent_num_ruta.focus_set()
      copia = rutas.matching_routes(fijo_ruta,'','')
      opciones = ['00.- Nueva ruta']
      contador = 1
      for a in copia:
          opciones.append('%02d' % (contador)+'.- '+a)
          contador = contador + 1
      if contador > 1:
        ent_num_ruta.insert(END,'01')
      else:
        ent_num_ruta.insert(END,'00')
      
      def numero(e=None):
        global ruta_escogida
        ruta_escogida = ''
        aux = ent_num_ruta.get()
        if aux <>'':
          aux = int (aux)
        else:
          aux = 1000
        if aux== 0:
          intro_ruta = Toplevel(frame)
          txt_titulo = Label (intro_ruta, text = 'Introduzca los puntos de la ruta separados por comas')
          ent_ruta = Entry(intro_ruta, width = 50, bg = 'white')
          def acc_ruta(e=None, frame = frame):
            global ruta_escogida
            ruta_escogida = ent_ruta.get().upper().rstrip()
            if ruta_escogida == '':
              ruta_escogida['bg'] = 'red'
            else:
              pto_no_conocido = ''
              for pto in ruta_escogida.split(','):
                if pto not in puntos: pto_no_conocido += pto+' '
              intro_ruta.destroy()
              # Comprobamos que los puntos existan. En caso contrario avisa
              if pto_no_conocido <> '':
                punto_desc = Toplevel(frame)
                txt_att = Label (punto_desc, text = 'ATENCIÓN',fg='red')
                txt_att2 = Label (punto_desc, text = 'Los siguientes puntos no están en ninguna ruta archivada: '+pto_no_conocido, fg='red')
                def acept (e=None):
                  punto_desc.destroy()
                but_ok = Button (punto_desc, text = 'Roger', command = acept)
                punto_desc.bind('<Return>',acept)
                punto_desc.bind('<KP_Enter>',acept)
                txt_att.pack(side = TOP)
                txt_att2.pack(side = TOP)
                but_ok.pack(side=TOP)
                but_ok.focus_set()
                def set_window_size():
                  window_width = root.winfo_reqwidth()
                  window_height = root.winfo_reqheight()
                  screen_width = root.winfo_screenwidth()
                  screen_height = root.winfo_screenheight()
                  px = (screen_width - window_width) / 2
                  py = (screen_height - window_height) / 2
                  punto_desc.wm_geometry("+%d+%d" % (px,py))
                punto_desc.after_idle(set_window_size)
                punto_desc.wait_window()
          but_acept = Button (intro_ruta, text = 'Aceptar',command = acc_ruta)
          intro_ruta.bind('<Return>',acc_ruta)
          intro_ruta.bind('<KP_Enter>',acc_ruta)
          txt_titulo.pack(side='top')
          ent_ruta.pack(side='top')
          ent_ruta.focus_set()
          but_acept.pack()
          def set_window_size():
            window_width = root.winfo_reqwidth()
            window_height = root.winfo_reqheight()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            px = (screen_width - window_width) / 2
            py = (screen_height - window_height) / 2
            intro_ruta.wm_geometry("+%d+%d" % (px,py))
          intro_ruta.after_idle(set_window_size)

          intro_ruta.wait_window()
          frame.destroy()
        elif aux < len(opciones):
          ruta_escogida = opciones[aux][5:]
          frame.destroy()
        else :
          ent_num_ruta['bg'] = 'red'
      but_siguiente = Button(frame, text = 'Siguiente >',command = numero)
      frame.bind('<Return>',numero)
      frame.bind('<KP_Enter>',numero)
      txt_fijo_ruta.grid(column=0,row=6,sticky=W)
      ent_fijo_ruta.grid(column=1,row=6,sticky=W)
      txt_num_ruta.grid(column=0,row=7,sticky=W)
      ent_num_ruta.grid(column=1,row=7,sticky=W)
      fila = 8
      for o in opciones:
        txt_o = Label (frame, text = o)
        txt_o.grid(column=0,row=fila,columnspan=2,sticky = W)
        fila=fila+1
      but_siguiente.grid(column=1,row=fila,sticky=E)
      def set_window_size():
	window_width = root.winfo_reqwidth()
	window_height = root.winfo_reqheight()
	screen_width = root.winfo_screenwidth()
	screen_height = root.winfo_screenheight()
	px = (screen_width - window_width) / 2
	py = (screen_height - window_height) / 2
	frame.wm_geometry("+%d+%d" % (px,py))
      frame.after_idle(set_window_size)

      frame.wait_window()
      return ruta_escogida    
    
    # Entrada de datos
    frame = Toplevel(root)
    frame.title = 'Entrada de datos'
    txt_datos = Label (frame, text = 'DATOS DEL VUELO')
    txt_ind = Label (frame, text = 'Indicativo:')
    ent_ind = Entry (frame, width = 12, bg='white')
    ent_ind.insert(END,ind)
    txt_tipo = Label (frame, text = 'Modelo avión')
    ent_tipo = Entry (frame, width = 6, bg='white')
    ent_tipo.insert(END,kind)
    txt_estela = Label (frame, text = 'Estela')
    ent_estela = Entry (frame, width = 2, bg='white')
    ent_estela.insert(END,wake)
    txt_velocidad = Label (frame, text = 'Velocidad ficha')
    ent_velocidad = Entry (frame, width = 4, bg='white')
    ent_velocidad.insert(END,p_spd)
    txt_origen = Label (frame, text = 'Origen:')
    ent_origen = Entry (frame, width = 5, bg='white')
    ent_origen.insert(END,origin)
    txt_destino = Label (frame, text = 'Destino:')
    ent_destino = Entry (frame, width = 5, bg='white')
    ent_destino.insert(END,destination)
    txt_ruta = Label (frame, text = 'Ruta:')
    txt_ruta_esc = Label(frame,text = ruta_escogida)
    def escoger_ruta():
      global ruta_escogida,txt_ruta_esc
      ruta_escogida = definir_ruta(frame)
      txt_ruta_esc['text'] = ruta_escogida
    ent_ruta = Button(frame, text = 'Escoger ruta',command = escoger_ruta)
    txt_fl_one = Label (frame, text = 'Nivel en 1er fijo ruta:')
    ent_fl_one = Entry (frame, width = 3, bg = 'white')
    ent_fl_one.insert(END,p_alt)
    txt_cfl = Label (frame, text = 'Nivel autorizado (CFL):')
    ent_cfl = Entry (frame, width = 3, bg = 'white')
    ent_cfl.insert(END,p_cfl)
    txt_rfl = Label (frame, text = 'Nivel requerido (RFL):')
    ent_rfl = Entry (frame, width = 3, bg = 'white')
    ent_rfl.insert(END,p_rfl)
    txt_fijo_eto = Label (frame, text = 'Fijo definición hora:')
    ent_fijo_eto = Entry (frame, width = 7, bg = 'white')
    ent_fijo_eto.insert(END,p_fijo)
    txt_eto = Label (frame, text = 'ETO en fijo (hhmmss):')
    ent_eto = Entry (frame, width = 6, bg = 'white')
    ent_eto.insert(END,p_hora)
    txt_hora_inc = Label (frame, text= 'Hora incidencia (hhmm):')
    ent_hora_inc = Entry (frame, width=4, bg = 'white')
    ent_hora_inc.insert(END,hora_inc)
    txt_inc = Label (frame, text = 'Incidencia:')
    ent_inc = Entry (frame, width = 10, bg = 'white')
    ent_inc.insert(END,inc)
    grabar = False
    otro_avo = False
    def comprobar():
      global indicativo,tipo,estela,fijo_ruta,origen,destino
      global fl_one,cfl,rfl,fijo_eto,eto,grabar,vel, otro_avo
      global incidencia
      bueno = True
      vel = ent_velocidad.get()
      if len(vel) <> 3:
        bueno = False
        ent_velocidad['bg'] = 'red'
        ent_velocidad.focus_set()
      else:
        ent_velocidad['bg'] = 'white'
      eto = ent_eto.get()
      if len(eto) <> 6:
        bueno = False
        ent_eto['bg'] = 'red'
        ent_eto.focus_set()
      else:
        ent_eto['bg'] = 'white'
      rfl = ent_rfl.get()
      if len(rfl)<>3:
        bueno = False
        ent_rfl['bg'] = 'red'
        ent_rfl.focus_set()
      else:
        ent_rfl['bg'] = 'white'
      cfl = ent_cfl.get()
      if len(cfl)<> 3:
        bueno = False
        ent_cfl['bg'] = 'red'
        ent_cfl.focus_set()
      else:
        ent_cfl['bg'] = 'white'
      fijo_eto = ent_fijo_eto.get().upper()
      if (fijo_eto == '') or (fijo_eto not in ruta_escogida.split(',')):
        bueno = False
        ent_fijo_eto['bg'] = 'red'
        ent_fijo_eto.focus_set()
      else:
        ent_fijo_eto['bg'] = 'white'
      fl_one = ent_fl_one.get()
      if len(fl_one) <>3:
        bueno = False
        ent_fl_one['bg'] = 'red'
        ent_fl_one.focus_set()
      else:
        ent_fl_one['bg'] = 'white'
      destino = ent_destino.get().upper()
      if len(destino)<>4:
        bueno = False
        ent_destino['bg'] = 'red'
        ent_destino.focus_set()
      else:
        ent_destino['bg'] = 'white'
      origen = ent_origen.get().upper()
      if len(origen)<>4:
        bueno = False
        ent_origen['bg'] = 'red'
        ent_origen.focus_set()
      else:
        ent_origen['bg'] = 'white'
      estela = ent_estela.get().upper()
      if len(estela)<>1:
        bueno = False
        ent_estela['bg'] = 'red'
        ent_estela.focus_set()
      else:
        ent_estela['bg'] = 'white'
      tipo = ent_tipo.get().upper()
      if tipo == '':
        bueno = False
        ent_tipo['bg'] = 'red'
        ent_tipo.focus_set()
      else:
        ent_tipo['bg'] = 'white'
      indicativo = ent_ind.get().upper()
      if indicativo == '':
        bueno = False
        ent_ind['bg'] = 'red'
        ent_ind.focus_set()
      else:
        ent_ind['bg'] = 'white'
      hora_inc=ent_hora_inc.get()
      if (hora_inc<>'' and len(hora_inc)==4 and hora_inc.isdigit()) or hora_inc=='':
        ent_hora_inc['bg']='white'
      else:
        ent_hora_inc['bg']='red'
        ent_hora_inc.focus_set()
        bueno=False
      inc=ent_inc.get()
      if (hora_inc<>'' and inc==''):
        ent_inc['bg']='red'
        ent_inc.focus_set()
        bueno=False
      else:
        ent_inc['bg']='white'
      incidencia=hora_inc+','+'"'+inc+'"'
      return bueno
    def terminar():
      if comprobar():
        global otro_avo, grabar
        grabar = True
        otro_avo = False
        frame.destroy()
    def otro_mas():
      if comprobar():
        global otro_avo, grabar
        grabar = True
        otro_avo = True
        frame.destroy()
    but_otro_mas = Button(frame, text = 'Siguiente vuelo', command = otro_mas)
    but_terminar = Button(frame, text = 'Terminar',command = terminar)
    txt_datos.grid(column=0,row=0, columnspan=2)
    txt_ind.grid(column=0, row=1,sticky=W)
    ent_ind.grid(column=1,row=1,sticky=W)
    ent_ind.focus_set()
    txt_tipo.grid(column=0,row=2,sticky=W)
    ent_tipo.grid(column=1,row=2,sticky=W)
    txt_estela.grid(column=0,row=3,sticky=W)
    ent_estela.grid(column=1,row=3,sticky=W)
    txt_velocidad.grid(column=0,row=4,sticky=W)
    ent_velocidad.grid(column=1,row=4,sticky=W)
    txt_origen.grid(column=0, row=5,sticky=W)
    ent_origen.grid(column=1,row=5,sticky=W)
    txt_destino.grid(column=0, row=6,sticky=W)
    ent_destino.grid(column=1,row=6,sticky=W)
    txt_ruta.grid(column=0,row=7,sticky=W)
    txt_ruta_esc.grid(column=1,row=7,sticky=W)
    ent_ruta.grid(column=1,row=8,sticky=W)
    txt_fl_one.grid(column=0,row=9,sticky=W)
    ent_fl_one.grid(column=1,row=9,sticky=W)
    txt_cfl.grid(column=0,row=10,sticky=W)
    ent_cfl.grid(column=1,row=10,sticky=W)
    txt_rfl.grid(column=0,row=11,sticky=W)
    ent_rfl.grid(column=1,row=11,sticky=W)
    txt_fijo_eto.grid(column=0,row=12,sticky=W)
    ent_fijo_eto.grid(column=1,row=12,sticky=W)
    txt_eto.grid(column=0,row=13,sticky=W)
    ent_eto.grid(column=1,row=13,sticky=W)
    txt_hora_inc.grid(column=0,row=14,sticky=W)
    ent_hora_inc.grid(column=1,row=14,sticky=W)
    txt_inc.grid(column=0,row=15,sticky=W)
    ent_inc.grid(column=1,row=15,sticky=W)
    but_otro_mas.grid(column=0,row=16,sticky=W)
    but_terminar.grid(column=1,row=16,sticky=E)
    def set_window_size():
	window_width = root.winfo_reqwidth()
	window_height = root.winfo_reqheight()
	screen_width = root.winfo_screenwidth()
	screen_height = root.winfo_screenheight()
	px = (screen_width - window_width) / 2
	py = (screen_height - window_height) / 2
	frame.wm_geometry("+%d+%d" % (px,py))
    frame.after_idle(set_window_size)

    
    frame.wait_window()
    
    # Ahora montamos la linea del vuelo
    resto = tipo+','+estela+','+origen+','+destino+','+rfl+','+cfl
    grupo='H'+eto+'F'+fl_one+'V'+vel
    for f in ruta_escogida.split(','):
      resto = resto +','+f
      if f == fijo_eto:
        resto = resto + ',' + grupo
    resto = resto.rstrip() # Quitamos los posibles espacios en blanco
    return (grabar,indicativo,resto,otro_avo)
  
  
  if not ejer.has_section('datos'):
    global fichero
    ejer.add_section('datos')
    ejer.set('datos','fir',fir_elegido)
    ejer.set('datos','sector','')
    ejer.set('datos','hora_inicio','')
    ejer.set('datos','comentario','')
    ejer.set('datos','viento','')
    fichero = ''
  elif not ejer.has_option('datos','viento'):
    ejer.set('datos','viento','')
  if not ejer.has_section('vuelos'):
    ejer.add_section('vuelos')
  if not ejer.has_section('req'):
    ejer.add_section('req')
  vuelos = []
  root = Tk()

  screen_width = root.winfo_screenwidth()
  screen_height = root.winfo_screenheight()
  root.wm_geometry("%dx%d+%d+%d" % (screen_width,screen_height,0,0))

  txt_datos = Label (root, text = 'DATOS GENERALES DEL EJERCICIO')
  txt_datos.grid(column=0, row=0, columnspan=4)
  txt_nombre = Label(root, text = 'Fichero: '+fichero)
  txt_nombre.grid(column=0, row=1, columnspan=2, sticky=W)
  txt_viento = Label (root, text = 'Viento: '+ejer.get('datos','viento'))
  txt_viento.grid(column=2, row=1, columnspan=2, sticky=W)
  txt_fir = Label (root, text = 'FIR: '+ejer.get('datos','fir'))
  txt_sector = Label (root, text = 'Sector: '+ejer.get('datos','sector'))
  txt_fir.grid(column=0, row=2, columnspan=2, sticky=W)
  txt_sector.grid(column=2, row=2, columnspan=2, sticky=W)
  txt_hora = Label (root, text='Hora de inicio: '+ejer.get('datos','hora_inicio'))
  txt_hora.grid(column=0, row=3, columnspan=2, sticky=W)
  txt_coment = Label (root, text = 'Comentario: '+ejer.get('datos','comentario'))
  txt_coment.grid(column=0,row=4, columnspan=4, sticky=W)
  def editar_datos_generales(root = root):
#     global txt_nombre, txt_fir, txt_sector, txt_hora, fichero, txt_coment
    datos_generales(root)
#     txt_nombre.config(text = 'Fichero: '+fichero)
#     txt_fir['text'] = 'fir: '+ejer.get('datos','fir')
#     txt_sector["text"] = 'sector: '+ejer.get('datos','sector')
#     txt_coment['text'] = 'Comentario: '+ejer.get('datos','comentario')
#     txt_hora['text'] = 'hora de inicio: '+ejer.get('datos','hora_inicio')
  but_edit_gen = Button(root, text='Editar datos generales', command=editar_datos_generales)
  but_edit_gen.grid(column=2, row=3, columnspan=2, sticky=E)
  txt_ventana = Label (root, text = '---------- VUELOS DEL EJERCICIO ----------')
  txt_ventana.grid(column=0,row=5,columnspan=4)  
  window = Text(root, bg = 'white', width = 150, height = 40)
  window.grid(column=0, row=6, columnspan = 4)
#   scroll_x = Scrollbar(window)
#   scroll_x.pack(side=RIGHT)
#   scroll_x.config(command = window.xview)
#   window.config(xscrollcommand = scroll_x.set)
#   scroll_y = Scrollbar(window)
#   scroll_y.pack(side=BOTTOM)
#   scroll_y.config(command = window.yview)
#   window.config(yscrollcommand = scroll_y.set)
  def poner_vuelos(window):
    # Actualizar el texto de los vuelos
    window.config(state=NORMAL)
    window.delete(1.0,END)
    window.config(cursor="arrow")
    vuelos = ejer.items('vuelos')   
    print 'Vuelos: ',vuelos
    fila=0
    for (ind,resto) in vuelos:
      def show_hand_cursor(e=None):
        window.config(cursor = 'hand2')
      def show_arrow_cursor(e=None):
        window.config(cursor = 'arrow')
      def editar(e=None, call=ind):
        print 'Editando ',call
        (guardar, indicativo,ruta,kk) = entrada(call,root)
        if guardar:
          if call <> indicativo:
            ejer.remove_option('vuelos',call)
          ejer.set('vuelos',indicativo,ruta)
          poner_vuelos(window)
          if incidencia<>',""':
              ejer.set('req',indicativo,incidencia)
          else:
              ejer.remove_option('req',indicativo)
      def quitar(e=None, call=ind):
        print 'Quitando ',call
        seguro = Toplevel(root)
        txt_seguro = Label (seguro, text = '¿ Quieres eliminar el '+call.upper()+ '?')
        def grabar():
          ejer.remove_option('vuelos',call)
          poner_vuelos(window)
          seguro.destroy()
        def anular():
          seguro.destroy()
        but_acp = Button(seguro, text = 'SI', command = grabar)
        but_anl = Button (seguro, text = 'NO', command = anular)
        txt_seguro.pack(side='top')
        but_acp.pack(side='right')
        but_anl.pack()
        seguro.wait_window()
      window.tag_config('q'+ind, foreground='blue', underline=1)
      window.tag_bind('q'+ind,"<Enter>", show_hand_cursor)
      window.tag_bind('q'+ind,"<Leave>", show_arrow_cursor)
      window.tag_bind('q'+ind,"<Button-1>",quitar)
      window.tag_config('e'+ind, foreground='blue', underline=1)
      window.tag_bind('e'+ind,"<Enter>", show_hand_cursor)
      window.tag_bind('e'+ind,"<Leave>", show_arrow_cursor)
      window.tag_bind('e'+ind,"<Button-1>",editar)
      texto = ind.upper()+' = '+resto
      print 'Insertando: ',texto
      b_edit = window.insert (END, '(Editar)','e'+ind)
      window.insert(END,'  ')
      b_quit = window.insert(END,'(Quitar)','q'+ind)
      window.insert(END, '  '+texto +'\r\n')
    window.config(state=DISABLED)
  poner_vuelos(window)
  def mas():
    meter_vuelo = True
    while meter_vuelo:
      (guardar, indicativo,ruta,meter_vuelo) = entrada('new',root)
      print 'Datos de vuelta: ',(guardar, indicativo,ruta,meter_vuelo)
      if guardar:
        ejer.set('vuelos',indicativo,ruta)
        poner_vuelos(window)
        if incidencia<>',""':
          ejer.set('req',indicativo,incidencia)
        else:
          ejer.remove_option('req',indicativo)

  but_nuevo_vuelo = Button(root, text = 'Nuevo vuelo',command = mas)
  but_nuevo_vuelo.grid(column=3,row=7)
  def terminar(e=None):
    if fichero == '':
      not_yet = Tk()
      txt_titulo = Label (not_yet, text = 'Imposible guardar')
      txt_titulo1 = Label (not_yet, text = 'Faltan los datos generales')
      def salir():
        not_yet.destroy()
      but_salir = Button (not_yet, text = 'Completar datos', command = salir)
      txt_titulo.pack()
      txt_titulo1.pack()
      but_salir.pack()
      not_yet.mainloop()
      return
    else:
      num_eje = len(ejer.items('vuelos'))
      coment = ejer.get('datos','comentario')
      if coment.endswith(')'):
        for kk in range(len(coment)):
          if coment[-1] == '(':
            coment = coment[:-1]
            break
          else:
            coment = coment[:-1]
      ejer.set('datos','comentario',coment+'('+str(num_eje)+')')
      if len(ejer.items('req'))==0: ejer.remove_section('req')
      ejer.write(open(fichero,'w'))
      root.destroy()
      bye = Tk()
      txt_titulo = Label (bye, text = 'Ejercicio guardado en '+fichero)
      txt_titulo1 = Label (bye, text = 'Para que la puedas usar debes moverla al subdirectorio /pasadas/')
      txt_titulo2 = Label (bye, text = '¡Acuérdate de subirla al repositorio con la tortuga!')
      def salir():
        bye.destroy()
      but_salir = Button (bye, text = 'salir', command = salir)
      bye.bind('<Return>',salir)
      bye.bind('<KP_Enter>',salir)
      txt_titulo.pack()
      txt_titulo1.pack()
      txt_titulo2.pack()
      but_salir.pack()
      but_salir.focus_set()
      
      bye.mainloop()
  but_terminar = Button(root, text = 'Grabar',command = terminar)
  but_terminar.grid(column=2,row=7)
  def cancelar():
    root.destroy()
  but_cancelar = Button(root, text = 'Cancelar', command=cancelar)
  but_cancelar.grid(column=1, row = 7)
  but_nuevo_vuelo.focus_set()
  
  root.mainloop()
    

global fichero
fichero = ''
def nueva():
  global ejer, fichero
  fichero = ''
  ejer = ConfigParser()
  ejercicio()  

def modificar(seleccion_usuario):
  global ejer, fichero
  [fir_elegido , sector_elegido , ejercicio_elegido , imprimir_fichas] = seleccion_usuario
  fichero = ejercicio_elegido[1]
  ejer = ConfigParser()
  ejer.readfp(open(fichero,'r'))
  fichero = './'+os.path.basename(fichero)
  ejercicio()

class RouteDB:
  """A database of routes that are known for a specific FIR"""
  
  def __init__(self):
    self._routes={}
  
  def append(self,route,orig,dest):
    """Append a route together with the orig and dest to the DB of routes"""
    if route not in self._routes.keys():
      # We add the route to the database, with a frequency of one, and
      # adding the first pair of orig and dest
      self._routes[route]=(1,[orig+dest])
    else:
      # If the route already exists, we increment the frequency for the route
      # and if the orig_dest pair is new, add it to the list.
      (frequency,orig_dest_list)=self._routes[route]
      frequency=frequency+1
      if (orig+dest) not in orig_dest_list:
        orig_dest_list.append(orig+dest)
      self._routes[route]=(frequency,orig_dest_list)
      
  def size(self):
    """Return the number of known routes"""
    len(self._routes)
  
  def matching_routes(self,fix_list,orig,dest):
    """Given a list of points, and optional orig and dest airports, return
    a sorted list of possible matching routes"""
    match_routes=self._routes.copy()
    # Routes must contain the given fixes in the same order
    for route in match_routes.keys():
      i=0
      rs=route.split(',')
      for f in rs:
        if f==fix_list[i]:
          i=i+1
      if i<len(fix_list):
        del match_routes[route]

    # Out of the remaining routes, we need to sort them according to whether
    # it is appropriate for the orig-dest pair first, and frequency second
    
    sorted_routes=[]
    for (route, (frequency, orig_dest_list)) in match_routes.items():
      if (orig+dest) in orig_dest_list:
        matches_orig_dest=1
      else:
        matches_orig_dest=0
      sorted_routes.append([matches_orig_dest,frequency,route])
    sorted_routes.sort(reverse=True)
    logging.debug(sorted_routes)
    for i in range(len(sorted_routes)):
      sorted_routes[i]=sorted_routes[i][2]
    return sorted_routes
        
    