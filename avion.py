#!/usr/bin/python
#-*- coding:"iso8859-15" -*-

# Movimiento de un móvil con velocidad uniforme

from math import *
from Tkinter import *
import tkFont
import lads
import sys

all_lads = []
definiendo_lad = 0
latest_lad_event_processed = 0
lad_origen = None

label_font = None
label_font_size = 1

xm=ym=0
escala=1.0
centro_x = 10
centro_y = 10

speed_time = 0./60.

seleccionado = None


def set_speed_time(new_speed_time):
	global speed_time
	speed_time = new_speed_time

def set_canvas_info(_xm, _ym, _escala, _centro_x, _centro_y, _punto):
	global xm, ym, escala, centro_x, centro_y, punto
	xm = _xm
	ym = _ym
	escala = _escala
	centro_x = _centro_x
	centro_y = _centro_y
        punto = _punto

def set_label_font(new_font):
	global label_font
	label_font = new_font

def set_label_font_size(new_size):
	global label_font_size
	label_font_size = new_size

def do_scale(a):
  # Devuelve las coordenadas en a transformadas centro_pantalla+(x-x0)*scale
  return s((centro_x,centro_y),p(r((a[0],-a[1]),(xm,-ym)),escala))

def do_unscale(xy):
  (x, y) = xy
  return ( xm+(x-centro_x)/escala, ym-(y-centro_y)/escala )

def s(a,b):
  return (a[0]+b[0],a[1]+b[1]) # Suma de vectores

def r(a,b):
  return (a[0]-b[0],a[1]-b[1]) # Resta de vectores

def p(a,b):
  return (a[0]*b,a[1]*b) #Multiplica el vector a x b

def rp(a): # Rextangulares a polares
  x=a[0]
  y=a[1]
  r=sqrt(pow(x,2)+pow(y,2))
  if r>0:
    ang=degrees(acos(y/r))
  else:
    ang=0.0
  if x<0:
    ang=360-ang
  return (r,ang)
  
def pr(a):  # Polares a rectangulares
  r=a[0]
  ang=a[1]
  return(r*sin(radians(ang)),r*cos(radians(ang)))

def sgn(a):
  if a<>0.:
    return a/abs(a)
  else:
    return 0
  
def v(self):
  #Devuelve TAS 
  if not self.es_spd_std: # Velocidad máxima manteniedo IAS
    ias_max=self.spd_max/(1+0.002*self.fl_max)
    tas_max=ias_max*(1+0.002*self.alt)
    return min(tas_max,self.spd) # Se debe mejorar
  inicio_app = 6.
  trans_tma = 8.
  vel_tma = 153.
  if self.alt<=inicio_app: # Velocidad de aproximación
    return self.spd_app
  elif self.alt<=trans_tma: # Transición entre vel aprox y tma
    p=(self.alt-inicio_app)/(trans_tma - inicio_app)
    return self.spd_app*p+self.spd_tma*(1-p)
  elif self.alt<=vel_tma:
    return self.spd_tma
  else:
    p=min((self.alt-vel_tma)/(self.fl_max-vel_tma),1.)
    return min(self.spd_max * p + self.spd_tma * (1 - p),self.spd_std)
 
def mach(self):
  # Devuelve el número de mach
  return self.spd/600

def f_vert(self):
  # Devuelve factor corrección de velocidad vertical
  q=self.alt/self.fl_max
  if q<.75:
    return 1.0
  elif q<.90:
    return 0.80
  else:
    return 0.60
  
def mach_tas(perc):
  # Transforma número de mach a IAS
  return perc*600

