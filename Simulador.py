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

def set_latest_lad(num):
  global latest_lad_event_processed
  print 'Set_latest_lad llamado. Antes despues', latest_lad_event_processed,num
  latest_lad_event_processed = num

  
# Modules to be imported  
from avion import *
from RaDisplay import *
from tpv import *
from Tix import *
import Image
import ImageTk
Image._initialized=2
from time import time,sleep
import lads
from math import sqrt
import os.path

# Global variables
global wind
punto = []
ejercicio = []
rutas = []
limites = []
tmas = []
deltas = []
local_maps = {}
h_inicio=1.
wind = [0.0,0.0]
aeropuertos = []
esperas_publicadas = []
rwys = []
sids = []
stars = []
procedimientos = {}
proc_app = {}
auto_departures = True
min_sep = 8.0
reloj_funciona = False
listado_salidas = {}

superlad = None
win_manual = None
win_datos = None
vent_ident_dcha = None
vent_ident_maps = None
vent_ident_procs = None
vent_ident_mapas = None

# Constants
IMGDIR='./img/'
CRUJISIMICO=IMGDIR+'crujisim.ico'
SNDDIR='./snd/'

# Start loading data
[punto,ejercicio,rutas,limites,deltas,tmas,local_maps,h_inicio,wind,aeropuertos,esperas_publicadas,rwys,procedimientos,proc_app,rwyInUse,auto_departures,min_sep] = tpv()

set_global_vars(punto, wind, aeropuertos, esperas_publicadas,rwys,rwyInUse,procedimientos, proc_app,min_sep)
# Plot size
size=2

root=Tk()
if sys.platform.startswith('win'):
	root.wm_iconbitmap(CRUJISIMICO)
	root.wm_state('zoomed')
root.wm_title('Crujisim - '+os.path.basename(g_seleccion_usuario[2][1]))  # Display exercise name in window title

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.wm_geometry("%dx%d+%d+%d" % (screen_width, screen_height, 0, 0))

var_vect_vel = IntVar()
var_vect_vel.set(0)
var_vel_reloj = DoubleVar()
var_vel_reloj.set(1.0)

x0=0.
y0=0.
scale=1.0
ancho=root.winfo_screenwidth()
alto=root.winfo_screenheight()*0.90
altura_barra_inferior = 60
centro_x=ancho/2
centro_y=(alto-altura_barra_inferior)/2
nombre_fijos = True
var_ver_ptos = IntVar()
var_ver_ptos.set(1)
ver_tmas = False
var_ver_tmas = IntVar()
var_ver_tmas.set(0)
ver_deltas = False
var_ver_deltas = IntVar()
var_ver_deltas.set(0)
auto_sep = True
var_auto_sep = IntVar()
var_auto_sep.set(1)

local_maps_shown = []
var_ver_localmap = {}
for map_name in local_maps:
	var_ver_localmap[map_name] = IntVar()
	var_ver_localmap[map_name].set(0)

w=Canvas(root,bg='black')
w.pack(expand=1,fill=BOTH)
root.update_idletasks()

ancho=root.winfo_width()
alto=root.winfo_height()
altura_barra_inferior = 60
centro_x=ancho/2
centro_y=(alto-altura_barra_inferior)/2

radius = 30
label_font_size = 11
label_font = tkFont.Font(family="Helvetica",size=label_font_size)
set_label_font(label_font)
set_label_font_size(label_font_size)


# Definición de LAD's en el canvas
class fix_point:
  def __init__(self,coord):
    self.pos = coord
    
  def get_track(self):
    return 0.01
  
  def get_coords(self):
    return self.pos
  
  def get_ground_speed(self):
    return 0.01
  
def get_acft_or_point(x,y):
  # Returns the closest acft to (x,y) or otherwise a point
  esta_cerca = 8.
  mas_cercano = None
  for avo in ejercicio:
    if avo.is_flying():
      (x0,y0) = do_scale(avo.get_coords())
      dist = ((x - x0)**2 + (y - y0)**2)**0.5
      if dist < esta_cerca:
        mas_cercano = avo
        esta_cerca = dist
  if mas_cercano == None:
    mas_cercano = fix_point(coord = undo_scale((x,y)))
  return mas_cercano
  
def crea_lad(origen, destino):
	nuevo_lad = lads.LAD(origen, destino)
	all_lads.append(nuevo_lad)
  
def cancel_def_lad(e, canvas = w):
  global definiendo_lad, latest_lad_event_processed
  if e.serial == latest_lad_event_processed:
      return
  latest_lad_event_processed = e.serial
  # Cancelar creación de un LAD
  global definiendo_lad
  if definiendo_lad == 0:
    # No se estaba definiendo un LAD. Ignorar evento
    return
  elif definiendo_lad == 1:
    # Se estaba definiendo un LAD. Cancelar definición.
    canvas.delete('lad_defined')
    canvas.unbind('<Motion>')
    canvas.delete('lad_defined')
    canvas.unbind('<Button-2>')
    canvas.bind('<Button-2>', def_lad)
    definiendo_lad = 0

def def_lad(e, canvas = w):
  global definiendo_lad, lad_origen, latest_lad_event_processed
#   print 'Definiendo LAD. Actual, anterior',e.serial,latest_lad_event_processed
  # actualizar latest_lad_event
  for avo in ejercicio:
    if avo.last_lad>latest_lad_event_processed: latest_lad_event_processed = avo.last_lad
  if e.serial == latest_lad_event_processed:
      return
  latest_lad_event_processed = e.serial
  if definiendo_lad == 0:
    # No se estaba definiendo un LAD. Comenzar a definir uno
    lad_origen = get_acft_or_point(e.x,e.y)
    definiendo_lad = 1
    def update_lad_being_defined(e=None):
          canvas.delete('lad_defined')
          (x0, y0) = do_scale(lad_origen.pos)
          dest = undo_scale((e.x, e.y))
          lad_xsize = dest[0] - lad_origen.pos[0]
          lad_ysize = dest[1] - lad_origen.pos[1]
          angulo = 90.0 - degrees( atan2( lad_ysize, lad_xsize ) )
          if angulo < 0.0: angulo += 360.0
          dist = sqrt( lad_xsize * lad_xsize + lad_ysize * lad_ysize)
          time_min = 60.0 * dist / lad_origen.get_ground_speed()
          lad_center_x = (x0 + e.x)/2
          lad_center_y = (y0 + e.y)/2
          canvas.create_line(x0, y0,e.x, e.y, fill="orange", tags="lad_defined")
          lad_text1 = "A: %03d" % angulo
          lad_text2 = "D: %03d" % dist
	  # Check if LAD begins in a point or in a plane
          if lad_origen.get_ground_speed() < 10.:
            lad_text3 = ""
	    lad_lines = 2  # LAD will show 2 lines with information (Azimuth, Distance)
          else:
            lad_text3 = "T: %03d" % time_min
	    lad_lines = 3  # LAD will show 3 lines with information (Azimuth, Distance and Time to reach)
          lad_rect_width = label_font.measure(lad_text1)
#          lad_rect_width = max(label_font.measure(self.name) + 4,label_font.measure(spd_text+wake_text+eco_text) + 4)
          lad_line_height = label_font.metrics('linespace')
          canvas.create_text(lad_center_x, lad_center_y - lad_lines * lad_line_height, text=lad_text1, fill="orange", tags="lad_defined")
          canvas.create_text(lad_center_x, lad_center_y - (lad_lines-1) * lad_line_height , text=lad_text2, fill="orange", tags="lad_defined")
          canvas.create_text(lad_center_x, lad_center_y - (lad_lines-2) * lad_line_height, text=lad_text3, fill="orange", tags="lad_defined")
          canvas.tag_lower('lad_defined', 'plot')
    canvas.bind('<Motion>', update_lad_being_defined)
    canvas.bind('<Button-2>', cancel_def_lad)

def end_def_lad(e, canvas = w):
  # Fin de creación de un LAD con destino un AVO
  global definiendo_lad, lad_origen
  if definiendo_lad == 0:
    # No se estaba definiendo un LAD. Ignorar evento
    return
  elif definiendo_lad == 1:
    # Se estaba definiendo un LAD. Terminar definición...
#     # ... salvo que se haya tirado un LAD entre un avión y él mismo!
#     if lad_origen == self:
#           print "LAD entre un avión y él mismo. Ignorando..."
#           return
    canvas.delete('lad_defined')
    canvas.unbind('<Motion>')
    definiendo_lad = 0
    crea_lad(origen=lad_origen, destino=get_acft_or_point(e.x,e.y))
    canvas.unbind('<Button-2>')
    canvas.bind('<Button-2>', def_lad)
    

w.bind('<Button-2>', def_lad)
w.bind('<Button-3>', end_def_lad)

# Tratamiento del botón izquierdo con el plan de vuelo sobre el plot
def see_hide_fpr(e, canvas = w):
  global latest_lad_event_processed
#   print 'Definiendo ruta. Actual, anterior',e.serial,latest_lad_event_processed
  # actualizar latest_lad_event
  for avo in ejercicio:
    if avo.last_lad>latest_lad_event_processed: latest_lad_event_processed = avo.last_lad
  if e.serial == latest_lad_event_processed:
      return
  latest_lad_event_processed = e.serial
  # Encontramos la aeronave a la que nos referimos
  acft = get_acft_or_point(e.x,e.y)
  print 'Datos acft or point', acft.get_ground_speed(), acft.get_track()
  # En caso de ser un punto, anulamos
  if acft.get_ground_speed()<50.:
    return
  else:
    # Copia del código en avion.py
    if canvas.itemcget(acft.name+'fpr',"fill")=='orange':
      canvas.delete(acft.name+'fpr')
    else:
      line=()
      if acft.vfp:
        line=line+do_scale(acft.pos)
      for a in acft.route:
        pto=do_scale(a[0])
        if a[1][0] <> '_' or a[1] in proc_app.keys():
          canvas.create_text(pto,text=a[1],fill='orange',tag=acft.name+'fpr',anchor=SE,font='-*-Helvetica-*--*-10-*-')
          canvas.create_text(pto,text=a[2],fill='orange',tag=acft.name+'fpr',anchor=NE,font='-*-Helvetica-*--*-10-*-')
        line=line+pto
      if len(line)>3: canvas.create_line(line,fill='orange',tags=acft.name+'fpr')
    
w.bind('<Button-1>', see_hide_fpr)

