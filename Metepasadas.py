#!/usr/bin/python
#-*- coding:"iso8859-15" -*-
from ConfigParser import *
import glob
from Tkinter import *

def ejercicio():
  # En primer lugar escojo el FIR
  fires = glob.glob('*.fir')
  config=ConfigParser()
  lista = []
  for a in fires:
    config.readfp(open(a,'r'))
    lista.append(config.get('datos','nombre'))
  lista.sort()
  root = Tk()
  txt_Escoge = Label(root,text='Escoge FIR:')
  lista_fir = Listbox(root)
  for a in lista:
    lista_fir.insert(END,a)
  def escoge_fir():
    global fir_elegido
    fir_elegido = lista[int(lista_fir.curselection()[0])]
    root.destroy()
  txt_Aceptar = Button(root,text='Aceptar',command=escoge_fir)
  txt_Escoge.pack()
  lista_fir.pack()
  txt_Aceptar.pack()  
  root.mainloop()
  print 'Fir escogido: ',fir_elegido
  for a in config.sections():
    config.remove_section(a)
  
  # Ahora creamos la base de datos con las rutas
  a_extraer = glob.glob('./pasadas/*.eje')
  rutas=[]
  for e in a_extraer:
    config.readfp(open(e,'r'))
    if config.get('datos','fir') == fir_elegido:
      for (ident,datos) in config.items('vuelos'):
        datos=datos.split(',')
        ruta = ''
        for punto in datos[6:]:
          if len(punto)<7:
            ruta = ruta + punto.upper() + ','
        ruta = ruta[:-1]
      if ruta not in rutas:
        rutas.append(ruta)
    for a in config.sections():
      config.remove_section(a)
  rutas.sort()
  print 'Total de rutas: ',len(rutas)
  # Ahora empezamos introducir el ejercicio
  # Primero datos generales
  root = Tk()
  txt_datos = Label (root, text = 'DATOS GENERALES EJERCICIO')
  txt_fichero = Label(root,text = 'Nombre del fichero:')
  ent_fichero = Entry (root,width = 30, bg='white')
  txt_sector = Label (root, text = 'Sector:')
  ent_sector = Entry (root, width = 10, bg='white')
  txt_hora_inicio = Label (root, text = 'Hora de inicio (hhmm):')
  ent_hora_inicio = Entry (root, width = 6, bg='white')
  txt_descripcion = Label (root, text = 'Descripción ejercicio: ')
  ent_descripcion = Entry (root, width = 30, bg='white')
  def siguiente():
    global fichero, sector, hora_inicio, descrip
    correcto = True
    fichero = ent_fichero.get()
    if fichero == '':
      correcto = False
      ent_fichero['bg'] = 'red'
    else:
      ent_fichero['bg'] = 'white'
    sector = ent_sector.get().upper()
    if sector == '':
      correcto = False
      ent_sector['bg'] = 'red'
    else:
      ent_sector['bg'] = 'white'
    hora_inicio = ent_hora_inicio.get()
    if len(hora_inicio) <>4:
      correcto = False
      ent_hora_inicio['bg'] = 'red'
    else:
      ent_hora_inicio['bg'] = 'white'
    descrip = ent_descripcion.get()
    if descrip == '':
      correcto = False
      ent_descripcion['bg'] = 'red'
    else:
      ent_descripcion['bg'] = 'white'
    if correcto: root.destroy()
  but_siguiente = Button (root, text='Siguiente >', command = siguiente)
  txt_datos.grid(column=0,row=0,columnspan=2)
  txt_fichero.grid(column=0, row=1,sticky=W)
  ent_fichero.grid(column=1,row=1,sticky=W)
  txt_sector.grid(column=0,row=2,sticky=W)
  ent_sector.grid(column=1,row=2,sticky=W)
  txt_hora_inicio.grid(column=0,row=3,sticky=W)
  ent_hora_inicio.grid(column=1,row=3,sticky=W)
  txt_descripcion.grid(column=0,row=4,sticky=W)
  ent_descripcion.grid(column=1,row=4,sticky=W)
  but_siguiente.grid(column=1,row=5,sticky=E)
  
  root.mainloop()
  print fichero, sector, hora_inicio, descrip
  ejer = ConfigParser()
  ejer.add_section('datos')
  ejer.set('datos','fir',fir_elegido)
  ejer.set('datos','sector',sector)
  ejer.set('datos','hora_inicio',hora_inicio[0:2]+':'+hora_inicio[2:4])
  ejer.set('datos','comentario',descrip)
  
  # Ahora, bucle sobre los vuelos.
  vuelos = []
  def entrada(root):
    global vuelos
    frame = Toplevel(root)
    txt_datos = Label (frame, text = 'DATOS DEL VUELO')
    txt_ind = Label (frame, text = 'Indicativo:')
    ent_ind = Entry (frame, width = 12, bg='white')
    txt_origen = Label (frame, text = 'Origen:')
    ent_origen = Entry (frame, width = 6, bg='white')
    txt_destino = Label (frame, text = 'Destino:')
    ent_destino = Entry (frame, width = 6, bg='white')
    txt_tipo = Label (frame, text = 'Modelo avión')
    ent_tipo = Entry (frame, width = 7, bg='white')
    txt_estela = Label (frame, text = 'Estela')
    ent_estela = Entry (frame, width = 1, bg='white')
    txt_fijo_ruta = Label (frame, text = 'Fijo entrada/salida: ')
    ent_fijo_ruta = Entry (frame, width = 8, bg='white')
    def siguiente():
      global indicativo,tipo,estela,fijo_ruta,origen,destino
      bueno = True
      indicativo = ent_ind.get().upper()
      if indicativo == '':
        bueno = False
        ent_ind['bg'] = 'red'
      else:
        ent_ind['bg'] = 'white'
      tipo = ent_tipo.get().upper()
      if tipo == '':
        bueno = False
        ent_tipo['bg'] = 'red'
      else:
        ent_tipo['bg'] = 'white'
      origen = ent_origen.get().upper()
      if len(origen)<>4:
        bueno = False
        ent_origen['bg'] = 'red'
      else:
        ent_origen['bg'] = 'white'
      destino = ent_destino.get().upper()
      if len(destino)<>4:
        bueno = False
        ent_destino['bg'] = 'red'
      else:
        ent_destino['bg'] = 'white'
      estela = ent_estela.get().upper()
      if len(estela)<>1:
        bueno = False
        ent_estela['bg'] = 'red'
      else:
        ent_estela['bg'] = 'white'
      fijo_ruta = ent_fijo_ruta.get().upper()
      if fijo_ruta == '':
        bueno = False
        ent_fijo_ruta['bg'] = 'red'
      else:
        ent_fijo_ruta['bg'] = 'white'
      if bueno: frame.destroy()
    but_siguiente = Button(frame, text = 'Siguiente >',command = siguiente)
    txt_datos.grid(column=0,row=0, columnspan=2)
    txt_ind.grid(column=0, row=1,sticky=W)
    ent_ind.grid(column=1,row=1,sticky=W)
    txt_origen.grid(column=0, row=2,sticky=W)
    ent_origen.grid(column=1,row=2,sticky=W)
    txt_destino.grid(column=0, row=3,sticky=W)
    ent_destino.grid(column=1,row=3,sticky=W)
    txt_tipo.grid(column=0,row=4,sticky=W)
    ent_tipo.grid(column=1,row=4,sticky=W)
    txt_estela.grid(column=0,row=5,sticky=W)
    ent_estela.grid(column=1,row=5,sticky=W)
    txt_fijo_ruta.grid(column=0,row=6,sticky=W)
    ent_fijo_ruta.grid(column=1,row=6,sticky=W)
    but_siguiente.grid(column=1,row=7,sticky=E)
    
    frame.wait_window()
    
    # Ahora vamos a por las rutas
    frame = Toplevel(root)
    txt_datos = Label (frame, text = 'DATOS DEL VUELO')
    txt_ind = Label (frame, text = 'Indicativo: ')
    ent_ind = Label (frame, text = indicativo)
    txt_origen = Label (frame, text = 'Origen:')
    ent_origen = Label (frame, text = origen)
    txt_destino = Label (frame, text = 'Destino:')
    ent_destino = Label (frame, text = destino)
    txt_tipo = Label (frame, text = 'Modelo avión')
    ent_tipo = Label (frame, text = tipo)
    txt_estela = Label (frame, text = 'Estela')
    ent_estela = Label (frame, text = estela)
    txt_fijo_ruta = Label (frame, text = 'Fijo en ruta:')
    ent_fijo_ruta = Label (frame, text = fijo_ruta)
    txt_num_ruta = Label (frame, text = 'Número de la ruta')
    ent_num_ruta = Entry (frame, width = 2, bg='white')
    opciones = ['00.- Nueva ruta']
    contador = 1
    for a in rutas:
      if fijo_ruta in a.split(','):
        opciones.append('%02d' % (contador)+'.- '+a)
        contador = contador + 1
    def numero():
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
        def acc_ruta():
          global ruta_escogida
          ruta_escogida = ent_ruta.get().upper().rstrip()
          if ruta_escogida == '':
            ruta_escogida['bg'] = 'red'
          else:
            intro_ruta.destroy()
        but_acept = Button (intro_ruta, text = 'Aceptar',command = acc_ruta)
        txt_titulo.pack(side='top')
        ent_ruta.pack(side='top')
        but_acept.pack()
        intro_ruta.wait_window()
        frame.destroy()
      elif aux < len(opciones):
        ruta_escogida = opciones[aux][5:]
        frame.destroy()
      else :
        ent_num_ruta['bg'] = 'red'
    but_siguiente = Button(frame, text = 'Siguiente >',command = numero)
    txt_datos.grid(column=0,row=0, columnspan=2)
    txt_ind.grid(column=0, row=1,sticky=W)
    ent_ind.grid(column=1,row=1,sticky=W)
    txt_origen.grid(column=0, row=2,sticky=W)
    ent_origen.grid(column=1,row=2,sticky=W)
    txt_destino.grid(column=0, row=3,sticky=W)
    ent_destino.grid(column=1,row=3,sticky=W)
    txt_tipo.grid(column=0,row=4,sticky=W)
    ent_tipo.grid(column=1,row=4,sticky=W)
    txt_estela.grid(column=0,row=5,sticky=W)
    ent_estela.grid(column=1,row=5,sticky=W)
    txt_fijo_ruta.grid(column=0,row=6,sticky=W)
    ent_fijo_ruta.grid(column=1,row=6,sticky=W)
    txt_num_ruta.grid(column=0,row=7,sticky=W)
    ent_num_ruta.grid(column=1,row=7,sticky=W)
    fila = 8
    print 'opciones:',opciones
    for o in opciones:
      txt_o = Label (frame, text = o)
      txt_o.grid(column=0,row=fila,columnspan=2,sticky = W)
      fila=fila+1
    but_siguiente.grid(column=1,row=fila,sticky=E)
    frame.wait_window()
    print 'Ruta escogida: ',ruta_escogida
    
    # Ahora a por el RFL,PFL, velocidad nivel en primer fijo y hora de aparición
    frame = Toplevel(root)
    txt_datos = Label (frame, text = 'DATOS DEL VUELO')
    txt_ind = Label (frame, text = 'Indicativo: ')
    ent_ind = Label (frame, text = indicativo)
    txt_origen = Label (frame, text = 'Origen:')
    ent_origen = Label (frame, text = origen)
    txt_destino = Label (frame, text = 'Destino:')
    ent_destino = Label (frame, text = destino)
    txt_tipo = Label (frame, text = 'Modelo avión')
    ent_tipo = Label (frame, text = tipo)
    txt_estela = Label (frame, text = 'Estela')
    ent_estela = Label (frame, text = estela)
    txt_velocidad = Label (frame, text = 'Velocidad en ficha')
    ent_velocidad = Entry (frame, width = 5, bg = 'white')
    txt_ruta = Label (frame, text = 'Ruta:')
    ent_ruta = Label (frame, text = ruta_escogida)
    txt_fl_one = Label (frame, text = 'Nivel en 1er fijo ruta:')
    ent_fl_one = Entry (frame, width = 5, bg = 'white')
    txt_cfl = Label (frame, text = 'Nivel autorizado (CFL):')
    ent_cfl = Entry (frame, width = 5, bg = 'white')
    txt_rfl = Label (frame, text = 'Nivel requerido (RFL):')
    ent_rfl = Entry (frame, width = 5, bg = 'white')
    txt_fijo_eto = Label (frame, text = 'Fijo definición hora:')
    ent_fijo_eto = Entry (frame, width = 7, bg = 'white')
    txt_eto = Label (frame, text = 'ETO en fijo (hhmmss):')
    ent_eto = Entry (frame, width = 9, bg = 'white')
    def niveles():
      global fl_one,cfl,rfl,fijo_eto,eto,grabar,vel
      bueno = True
      fl_one = ent_fl_one.get()
      if len(fl_one) <>3:
        bueno = False
        ent_fl_one['bg'] = 'red'
      else:
        ent_fl_one['bg'] = 'white'
      cfl = ent_cfl.get()
      if len(cfl)<> 3:
        bueno = False
        ent_cfl['bg'] = 'red'
      else:
        ent_cfl['bg'] = 'white'
      rfl = ent_rfl.get()
      if len(rfl)<>3:
        bueno = False
        ent_rfl['bg'] = 'red'
      else:
        ent_rfl['bg'] = 'white'
      fijo_eto = ent_fijo_eto.get().upper()
      if fijo_eto == '' or fijo_eto not in ruta_escogida.split(','):
        bueno = False
        ent_fijo_eto['bg'] = 'red'
      else:
        ent_fijo_eto['bg'] = 'white'
      eto = ent_eto.get()
      if len(eto) <> 6:
        bueno = False
        ent_eto['bg'] = 'red'
      else:
        ent_eto['bg'] = 'white'
      vel = ent_velocidad.get()
      if len(vel) <> 3:
        bueno = False
        ent_velocidad['bg'] = 'red'
      else:
        ent_velocidad['bg'] = 'white'
      if bueno:
        seguro = Toplevel(frame)
        txt_seguro = Label (seguro, text = '¿Quieres guardar este vuelo?')
        def grabar():
          grabar = True
          seguro.destroy()
        def anular():
          grabar = False
          seguro.destroy()
        but_acp = Button(seguro, text = 'Aceptar', command = grabar)
        but_anl = Button (seguro, text = 'Anular', command = anular)
        txt_seguro.pack(side='top')
        but_acp.pack(side='right')
        but_anl.pack()
        seguro.wait_window()
        frame.destroy()
    but_terminar = Button(frame, text = 'Terminar',command = niveles)
    txt_datos.grid(column=0,row=0, columnspan=2)
    txt_ind.grid(column=0, row=1,sticky=W)
    ent_ind.grid(column=1,row=1,sticky=W)
    txt_origen.grid(column=0, row=2,sticky=W)
    ent_origen.grid(column=1,row=2,sticky=W)
    txt_destino.grid(column=0, row=3,sticky=W)
    ent_destino.grid(column=1,row=3,sticky=W)
    txt_tipo.grid(column=0,row=4,sticky=W)
    ent_tipo.grid(column=1,row=4,sticky=W)
    txt_estela.grid(column=0,row=5,sticky=W)
    ent_estela.grid(column=1,row=5,sticky=W)
    txt_ruta.grid(column=0,row=6,sticky=W)
    ent_ruta.grid(column=1,row=6,sticky=W)
    txt_velocidad.grid(column=0,row=7,sticky=W)
    ent_velocidad.grid(column=1,row=7,sticky=W)
    txt_fl_one.grid(column=0,row=8,sticky=W)
    ent_fl_one.grid(column=1,row=8,sticky=W)
    txt_cfl.grid(column=0,row=9,sticky=W)
    ent_cfl.grid(column=1,row=9,sticky=W)
    txt_rfl.grid(column=0,row=10,sticky=W)
    ent_rfl.grid(column=1,row=10,sticky=W)
    txt_fijo_eto.grid(column=0,row=11,sticky=W)
    ent_fijo_eto.grid(column=1,row=11,sticky=W)
    txt_eto.grid(column=0,row=12,sticky=W)
    ent_eto.grid(column=1,row=12,sticky=W)
    but_terminar.grid(column=1,row=13,sticky = E)
    frame.wait_window()
    
    # Ahora montamos la linea del vuelo
    resto = tipo+','+estela+','+origen+','+destino+','+rfl+','+cfl
    grupo='H'+eto+'F'+fl_one+'V'+vel
    for f in ruta_escogida.split(','):
      resto = resto +','+f
      if f == fijo_eto:
        resto = resto + ',' + grupo
    return (grabar,indicativo,resto)
  
  
  ejer.add_section('vuelos')
  global aux
  aux = []
  while len(aux) == 0:
    vuelos = ejer.items('vuelos')
    root = Tk()
    txt_ventana = Label (root, text = 'VUELOS DEL EJERCICIO')
    txt_ventana.grid(column=0,row=0,columnspan=2)
    fila=1
    for (ind,resto) in vuelos:
      txt_vuelo = Label (root, text = ind.upper())
      txt_vuelo.grid(column=0,row=fila)
      fila=fila+1
    def mas():
      (guardar, indicativo,ruta) = entrada(root)
      if guardar:
        ejer.set('vuelos',indicativo,ruta)
        root.destroy()
    but_nuevo_vuelo = Button(root, text = 'Nuevo vuelo',command = mas)
    but_nuevo_vuelo.grid(column=1,row=fila)
    def terminar(e=None):
      global aux
      num_eje = len(ejer.items('vuelos'))
      ejer.set('datos','comentario',descrip+'('+str(num_eje)+')')     
      ejer.write(open(fichero,'w'))
      aux.append(['kk vaca paca'])
      root.destroy()
      bye = Tk()
      txt_titulo = Label (bye, text = 'Ejercicio guardado en '+fichero)
      txt_titulo1 = Label (bye, text = 'Para que la puedas usar debes moverla al subdirectorio /pasadas/')
      txt_titulo2 = Label (bye, text = '¡Acuérdate de enviarlas al Crujimaster para ponerla en común!')
      def salir():
        bye.destroy()
      but_salir = Button (bye, text = 'salir', command = salir)
      txt_titulo.pack()
      txt_titulo1.pack()
      txt_titulo2.pack()
      but_salir.pack()
      bye.mainloop()
    but_terminar = Button(root, text = 'Grabar',command = terminar)
    but_terminar.grid(column=0,row=fila)  
    
    root.mainloop()
    


ejercicio()