class Airplane:
  
  def __init__(self):
    self.name='IBE767'
    self.tipo='B747'
    self.estela='H'
    self.origen='LEBB'
    self.destino='LEMD'
    self.pos=(0.0,0.0) #x,y
    self.t=0.0 # último tiempo calculado
    self.hist=[] #Histórico últimos 5 puntos
    self.hist_t=0.0 # Tiempo del último punto
    self.hdg=400.0 # Último rumbo calculado. Este valor es para saber la primera vez
    self.hold_hdg=400.0 
    self.alt=350.0 # Altitud
    self.cfl=350.0 # Altitud autorizada
    self.pfl=self.cfl
    self.rfl=self.cfl
    self.fl_max=350.0
    self.rate_climb_max=25.0/60.
    self.rate_climb_std=15.0/60.
    self.rate_desc_max=25.0/60.
    self.rate_desc_std=15.0/60.
    self.es_std=True
    self.rate=0.0 #Tasa de asc/desc.
    self.spd=350.
    self.spd_std=self.spd
    self.spd_max=self.spd
    self.spd_tma=200.
    self.spd_app=180.
    self.es_spd_std=True
    self.ias=300. # Velocidad indicada
    self.route=[[(-8.0,10.0),'punto','00:00']] #Ruta con los puntos
    self.turn=3.0*60.*60. #Los máximos grados por segundo que vira el avión
    self.vfp=True # Vale 1 si via flight plan y 0 si mantiene rumbo 
    self.label_heading = 27
    self.label_radius = 30
    self.label_x = self.label_radius * sin(radians(self.label_heading))
    self.label_y = self.label_radius * cos(radians(self.label_heading))
    self.se_pinta=False
    self.see_mach=False
    self.plotid = None
    self.ficha_imprimida=False
    self.t_ficha=0.
    self.t_impresion=0.
    self.campo_eco=''
    self.esta_asumido=False
    self.plotid = None
    self.last_lad = 0
    self.auto_separation = True


  def next(self,t):
    # Devuelve la posición en el tiempo t
    if t<self.t:
      self.se_pinta=False
      return self.se_pinta # Con esto activamos los vuelos a la hora inicial y se dejan
    else:
      self.se_pinta=1
    # Cálculo de la altitud
    if self.cfl>self.alt:
      if self.es_std:
        self.rate = self.rate_climb_std * f_vert(self)
      else:
        self.rate = min(self.rate_climb_max * f_vert(self),abs(self.rate))
    elif self.cfl<self.alt:
      if self.es_std:
        self.rate = -self.rate_desc_std * f_vert(self)
      else:
        self.rate = -min(self.rate_desc_max * f_vert(self),abs(self.rate))
    inch=self.rate*(t-self.t)
    if abs(self.alt-self.cfl)<abs(inch):
      self.alt=self.cfl
      self.rate =0.
      self.es_std=True
    else:
      self.alt=self.alt+inch
    # Iteración para encontrar la posición
    while t>=self.t+1./60./60.:
      self.spd=v(self)
      if self.vfp:
        self.pto=self.route[0][0] #Punto al que se dirige
      else:
        self.pto=s(self.pos,pr((2*self.spd,self.hold_hdg)))
      self.vect=rp(r(self.pto,self.pos))
      r_obj=self.vect[1]
      if self.hdg<180 and r_obj>self.hdg+180:
        r_obj=r_obj-360
      elif self.hdg>180 and r_obj<self.hdg-180:
        r_obj=r_obj+360
      aux=r_obj-self.hdg
      if abs(aux)<self.turn*(t-self.t) or self.hdg==400.0:
        self.hdg=r_obj%360
      else:
        self.hdg=(self.hdg+(t-self.t)*self.turn*sgn(aux))%360
      self.salto=self.spd*(t-self.t) # Distancia recorrida en este inc. de t
      # Ha pasado el punto al que se dirige
      if self.salto>self.vect[0]:
        if len(self.route)==1:
          self.vfp=False # Si es el último punto, mantiene el rumbo   
          self.hold_hdg=self.hdg
        else:
          self.route.pop(0) # Eliminamos el punto ya pasado de la ruta e iteramos
          perc=self.vect[0]/self.salto
          self.salto=self.spd*(t-self.t)*perc
          self.t=self.t+(t-self.t)*perc
      else:
        self.t=t #Almacenamos el tiempo
      self.pos=s(self.pos,pr((self.salto,self.hdg))) #Cambiamos la posición
    # Recálculo del histórico cada 5 segundos
    step=5./60./60.
    while self.t-self.hist_t>step:
      self.hist.pop(0)
      self.hist.append(s(self.hist[-1],p(r(self.pos,self.hist[-1]),step/(self.t-self.hist_t))))
      self.hist_t = self.hist_t+step
    return self.se_pinta
        
  def tas(h):
    #Devuelve TAS en función de la altitud      
    if h>250:
      return self.ias*(1+0.002*h)
    elif h<200:
      return min(self.ias,180+h)
    else:
      a0=ias*(1+0.002*250)
      a1=min(self.ias,180+200)
      return a0+(a1-a0)*(h-200)

  def set_initial_heading(self):
    self.pto = self.route[0][0] #Punto al que se dirige
    self.vect = rp(r(self.pto,self.pos))
    self.hdg = self.vect[1]
  
  def set_coords(self, (x0, y0)):
    self.x0 = x0
    self.y0 = y0
    
  def set_position(self,pos):
    self.pos=pos
    
  def set_callsign(self,name):
    self.name = name
    
  def set_kind(self,tipo):
    self.tipo = tipo
    
  def set_wake(self,wake):
    self.estela = wake
    
  def set_origin(self,ori):
    self.origen = ori
    
  def set_destination(self,dest):
    self.destino = dest
  
  def set_alt(self, alt):
    self.alt = alt
    
  def set_spd(self,spd):
    self.es_spd_std = False
    vel=float(spd)
    if vel<1.:
      vel = mach_tas(vel)
    ias_max=self.spd_max/(1+0.002*self.fl_max)
    tas_max=ias_max*(1+0.002*self.alt)
    if vel < tas_max:
      self.spd = vel
      return True
    else:
      self.spd = tas_max
      return False
  
  def set_std_spd(self):
    self.es_spd_std = True
  
  def set_cfl(self, alt):
    if alt <= self.fl_max:
      self.cfl = alt
      return True
    else:
      self.cfl = self.fl_max
      return False
    
  def set_pfl(self, alt):
    self.pfl = alt
    
  def set_rfl(self,rfl):
    self.rfl = rfl
    
  def set_heading(self, hdg):
    self.hold_hdg = hdg
    self.vfp = False
    
  def set_route(self,route):
    self.route = route
    self.vfp = True
    
  def set_initial_t(self,t):
    self.t = t
    
  def set_hist_t(self,t):
    self.hist_t = t
    
  def set_hist(self,hist):
    self.hist=hist
    
  def set_vfp(self,vfp):
    self.vfp = vfp
    
  def set_se_pinta(self,opci):
    self.se_pinta = opci
    
  def set_campo_eco(self,eco):
    self.campo_eco = eco
    
  def set_pac(self,canvas):
    canvas.itemconfigure(self.name+'lblrect',outline='orange')
    canvas.itemconfigure(self.name+'support',fill='orange')
    canvas.itemconfigure(self.name+'ind',fill='orange')
    
  def set_vac(self,canvas):
    canvas.itemconfigure(self.name+'lblrect',outline='red')
    canvas.itemconfigure(self.name+'support',fill='red')
    canvas.itemconfigure(self.name+'ind',fill='red')
    canvas.itemconfigure(self.name+'alt',fill='red')
    canvas.itemconfigure(self.name+'hdg',fill='red')
    canvas.itemconfigure(self.name+'spd',fill='red')
    canvas.itemconfigure(self.name+'wake',fill='red')
    canvas.itemconfigure(self.name+'eco',fill='red')
    
  def set_asumido(self):
    self.esta_asumido = not self.esta_asumido
    
  def get_asumido(self):
    return self.esta_asumido
       
  def get_callsign(self):
    return self.name
  
  def get_coords(self):
    return self.pos
  
  def get_cfl(self):
    return self.cfl
  
  def get_pfl(self):
    return self.pfl

  def get_origin(self):
      return self.origen
    
  def get_destination(self):
      return self.destino

  def get_kind(self):
      return self.tipo
    
  def get_alt(self):
    return self.alt
  
  def get_heading(self):
    return self.hdg
  
  def get_ias(self):
    return self.ias
  
  def set_ias(self, ias):
    self.ias = ias
    
  def set_rate_descend(self,rate):
    self.es_std=False
    if self.cfl>self.alt:
      self.rate = rate/100.*60.
      if self.rate <= self.rate_climb_max*f_vert(self):
        return True
      else:
        self.rate = self.rate_climb_max*f_vert(self)
        return False
    else:
      self.rate = -abs(rate/100.*60.)
      if abs(self.rate) <= self.rate_desc_max:
        return True
      else:
        self.rate = -self.rate_desc_max
        return False

  def set_std_rate(self):
    self.es_std = True
    if self.rate>0:
      self.rate = self.rate_climb_std * f_vert(self)
    else:
      self.rate = -self.rate_desc_std
  
  def get_rate_descend(self):
    return self.rate/60.*100.
    
  def get_speed(self):
    return self.spd
  
  def se_debe_imprimir(self,t):
    # Definimos cuánto tiempo antes nos sale la ficha y el tiempo de premanencia del mensaje
    prevision=10./60.
    permanece=2./60.
    if not self.ficha_imprimida and self.t_impresion-t<prevision:
      self.ficha_imprimida=True
      self.t_ficha=t
      return True
    elif t-self.t_ficha<permanece:
      return True
    else:
      return False
  
  def esta_seleccionado(self):
    if seleccionado == self:
      return True
    else:
      return False
    
  def kill_airplane(self,canvas):
      # Display window offering "Terminar" and "Cancel" options.
      global seleccionado
      if seleccionado<>self:
        return
      print 'Ventana kilear avión',self.name
      win = Frame(canvas)
      but_kill = Button(win, text="Terminar "+self.name)
      but_cancel = Button(win, text="Cancelar")
      but_kill.pack(side=TOP)
      but_cancel.pack(side=TOP)
      win_identifier = canvas.create_window(do_scale(self.pos), window=win)
      def close_win(ident=win_identifier):
              canvas.delete(ident)
      def kill_acft():
              global seleccionado
              self.t=self.t+10.
              self.hist_t=self.hist_t+10.
              seleccionado = None
              close_win()
      but_cancel['command'] = close_win
      but_kill['command'] = kill_acft
        
  def is_flying(self):
    return self.se_pinta

  def rotate_label(self, e=None):