def draw_all_lads(canvas):
	global superlad, all_lads
	canvas.delete('crosspoint')
	for lad in all_lads:
		if lad.line_id != None: canvas.delete(lad.line_id)
		if lad.text_id1 != None: canvas.delete(lad.text_id1)
		if lad.text_id2 != None: canvas.delete(lad.text_id2)
		if lad.text_id3 != None: canvas.delete(lad.text_id3)
		if lad.text_id4 != None: canvas.delete(lad.text_id4)
		(xinitA, yinitA) = lad.origin.get_coords()
		(xinitB, yinitB) = lad.destination.get_coords()
		lad_xdif = xinitB - xinitA
		lad_ydif = yinitB - yinitA
		current_azimuth = 90.0 - degrees( atan2 (lad_ydif, lad_xdif) )
		if current_azimuth < 0.0: current_azimuth += 360.0
		lad_lines = 2 # 2 lines of text if planes won't cross; 4 if they will cross
		text1 = "A: %03d" % current_azimuth
		current_distance = sqrt(lad_xdif*lad_xdif + lad_ydif*lad_ydif)
		text2 = "D: %.1f" % current_distance
		(x0, y0) = do_scale((xinitA, yinitA))
		(x1, y1) = do_scale((xinitB, yinitB))
		if lad == superlad:
			color = 'red'
		else:
			color = 'orange'
		lad.line_id = canvas.create_line(x0, y0, x1, y1, fill=color, tags="lad")
		xm = (x0+x1) / 2
		ym = (y0+y1) / 2
		min_dist_time = lads.compute_mindisttime(xinitA, yinitA, lad.origin.get_track(), lad.origin.get_ground_speed(), xinitB, yinitB, lad.destination.get_track(), lad.destination.get_ground_speed())
		if (min_dist_time != None) and (min_dist_time > 0.0):
			# Flights will cross
			min_dist = lads.compute_mindist(xinitA, yinitA, lad.origin.get_track(), lad.origin.get_ground_speed(), xinitB, yinitB, lad.destination.get_track(), lad.destination.get_ground_speed())
			lad_lines = 4 # 4 lines of text in LAD square
			text3 = "T: %d" % min_dist_time
			text4 = "C: %.1f" % min_dist
		lad_line_height = label_font.metrics('linespace')
		lad.text_id1 = canvas.create_text(xm, ym - lad_lines * lad_line_height,     text=text1, fill="orange", tags="lad_text")
		lad.text_id2 = canvas.create_text(xm, ym - (lad_lines-1) * lad_line_height, text=text2, fill="orange", tags="lad_text")
		if lad_lines == 4:
			lad.text_id3 = canvas.create_text(xm, ym - (lad_lines-2) * lad_line_height, text=text3, fill="orange", tags="lad_text")
			lad.text_id4 = canvas.create_text(xm, ym - (lad_lines-3) * lad_line_height, text=text4, fill="orange", tags="lad_text")
		def set_superlad(e=None, new_superlad = lad):
			global superlad
			if superlad == new_superlad:
				# The selected LAD is already superlad. Set as normal LAD.
				superlad = None
			else:
				superlad = new_superlad
		canvas.tag_bind(lad.text_id1, '<1>', set_superlad)
		canvas.tag_bind(lad.text_id2, '<1>', set_superlad)
		if lad_lines == 4:
			canvas.tag_bind(lad.text_id3, '<1>', set_superlad)
			canvas.tag_bind(lad.text_id4, '<1>', set_superlad)
		def remove_lad(e=None, lad_to_remove = lad):
			global all_lads, superlad,latest_lad_event_processed
                        latest_lad_event_processed = e.serial
			if lad_to_remove.line_id != None: canvas.delete(lad_to_remove.line_id)
			if lad_to_remove.text_id1 != None: canvas.delete(lad_to_remove.text_id1)
			if lad_to_remove.text_id2 != None: canvas.delete(lad_to_remove.text_id2)
			if lad_to_remove.text_id3 != None: canvas.delete(lad_to_remove.text_id3)
			if lad_to_remove.text_id4 != None: canvas.delete(lad_to_remove.text_id4)
			all_lads.remove(lad_to_remove)
			lad_to_remove.destroy()
			if superlad == lad_to_remove: superlad = None
		canvas.tag_bind(lad.text_id1, '<2>', remove_lad)
		canvas.tag_bind(lad.text_id2, '<2>', remove_lad)
		if lad_lines == 4:
			canvas.tag_bind(lad.text_id3, '<2>', remove_lad)
			canvas.tag_bind(lad.text_id4, '<2>', remove_lad)
		if (superlad == lad) and (min_dist_time != None) and (min_dist_time > 0.0):
			# Flights will cross
			(posAx, posAy, posBx, posBy) = lads.compute_cross_points(xinitA, yinitA, lad.origin.get_track(), lad.origin.get_ground_speed(), xinitB, yinitB, lad.destination.get_track(), lad.destination.get_ground_speed())
			(crossAx, crossAy) = do_scale((posAx, posAy))
			(crossBx, crossBy) = do_scale((posBx, posBy))
			canvas.create_line(x0, y0, crossAx, crossAy, fill='red', tags="crosspoint")
			canvas.create_rectangle(crossAx-size, crossAy-size, crossAx +size, crossAy +size, fill='red', tags="crosspoint")
			canvas.create_line(x1, y1, crossBx, crossBy, fill='red', tags="crosspoint")
			canvas.create_rectangle(crossBx - size, crossBy -size, crossBx + size, crossBy + size, fill='red', tags="crosspoint")
			canvas.tag_lower("crosspoint", "plot")
			canvas.tag_lower("crosspoint", "lad")
	canvas.tag_lower('lad', 'plot')

def draw_print_list():
  n=1
  for a in ejercicio:
    if a.se_debe_imprimir(last_update/60./60.):
      if not auto_departures and a.origen in rwys.keys():
        if a.origen in listado_salidas.keys():
          aux = listado_salidas[a.origen]
        else:
          aux = {}
          listado_salidas[a.origen]=aux
        if a.get_callsign() in listado_salidas[a.origen].keys():
          pass
        else:
          ho=int(a.t)
          m=int(a.t*60.)-ho*60.
          s=int(a.t*60.*60.)-60.*60.*ho-60.*m
          etd = '%02d:%02d:%02d' % (ho, m, s)
          a.t +=  100.
          a.t_ficha -= 100.
          (sid,star) = procedimientos[rwyInUse[a.origen]]
          sid_auto = ''
          for i in range(len(a.route)):
            [(x,y),fijo,hora,auxeto] = a.route[i]
            if fijo in sid.keys():
              sid_auto = sid[fijo][0]
              break
          if sid_auto == '':
            print 'No hay SID',a.get_callsign()
            print 'RUTA: ',a.route
            print 'SIDs',sid.keys()
          aux[a.get_callsign()] = (etd,sid_auto)
          listado_salidas[a.origen] = aux
          manual_dep_window(last_update/60./60.)
          # listado_salidas = {{'LEBB',{'IB4148';('10:18:15','NORTA1A'),'BAW317':('10:23:15','ROKIS1B'),...}
      else:
        w.create_text(ancho-10,n*13,text=a.get_callsign(),fill='yellow',tag='fichas',anchor=NE,font='-*-Helvetica-*--*-12-*-')
        print_fs(a.get_callsign()) # Play the printing sound if necessary
        n=n+1


palote_identifier=None
images = {}
def load_image(image_name):
        new_img = Image.open(IMGDIR+image_name+".gif").convert("RGBA")
        tkimg = ImageTk.PhotoImage(image=new_img)
	images[image_name] = tkimg
        return tkimg


def palote(pintar,canvas):
      global palote_identifier
      if palote_identifier<>None and not pintar:
        canvas.delete(palote_identifier)
        palote_identifier=None
        return
      if palote_identifier == None and pintar:
        win=Frame(canvas)
        banner_image = load_image("Palotes")
        wi = banner_image.width()
        he = banner_image.height()
        banner_canvas = Canvas(win, width=wi, height=he)
        banner_canvas.create_image(0, 0, image=banner_image, anchor=N+W)
        banner_canvas.pack(side=TOP)
        palote_identifier = canvas.create_window(ancho-80,alto-80, window=win)

def get_scale():
  #Calcula el centro y la escala adecuada
  global x0,y0,scale
  xmax=-1.e8
  xmin=1.e8
  ymax=-1.e8
  ymin=1.e8
  for a in limites:
    if a[0]>xmax:
      xmax=a[0]
    if a[0]<xmin:
      xmin=a[0]
    if a[1]>ymax:
      ymax=a[1]
    if a[1]<ymin:
      ymin=a[1]
  x0=(xmax+xmin)/2
  y0=(ymax+ymin)/2
  x_scale=ancho/(xmax-xmin)
  y_scale=(alto-altura_barra_inferior)/(ymax-ymin)
  scale=min(x_scale,y_scale)*0.9
  return
  
def do_scale(a):
  # Devuelve las coordenadas en a transformadas de real a coordenadas canvas
  return s((centro_x,centro_y),p(r((a[0],-a[1]),(x0,-y0)),scale))

def undo_scale(a):
  # Devuelve las coordenadas en a transformadas de coordenadas canvas a reales
  return s((x0,y0),p(r((a[0],-a[1]),(centro_x,-centro_y)),1/scale))

def manual_dep_window(t):
  # Crea la ventana con botones para los despegues manuales
  # listado_salidas = {{'LEBB',{'IB4148';('10:18:15','NORTA1A'),'BAW317':('10:23:15','ROKIS1B'),...}
  global win_manual,avo,manual,listado_salidas
  if win_manual <> None:
    manual.destroy()
    win_manual = None
  manual = Frame(w)
  line = 1
  airp_list = listado_salidas.keys()
  avo = []
  for airp in airp_list:
    aux = []
    for callsign in listado_salidas[airp].keys():
      (etd,sid) = listado_salidas[airp][callsign]
      aux.append((etd,callsign,sid))
    aux.sort()
    nombre = Label(manual, text = 'DEP\'s '+airp)
    nombre.grid(column=0,row=line)
    line=line + 1
    for (etd,callsign,sid) in aux:
      boton = Button(manual,text = callsign,command=None)
      boton.grid(column=0,row=line)
      avo.append([boton,etd,callsign,sid])
      line=line+1
  win_manual = w.create_window(0,60,window=manual,anchor='nw')
  manual.update_idletasks()
  manual_dep_window_update(t)
  
def manual_dep_window_update(t): 
  global avo,manual,listado_salidas
  for [button,etd,callsign,sid] in avo:
    t_etd = float(etd[0:2])+float(etd[3:5])/60.+float(etd[6:8])/60./60.
    if t>t_etd and button['bg'] <> 'green':
      def dep_avo(x=manual.winfo_x()+button.winfo_x()+button.winfo_width(),y=manual.winfo_y()+button.winfo_y(),button_avo=button,callsign=callsign,sid=sid,etd=etd):
        global win_datos
        if win_datos != None:
          w.delete(win_datos)
          win_datos = None
          return
        dep = Frame()
        txt_estado = Label (dep,text= callsign.upper()+' LISTO',fg='red')
        txt_ind = Label (dep,text= 'ETD '+etd[0:5])
        combo_sid = ComboBox (dep,label= 'SID ',editable = True)
        # Ahora incluyo todos los procedimientos del aeropuerto en el ComboBox
        for airp in listado_salidas.keys():
          if callsign in listado_salidas[airp].keys():
            break
        ind = 0
        for pista in rwys[airp].split(','):
          (sid_proc,star_proc) = procedimientos[pista]
          for fijo_proc in sid_proc.keys():
            (nombre_sid,proc_sid) = sid_proc[fijo_proc]
            combo_sid.insert(ind,nombre_sid)
            if nombre_sid.upper()[:-2] == sid.upper()[:-2] and pista == rwyInUse[airp]:
              combo_sid.pick(ind)
            ind=ind+1
        combo_cfl = ComboBox (dep,label = 'para FL', editable = True)
        ind = 0
        for h in range(180,0,-10):
          combo_cfl.insert(ind,str(h))
          ind += 1
        combo_cfl.pick(4)
        but_suelto = Button(dep,text='SUELTO')
        txt_estado.pack(side='top')
        txt_ind.pack(side='top')
        combo_sid.pack(side='top')
        combo_cfl.pack(side = 'top')
        but_suelto.pack(side='top')
        win_datos = w.create_window(x,y,window=dep,anchor='nw')
        def despegue_avo(callsign=callsign,sid=sid):
          global listado_salidas,manual
          # Ecoger el avión a despegar
          for a in ejercicio:
            if a.get_callsign() == callsign:
              break
          # Tomamos la sid escogida y la asignada automáticamente
          sid_final = combo_sid.cget('value')
          cfl = float(combo_cfl.cget('value'))
          if sid.upper() not in sid_final.upper():
            for [p,(x,y)] in punto:
              if p in sid_final.upper():
                break
            for i in range(len(a.route)):
              if a.route[i][1] in sid.upper():
                a.route = a.route[i+1:]
                a.route.insert(0,[(x,y),p,''])
                complete_flight_plan(a)
                break
          # Ahora se depega el avión y se elimina de la lista
          a.t = last_update/60./60.
          a.t_ficha = last_update/60./60.-100.
          a.ficha_imprimida = True
          a.cfl = cfl
          a.next(t)
          print last_update,a.route
          print a.get_callsign()+' despegando'
          for airp in listado_salidas.keys():
            if callsign in listado_salidas[airp]:
              del listado_salidas[airp][callsign]
          global win_datos
          w.delete(win_datos)
          win_datos = None
          manual.destroy()
          manual_dep_window(t)
        but_suelto['command'] = despegue_avo

      button['command'] = dep_avo
      button['bg'] = 'green'
    elif t<= t_etd and button['bg'] <> 'yellow':
      def datos_avo(x=manual.winfo_x()+button.winfo_x()+button.winfo_width(),y=manual.winfo_y()+button.winfo_y(),button_avo=button,callsign=callsign,sid=sid,etd=etd):
        global win_datos
        if win_datos != None:
          w.delete(win_datos)
          win_datos = None
          return
        datos = Frame()
        txt_estado = Label (datos,text= callsign+' PREACTIVO',fg='red')
        txt_ind = Label (datos,text= 'ETD '+etd[0:5])
        txt_sid = Label (datos,text= 'SID '+sid)
        txt_estado.pack(side='top')
        txt_ind.pack(side='top')
        txt_sid.pack(side='top')
        print 'datos de coordenadas ',x,y
        win_datos = w.create_window(x,y,window=datos,anchor='nw')

      button['bg'] = 'yellow'
      button['command'] = datos_avo