#   	print "rotate_label 473"
	if e != None:
		self.last_lad = e.serial
	[x,y] = do_scale(self.pos)
        self.auto_separation = True
	self.label_heading += 45.0
        # Evitar soportes verticales
#         aux = self.label_heading % 360.
#         if aux < 20. or aux > 340. or (aux > 160. and aux < 200.):
#   	  self.label_heading += 45.0
	new_label_x = x + self.label_radius * sin(radians(self.label_heading))
	new_label_y = y + self.label_radius * cos(radians(self.label_heading))
        self.reposition_label(new_label_x, new_label_y)
  
  def counter_rotate_label(self, e=None):
  	print "counter rotate label 483"
	[x,y] = do_scale(self.pos)
        self.auto_separation = True
	self.label_heading -= 45.0
        # Evitar soportes verticales
#         aux = self.label_heading %360.
#         if aux < 20. or aux > 340. or (aux > 160. and aux < 200.):
#   	  self.label_heading -= 45.0
	new_label_x = x + self.label_radius * sin(radians(self.label_heading))
	new_label_y = y + self.label_radius * cos(radians(self.label_heading))
	self.reposition_label(new_label_x, new_label_y)

  def reposition_label(self, newx, newy):
        [x,y] = do_scale(self.pos)
#         new_label_x = newx - x
#         new_label_y = newy - y
#         support_x = new_label_x
#         support_y = new_label_y +10
        support_x = newx - x
        support_y = newy - y
        if support_x > 0.:  
          new_label_x = support_x
          new_label_y = support_y -10
        else:
          new_label_x = support_x - self.label_width
          new_label_y = support_y -10
        self.label_heading = 90.0-degrees(atan2(support_y, support_x))
        self.canvas.delete(self.name+'support')	
        if self.esta_asumido:
          size = 4
        else:
          size = 3
	xi = x + (size+1) * sin(radians(self.label_heading))
	yi = y + (size+1) * cos(radians(self.label_heading))
        if self.esta_asumido:
          color_avo='green'
        else:
          color_avo='gray'
        self.canvas.create_line(xi, yi, x + support_x, y + support_y, fill=color_avo, tags=self.name+'support')
 	self.canvas.tag_bind(self.name+'support', '<1>', self.rotate_label)
 	self.canvas.tag_bind(self.name+'support', '<3>', self.counter_rotate_label)
        self.canvas.move(self.name+'ind', new_label_x - self.label_x, new_label_y - self.label_y)
        self.canvas.move(self.name+'alt', new_label_x - self.label_x, new_label_y - self.label_y)
        self.canvas.move(self.name+'alt2', new_label_x - self.label_x, new_label_y - self.label_y)
        self.canvas.move(self.name+'hdg', new_label_x - self.label_x, new_label_y - self.label_y)
        self.canvas.move(self.name+'spd', new_label_x - self.label_x, new_label_y - self.label_y)
        self.canvas.move(self.name+'wake', new_label_x - self.label_x, new_label_y - self.label_y)
        self.canvas.move(self.name+'eco', new_label_x - self.label_x, new_label_y - self.label_y)
        self.canvas.move(self.name+'lblrect', new_label_x - self.label_x, new_label_y - self.label_y)
	self.label_x = new_label_x
	self.label_y = new_label_y
  
  def redraw(self, canvas):
      self.canvas = canvas
      color_normal_o_seleccionado = 'black'
      if seleccionado == self:
        color_normal_o_seleccionado = 'yellow'
      def show_hide_fpr(e=None,canvas=canvas):
        if e != None:
          self.last_lad = e.serial
        if canvas.itemcget(self.name+'fpr',"fill")=='orange':
          canvas.delete(self.name+'fpr')
        else:
          line=()
          if self.vfp:
            line=line+do_scale(self.pos)
          for a in self.route:
            pto=do_scale(a[0])
            canvas.create_text(pto,text=a[1],fill='orange',tag=self.name+'fpr',anchor=SE,font='-*-Helvetica-*--*-10-*-')
            canvas.create_text(pto,text=a[2],fill='orange',tag=self.name+'fpr',anchor=NE,font='-*-Helvetica-*--*-10-*-')
            line=line+pto
          if len(line)>3: canvas.create_line(line,fill='orange',tags=self.name+'fpr')

      def show_hide_way_point(e,canvas=canvas):
        global punto
        if canvas.itemcget(self.name+'wp',"fill")=='yellow':
          canvas.delete(self.name+'wp')
        else:
          canvas.delete(self.name+'fpr')
          canvas.delete(self.name+'wp')
          line=()
          if self.vfp:
            line=line+do_scale(self.pos)
          for a in self.route:
            pto=do_scale(a[0])
            canvas.create_text(pto,text=a[1],fill='yellow',tag=self.name+'wp',anchor=SE,font='-*-Helvetica-*--*-10-*-')
            canvas.create_text(pto,text=a[2],fill='yellow',tag=self.name+'wp',anchor=NE,font='-*-Helvetica-*--*-10-*-')
            line=line+pto
          if len(line)>3: canvas.create_line(line,fill='yellow',tags=self.name+'wp')
          size=2
          for a in self.route:
            (rect_x, rect_y) = do_scale(a[0])
            point_ident = canvas.create_rectangle(rect_x-size, rect_y-size, rect_x+size, rect_y+size,fill='yellow',outline='yellow',tags=self.name+'wp')
            def clicked_on_waypoint(e, point_coord=a[0],point_name=a[1]):
                # Display window offering "Direct to..." and "Cancel" options.
                global punto
                self.last_lad = e.serial
                win = Frame(canvas)
                id_avo = Label(win,text=self.name)
                id_avo.pack(side=TOP)                
                id_pto = Entry (win,width=8)
                id_pto.insert(0,point_name)
                id_pto.pack(side=TOP)
                but_direct = Button(win, text="Dar directo")
                but_cancel = Button(win, text="Cancelar")
                but_direct.pack(side=TOP)
                but_cancel.pack(side=TOP)
                win_identifier = canvas.create_window(e.x, e.y, window=win)
                def close_win(ident=win_identifier):
                        canvas.delete(ident)
                def direct_to():
                        global punto
                        pto=id_pto.get()
                        # Caso de dar directo al punto seleccionado
                        if pto == point_name:
                          print "Selected plane should fly direct to point", point_coord
                          for i in range(len(self.route)):
                            if point_coord==self.route[i][0]:
                              aux=self.route[i:]
                          self.set_route(aux)
                          close_win()
                          canvas.delete(self.name+'wp')
                          #show_hide_fpr("")
                        else:
                          aux = None
                          # Si es un punto intermedio de la ruta, lo detecta
                          for i in range(len(self.route)):
                            if self.route[i][1] == pto.upper():
                              aux = self.route[i:]
                          # Si no está en la ruta, insertamos el punto como nº 1
                          if aux == None:
                            for [nombre,coord] in punto:
                              if nombre == pto.upper():
                                aux = [[coord,nombre,'']]
                                print "Selected plane should fly direct to point", nombre,coord
                                for a in self.route:
                                  aux.append(a)
                          # Si no encuentra el punto, fondo en rojo y no hace nada
                          if aux == None:
                            id_pto.config(bg='red')
                            print 'Punto ',pto.upper(),' no encontrado'
                          else:
                            self.set_route(aux)
                            close_win()
                            canvas.delete(self.name+'wp')
                            show_hide_fpr()
                but_cancel['command'] = close_win
                but_direct['command'] = direct_to
            canvas.tag_bind(point_ident, "<1>", clicked_on_waypoint)

      # Remove previous items
      canvas.delete(self.name+'plot')
      canvas.delete(self.name+'ind')
      canvas.delete(self.name+'alt')
      canvas.delete(self.name+'alt2')
      canvas.delete(self.name+'hdg')
      canvas.delete(self.name+'spd')
      canvas.delete(self.name+'wake')
      canvas.delete(self.name+'eco')
      canvas.delete(self.name+'support')
      canvas.delete(self.name+'lblrect')
      canvas.delete(self.name+'speedvector')
      canvas.delete(self.name+'hist')
      if canvas.itemcget(self.name+'fpr',"fill")=='orange':
        canvas.delete(self.name+'fpr')
        show_hide_fpr(None)
      if canvas.itemcget(self.name+'wp',"fill")=='yellow':
        canvas.delete(self.name+'wp')
        show_hide_way_point(None)
      
      if not self.se_pinta:
        return
      
      if self.esta_asumido:
        color_avo='green'
      else:
        color_avo='gray'
      [x0,y0]=do_scale(self.pos)
      # Display updated items
      # Plot
      if self.esta_asumido:
        size = 4
        self.plotid = canvas.create_line(x0-size,y0,x0,y0-size,x0+size,y0,x0,y0+size,x0-size,y0,fill=color_avo,tags='plot')
      else:
        size = 3
        self.plotid = canvas.create_line(x0-size,y0-size,x0-size,y0+size,x0+size,y0+size,x0+size,y0-size,x0-size,y0-size,fill=color_avo,tags='plot')
      canvas.addtag_withtag(self.name+'plot', self.plotid)
     
      # Plot history
      for h in self.hist:
        aux=do_scale(h)
        h0=aux[0]
        h1=aux[1]
        canvas.create_rectangle(h0,h1,h0+1,h1+1,outline=color_avo,tags=self.name+'hist')
      # Label
      # Speed string
      if self.see_mach:
        spd_text='.'+str(int(round(mach(self)*100)))
      else:
        spd_text = str(int(self.spd/10))
      wake_text = self.estela+' '
      wake_desp = label_font.measure(spd_text)
      if self.estela=='H':
        wake_colour='yellow'
      else:
        wake_colour='green'
      if not self.esta_asumido:
        wake_colour=color_avo
      eco_text = self.campo_eco
      eco_desp = label_font.measure(spd_text+wake_text)
      # Heading string
      hdg_text='%03d'%(int(self.hdg))
      # Altitude text
      alt_txt='%03d'%(int(self.alt))
      if self.cfl-self.alt>2.:
        alt_txt2=chr(94)+'%03d'%(int(self.cfl))
      elif self.cfl-self.alt<-3.:
        alt_txt2=chr(118)+'%03d'%(int(self.cfl))
      else:
        alt_txt2 = ''
      alt_desp = label_font.measure(alt_txt)
      # Label definition
      min_label_width = 20 # Minimum label width
      if sys.platform.startswith('linux'):
        aj = 0
      else:
        aj = 1
      label_width = max(min_label_width, label_font.measure(self.name) + 4,label_font.measure(alt_txt+alt_txt2),label_font.measure(spd_text+wake_text+eco_text) + 4)
      label_height = 4 * (label_font_size+aj) + 4
      self.label_width = label_width
      self.label_height = label_height
#       support_x0 = x0 + self.label_x
#       support_y0 = y0 + self.label_y
#       if (self.label_x > 0):
#       	label_x0 = support_x0
# 	label_y0 = support_y0 - 10
#       else:
#       	label_x0 = support_x0 - label_width
# 	label_y0 = support_y0 - 10
      label_x0 = x0 + self.label_x
      label_y0 = y0 + self.label_y
      if (self.label_x > 0):
      	support_x0 = label_x0
	support_y0 = label_y0 + 10
      else:
      	support_x0 = label_x0 + label_width
	support_y0 = label_y0 + 10
      self.reposition_label(support_x0, support_y0)
      canvas.tag_bind(self.name+'support', '<1>', self.rotate_label)
      canvas.tag_bind(self.name+'support', '<3>', self.counter_rotate_label)
      if color_normal_o_seleccionado=='yellow':
        canvas.create_rectangle(label_x0, label_y0, label_x0 + label_width, label_y0 + label_height, outline=color_normal_o_seleccionado, tags=self.name+'lblrect')
      txt_ident = canvas.create_text(label_x0+2, label_y0+2,text=self.name,fill=color_avo,tag=self.name+'ind',anchor=NW,font=label_font)
      alt_identifier = canvas.create_text(label_x0+2, label_y0+(label_font_size+aj)+2, text=alt_txt, fill=color_avo, tag=self.name+'alt', anchor=NW, font=label_font)
      alt_identifier2 = canvas.create_text(label_x0+alt_desp+2, label_y0+(label_font_size+aj)+2, text=alt_txt2, fill=color_avo, tag=self.name+'alt2', anchor=NW, font=label_font)
      hdg_identifier = canvas.create_text(label_x0+2, label_y0+2*(label_font_size+aj)+2, text=hdg_text, fill=color_avo, tag=self.name+'hdg', anchor=NW, font=label_font)
      spd_identifier = canvas.create_text(label_x0+2, label_y0+3*(label_font_size+aj)+2, text=spd_text, fill=color_avo, tag=self.name+'spd', anchor=NW, font=label_font)
      wake_identifier = canvas.create_text(label_x0+wake_desp+2, label_y0+3*(label_font_size+aj)+2, text=wake_text, fill=wake_colour, tag=self.name+'wake', anchor=NW, font=label_font)
      eco_identifier = canvas.create_text(label_x0+eco_desp+2, label_y0+3*(label_font_size+aj)+2, text=eco_text, fill=color_avo, tag=self.name+'eco', anchor=NW, font=label_font)
      def txt_moved(e):
      	self.reposition_label(e.x, e.y)
      def txt_released(e):
        canvas.tag_unbind(txt_ident, "<Motion>")
        canvas.tag_unbind(txt_ident, "<ButtonRelease-2>")
        canvas.tag_bind(txt_ident, '<ButtonRelease-2>', seleccionar)
      def txt_clicked(e):
        self.last_lad = e.serial
        self.auto_separation = False
        canvas.tag_bind(txt_ident, "<Motion>", txt_moved)
        canvas.tag_bind(txt_ident, "<ButtonRelease-2>", txt_released)
        canvas.tag_bind(txt_ident, '<ButtonRelease-2>', seleccionar)
      canvas.tag_bind(txt_ident, "<Button-2>", txt_clicked)
      def asumir_vuelo(e):
        self.last_lad = e.serial
        self.set_asumido()
        print 'Cambiando estado vuelo ',self.name
        self.redraw(canvas)
      canvas.tag_bind(txt_ident,"<Button-1>",asumir_vuelo)
      def cambio_mach(e):
        self.last_lad = e.serial
        self.see_mach = not self.see_mach
        self.redraw(canvas)
      canvas.tag_bind(self.name+'spd', '<Button-2>',cambio_mach)
      
      def seleccionar(e):
        global seleccionado
        if seleccionado == self:
          # Se ha pinchado sobre el ya seleccionado: deseleccionar
          seleccionado = None
          self.redraw(canvas)
          return
	anterior_seleccionado = seleccionado
	seleccionado = self
	if anterior_seleccionado != None:
	  anterior_seleccionado.redraw(canvas)
	self.redraw(canvas)
      canvas.tag_bind(self.plotid, '<Button-1>', show_hide_fpr)
      canvas.tag_bind(txt_ident, '<ButtonRelease-2>', seleccionar)
      min_label_width = 80 # Minimum label width