def print_fs(callsign):
    """Simulate the printing of a flight strip"""
    import winsound
    try:
        print_fs._callsigns=print_fs._callsigns
    except:
        print_fs._callsigns={}
    if print_fs._callsigns.has_key(callsign) and print_fs._callsigns[callsign]==3:
        return
    if sys.platform=='win32':
        try:
            if reloj_funciona:  # Avoid the annoying sound at the beginning
#                winsound.PlaySound("*", winsound.SND_ALIAS|winsound.SND_NOSTOP|winsound.SND_ASYNC)
                winsound.PlaySound(SNDDIR+'/printer.wav', winsound.SND_NOSTOP|winsound.SND_ASYNC)
        except:
            return
        if not print_fs._callsigns.has_key(callsign):
            print_fs._callsigns[callsign]=0
        print_fs._callsigns[callsign]+=1
  
def redraw_all():
  # Dibujar las rutas y nombre de los puntos
  global x0,y0,scale,centro_x,centro_y,listado_salidas
  set_canvas_info(x0,y0,scale,centro_x,centro_y)
  w.delete('puntos')
  w.delete('nombres_puntos')
  w.delete('rutas')
  w.delete('tmas')
  w.delete('deltas')
  w.delete('local_maps')
  # Dibujar límites del FIR
  aux=()
  for a in limites:
    aux=aux+do_scale(a)
  w.create_polygon(aux,fill='gray12',outline='blue',tag='rutas')
  # Dibujar las rutas
  for a in rutas:
    aux=()
    for i in range(0,len(a[0]),2):
      aux=aux+do_scale((a[0][i],a[0][i+1]))
    w.create_line(aux,fill='gray50',tag='rutas')
  # Dibujar los fijos
  for a in punto:
    if a[0][0]<>'_':
      (cx,cy) = do_scale(a[1])
      coord_pol = (cx,cy-3.,cx+3.,cy+2.,cx-3.,cy+2.,cx,cy-3.)
      w.create_polygon(coord_pol,outline='gray50',fill='black',tag='rutas')
  # Dibujar el nombre de los puntos
  if nombre_fijos:
    for a in punto:
      if a[0][0]<>'_':
        w.create_text(do_scale(a[1]),text=a[0],fill='gray50',tag='nombres_puntos',anchor=SW,font='-*-Times-Bold-*--*-10-*-')
  # Dibujar TMA's
  if ver_tmas:
    for a in tmas:
      aux=()
      for i in range(0,len(a[0]),2):
        aux=aux+do_scale((a[0][i],a[0][i+1]))
      w.create_line(aux,fill='gray25',tag='tmas')
  # Dibujar zonas delta
  if ver_deltas:
    for a in deltas:
      aux=()
      for i in range(0,len(a[0]),2):
        aux=aux+do_scale((a[0][i],a[0][i+1]))
      w.create_line(aux,fill='gray25',tag='deltas')
  # Dibujar mapas locales
  for nombre_mapa in local_maps_shown:
    objetos = local_maps[nombre_mapa]
    for ob in objetos:
      if ob[0] == 'linea':
        cx0 = float(ob[1])
	cy0 = float(ob[2])
        cx1 = float(ob[3])
	cy1 = float(ob[4])
	if len(ob) > 5:
	  col = ob[5]
	else:
	  col = 'white'
	(px0, py0) = do_scale((cx0,cy0))
	(px1, py1) = do_scale((cx1,cy1))
	w.create_line(px0, py0, px1, py1, fill=col, tag='local_maps')
      elif ob[0] == 'arco':
        cx0 = float(ob[1])
	cy0 = float(ob[2])
        cx1 = float(ob[3])
	cy1 = float(ob[4])
        start_value = float(ob[5])
	extent_value = float(ob[6])
	if len(ob) > 7:
	  col = ob[7]
	else:
	  col = 'white'
	(px0, py0) = do_scale((cx0,cy0))
	(px1, py1) = do_scale((cx1,cy1))
	w.create_arc(px0, py0, px1, py1, start=start_value, extent=extent_value, outline=col, style='arc', tag='local_maps')
      elif ob[0] == 'ovalo':
        cx0 = float(ob[1])
	cy0 = float(ob[2])
        cx1 = float(ob[3])
	cy1 = float(ob[4])
	if len(ob) > 5:
	  col = ob[5]
	else:
	  col = 'white'
	(px0, py0) = do_scale((cx0,cy0))
	(px1, py1) = do_scale((cx1,cy1))
	w.create_oval(px0, py0, px1, py1, fill=col, tag='local_maps')
      elif ob[0] == 'rectangulo':
        cx0 = float(ob[1])
	cy0 = float(ob[2])
        cx1 = float(ob[3])
	cy1 = float(ob[4])
	if len(ob) > 5:
	  col = ob[5]
	else:
	  col = 'white'
	(px0, py0) = do_scale((cx0,cy0))
	(px1, py1) = do_scale((cx1,cy1))
	w.create_rectangle(px0, py0, px1, py1, fill=col, tag='local_maps')
      elif ob[0] == 'texto':
        x = float(ob[1])
	y = float(ob[2])
	txt = ob[3]
	if len(ob) > 4:
	  col = ob[4]
	else:
	  col = 'white'
	(px, py) = do_scale((x,y))
	w.create_text(px, py, text=txt, fill=col,tag='local_maps',anchor=SW,font='-*-Times-Bold-*--*-10-*-')

  w.delete('fichas')
  # Poner las fichas que se imprimen
  draw_print_list()
  # Dibujar los aviones
  for a in ejercicio:
    a.redraw(w)
  draw_all_lads(w)  
  # Comprobar si hay PAC o VAC
  for i in range(len(ejercicio)):
    for j in range(i+1,len(ejercicio)):
      if pac(ejercicio[i],ejercicio[j]):
        ejercicio[i].set_pac(w)
        ejercicio[j].set_pac(w)
  w.delete('vac')
  poner_palote=False
  palote(poner_palote,w)
  for i in range(len(ejercicio)):
    for j in range(i+1,len(ejercicio)):
      line=()
      if vac(ejercicio[i],ejercicio[j]):
        poner_palote=True
        ejercicio[i].set_vac(w)
        line=do_scale(ejercicio[i].get_coords())
        ejercicio[j].set_vac(w)
        line=line+do_scale(ejercicio[j].get_coords())
        w.create_line(line,fill='red',tag='vac')
  palote(poner_palote,w)
  t=float(tlocal(t0))
  ho=int(t/60/60)
  m=int(t/60)-ho*60
  s=int(t)-60*60*ho-60*m
 
fact_t=1.0
t0=fact_t*time()-h_inicio

def tlocal(t):
  return fact_t*time()-t

last_update=tlocal(t0)-10.
 
def set_vel_reloj(k):
  global t0,fact_t,h_inicio
  h_inicio=fact_t*time()-t0
  fact_t=k
  t0=fact_t*time()-h_inicio

def se_cortan (label_modif,i,j):
  # Devuelve si las etiquetas está separadas entre los aviones i y j de ejercicio
  if ejercicio[i].is_flying():
    (xip,yip) = do_scale(ejercicio[i].get_coords())
    xis , yis = xip + label_modif[i][0] , yip + label_modif[i][1]
    xii , yii = xis + ejercicio[i].label_width , yis + ejercicio[i].label_height
    # Comprobamos las cuatro esquinas del avión j y que no se corten los soportes de etiquetas, asícomo ningn plot
    if ejercicio[j].is_flying():
      (xjp,yjp) = do_scale(ejercicio[j].get_coords())
      xjs , yjs = xjp + label_modif[j][0] , yjp + label_modif[j][1]
      xji , yji = xjs + ejercicio[j].label_width , yjs + ejercicio[j].label_height
      for x1 in (xjs,xji):
        for y1 in (yjs,yji):
          if x1>=xis and x1<=xii and y1>=yis and y1<=yii:
            return True
#       (v1,v2) = (xis-xip , yis-yip)
#       (oa1,oa2) = (xjp-xip , yjp-yip)
#       (ob1,ob2) = (xjs-xip , yjs-yip)
#       norma_v = max((v1 * v1 + v2 * v2)**(0.5),0.00001)
#       (v1,v2) = (v1 / norma_v, v2 / norma_v)
#       oa_x_vperp = oa1 * v2 - oa2 * v1
#       ob_x_vperp = ob1 * v2 - ob2 * v1
#       oa_x_v = oa1 * v1 + oa2 * v2
#       ob_x_v = ob1 * v1 + ob2 * v2
#       cond1 = oa_x_vperp * ob_x_vperp # Negativo si cada uno estáa un lado
#       if abs(oa_x_vperp) + abs(ob_x_vperp) > 0.:
#         cond2 = (oa_x_v * abs(ob_x_vperp) + ob_x_v * abs(oa_x_vperp))/(abs(oa_x_vperp) + abs(ob_x_vperp))
#       else:
#         cond2 = norma_v * 2.
#       if cond1 <= 0. and cond2>=0. and cond2 <= norma_v:
#         corta = True
      if xjp>=xis and xjp<=xii and yjp>=yis and yjp<=yii:
        return True
  return False

def rotate_label(labels_modif,i):       
  [support_x,support_y,label_radius, label_heading] = labels_modif[i]
  label_heading += 45.0
  support_x = label_radius * sin(radians(label_heading))
  support_y = label_radius * cos(radians(label_heading))
  if support_x > 0.:  
    new_label_x = support_x
    new_label_y = support_y -10
  else:
    new_label_x = support_x - ejercicio[i].label_width
    new_label_y = support_y -10
  return [new_label_x,new_label_y,label_radius, label_heading]

def timer():
  # Subrutina que controla los refrescos de pantalla cada 5 segundos
  global last_update,t0
  refresco=5.
  # Si el reloj estáparado actualizamos t0 para ajustarque no corra el tiempo y no actualizamos.
  if not reloj_funciona:
    t0=fact_t*time()-h_inicio
#     return
  etiq1=28
  w.update()
  if tlocal(t0)-last_update<refresco:
    t=float(tlocal(t0))
    ho=int(t/60/60)
    m=int(t/60)-ho*60
    s=int(t)-60*60*ho-60*m
    clock.configure({'time':'%02d:%02d:%02d' % (ho, m, s)})

  else:
    last_update=tlocal(t0)
    # Mover los aviones con auto-separación
    for a in ejercicio:
      a.next(last_update/60./60.)
      a.redraw(w)
    if auto_sep:
      crono = tlocal(t0)
      labels = []
      for i in range (len(ejercicio)):
        labels.append([ejercicio[i].label_x, ejercicio[i].label_y, ejercicio[i].label_radius,ejercicio[i].label_heading])
      for i in range (len(ejercicio)):
        if (tlocal(t0)-crono)/fact_t > 0.85:
          break
        moviendo = [i]
        cuenta = [0]
        giro_min = [0]
        intersectan = 0
        for j in range(len(ejercicio)):
          if i == j: continue
          if se_cortan(labels,i,j):
            intersectan = intersectan + 1
            if (j not in moviendo) and (ejercicio[j].auto_separation) and len(moviendo)<10:
#               print 'Añadiendo ',ejercicio[j].get_callsign()
              moviendo.append(j)
              cuenta.append(0)
              giro_min.append(0)
        # Si intersectan probamos las posiciones posibles de la etiqueta para ver si libra en alguna. En caso contrario,se escoge 
        # el de menor interferencia
        intersectan_girado = intersectan
        cuenta_menos_inter = cuenta
        menos_inter = intersectan
        crono_ini = tlocal(t0)
        while (intersectan_girado > 0) and (cuenta[0] < 8) and (tlocal(t0)-crono_ini)/fact_t < 0.5:
          for k in range(len(moviendo)-1,-1,-1):
            if cuenta[k]<8:
              cuenta[k] += 1
              labels[moviendo[k]] = rotate_label(labels,moviendo[k])
              break
            elif cuenta[k]==8: 
              cuenta[k] = 0 
          # Comprobamos si está separados todos entre ellos
          intersectan_girado = 0
          for j in range(len(moviendo)):
            for k in range(j+1,len(moviendo)):
              if se_cortan(labels,moviendo[j],moviendo[k]):
                intersectan_girado += 1
#           print 'cuenta: ',cuenta, intersectan_girado
        # En caso de que haya conflicto, escogemos el giro con menos intersecciones
          if intersectan_girado < menos_inter:
            menos_inter = intersectan_girado
            cuenta_menos_inter = cuenta
          # Comprobamos que no estemos afectando a ningn otro avión con el reción girado. En caso contrario, se añade
          if intersectan_girado == 0:
            for k in moviendo:
              for j in range(len(ejercicio)):
                if (j not in moviendo) and (len(moviendo)<10) and se_cortan(labels,j,k):
#                   print 'Añadiendo ',ejercicio[j].get_callsign()
                  intersectan_girado += 1
                  moviendo.append(j)
                  cuenta.append(0)
        # Giramos los aviones lo calculado
        if intersectan >0: 
#           print 'Conflictos antes y despues', intersectan, menos_inter
          for k in moviendo:
            pass
#             print 'son conflicto con ',ejercicio[k].get_callsign()
        for l in range(len(moviendo)):
          for k in range(cuenta_menos_inter[l]):
            ejercicio[moviendo[l]].rotate_label()
          labels[moviendo[l]] = [ejercicio[moviendo[l]].label_x, ejercicio[moviendo[l]].label_y, ejercicio[moviendo[l]].label_radius,ejercicio[moviendo[l]].label_heading]
#       print 'Tiempo en separar: ',(tlocal(t0)-crono)/fact_t
    # Comprobar si hay PAC o VAC
    for i in range(len(ejercicio)):
      for j in range(i+1,len(ejercicio)):
        if pac(ejercicio[i],ejercicio[j]):
          ejercicio[i].set_pac(w)
          ejercicio[j].set_pac(w)
    w.delete('vac')
    poner_palote=False
    palote(poner_palote,w)
    for i in range(len(ejercicio)):
      for j in range(i+1,len(ejercicio)):
        line=()
        if vac(ejercicio[i],ejercicio[j]):
          poner_palote=True
          ejercicio[i].set_vac(w)
          line=do_scale(ejercicio[i].get_coords())
          ejercicio[j].set_vac(w)
          line=line+do_scale(ejercicio[j].get_coords())
          w.create_line(line,fill='red',tag='vac')
  #         print 'Conflicto entre ',ejercicio[i].get_callsign(),' y ',ejercicio[j].get_callsign(),'a las ',last_update/60./60.
    palote(poner_palote,w)
#     print 'Cosas en canvas'
#     for a in w.find_withtag(ALL):
#       print a
  draw_all_lads(w)
  # Poner las fichas que se imprimen
  w.delete('fichas')
  # Poner las fichas que se imprimen
  draw_print_list()
  
  if auto_departures == False:
    manual_dep_window_update(last_update/60./60.)

  root.after(100,timer)

def b_izquierda():
  global x0
  x0 = x0 - ancho/10/scale
  redraw_all()

def b_derecha():
  global x0
  x0 = x0 + ancho/10/scale
  redraw_all()
  
def b_arriba():
  global y0
  y0 = y0 + alto/10/scale
  redraw_all()
  
def b_abajo():
  global y0
  y0 = y0 - alto/10/scale
  redraw_all()
  
def b_zoom_mas():
  global scale
  scale=scale*1.1
  redraw_all()
  
def b_zoom_menos():
  global scale
  scale=scale/1.1
  redraw_all()
  
def b_standard():
  global centro_x,centro_y
  centro_x=ancho/2
  centro_y=(alto-40.)/2
  get_scale()
  redraw_all()
  
def b_inicio():
  global t0,reloj_funciona
  if not reloj_funciona:
#     print 'Iniciando simulación'
    t0=fact_t*time()-h_inicio
    reloj_funciona = True
#   print reloj_funciona
  
def b_parar():
  global h_inicio,reloj_funciona
  if reloj_funciona:
#     print 'Parando la simulación'
    h_inicio=fact_t*time()-t0
    reloj_funciona=False
  
def b_tamano_etiquetas():
  global label_font_size, label_font, radius
  label_font_size += 2
  if label_font_size >= 15:
  	label_font_size = 9
  label_font = tkFont.Font(family="Helvetica",size=label_font_size)
  set_label_font(label_font)
  set_label_font_size(label_font_size)
  redraw_all()

def b_show_hide_localmaps():
  global local_maps_shown
  local_maps_shown = []
  for map_name in local_maps:
    print var_ver_localmap[map_name].get()
    if var_ver_localmap[map_name].get() != 0:
      local_maps_shown.append(map_name)
  redraw_all()

def b_show_hide_points():
  global nombre_fijos
  nombre_fijos = not nombre_fijos
  redraw_all()
  
def b_show_hide_tmas():
  global ver_tmas
  ver_tmas = not ver_tmas
  redraw_all()
  
def b_show_hide_deltas():
  global ver_deltas
  ver_deltas = not ver_deltas
  redraw_all()
  
def b_auto_separation():
  global auto_sep
  auto_sep = not auto_sep
  
def kill_acft():
  for a in ejercicio:
    a.kill_airplane(w)
  
def quitar_fpr():
  for a in ejercicio:
    if w.itemcget(a.name+'fpr','fill')=='orange':
      w.delete(a.name+'fpr')

def quitar_lads():
  global all_lads, superlad
  for lad_to_remove in all_lads:
    if lad_to_remove.line_id != None: w.delete(lad_to_remove.line_id)
    if lad_to_remove.text_id1 != None: w.delete(lad_to_remove.text_id1)
    if lad_to_remove.text_id2 != None: w.delete(lad_to_remove.text_id2)
    if lad_to_remove.text_id3 != None: w.delete(lad_to_remove.text_id3)
    if lad_to_remove.text_id4 != None: w.delete(lad_to_remove.text_id4)
#     all_lads.remove(lad_to_remove)
#     lad_to_remove.destroy()
    if superlad == lad_to_remove: superlad = None
  all_lads = []  
win_identifier=None

def cancel_app_auth(sel):
  if sel.app_auth:
    for i in range(len(sel.route),0,-1):
      if sel.route[i-1][1] == sel.fijo_app:
        sel.route = sel.route[:i]
        break

def define_holding():
  global win_identifier
  if win_identifier<>None:
    w.delete(win_identifier)
    win_identifier=None
    return
  sel = None
  for a in ejercicio:
    if a.esta_seleccionado():
      sel=a
  if sel == None:
    win = Frame(w)
    txt_ruta0 = Label (win,text='Entrar en una espera')
    txt_ruta = Label (win,text='NO HAY NINGUN VUELO SELECCIONADO ',fg='red')
    but_acept = Button(win, text="Aceptar")
    txt_ruta0.pack(side=TOP)
    txt_ruta.pack(side=LEFT)
    but_acept.pack(side=LEFT)
    win_identifier = w.create_window(ancho/2,alto-75, window=win)
    def close_win(ident=win_identifier):
            global win_identifier
            win_identifier=None
            w.delete(ident)
    but_acept['command'] = close_win
  else:
    global vent_ident_procs
    if vent_ident_procs != None:
      w.delete(vent_ident_procs)
      vent_ident_procs = None
    win = Frame(w)
    title = Label(win, text = 'Espera: '+sel.get_callsign())
    lbl_hold = Label(win, text="Fijo principal:")
    ent_hold = Entry(win, width=5)
    ent_hold.insert(0, str(sel.route[0][1]))
    lbl_side = Label (win, text = 'Virajes (I/D):')
    ent_side = Entry(win,width=1)
    ent_side.insert(0, 'D')
    but_Acp = Button(win, text="Aceptar")
    but_Can = Button(win, text="Cancelar")
    title.grid(row=0,column=0, columnspan=2)
    lbl_hold.grid(row=1, column=0)
    ent_hold.grid(row=1, column=1)
    lbl_side.grid(row=2, column=0)
    ent_side.grid(row=2, column=1)
    but_Acp.grid(row=3, column=0, columnspan=2)
    but_Can.grid(row=4, column=0, columnspan=2)
    win_identifier = w.create_window(do_scale(sel.pos), window=win)
    ent_hold.focus_set()
    def close_win(e=None,ident=win_identifier,w=w):
            global win_identifier
            w.unbind_all("<Return>")
            w.unbind_all("<KP_Enter>")
            w.unbind_all("<Escape>")
            win_identifier=None
            w.delete(ident)
    def set_holding(e=None):
            error = True
            fijo = ent_hold.get().upper()
            lado = ent_side.get().upper()
            auxiliar = ''
            # Si la espera estápublicada, los datos de la espera
            for [fijo_pub,rumbo,tiempo,lado_pub] in esperas_publicadas:
              if fijo_pub == fijo:
                lado = lado_pub.upper()
                derrota_acerc = rumbo
                tiempo_alej = tiempo/60.0
                for i in range(len(sel.route)):
                  [a,b,c] = sel.route[i]
                  if b == fijo:
                    auxiliar = [a,b,c]
                    error = False
                    break
            # En caso contrario, TRK acerc = TRK de llegada y tiempo = 1 min
            if auxiliar == '':
              for i in range(len(sel.route)):
                [a,b,c] = sel.route[i]
                if b == fijo:
                  if i == 0: # La espera se inicia en el siguiente punto del avión
                    auxi = sel.pos
                  else:
                    auxi = sel.route[i-1][0]
                  aux1 = r(a,auxi)
                  derrota_acerc = rp(aux1)[1]
                  auxiliar = [a,b,c]
                  error = False
                  tiempo_alej = 1.0/60.0
                  break
            if error:
              ent_hold['bg'] = 'red'
              ent_hold.focus_set()
            if lado == 'I':
              giro = -1.0
            elif lado == 'D':
              giro = +1.0
            else:
              ent_side['bg'] = 'red'
              ent_side.focus_set()
              error = True
            if not error:
              sel.vfp = False
              sel.to_do = 'hld'
              sel.to_do_aux = [auxiliar, derrota_acerc, tiempo_alej, 0.0, False, giro]
              # Cancelar posible autorización de aproximación
              cancel_app_auth(sel)
              print "Holding pattern:", sel.to_do_aux
              close_win()
    but_Acp['command'] = set_holding
    but_Can['command'] = close_win
    w.bind_all("<Return>",set_holding)
    w.bind_all("<KP_Enter>",set_holding)
    w.bind_all("<Escape>",close_win)
      