#       def cursor_box(e=None):
#         canvas.configure(cursor="draped_box")
#       def cursor_normal(e=None):
#         canvas.configure(cursor="arrow")
#       canvas.tag_bind(self.plotid, '<Enter>', cursor_box)
#       canvas.tag_bind(self.plotid, '<Leave>', cursor_normal)

      def change_altitude(e):
        self.last_lad = e.serial
      	win = Frame(canvas)
	lbl_CFL = Label(win, text="CFL:")
	ent_CFL = Entry(win, width=3)
	ent_CFL.insert(0, str(int(self.get_cfl())))
	lbl_PFL = Label(win, text="PFL:")
	ent_PFL = Entry(win, width=3)
	ent_PFL.insert(0, str(int(self.get_pfl())))
	but_Comm = Button(win, text="Comunicar")
	but_Acp = Button(win, text="Aceptar")
	but_Can = Button(win, text="Cancelar")
	lbl_CFL.grid(row=0, column=0)
	ent_CFL.grid(row=0, column=1)
	lbl_PFL.grid(row=1, column=0)
	ent_PFL.grid(row=1, column=1)
	but_Comm.grid(row=2, column=0, columnspan=2)
	but_Acp.grid(row=3, column=0, columnspan=2,)
	but_Can.grid(row=4, column=0, columnspan=2)
	window_ident = canvas.create_window(e.x, e.y, window=win)
	def close_win(e=None, ident=window_ident, w=canvas):
                w.unbind_all("<Return>")
                w.unbind_all("<KP_Enter>")
                w.unbind_all("<Escape>")
		canvas.delete(ident)
	def set_FLs(e=None):
		cfl = ent_CFL.get()
		pfl = ent_PFL.get()
		print "New CFL:", cfl
		print "New PFL:", pfl
		self.set_pfl(int(pfl))
		flag = self.set_cfl(int(cfl))
		if flag:
                  close_win()
                else:
                  ent_CFL.delete(0,END)
                  ent_CFL.insert(0, str(abs(int(self.get_cfl()))))
	          ent_CFL['bg'] = 'red'                 
	def comm():
		cfl=pfl=ent_PFL.get()
		print "New CFL=New PFL:", cfl
		self.set_pfl(int(pfl))
		flag = self.set_cfl(int(cfl))
		if flag:
                  close_win()
                else:
                  ent_CFL.delete(0,END)
                  ent_CFL.insert(0, str(abs(int(self.get_cfl()))))
	          ent_CFL['bg'] = 'red'                 
	but_Comm['command'] = comm
	but_Acp['command'] = set_FLs
	but_Can['command'] = close_win
        canvas.bind_all("<Return>",set_FLs)
        canvas.bind_all("<KP_Enter>",set_FLs)
        canvas.bind_all("<Escape>",close_win)
      canvas.tag_bind(alt_identifier, "<1>", change_altitude)
      def change_rate(e):
        self.last_lad = e.serial
      	win = Frame(canvas)
	lbl_hdg = Label(win, text="Rate:")
	ent_hdg = Entry(win, width=4)
	ent_hdg.insert(0, str(abs(int(self.get_rate_descend()))))
	but_Acp = Button(win, text="Aceptar")
	but_Can = Button(win, text="Cancelar")
	but_Std = Button(win,text="Estandar")
	lbl_hdg.grid(row=0, column=0)
	ent_hdg.grid(row=0, column=1)
	but_Acp.grid(row=1, column=0, columnspan=2)
	but_Can.grid(row=2, column=0, columnspan=2)
	but_Std.grid(row=3, column=0, columnspan=2)
	window_ident = canvas.create_window(e.x, e.y, window=win)
	def close_win(e=None,ident=window_ident,w=canvas):
                w.unbind_all("<Return>")
                w.unbind_all("<KP_Enter>")
                w.unbind_all("<Escape>")
		canvas.delete(ident)
	def set_rate(e=None):
		hdg = ent_hdg.get()
		print "New rate:", hdg
		flag = self.set_rate_descend(int(hdg))
                if flag:
		  close_win()
                else:
                  ent_hdg.delete(0,END)
                  ent_hdg.insert(0, str(abs(int(self.get_rate_descend()))))
	          ent_hdg['bg'] = 'red'
	def set_std():
                print "Standard rate:"
                self.set_std_rate()
                close_win()
	but_Acp['command'] = set_rate
	but_Can['command'] = close_win
	but_Std['command'] = set_std
        canvas.bind_all("<Return>",set_rate)
        canvas.bind_all("<KP_Enter>",set_rate)
        canvas.bind_all("<Escape>",close_win)
      canvas.tag_bind(alt_identifier2, "<1>", change_rate)
      def change_heading(e):
        self.last_lad = e.serial
      	win = Frame(canvas)
	lbl_hdg = Label(win, text="Heading:")
	ent_hdg = Entry(win, width=3)
	ent_hdg.insert(0, str(int(self.get_heading())))
	but_Acp = Button(win, text="Aceptar")
	but_Can = Button(win, text="Cancelar")
	lbl_hdg.grid(row=0, column=0)
	ent_hdg.grid(row=0, column=1)
	but_Acp.grid(row=1, column=0, columnspan=2)
	but_Can.grid(row=2, column=0, columnspan=2)
	window_ident = canvas.create_window(e.x, e.y, window=win)
	def close_win(e=None,ident=window_ident,w=canvas):
                w.unbind_all("<Return>")
                w.unbind_all("<KP_Enter>")
                w.unbind_all("<Escape>")
		canvas.delete(ident)
	def set_heading(e=None):
		hdg = ent_hdg.get()
		print "New heading:", hdg
		self.set_heading(int(hdg))
		close_win()
	but_Acp['command'] = set_heading
	but_Can['command'] = close_win
        canvas.bind_all("<Return>",set_heading)
        canvas.bind_all("<KP_Enter>",set_heading)
        canvas.bind_all("<Escape>",close_win)
      canvas.tag_bind(hdg_identifier, "<1>", change_heading)
      def change_speed(e):
        self.last_lad = e.serial
      	win = Frame(canvas)
	lbl_spd = Label(win, text="IAS:")
	ent_spd = Entry(win, width=3)
	ent_spd.insert(0, str(int(self.get_speed())))
	but_Acp = Button(win, text="Aceptar")
	but_Can = Button(win, text="Cancelar")
	but_Std = Button(win, text="Estandar")
	lbl_spd.grid(row=0, column=0)
	ent_spd.grid(row=0, column=1)
	but_Acp.grid(row=1, column=0, columnspan=2)
	but_Can.grid(row=2, column=0, columnspan=2)
	but_Std.grid(row=3, column=0, columnspan=2)
	window_ident = canvas.create_window(e.x, e.y, window=win)
	def close_win(e=None,ident=window_ident,w=canvas):
                w.unbind_all("<Return>")
                w.unbind_all("<KP_Enter>")
                w.unbind_all("<Escape>")
		canvas.delete(ident)
	def set_speed(e=None):
		spd = ent_spd.get()
		print "New speed:", spd
		flag = self.set_spd(spd)
                if flag:
		  close_win()
                else:
                  ent_spd.delete(0,END)
                  ent_spd.insert(0, str(abs(int(self.get_speed()))))
	          ent_spd['bg'] = 'red'
	def set_std():
                self.set_std_spd()
                print "Standard speed"
                close_win()
	but_Acp['command'] = set_speed
	but_Can['command'] = close_win
	but_Std['command'] = set_std
        canvas.bind_all("<Return>",set_speed)
        canvas.bind_all("<KP_Enter>",set_speed)
        canvas.bind_all("<Escape>",close_win)
      canvas.tag_bind(spd_identifier, "<1>", change_speed)
      canvas.tag_bind(self.plotid, "<Button-1>", show_hide_fpr)
      canvas.tag_bind(self.name+'eco', "<Button-3>",show_hide_way_point)

      # Speed vector
      speed_pos = s(self.pos,pr((speed_time * self.spd,self.hdg)))
      aux=do_scale(speed_pos)
      speed_x0=aux[0]
      speed_y0=aux[1]
      canvas.create_line(x0, y0, speed_x0, speed_y0, fill=color_avo, tags=self.name+'speedvector')
            