def nueva_ruta():
    global win_identifier
    if win_identifier<>None:
      w.delete(win_identifier)
      win_identifier=None
      return
    sel = None
    for a in ejercicio:
      if a.esta_seleccionado():
        sel=a
    if sel == None:
      win = Frame(w)
      txt_ruta0 = Label (win,text='Definir nueva ruta')
      txt_ruta = Label (win,text='NO HAY NINGUN VUELO SELECCIONADO ',fg='red')
      but_acept = Button(win, text="Aceptar")
      txt_ruta0.pack(side=TOP)
      txt_ruta.pack(side=LEFT)
      but_acept.pack(side=LEFT)
      win_identifier = w.create_window(ancho/2,alto-75, window=win)
      def close_win(ident=win_identifier):
              global win_identifier
              win_identifier=None
              w.delete(ident)
      but_acept['command'] = close_win
    else:
      win = Frame(w)
      txt_ruta = Label (win,text='Nueva ruta '+sel.get_callsign()+':')
      ent_ruta = Entry(win,width=50)
      txt_dest = Label (win,text='Destino')
      ent_dest = Entry(win,width=5)
      ent_dest.insert(END,sel.destino)
      but_acept = Button(win, text="Aceptar")
      but_cancel = Button(win, text="Cancelar")
      txt_ruta.pack(side=LEFT)
      ent_ruta.pack(side=LEFT)
      txt_dest.pack(side=LEFT)
      ent_dest.pack(side=LEFT)
      but_acept.pack(side=LEFT)
      but_cancel.pack(side=LEFT)
      win_identifier = w.create_window(ancho/2,alto-75, window=win)
      ent_ruta.focus_set()
      def close_win(e=None,ident=win_identifier):
              global win_identifier
              w.unbind_all("<Return>")
              w.unbind_all("<KP_Enter>")
              w.unbind_all("<Escape>")
              win_identifier=None
              w.delete(ident)
      def change_fpr(e=None):
              pts=ent_ruta.get().split(' ')
#               print 'Puntos son:'
              aux=[]
              fallo=False
              for a in pts:
                hay_pto=False
                for b in punto:
                  if a.upper() == b[0]:
                    aux.append([b[1],b[0],''])
                    hay_pto=True
                if not hay_pto:
                  fallo=True
              if fallo:
                ent_ruta['bg'] = 'red'
                ent_ruta.focus_set()
              else:
                sel.destino = ent_dest.get().upper()
                cancel_app_auth(sel)
                sel.set_route(aux)
                print 'Cambiando plan de vuelo a ',aux
                sel.set_app_fix()
                close_win()
      but_cancel['command'] = close_win
      but_acept['command'] = change_fpr
      w.bind_all("<Return>",change_fpr)
      w.bind_all("<KP_Enter>",change_fpr)
      w.bind_all("<Escape>",close_win)
        
def cambiar_viento():
	global win_identifier
	if win_identifier<>None:
		w.delete(win_identifier)
		win_identifier=None
		return
	win = Frame(w)
	txt_title = Label (win,text='Definir viento')
	txt_dir = Label (win,text='Dirección')
	ent_dir = Entry(win,width=5)
	ent_dir.insert(END,int((wind[1]+180.0)%360.0))
	txt_int = Label (win,text='Intensidad (kts)')
	ent_int = Entry(win,width=4)
	ent_int.insert(END,int(wind[0]))
	but_acept = Button(win, text="Aceptar")
	but_cancel = Button(win, text="Cancelar")
	txt_title.grid(column=0,row=0,columnspan=2)
	txt_dir.grid(column=0,row=1)
	ent_dir.grid(column=1,row=1)
	txt_int.grid(column=0,row=2)
	ent_int.grid(column=1,row=2)
	but_acept.grid(column=0,row=3,columnspan=2)
	but_cancel.grid(column=0,row=4,columnspan=2)
	win_identifier = w.create_window(ancho/2,alto-100, window=win)
	ent_dir.focus_set()
	def close_win(e=None,ident=win_identifier):
	      global win_identifier
	      w.unbind_all("<Return>")
	      w.unbind_all("<KP_Enter>")
	      w.unbind_all("<Escape>")
	      win_identifier=None
	      w.delete(ident)
	def change_wind(e=None):
		global wind, vent_ident_procs
		int=ent_int.get()
		dir=ent_dir.get()
		fallo = False
		if dir.isdigit():
			rumbo = (float(dir)+180.0) % 360.0
		else:
			ent_dir['bg'] = 'red'
			ent_dir.focus_set()
			fallo = True
		if int.isdigit():
			intensidad = float(int)
		else:
			ent_int['bg'] = 'red'
			ent_int.focus_set()
			fallo = True
		if not fallo:
			if vent_ident_procs != None:
				w.delete(vent_ident_procs)
				vent_ident_procs = None
			# Cambiamos el viento en todos los módulos
			wind = [intensidad,rumbo]
			set_global_vars(punto, wind, aeropuertos, esperas_publicadas,rwys,rwyInUse,procedimientos,proc_app,min_sep)

			print 'Viento ahora es (int,rumbo)', wind
			close_win()
	but_cancel['command'] = close_win
	but_acept['command'] = change_wind
	w.bind_all("<Return>",change_wind)
	w.bind_all("<KP_Enter>",change_wind)
	w.bind_all("<Escape>",close_win)


def hdg_after_fix():
    global win_identifier
    if win_identifier<>None:
      w.delete(win_identifier)
      win_identifier=None
      return
    sel = None
    for a in ejercicio:
      if a.esta_seleccionado():
        sel=a
    if sel == None:
      win = Frame(w)
      txt_ruta0 = Label (win,text='Rumbo después de fijo')
      txt_ruta = Label (win,text='NO HAY NINGUN VUELO SELECCIONADO ',fg='red')
      but_acept = Button(win, text="Aceptar")
      txt_ruta0.pack(side=TOP)
      txt_ruta.pack(side=LEFT)
      but_acept.pack(side=LEFT)
      win_identifier = w.create_window(ancho/2,alto-75, window=win)
      def close_win(ident=win_identifier):
              global win_identifier
              win_identifier=None
              w.delete(ident)
      but_acept['command'] = close_win
    else:
      global vent_ident_procs
      if vent_ident_procs != None:
        w.delete(vent_ident_procs)
        vent_ident_procs = None
      win = Frame(w)
      title = Label(win, text = 'Rumbo después de fijo: '+sel.get_callsign())
      lbl_fix = Label(win, text="Fijo:")
      ent_fix = Entry(win, width=5)
      ent_fix.insert(0, str(sel.route[0][1]))
      lbl_hdg = Label (win, text = 'Rumbo:')
      ent_hdg = Entry(win,width=3)
      but_Acp = Button(win, text="Aceptar")
      but_Can = Button(win, text="Cancelar")
      title.grid(row=0,column=0, columnspan=2)
      lbl_fix.grid(row=1, column=0)
      ent_fix.grid(row=1, column=1)
      lbl_hdg.grid(row=2, column=0)
      ent_hdg.grid(row=2, column=1)
      but_Acp.grid(row=3, column=0, columnspan=2)
      but_Can.grid(row=4, column=0, columnspan=2)
      win_identifier = w.create_window(do_scale(sel.pos), window=win)
      ent_hdg.focus_set()
      def close_win(e=None,ident=win_identifier,w=w):
              global win_identifier
              w.unbind_all("<Return>")
              w.unbind_all("<KP_Enter>")
              w.unbind_all("<Escape>")
              win_identifier=None
              w.delete(ident)
      def set_fix_hdg(e=None):
              error = True
              fijo = ent_fix.get().upper()
              hdg = ent_hdg.get().upper()
              for i in range(len(sel.route)):
                [a,b,c] = sel.route[i]
                if b == fijo:
                  auxiliar = [a,b,c]
                  error = False
                  break
              if error:
                ent_fix['bg'] = 'red'
                ent_fix.focus_set()
              if not hdg.isdigit():
                ent_hdg['bg'] = 'red'
                ent_hdg.focus_set()
                error = True
              else: 
                hdg = float(hdg)
              if not error:
                sel.vfp = False
                sel.to_do = 'hdg<fix'
                sel.to_do_aux = [auxiliar, hdg]
                print "Heading after fix:", sel.to_do_aux
                cancel_app_auth(sel)
                close_win()
      but_Acp['command'] = set_fix_hdg
      but_Can['command'] = close_win
      w.bind_all("<Return>",set_fix_hdg)
      w.bind_all("<KP_Enter>",set_fix_hdg)
      w.bind_all("<Escape>",close_win)
        
def int_rdl():
    global win_identifier
    if win_identifier<>None:
      w.delete(win_identifier)
      win_identifier=None
      return
    sel = None
    for a in ejercicio:
      if a.esta_seleccionado():
        sel=a
    if sel == None:
      win = Frame(w)
      txt_ruta0 = Label (win,text='Interceptar radial')
      txt_ruta = Label (win,text='NO HAY NINGUN VUELO SELECCIONADO ',fg='red')
      but_acept = Button(win, text="Aceptar")
      txt_ruta0.pack(side=TOP)
      txt_ruta.pack(side=LEFT)
      but_acept.pack(side=LEFT)
      win_identifier = w.create_window(ancho/2,alto-75, window=win)
      def close_win(ident=win_identifier):
              global win_identifier
              win_identifier=None
              w.delete(ident)
      but_acept['command'] = close_win
    else:
      global vent_ident_procs
      if vent_ident_procs != None:
        w.delete(vent_ident_procs)
        vent_ident_procs = None
        win = Frame(w)
      win = Frame(w)
      title = Label(win, text = 'Interceptar radial: '+sel.get_callsign())
      lbl_fix = Label(win, text="Fijo:")
      ent_fix = Entry(win, width=5)
      ent_fix.insert(0, str(sel.route[0][1]))
      lbl_rdl = Label (win, text = 'Radial:')
      ent_rdl = Entry(win,width=3)
      lbl_d_h = Label (win, text= 'Desde/Hacia (D/H)')
      ent_d_h = Entry(win,width=1)
      ent_d_h.insert(0,str('D'))
      but_Acp = Button(win, text="Aceptar")
      but_Can = Button(win, text="Cancelar")
      title.grid(row=0,column=0, columnspan=2)
      lbl_fix.grid(row=1, column=0)
      ent_fix.grid(row=1, column=1)
      lbl_rdl.grid(row=2, column=0)
      ent_rdl.grid(row=2, column=1)
      lbl_d_h.grid(row=3, column=0)
      ent_d_h.grid(row=3, column=1)
      but_Acp.grid(row=4, column=0, columnspan=2)
      but_Can.grid(row=5, column=0, columnspan=2)
      win_identifier = w.create_window(do_scale(sel.pos), window=win)
      ent_fix.focus_set()
      def close_win(e=None,ident=win_identifier,w=w):
              global win_identifier
              w.unbind_all("<Return>")
              w.unbind_all("<KP_Enter>")
              w.unbind_all("<Escape>")
              win_identifier=None
              w.delete(ident)
      def set_rdl(e=None):
              error = True
              fijo = ent_fix.get().upper()
              rdl = ent_rdl.get().upper()
              d_h = ent_d_h.get().upper()
              for [nombre,coord] in punto:
                if nombre == fijo:
                  auxiliar = coord
                  error = False
                  break
              if error:
                ent_fix['bg'] = 'red'
                ent_fix.focus_set()
              if not rdl.isdigit():
                ent_rdl['bg'] = 'red'
                ent_rdl.focus_set()
                error = True
              else: 
                rdl = float(rdl)
              if d_h == 'H':
                correccion = 180.
              elif d_h == 'D':
                correccion = 0.
              else:
                ent_d_h['bg'] = 'red'
                ent_d_h.focus_set()
                error = True
              if not error:
                if sel.to_do <> 'hdg':
                  sel.hold_hdg = sel.hdg
                sel.vfp = False
                sel.to_do = 'int_rdl'
                sel.to_do_aux = [auxiliar, (rdl + correccion)% 360.]
                print "Intercep radial:", sel.to_do_aux
                cancel_app_auth(sel)
                close_win()
      but_Acp['command'] = set_rdl
      but_Can['command'] = close_win
      w.bind_all("<Return>",set_rdl)
      w.bind_all("<KP_Enter>",set_rdl)
      w.bind_all("<Escape>",close_win)

def b_execute_map():
    global win_identifier
    if win_identifier<>None:
      w.delete(win_identifier)
      win_identifier=None
      return
    sel = None
    for a in ejercicio:
      if a.esta_seleccionado():
        sel=a
    if sel == None or not sel.app_auth:
      win = Frame(w)
      txt_ruta0 = Label (win,text='Asignar ejecución aproximación frustrada')
      txt_ruta = Label (win,text='NO HAY NINGUN VUELO SELECCIONADO ',fg='red')
      txt2_ruta = Label (win,text='O EL VUELO NO ESTÁ AUTORIZADO APP ',fg='red')
      but_acept = Button(win, text="Aceptar")
      txt_ruta0.pack(side=TOP)
      txt_ruta.pack(side=LEFT)
      txt2_ruta.pack(side=LEFT)
      but_acept.pack(side=LEFT)
      win_identifier = w.create_window(ancho/2,alto-75, window=win)
      def close_win(ident=win_identifier):
              global win_identifier
              win_identifier=None
              w.delete(ident)
      but_acept['command'] = close_win
    elif sel.destino not in rwys.keys():
      win = Frame(w)
      txt_ruta0 = Label (win,text='Autorizar a aproximación')
      txt_ruta = Label (win,text='AEROPUERTO DE DESTINO SIN PROCEDIMIENTOS APP ',fg='red')
      but_acept = Button(win, text="Aceptar")
      txt_ruta0.pack(side=TOP)
      txt_ruta.pack(side=LEFT)
      but_acept.pack(side=LEFT)
      win_identifier = w.create_window(ancho/2,alto-75, window=win)
      def close_win(ident=win_identifier):
              global win_identifier
              win_identifier=None
              w.delete(ident)
      but_acept['command'] = close_win
    else:
      global vent_ident_maps
      if vent_ident_maps != None:
        w.delete(vent_ident_maps)
        vent_ident_maps = None
      win = Frame(w)
      title = Label(win, text = 'Ejecutar MAP: '+sel.get_callsign())
      but_Acp = Button(win, text="Aceptar")
      but_Can = Button(win, text="Cancelar")
      title.grid(row=0,column=0, columnspan=2)
      but_Acp.grid(row=1, column=0, columnspan=2)
      but_Can.grid(row=2, column=0, columnspan=2)
      win_identifier = w.create_window(do_scale(sel.pos), window=win)
      but_Acp.focus_set()
      def close_win(e=None,ident=win_identifier,w=w):
              global win_identifier
              w.unbind_all("<Return>")
              w.unbind_all("<KP_Enter>")
              w.unbind_all("<Escape>")
              win_identifier=None
              w.delete(ident)
      def exe_map(e=None):
              sel._map = True
              print "Ejecutará MAP"
              close_win()
      but_Acp['command'] = exe_map
      but_Can['command'] = close_win
      w.bind_all("<Return>",exe_map)
      w.bind_all("<KP_Enter>",exe_map)
      w.bind_all("<Escape>",close_win)

def b_int_llz():
    global win_identifier
    if win_identifier<>None:
      w.delete(win_identifier)
      win_identifier=None
      return
    sel = None
    for a in ejercicio:
      if a.esta_seleccionado():
        sel=a
    if sel == None:
      win = Frame(w)
      txt_ruta0 = Label (win,text='Interceptar localizador')
      txt_ruta = Label (win,text='NO HAY NINGUN VUELO SELECCIONADO ',fg='red')
      but_acept = Button(win, text="Aceptar")
      txt_ruta0.pack(side=LEFT)
      txt_ruta.pack(side=LEFT)
      but_acept.pack(side=LEFT)
      win_identifier = w.create_window(ancho/2,alto-75, window=win)
      def close_win(ident=win_identifier):
              global win_identifier
              win_identifier=None
              w.delete(ident)
      but_acept['command'] = close_win
    elif sel.destino not in rwys.keys():
      win = Frame(w)
      txt_ruta0 = Label (win,text='Autorizar a aproximación')
      txt_ruta = Label (win,text='AEROPUERTO DE DESTINO SIN PROCEDIMIENTOS APP ',fg='red')
      but_acept = Button(win, text="Aceptar")
      txt_ruta0.pack(side=TOP)
      txt_ruta.pack(side=LEFT)
      but_acept.pack(side=LEFT)
      win_identifier = w.create_window(ancho/2,alto-75, window=win)
      def close_win(ident=win_identifier):
              global win_identifier
              win_identifier=None
              w.delete(ident)
      but_acept['command'] = close_win
    else:
      if sel.fijo_app == 'N/A':
        win = Frame(w)
        txt_ruta0 = Label (win,text='Interceptar localizador y seguir senda de planeo')
        txt_ruta = Label (win,text='VUELO SIN IAF, añada ruta al IAF y reintente ',fg='red')
        but_acept = Button(win, text="Aceptar")
        txt_ruta0.pack(side=LEFT)
        txt_ruta.pack(side=LEFT)
        but_acept.pack(side=LEFT)
        win_identifier = w.create_window(ancho/2,alto-75, window=win)
        def close_win(ident=win_identifier):
                global win_identifier
                win_identifier=None
                w.delete(ident)
        but_acept['command'] = close_win
        return
      global vent_ident_maps
      if vent_ident_maps != None:
        w.delete(vent_ident_maps)
        vent_ident_maps = None
      win = Frame(w)
      title = Label(win, text = 'Int. LLZ + GP: '+sel.get_callsign())
      but_Acp = Button(win, text="Aceptar")
      but_Can = Button(win, text="Cancelar")
      title.grid(row=0,column=0, columnspan=2)
      but_Acp.grid(row=1, column=0, columnspan=2)
      but_Can.grid(row=2, column=0, columnspan=2)
      win_identifier = w.create_window(do_scale(sel.pos), window=win)
      but_Acp.focus_set()
      def close_win(e=None,ident=win_identifier,w=w):
              global win_identifier
              w.unbind_all("<Return>")
              w.unbind_all("<KP_Enter>")
              w.unbind_all("<Escape>")
              win_identifier=None
              w.delete(ident)
      def int_llz(e=None):
              if sel.to_do <> 'hdg':
                sel.hold_hdg = sel.hdg
              # Se supone que ha sido autorizado previamente
              sel.to_do = 'app'
              sel.app_auth = True
              (puntos_alt,llz,puntos_map) = proc_app[sel.fijo_app]
              [xy_llz ,rdl, dist_ayuda, pdte_ayuda, alt_pista] = llz
              sel.route = [[xy_llz,'_LLZ','']]
              sel.int_loc = True
              (puntos_alt,llz,puntos_map) = proc_app[sel.fijo_app]
              # En este paso se desciende el tráfico y se añaden los puntos
              print 'Altitud: ',puntos_alt[0][3]
              sel.set_cfl(puntos_alt[0][3]/100.)
              sel.set_std_rate()
              print sel.get_callsign()+'Interceptando ILS'
              close_win()
      but_Acp['command'] = int_llz
      but_Can['command'] = close_win
      w.bind_all("<Return>",int_llz)
      w.bind_all("<KP_Enter>",int_llz)
      w.bind_all("<Escape>",close_win)

def b_int_loc_no_GP():
    global win_identifier
    if win_identifier<>None:
      w.delete(win_identifier)
      win_identifier=None
      return
    sel = None
    for a in ejercicio:
      if a.esta_seleccionado():
        sel=a
        break
    if sel == None:
      win = Frame(w)
      txt_ruta0 = Label (win,text='Interceptar localizador')
      txt_ruta = Label (win,text='NO HAY NINGUN VUELO SELECCIONADO ',fg='red')
      but_acept = Button(win, text="Aceptar")
      txt_ruta0.pack(side=LEFT)
      txt_ruta.pack(side=LEFT)
      but_acept.pack(side=LEFT)
      win_identifier = w.create_window(ancho/2,alto-75, window=win)
      def close_win(ident=win_identifier):
              global win_identifier
              win_identifier=None
              w.delete(ident)
      but_acept['command'] = close_win
    elif sel.destino not in rwys.keys():
      win = Frame(w)
      txt_ruta0 = Label (win,text='Autorizar a aproximación')
      txt_ruta = Label (win,text='AEROPUERTO DE DESTINO SIN PROCEDIMIENTOS APP ',fg='red')
      but_acept = Button(win, text="Aceptar")
      txt_ruta0.pack(side=TOP)
      txt_ruta.pack(side=LEFT)
      but_acept.pack(side=LEFT)
      win_identifier = w.create_window(ancho/2,alto-75, window=win)
      def close_win(ident=win_identifier):
              global win_identifier
              win_identifier=None
              w.delete(ident)
      but_acept['command'] = close_win
    else:
      if sel.fijo_app == 'N/A':
        win = Frame(w)
        txt_ruta0 = Label (win,text='Interceptar localizador')
        txt_ruta = Label (win,text='VUELO SIN IAF, añada ruta al IAF y reintente ',fg='red')
        but_acept = Button(win, text="Aceptar")
        txt_ruta0.pack(side=LEFT)
        txt_ruta.pack(side=LEFT)
        but_acept.pack(side=LEFT)
        win_identifier = w.create_window(ancho/2,alto-75, window=win)
        def close_win(ident=win_identifier):
                global win_identifier
                win_identifier=None
                w.delete(ident)
        but_acept['command'] = close_win
        return
      global vent_ident_maps
      if vent_ident_maps != None:
        w.delete(vent_ident_maps)
        vent_ident_maps = None
      win = Frame(w)
      title = Label(win, text = 'Interceptar LLZ: '+sel.get_callsign())
      but_Acp = Button(win, text="Aceptar")
      but_Can = Button(win, text="Cancelar")
      title.grid(row=0,column=0, columnspan=2)
      but_Acp.grid(row=1, column=0, columnspan=2)
      but_Can.grid(row=2, column=0, columnspan=2)
      win_identifier = w.create_window(do_scale(sel.pos), window=win)
      but_Acp.focus_set()
      def close_win(e=None,ident=win_identifier,w=w):
              global win_identifier
              w.unbind_all("<Return>")
              w.unbind_all("<KP_Enter>")
              w.unbind_all("<Escape>")
              win_identifier=None
              w.delete(ident)
      def int_llz(e=None):
              if sel.to_do <> 'hdg':
                sel.hold_hdg = sel.hdg
              # Se supone que ha sido autorizado previamente
              (puntos_alt,llz,puntos_map) = proc_app[sel.fijo_app]
              [xy_llz ,rdl, dist_ayuda, pdte_ayuda, alt_pista] = llz
              sel.to_do = 'int_rdl'
              sel.to_do_aux = [xy_llz, rdl]
              print sel.get_callsign()+'Interceptando LLZ'
              close_win()
      but_Acp['command'] = int_llz
      but_Can['command'] = close_win
      w.bind_all("<Return>",int_llz)
      w.bind_all("<KP_Enter>",int_llz)
      w.bind_all("<Escape>",close_win)
  
def ver_detalles():
      global win_identifier
      if win_identifier<>None:
        w.delete(win_identifier)
        win_identifier=None
        return
      sel = None
      for a in ejercicio:
        if a.esta_seleccionado():
          sel=a
      if sel == None:
        win = Frame(w)
        txt_ruta0 = Label (win,text='Ver detalles de vuelo')
        txt_ruta = Label (win,text='NO HAY NINGUN VUELO SELECCIONADO ',fg='red')
        but_acept = Button(win, text="Aceptar")
        txt_ruta0.pack(side=TOP)
        txt_ruta.pack(side=LEFT)
        but_acept.pack(side=LEFT)
        win_identifier = w.create_window(ancho/2,alto-75, window=win)
        def close_win(ident=win_identifier):
                global win_identifier
                win_identifier=None
                w.delete(ident)
        but_acept['command'] = close_win
      else:
        win = Frame(w)
        txt_ind = Label(win,text=sel.get_callsign())
        txt_ind.grid(column=0,row=0,columnspan=4,sticky=E+W)
        txt_origen = Label(win,text='Origen: ')
        txt_origen.grid(column=0,row=1,sticky=E)
        txt_origen2 = Label(win,text=sel.get_origin())
        txt_origen2.grid(column=1,row=1,sticky=E)
        txt_destino = Label(win,text='Destino: ')
        txt_destino.grid(column=2,row=1,sticky=E)
        txt_destino2 = Label(win,text=sel.get_destination())
        txt_destino2.grid(column=3,row=1,sticky=E)
        txt_tipo = Label(win,text='Tipo: ')
        txt_tipo.grid(column=0,row=2,sticky=E)
        txt_tipo2 = Label(win,text=sel.get_kind())
        txt_tipo2.grid(column=1,row=2,sticky=E)
        txt_rfl = Label(win,text='RFL: ')
        txt_rfl.grid(column=2,row=2,sticky=E)
        txt_rfl2 = Label(win,text=str(int(sel.rfl)))
        txt_rfl2.grid(column=3,row=2,sticky=E)
        but_cerrar = Button(win, text="Cerrar ventana")
        but_cerrar.grid(column=1,row=3,columnspan=2)
        win_identifier = w.create_window(ancho/2,alto-75, window=win)
        def close_win(ident=win_identifier):
                global win_identifier
                win_identifier=None
                w.delete(ident)
        but_cerrar['command'] = close_win