def dist_t(a,b,t):
  # Distancia entre dos objetos a la hora t
  pos_a_t=s(a.pos,pr(((t-a.t)*a.spd,a.hdg)))
  pos_b_t=s(b.pos,pr(((t-b.t)*b.spd,b.hdg)))
  return rp(r(pos_a_t,pos_b_t))[0]
 
def vac(a,b):
  # Comprueba si es una violación de la separación
  if not a.is_flying() or not b.is_flying():
    return False
  minsep=7.9  #MINIMA DE SEPARACIÓN HORIZONTAL
  minvert=9.00 #MINIMA DE SEPARACIÓN VERTICAL
  t=max(a.t,b.t)
  if dist_t(a,b,t)<minsep and abs(a.alt-b.alt)<minvert:
    return True
  else:
    return False
  
def pac(a,b):
  # Aviso de pérdida de separación
  if not a.is_flying() or not b.is_flying():
    return False
  aviso=1.0/60.  # PARÁMETRO DE TIEMPO EN EL CUAL SE PREVÉ QUE HAY VAC (1 min)
  minsep=7.9 # MINIMA DE SEPARACIÓN HORIZONTAL
  if a.rate==0. and b.rate==0:
    minvert=9.00
  else:
    minvert=14.00
  t=max(a.t,b.t) #Tiempo actual
  svert=a.alt+aviso*a.rate
  for i in range(1,2):
    if dist_t(a,b,t+aviso*i/2)<minsep and abs(a.alt+aviso*a.rate*i/2-b.alt-aviso*b.rate*i/2)<minvert:
      return True
  return False