def b_orbitar():
      global vent_ident_procs
      if vent_ident_procs != None:
	w.delete(vent_ident_procs)
	vent_ident_procs = None
	win = Frame(w)
      global win_identifier
      if win_identifier<>None:
        w.delete(win_identifier)
        win_identifier=None
        return
      sel = None
      for a in ejercicio:
        if a.esta_seleccionado():
          sel=a
      if sel == None:
        win = Frame(w)
        txt_orbit0 = Label (win,text='Orbitar en presente posición')
        txt_orbit = Label (win,text='NO HAY NINGUN VUELO SELECCIONADO ',fg='red')
        but_acept = Button(win, text="Aceptar")
        txt_orbit0.pack(side=TOP)
        txt_orbit.pack(side=LEFT)
        but_acept.pack(side=LEFT)
        win_identifier = w.create_window(ancho/2,alto-75, window=win)
        def close_win(ident=win_identifier):
                global win_identifier
                win_identifier=None
                w.delete(ident)
        but_acept['command'] = close_win
      else:
        win = Frame(w)
	lbl_orb = Label(win, text="Orbitar ahora")
	ent_side = OptionMenu (win,bg='white')
	num = 0
	for opc in ['DCHA','IZDA']:
		ent_side.add_command(opc)
		num=num+1
	ent_side['value'] = 'DCHA'
	but_Acp = Button(win, text="Aceptar")
	but_Can = Button(win, text="Cancelar")
	lbl_orb.grid(row=0, column=0)
	ent_side.grid(row=3,column=0,columnspan=2)
	but_Acp.grid(row=1, column=0, columnspan=2)
	but_Can.grid(row=2, column=0, columnspan=2)
	window_ident = w.create_window(do_scale(sel.pos), window=win)
        def close_win(e=None,ident=window_ident):
                w.unbind_all("<Return>")
                w.unbind_all("<KP_Enter>")
                w.unbind_all("<Escape>")
		w.delete(ident)
	def set_orbit(e=None,sel=sel):
		side_aux = ent_side.cget('value')
		sel.to_do = 'orbit'
		if side_aux.upper() == 'IZDA':
			sel.to_do_aux = ['IZDA']
		else:
			sel.to_do_aux = ['DCHA']
		print "Orbitando a ",side_aux
		close_win()
	but_Acp['command'] = set_orbit
	but_Can['command'] = close_win
        w.bind_all("<Return>",set_orbit)
        w.bind_all("<KP_Enter>",set_orbit)
        w.bind_all("<Escape>",close_win)
      

def b_rwy_change():
  global vent_ident_procs
  if vent_ident_procs != None:
    w.delete(vent_ident_procs)
    vent_ident_procs = None
    win = Frame(w)
  global win_identifier
  if win_identifier<>None:
    w.delete(win_identifier)
    win_identifier=None
    return
  rwy_chg = Frame(w)
  txt_titulo = Label (rwy_chg, text = 'Nuevas pistas en uso')
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
  but_acept = Button(rwy_chg,text='Hecho')
  but_acept.grid(column=0,row=line)
  win_identifier = w.create_window(400,400,window=rwy_chg)
  def close_rwy_chg(e=None,ident = win_identifier):
    global rwyInUse
    com_airp.pop(0)
    for [airp,num] in com_airp:
      print 'Pista en uso de ',airp,' es ahora: ',num.cget('value'),'. Cambiando los procedimientos'
      rwyInUse[airp] = num.cget('value')
      for avo in ejercicio:
        complete_flight_plan(avo)
        if avo.origen in rwys.keys() and not avo.is_flying():
          avo.route.pop(0)
        avo.set_app_fix()   
    w.delete(ident)
  but_acept['command']= close_rwy_chg
  
  but_cancel = Button(rwy_chg,text='Descartar')
  but_cancel.grid(column=1,row=line)
  def discard_rwy_chg(e=None,ident = win_identifier):
       w.delete(ident)
  but_cancel['command']= discard_rwy_chg
  
def b_auth_approach():
    global win_identifier
    if win_identifier<>None:
      w.delete(win_identifier)
      win_identifier=None
      return
    sel = None
    for a in ejercicio:
      if a.esta_seleccionado():
        sel=a
    if sel == None:
      win = Frame(w)
      txt_ruta0 = Label (win,text='Autorizar a aproximación')
      txt_ruta = Label (win,text='NO HAY NINGUN VUELO SELECCIONADO ',fg='red')
      but_acept = Button(win, text="Aceptar")
      txt_ruta0.pack(side=TOP)
      txt_ruta.pack(side=LEFT)
      but_acept.pack(side=LEFT)
      win_identifier = w.create_window(ancho/2,alto-75, window=win)
      def close_win(ident=win_identifier):
              global win_identifier
              win_identifier=None
              w.delete(ident)
      but_acept['command'] = close_win
    elif sel.destino not in rwys.keys():
      win = Frame(w)
      txt_ruta0 = Label (win,text='Autorizar a aproximación')
      txt_ruta = Label (win,text='AEROPUERTO DE DESTINO SIN PROCEDIMIENTOS APP ',fg='red')
      but_acept = Button(win, text="Aceptar")
      txt_ruta0.pack(side=TOP)
      txt_ruta.pack(side=LEFT)
      but_acept.pack(side=LEFT)
      win_identifier = w.create_window(ancho/2,alto-75, window=win)
      def close_win(ident=win_identifier):
              global win_identifier
              win_identifier=None
              w.delete(ident)
      but_acept['command'] = close_win
    else:
      global vent_ident_maps
      if vent_ident_maps != None:
        w.delete(vent_ident_maps)
        vent_ident_maps = None
      for i in range(len(sel.route),0,-1):
        if sel.route[i-1][1] in proc_app.keys():
          fijo_app = sel.route[i-1][1]
          break
      win = Frame(w)
      title = Label(win, text = 'Aut. app. '+sel.get_callsign())
      lbl_apt = Label(win, text="Aerop.:")
      ent_apt = Entry(win, width=5)
      ent_apt.insert(0, sel.destino)
      lbl_fix = Label(win, text="IAF:")
      ent_fix = Entry(win, width=6)
      ent_fix.insert(0, fijo_app)
      but_Acp = Button(win, text="Aceptar")
      but_Can = Button(win, text="Cancelar")
      title.grid(row=0,column=0, columnspan=2)
      lbl_apt.grid(row=1, column=0)
      ent_apt.grid(row=1, column=1)
      lbl_fix.grid(row=2, column=0)
      ent_fix.grid(row=2, column=1)
      but_Acp.grid(row=3, column=0, columnspan=2)
      but_Can.grid(row=4, column=0, columnspan=2)
      win_identifier = w.create_window(do_scale(sel.pos), window=win)
      ent_fix.focus_set()
      def close_win(e=None,ident=win_identifier,w=w):
              global win_identifier
              w.unbind_all("<Return>")
              w.unbind_all("<KP_Enter>")
              w.unbind_all("<Escape>")
              win_identifier=None
              w.delete(ident)
      def auth_app(e=None,avo=sel):
              global win_identifier
              avo.app_auth = True
              avo._map = False
              avo.fijo_app = ''
              for i in range(len(avo.route),0,-1):
                if avo.route[i-1][1] in proc_app.keys():
                  avo.fijo_app = avo.route[i-1][1]
                  break
              if avo.fijo_app == '': # No encuentra procedimiento de aprox.
                pass
              (puntos_alt,llz,puntos_map) = proc_app[avo.fijo_app]
              # En este paso se desciende el tráfico y se añaden los puntos
              print 'Altitud: ',puntos_alt[0][3]
              avo.set_cfl(puntos_alt[0][3]/100.)
              if avo.to_do == 'hld':
                pass
              else:
                avo.to_do = 'app'
                for i in range(len(avo.route),0,-1):
                  if avo.route[i-1][1] == avo.fijo_app:
                    avo.route = sel.route[:i]
                    break
                for [a,b,c,h] in puntos_alt:
                  avo.route.append([a,b,c])
                avo.route.append([llz[0],'_LLZ',''])
              print "Autorizado aproximación: ", avo.route
              win_identifier=None
              close_win()
      but_Acp['command'] = auth_app
      but_Can['command'] = close_win
      w.bind_all("<Return>",auth_app)
      w.bind_all("<KP_Enter>",auth_app)
      w.bind_all("<Escape>",close_win)
 
  
ver_ventana_auxiliar=True

def ventana_auxiliar(e):
  global ver_ventana_auxiliar,vent_ident,vent_ident_izda,vent_ident_dcha
  if ver_ventana_auxiliar:
    if ancho > 800.:
      ventana=Frame(w,bg='gray',width=ancho)
      but_inicio = Button(ventana,bitmap='@'+IMGDIR+'start.xbm',command=b_inicio)
      but_inicio.pack(side=LEFT,expand=1,fill=X)
      but_parar = Button(ventana,bitmap='@'+IMGDIR+'pause.xbm',command=b_parar)
      but_parar.pack(side=LEFT,expand=1,fill=X)
      but_izq = Button(ventana,bitmap='@'+IMGDIR+'left.xbm',command=b_izquierda)
      but_izq.pack(side=LEFT,expand=1,fill=X)
      but_arriba = Button(ventana,bitmap='@'+IMGDIR+'up.xbm',command=b_arriba)
      but_arriba.pack(side=LEFT,expand=1,fill=X)
      but_abajo = Button(ventana,bitmap='@'+IMGDIR+'down.xbm',command=b_abajo)
      but_abajo.pack(side=LEFT,expand=1,fill=X)
      but_derecha = Button(ventana,bitmap='@'+IMGDIR+'right.xbm',command=b_derecha)
      but_derecha.pack(side=LEFT,expand=1,fill=X)
      but_zoom_mas = Button(ventana,bitmap='@'+IMGDIR+'zoom.xbm',command=b_zoom_mas)
      but_zoom_mas.pack(side=LEFT,expand=1,fill=X)
      but_zoom_menos = Button(ventana,bitmap='@'+IMGDIR+'unzoom.xbm',command=b_zoom_menos)
      but_zoom_menos.pack(side=LEFT,expand=1,fill=X)
      but_standard = Button(ventana,bitmap='@'+IMGDIR+'center.xbm',command=b_standard)
      but_standard.pack(side=LEFT,expand=1,fill=X)
      but_tamano_etiq = Button(ventana,bitmap='@'+IMGDIR+'labelsize.xbm',command=b_tamano_etiquetas)
      but_tamano_etiq.pack(side=LEFT,expand=1,fill=X)
      but_term = Button(ventana,text='Kill',command=kill_acft)
      but_term.pack(side=LEFT,expand=1,fill=X)
      but_ruta = Button(ventana,text='Ruta',command=nueva_ruta)
      but_ruta.pack(side=LEFT,expand=1,fill=X)
      but_datos = Button(ventana,text='Datos',command=ver_detalles)
      but_datos.pack(side=LEFT,expand=1,fill=X)
      but_quitar_lads = Button(ventana,text='LADs', fg = 'red',command = quitar_lads)
      but_quitar_lads.pack(side=LEFT,expand=1,fill=X)
      but_quitar_fpr = Button(ventana,text='Rutas', fg = 'red',command = quitar_fpr)
      but_quitar_fpr.pack(side=LEFT,expand=1,fill=X)
      but_ver_proc = Button(ventana, text = 'PROCs')
      but_ver_proc.pack(side=LEFT,expand=1,fill=X)
      def procs_buttons():
        global vent_ident_procs
        if vent_ident_procs != None:
          w.delete(vent_ident_procs)
          vent_ident_procs = None
          return
        ventana_procs = Frame(w,bg='gray')
        but_espera = Button(ventana_procs, text='Esperas', command = define_holding)
        but_espera.grid(column=0,row=0,sticky=E+W)
        but_hdg_fix = Button(ventana_procs, text = 'HDG despues fijo', command = hdg_after_fix)
        but_hdg_fix.grid(column=0,row=1,sticky=E+W)
        but_int_rdl = Button(ventana_procs, text = 'Int. RDL', command = int_rdl)
        but_int_rdl.grid(column=0,row=2,sticky=E+W)
        but_chg_rwy = Button(ventana_procs, text = 'Cambio RWY', command = b_rwy_change)
        but_chg_rwy.grid(column=0,row=3,sticky=E+W)
        but_orbit = Button(ventana_procs, text = 'Orbitar aquí', command = b_orbitar)
        but_orbit.grid(column=0,row=4,sticky=E+W)
	but_wind = Button(ventana_procs, text = 'Cambiar viento', command = cambiar_viento)
        but_wind.grid(column=0,row=5,sticky=E+W)
	vent_ident_procs=w.create_window(ventana.winfo_x()+but_ver_proc.winfo_x(),alto-ventana.winfo_height(),window=ventana_procs,anchor='sw')
      but_ver_proc['command'] = procs_buttons
      but_ver_app = Button(ventana, text = 'APP')
      but_ver_app.pack(side=LEFT,expand=1,fill=X)
      def maps_buttons():
        global vent_ident_maps
        if vent_ident_maps != None:
          w.delete(vent_ident_maps)
          vent_ident_maps = None
          return
        ventana_maps = Frame(w,bg='gray')
        but_app_proc = Button(ventana_maps, text = 'APP PROC.', command = b_auth_approach)
        but_app_proc.grid(column=0,row=0,sticky=E+W)
        but_ils_vec = Button(ventana_maps, text = 'ILS (vectores)', command = b_int_llz)
        but_ils_vec.grid(column=0,row=1,sticky=E+W)
        but_loc = Button(ventana_maps, text = 'LOCALIZADOR', command = b_int_loc_no_GP)
        but_loc.grid(column=0,row=2,sticky=E+W)
        but_exe_map = Button(ventana_maps, text = 'EJECUTAR MAP', command = b_execute_map)
        but_exe_map.grid(column=0,row=3,sticky=E+W)
        vent_ident_maps=w.create_window(ventana.winfo_x()+but_ver_app.winfo_x(),alto-ventana.winfo_height(),window=ventana_maps,anchor='sw')
      but_ver_app['command'] = maps_buttons
      but_auto_sep = Checkbutton(ventana, text = 'SEP', variable = var_auto_sep, command=b_auto_separation)
      but_auto_sep.pack(side=LEFT,expand=1,fill=X)
      but_ver_maps = Button(ventana, text = 'MAPAS')
      but_ver_maps.pack(side=LEFT,expand=1,fill=X)
      def mapas_buttons():
        global vent_ident_mapas
        if vent_ident_mapas != None:
          w.delete(vent_ident_mapas)
          vent_ident_mapas = None
          return
        ventana_mapas = Frame(w,bg='gray')
        but_ver_ptos = Checkbutton(ventana_mapas, text = 'Fijos', variable = var_ver_ptos, command=b_show_hide_points)
        but_ver_ptos.grid(column=0,row=0,sticky=E+W)
        but_ver_tmas = Checkbutton(ventana_mapas, text = 'TMAs', variable = var_ver_tmas, command=b_show_hide_tmas)
        but_ver_tmas.grid(column=0,row=1,sticky=E+W)
        but_ver_deltas = Checkbutton(ventana_mapas, text = 'Deltas', variable = var_ver_deltas, command=b_show_hide_deltas)
        but_ver_deltas.grid(column=0,row=2,sticky=E+W)
	
	myrow = 3
	map_name_list = local_maps.keys()
	map_name_list.sort()
	for map_name in map_name_list:
          but_ver_local_map = Checkbutton(ventana_mapas, text = map_name, variable = var_ver_localmap[map_name], command=b_show_hide_localmaps)
          but_ver_local_map.grid(column=0,row=myrow,sticky=E+W)
	  myrow += 1
	
        vent_ident_mapas=w.create_window(ventana.winfo_x()+but_ver_maps.winfo_x(),alto-ventana.winfo_height(),window=ventana_mapas,anchor='sw')
      but_ver_maps['command'] = mapas_buttons
      def cambia_vect_vel(e=None):
          set_speed_time(float(var_vect_vel.get())/60.)
          redraw_all()
      cnt_vect_vel = Control(ventana, label="Vel:", min=0, max=5, integer=1, command=cambia_vect_vel, variable=var_vect_vel)
      cnt_vect_vel.pack(side=LEFT,expand=1,fill=X)
      def cambia_vel_reloj(e=None):
          set_vel_reloj(float(var_vel_reloj.get()))
      cnt_vel_reloj = Control(ventana, label="Clock X:", min=0.5, max=9.0, step=0.1, command=cambia_vel_reloj, variable=var_vel_reloj)
      cnt_vel_reloj.pack(side=LEFT,expand=1,fill=X)
      
      vent_ident=w.create_window(0,alto,width=ancho,window=ventana,anchor='sw')
      ventana.update_idletasks()
      logging.debug ('Auxiliary window width: '+str(ventana.winfo_width()))
    
    else:
      ventana=Frame(w,bg='gray')
      button_width = 25 + (ancho - 804)/7
      but_inicio = Button(ventana,bitmap='@'+IMGDIR+'start.xbm',command=b_inicio)
      but_inicio.grid(column=0,row=0,sticky=E+W)
      but_parar = Button(ventana,bitmap='@'+IMGDIR+'pause.xbm',command=b_parar)
      but_parar.grid(column=1,row=0,sticky=E+W)
      but_arriba = Button(ventana,bitmap='@'+IMGDIR+'up.xbm',command=b_arriba)
      but_arriba.grid(column=1,row=1,sticky=E+W)
      but_izq = Button(ventana,bitmap='@'+IMGDIR+'left.xbm',command=b_izquierda)
      but_izq.grid(column=0,row=1,sticky=E+W)
      but_abajo = Button(ventana,bitmap='@'+IMGDIR+'down.xbm',command=b_abajo)
      but_abajo.grid(column=2,row=1,sticky=E+W)
      but_derecha = Button(ventana,bitmap='@'+IMGDIR+'right.xbm',command=b_derecha)
      but_derecha.grid(column=3,row=1,sticky=E+W)
      but_zoom_mas = Button(ventana,bitmap='@'+IMGDIR+'zoom.xbm',command=b_zoom_mas)
      but_zoom_mas.grid(column=4,row=1,sticky=E+W)
      but_zoom_menos = Button(ventana,bitmap='@'+IMGDIR+'unzoom.xbm',command=b_zoom_menos)
      but_zoom_menos.grid(column=5,row=1,sticky=E+W)
      but_standard = Button(ventana,bitmap='@'+IMGDIR+'center.xbm',command=b_standard)
      but_standard.grid(column=6,row=1,sticky=E+W)
      but_tamano_etiq = Button(ventana,bitmap='@'+IMGDIR+'labelsize.xbm',command=b_tamano_etiquetas)
      but_tamano_etiq.grid(column=7,row=1)
      def cambia_vect_vel(e=None):
          set_speed_time(float(var_vect_vel.get())/60.)
          redraw_all()
      cnt_vect_vel = Control(ventana, label="Velocidad:", min=0, max=5, integer=1, command=cambia_vect_vel, variable=var_vect_vel)
      cnt_vect_vel.grid(column=2,row=0,columnspan=4)
      def cambia_vel_reloj(e=None):
          set_vel_reloj(float(var_vel_reloj.get()))
      cnt_vel_reloj = Control(ventana, label="Vel reloj:", min=0.5, max=9.0, step=0.1, command=cambia_vel_reloj, variable=var_vel_reloj)
      cnt_vel_reloj.grid(column=6,row=0,columnspan=3)
  #     separador1 = Label(ventana,text='-----PSEUDOPILOTO-----')
  #     separador1.grid(column=0,row=10,columnspan=3,sticky=E+W)
      but_term = Button(ventana,text='Kill',command=kill_acft)
      but_term.grid(column=8,row=1)
      but_ruta = Button(ventana,text='Ruta',command=nueva_ruta)
      but_ruta.grid(column=9,row=1)
      but_datos = Button(ventana,text='Datos',command=ver_detalles)
      but_datos.grid(column=10,row=1)
      but_quitar_lads = Button(ventana,text='LADs', fg = 'red',command = quitar_lads)
      but_quitar_lads.grid(column=11,row=1)
      but_quitar_fpr = Button(ventana,text='Rutas', fg = 'red',command = quitar_fpr)
      but_quitar_fpr.grid(column=12,row=1)
      but_espera = Button(ventana, text='HLD', command = define_holding)
      but_espera.grid(column=13,row=1)
      but_hdg_fix = Button(ventana, text = 'HDG<FIX', command = hdg_after_fix)
      but_hdg_fix.grid(column=14,row=1)
      but_int_rdl = Button(ventana, text = 'RDL', command = int_rdl)
      but_int_rdl.grid(column=15,row=1)
      but_int_rdl = Button(ventana, text = 'RWY', command = b_rwy_change)
      but_int_rdl.grid(column=16,row=1)
#       but_int_rdl = Button(ventana, text = 'DEP', command = None)
#       but_int_rdl.grid(column=17,row=1)
      but_int_rdl = Button(ventana, text = 'APP', command = b_auth_approach)
      but_int_rdl.grid(column=18,row=1)
      but_int_rdl = Button(ventana, text = 'LLZ', command = b_int_llz)
      but_int_rdl.grid(column=17,row=1)
      but_int_rdl = Button(ventana, text = 'MAP', command = b_execute_map)
      but_int_rdl.grid(column=18,row=0)
      but_auto_sep = Checkbutton(ventana, text = 'AUTO SEP', variable = var_auto_sep, command=b_auto_separation)
      but_auto_sep.grid(column=9,row=0,columnspan=2,sticky = W+E)
      but_ver_ptos = Checkbutton(ventana, text = 'Nombre Fijos', variable = var_ver_ptos, command=b_show_hide_points)
      but_ver_ptos.grid(column=11,row=0,columnspan=2,sticky = W+E)
      but_ver_tmas = Checkbutton(ventana, text = 'TMAs', variable = var_ver_tmas, command=b_show_hide_tmas)
      but_ver_tmas.grid(column=13,row=0,columnspan=2,sticky = W+E)
      but_ver_deltas = Checkbutton(ventana, text = 'Deltas', variable = var_ver_deltas, command=b_show_hide_deltas)
      but_ver_deltas.grid(column=15,row=0,columnspan=2,sticky = W+E)
      
      vent_ident=w.create_window(0,alto,window=ventana,anchor='sw')
      ventana.update_idletasks()
  
  else:
    w.delete(vent_ident)
    
  ver_ventana_auxiliar = not ver_ventana_auxiliar
  
ventana_auxiliar(None)
clock=RaClock(w)
clock.bind('<Button-1>',ventana_auxiliar)

get_scale()

if not auto_departures:
  manual_dep_window(last_update/60./60.)

redraw_all()

timer()

def change_widget_size(e):
  global ancho,alto,ver_ventana_auxiliar
  ancho = e.width
  alto = e.height
  w.update_idletasks()
  ventana_auxiliar(None)
  ventana_auxiliar(None)
  
w.bind('<Configure>',change_widget_size)

root.mainloop()

