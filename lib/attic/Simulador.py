#!/usr/bin/python
#-*- coding:iso8859-15 -*-
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


#############################
# W A R N I N G ! ! !
#
# Do not edit this code. This code is actually not in use anymore.
# Functionality here is now implemented in GTA.py and Pseudopilot.py
# and this file is left here only for reference for tidbits of functionality
# not yet ported to the new architecture (namely, storms)
#
#############################


def set_latest_lad(num):
    global latest_lad_event_processed
    print 'Set_latest_lad llamado. Antes despues', latest_lad_event_processed,num
    latest_lad_event_processed = num
    
    
        # Modules to be imported  
from avion import *
from RaDisplay import *
from FIR import *
from tpv import *
import Pseudopilot
from Pseudopilot import PpDisplay
from Tix import *
import Image
import ImageTk
Image._initialized=2
from time import time,sleep
import lads
from math import sqrt
import os.path
import ConfMgr
import logging
try:
  from twisted.internet.protocol import Factory
  from twisted.internet import reactor, tksupport
  from twisted.protocols.basic import NetstringReceiver
  import pickle
  import zlib
except:
  logging.warning ("Error while importing the Twisted Framefork modules")

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
storms = []
win_manual = None
win_datos = None
vent_ident_dcha = None
vent_ident_maps = None
vent_ident_procs = None
vent_ident_mapas = None
vent_ident_tabs = None
conf = ConfMgr.CrujiConfig()


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
#root.withdraw()

fir_file = g_seleccion_usuario[0][1]
fir = FIR(fir_file)
for sector,section in fir._sector_sections.items():
    if section==g_seleccion_usuario[1][1]:
        break
#display=PpDisplay(ejercicio,'Crujisim - '+os.path.basename(g_seleccion_usuario[2][1]),
#                  CRUJISIMICO,fir,sector)

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

label_font_size = 11
label_font = tkFont.Font(family="Helvetica",size=label_font_size)

# Definición de LAD's en el canvas
class fix_point:
    def __init__(self,coord):
        self.pos = coord
        self.se_pinta = True
        
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

def draw_all_lads(canvas):
    global superlad, all_lads
    canvas.delete('crosspoint')
    for lad in all_lads:
        if lad.line_id != None: canvas.delete(lad.line_id)
        if lad.text_id1 != None: canvas.delete(lad.text_id1)
        if lad.text_id2 != None: canvas.delete(lad.text_id2)
        if lad.text_id3 != None: canvas.delete(lad.text_id3)
        if lad.text_id4 != None: canvas.delete(lad.text_id4)
        if lad.origin.se_pinta == False:
            all_lads.remove(lad)
            continue
        if lad.destination.se_pinta == False:
            all_lads.remove(lad)
            continue
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
        #added the condition min_dist_time<500.0 to avoid overflow problems when min_dist_time was too high
        if (min_dist_time != None) and (min_dist_time > 0.0)and (min_dist_time<500.0):
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
    if not conf.show_palotes_image:
        return
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
        palote_identifier = canvas.create_window(ancho-wi,alto-he, window=win)
        
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
    #import winsound
    try:
        print_fs._callsigns=print_fs._callsigns
    except:
        print_fs._callsigns={}
    if print_fs._callsigns.has_key(callsign) and print_fs._callsigns[callsign]==3:
        return
    if sys.platform=='win32' and conf.printer_sound:
        import winsound
        try:
            if reloj_funciona:  # Avoid the annoying sound at the beginning
            #                winsound.PlaySound("*", winsound.SND_ALIAS|winsound.SND_NOSTOP|winsound.SND_ASYNC)
                winsound.PlaySound(SNDDIR+'/printer.wav', winsound.SND_NOSTOP|winsound.SND_ASYNC)
        except:
            return
        if not print_fs._callsigns.has_key(callsign):
            print_fs._callsigns[callsign]=0
        print_fs._callsigns[callsign]+=1
        
        
        

        
def draw_SID_STAR(object,procedimientos,canvas = w):
    
    def draw_single_SID_STAR(single_sid_star,remove_underscored = True):
        for i in range(0,len(single_sid_star[1])-1):
            #We are not going to plot points which name starts with undescore
            first_point_chosen = False
            last_point_chosen = False
            if single_sid_star[1][i][1][0]<>'_' or not remove_underscored:
                cx0 = float(single_sid_star[1][i][0][0])
                cy0 = float(single_sid_star[1][i][0][1])
                first_point_chosen = True
                for j in range(i+1,len(single_sid_star[1])):
                    if single_sid_star[1][j][1][0]<>'_' or not remove_underscored:
                        cx1 = float(single_sid_star[1][j][0][0])
                        cy1 = float(single_sid_star[1][j][0][1])
                        last_point_chosen = True
                        break
            if first_point_chosen and last_point_chosen:
                (px0, py0) = do_scale((cx0,cy0))
                (px1, py1) = do_scale((cx1,cy1))
                canvas.create_line(px0, py0, px1, py1, fill=color, tag='local_maps')
    
    sid_star_index = 0              #plot SID by default
    if object[0] == 'draw_sid':
        sid_star_index = 0
    elif object[0] == 'draw_star':
        sid_star_index = 1
        
    sid_star_rwy = object[1]
    sid_star_name = object[2]
    if len(object) > 3:
        color = object[3]
    else:
        color = 'white'
        
    for sid_star_index_word in procedimientos[sid_star_rwy][sid_star_index]:              #cycle through al SID's or STAR's of one RWY
        sid_star=procedimientos[sid_star_rwy][sid_star_index][sid_star_index_word]
        if (sid_star_name == '') or (sid_star_name == sid_star[0]):
            draw_single_SID_STAR(sid_star,True)
            
def draw_polyline(object,fir1,canvas):
    #draw a series of lines from point to point defined in object[2:]. object[2:] contains
    #points' names and points_definition contains de names and coordinates.
    color = object[1]
    if object[1]=='':
        color = 'white'
    if len(object) > 3:
        point_name = str(object[2])
#        (px0, py0) = do_scale(fir1.get_point_coordinates(point_name))
        (px0, py0) = do_scale(fir1.get_point_coordinates(point_name))
        for point in object[3:]:
            (px1, py1) = do_scale(fir1.get_point_coordinates(point))
            canvas.create_line(px0, py0, px1, py1, fill=color, tag='local_maps')
            (px0, py0) = (px1,py1)
        
    
  
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
            elif ob[0] == 'draw_star' or ob[0] == 'draw_sid':
                draw_SID_STAR(ob,fir.procedimientos,w)
            elif ob[0] == 'polyline':
                draw_polyline(ob,fir,w)
                
    w.delete('fichas')
    # Poner las fichas que se imprimen
    draw_print_list()
    # Dibujar los aviones
    for acft in ejercicio:
        acft.redraw(w)
        
    draw_all_lads(w)
    for s in storms[:]:
        s.redraw()
    # Comprobar si hay PAC o VAC
    # First we reset state
    for acft in ejercicio:
        acft.vt.pac=acft.vt.vac=False
    for i in range(len(ejercicio)):
        for j in range(i+1,len(ejercicio)):
            if pac(ejercicio[i],ejercicio[j]):
                ejercicio[i].vt.pac=True
                ejercicio[j].vt.pac=True
                
    w.delete('vac')
    poner_palote=False
    palote(poner_palote,w)
    for i in range(len(ejercicio)):
        for j in range(i+1,len(ejercicio)):
            line=()
            if vac(ejercicio[i],ejercicio[j]):
                poner_palote=True
                ejercicio[i].vt.vac=True
                ejercicio[i].vt.pac=False
                line=do_scale(ejercicio[i].get_coords())
                ejercicio[j].vt.vac=True
                ejercicio[j].vt.pac=False
                line=line+do_scale(ejercicio[j].get_coords())
                w.create_line(line,fill='red',tag='vac')
                
    palote(poner_palote,w)
    t=float(tlocal(t0))
    ho=int(t/60/60)
    m=int(t/60)-ho*60
    s=int(t)-60*60*ho-60*m
    w.stop_separating = True
    
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

def separate_labels(canvas):
    global ejercicio,ancho,alto
    width=ancho
    height=alto
    tracks=[]
    for acft in ejercicio:
        tracks.append(acft.vt)
    
    crono = time()
    canvas.stop_separating = False
    
    # Find the tracks that we have to separate
    sep_list = []  # List of track whose labels we must separate
    o = 0  # Amount of label overlap that we can accept
    new_pos = {}  # For each track, maintain the coords of the label position being tested
    best_pos = {} # These are the best coodinates found for each label track
    
    for track in tracks:
        x,y=track.label_x,track.label_y
        h,w=track.label_height,track.label_width
        if not track.visible or track.plot_only or x<0 or y<0 or x+w>width or y+h>height:
            continue
        sep_list.append(track)
        track.label_x_alt,track.label_y_alt=x,y  # Set the alternate coords to be used later
        track.label_heading_alt = track.label_heading
        new_pos[track]=(x,y)
        
    best_pos = new_pos
    move_list = []

    #print [t.cs for t in sep_list]
    # Find intersecting labels
    for i in range (len(sep_list)):
        if time()-crono > 3:
            break
        ti = sep_list[i]  # Track i
        # Find vertices of track label i
        ix0,iy0 = ti.x,ti.y
        ix1,iy1 = ti.label_x,ti.label_y
        ix2,iy2 = ix1+ti.label_width, iy1+ti.label_height
        # Lists of conflicted labels and other helper lists
        conflict_list = [ti]
        cuenta = {ti:0}
        giro_min = [0]
        intersectan = 0
        
        for j in range(i+1,len(sep_list)):
            tj = sep_list[j]  # Track j
            # Find vertices of track label j
            jx0,jy0 = tj.x,tj.y
            jx1,jy1 = tj.label_x,tj.label_y
            jx2,jy2 = jx1+tj.label_width, jy1+tj.label_height
            
            conflict = False
            # Check whether any of the vertices, or the track plot of
            # track j is within label i
            # o is the label overlap. Defined at the beginning of the function
            for (x,y) in [(jx0,jy0),(jx1,jy1),(jx2,jy1),(jx2,jy2),(jx1,jy2)]:
                if x-o>ix1 and x+o<ix2 and y-o>iy1 and y+o<iy2:
                    conflict = True
                    break
            # Check whether the plot of track i is within the label j
            x,y=ix0,iy0
            if x-o>jx1 and x+o<jx2 and y-o>jy1 and y+o<jy2:
                conflict = True
            
            #canvas.create_line(jx0,jy0,jx1,jy1,jx2,jy1,jx2,jy2,jx1,jy2,fill='blue',tags='sep')
            
            if conflict == True:
                intersectan = intersectan + 1
                if (tj not in conflict_list) and len(conflict_list)<10:
                    conflict_list.append(tj)
                    cuenta[tj]=0
                    giro_min.append(0)
        # Si intersectan probamos las posiciones posibles de la ficha para ver si libra en alguna. En caso contrario,se escoge 
        # el de menor interferenci
        #print("Intersecting labels: "+str([t.cs for t in conflict_list]))
        intersectan_girado = intersectan
        cuenta_menos_inter = cuenta
        menos_inter = intersectan
        crono2 = time()
        rotating_labels = len(conflict_list)
        rotating_steps = 8
        rotating_angle = 360./rotating_steps
        # We want to try rotating first the tracks that were manually rotated,
        # and last those that were more recently manually rotated
        # last_rotation is bigger for the more recently rotated
        conflict_list.sort(lambda x,y: -cmp(x.last_rotation,y.last_rotation))
        #if len(conflict_list)>1:
        #    logging.debug("Conflict among "+str([t.cs for t in conflict_list]))
        while (intersectan_girado > 0) and (cuenta[conflict_list[0]] < rotating_steps) and rotating_labels and (time()-crono2)<1:
            canvas.update()
            if canvas.stop_separating: return  # Set, for instance, when moving the display
            # Try rotating one of the labels on the list
            for k in range(len(conflict_list)-1,-1,-1):
                t = conflict_list[k]
                if not t.auto_separation:
                    rotating_labels -= 1
                    continue  # Don't move labels that don't want to be moved
                if cuenta[t]<rotating_steps:
                    cuenta[t] += 1
                    # Find the alternative position of the label after the rotation
                    [x,y] = (t.x,t.y)
                    t.label_heading_alt += rotating_angle
                    ldr_x = x + t.label_radius * sin(radians(t.label_heading_alt))
                    ldr_y = y + t.label_radius * cos(radians(t.label_heading_alt))

                    ldr_x_offset = ldr_x - x
                    ldr_y_offset = ldr_y - y
                    # l_xo and lyo are the offsets of the label with respect to the plot
                    if ldr_x_offset > 0.:  
                        new_l_x = x+ldr_x_offset
                    else:
                        new_l_x = x+ldr_x_offset - t.label_width
                    new_l_y = y+ldr_y_offset -10
                    t.label_heading_alt = 90.0-degrees(atan2(ldr_y_offset, ldr_x_offset))
                    
                    t.label_x_alt = new_l_x
                    t.label_y_alt = new_l_y
                    new_pos[t]=(new_l_x,new_l_y)

                    break
                
                elif cuenta[t]==rotating_steps: 
                    cuenta[t] = 0 
            # Comprobamos si está separados todos entre ellos
            # We can't afford to call a function in here because this is
            # very deeply nested, and the function calling overhead
            # would be too much
            intersectan_girado = 0
            #logging.debug("Rotations: "+str([(t.cs, cuenta[t]) for t in conflict_list]))
            for k in range(len(conflict_list)):
                ti = conflict_list[k]  # Track i
                # Find vertices of track label i
                ix0,iy0 = ti.x,ti.y
                ix1,iy1 = ti.label_x_alt,ti.label_y_alt
                ix2,iy2 = ix1+ti.label_width, iy1+ti.label_height
                for j in range(k+1,len(conflict_list)):            
                    tj = conflict_list[j]  # Track j
                    # Find vertices of track label j
                    jx0,jy0 = tj.x,tj.y
                    jx1,jy1 = tj.label_x_alt,tj.label_y_alt
                    jx2,jy2 = jx1+tj.label_width, jy1+tj.label_height
                    
                    conflict = False
                    # Check whether any of the vertices, or the track plot of
                    # track j is within label i
                    # o is the label overlap. Defined at the beginning of the function
                    for (x,y) in [(jx0,jy0),(jx1,jy1),(jx2,jy1),(jx2,jy2),(jx1,jy2)]:
                        if x-o>ix1 and x+o<ix2 and y-o>iy1 and y+o<iy2:
                            conflict = True
                            break
                    # Check whether the plot of track i is within the label j
                    x,y=ix0,iy0
                    if x-o>jx1 and x+o<jx2 and y-o>jy1 and y+o<jy2:
                        conflict = True
                    
                    #logging.debug("Checking "+ti.cs+","+tj.cs+": "+str(conflict))    
                    if conflict == True:
                        intersectan_girado += 1
                        
            # Comprobamos que no estemos afectando a ningn otro avión con el reción girado. En caso contrario, se añ
            if intersectan_girado == 0:
                for ti in conflict_list:
                    if len(conflict_list)>=10: break
                    # Find vertices of track label i
                    ix0,iy0 = ti.x,ti.y
                    ix1,iy1 = ti.label_x_alt,ti.label_y_alt
                    ix2,iy2 = ix1+ti.label_width, iy1+ti.label_height                        
                    for tj in sep_list:
                        if (ti==tj) or (tj in conflict_list): continue

                        # Find vertices of track label j
                        jx0,jy0 = tj.x,tj.y
                        jx1,jy1 = tj.label_x_alt,tj.label_y_alt
                        jx2,jy2 = jx1+tj.label_width, jy1+tj.label_height
                        
                        conflict = False
                        # Check whether any of the vertices, or the track plot of
                        # track j is within label i
                        # o is the label overlap. Defined at the beginning of the function
                        for (x,y) in [(jx0,jy0),(jx1,jy1),(jx2,jy1),(jx2,jy2),(jx1,jy2)]:
                            if x-o>ix1 and x+o<ix2 and y-o>iy1 and y+o<iy2:
                                conflict = True
                                break
                        # Check whether the plot of track i is within the label j
                        x,y=ix0,iy0
                        if x-o>jx1 and x+o<jx2 and y-o>jy1 and y+o<jy2:
                            conflict = True

                        if conflict:
                            intersectan_girado += 1
                            conflict_list.append(tj)
                            cuenta[tj]=0
                            #logging.debug("Added to conflict list: "+tj.cs)

            # En caso de que haya conflicto, escogemos el giro con menos interseccione
            if intersectan_girado < menos_inter:
                menos_inter = intersectan_girado
                cuenta_menos_inter = cuenta
                best_pos = new_pos.copy()
                
        if intersectan_girado>0:
            logging.debug("Unable to separate "+str(intersectan_girado)+" label(s)")
            if cuenta[conflict_list[0]] >= rotating_steps:
                logging.debug("No solution found after checking all posibilities")
            if not rotating_labels:
                logging.debug("No autorotating labels left")
            if (time()-crono2>=1):
                logging.debug("No solution found after 1 second")
        
        move_list += conflict_list
        
    # We need to force redrawing of track labels that have moved
    # First we eliminate duplicates
    d = {}
    for track in move_list:
        d[track]=1
    move_list = d.keys()
    #logging.debug("Moving labels: "+str([t.cs for t in move_list if ((t.label_x,t.label_y)!=best_pos[t])]))
    # Update the labels
    for t in move_list:
        (x,y)=best_pos[t]
        t.label_coords(x,y)

    
def se_cortan (label_modif,i,j):
  # Devuelve si las fichas está separadas entre los aviones i y j de ejercicio
    if ejercicio[i].is_flying():
        (xip,yip) = do_scale(ejercicio[i].get_coords())
        xis , yis = xip + label_modif[i][0] , yip + label_modif[i][1]
        xii , yii = xis + ejercicio[i].vt.label_width , yis + ejercicio[i].vt.label_height
        # Comprobamos las cuatro esquinas del avión j y que no se corten los soportes de fichas, asícomo ningn plot
        if ejercicio[j].is_flying():
            (xjp,yjp) = do_scale(ejercicio[j].get_coords())
            xjs , yjs = xjp + label_modif[j][0] , yjp + label_modif[j][1]
            xji , yji = xjs + ejercicio[j].vt.label_width , yjs + ejercicio[j].vt.label_height
            for x1 in (xjs,xji):
                for y1 in (yjs,yji):
                    if x1>=xis and x1<=xii and y1>=yis and y1<=yii:
                        return True
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
        new_label_x = support_x - ejercicio[i].vt.label_width
        new_label_y = support_y -10
    return [new_label_x,new_label_y,label_radius, label_heading]
    
def timer():
  # Subrutina que controla los refrescos de pantalla cada 5 segundos
    global last_update,t0,protocol_factory
        
    refresco=5.
    # Si el reloj estáparado actualizamos t0 para ajustarque no corra el tiempo y no actualizamos.
    if not reloj_funciona:
        t0=fact_t*time()-h_inicio
        #     return
    etiq1=28
    w.update()

    # Only if we have network support.
    try:
        for protocol in protocol_factory.protocols:
            protocol.send_time(float(tlocal(t0)))
    except:
        pass

    if tlocal(t0)-last_update<refresco:
        t=float(tlocal(t0))
        ho=int(t/60/60)
        m=int(t/60)-ho*60
        s=int(t)-60*60*ho-60*m
        clock.configure(time='%02d:%02d:%02d' % (ho, m, s))
        
    else:
        # If network server, send flight information
        try:
            for protocol in protocol_factory.protocols:
                protocol.send_flights()
        except: pass
        last_update=tlocal(t0)
        # Mover los aviones con auto-separación
        for a in ejercicio:
            a.next(last_update/60./60.)
            a.redraw(w)
        # Move storms
        for s in storms:
            global wind
            # Wind is defined as a speed in knots
            # Since we are updating every 5 seconds, we have to divide the intensity accordingly
            (wind_x,wind_y)=pr((wind[0]*5/3600,wind[1]))
            s.wx+=wind_x
            s.wy+=wind_y
            s.wrx+=wind_x
            s.wry+=wind_y
            s.redraw()
        # Lo eliminamos por ahora puesto que tenemos el cliente remoto
        #display.update()
        if auto_sep:
            separate_labels(w)
        # Comprobar si hay PAC
        for acft in ejercicio:
            acft.vt.pac=acft.vt.vac=False
        for i in range(len(ejercicio)):
            for j in range(i+1,len(ejercicio)):
                if pac(ejercicio[i],ejercicio[j]):
                    ejercicio[i].vt.pac=True
                    ejercicio[j].vt.pac=True
        w.delete('vac')
        poner_palote=False
        palote(poner_palote,w)
        for i in range(len(ejercicio)):
            for j in range(i+1,len(ejercicio)):
                line=()
                if vac(ejercicio[i],ejercicio[j]):
                    poner_palote=True
                    ejercicio[i].vt.vac=True
                    ejercicio[i].vt.pac=False
                    line=do_scale(ejercicio[i].get_coords())
                    ejercicio[j].vt.vac=True
                    ejercicio[j].vt.pac=False
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
        
        # Update the aircrfat notices tabular
    acftnotices.update(last_update/60./60.)
    
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
        
def b_tamano_fichas():
    global label_font, label_font_size
    LABEL_MIN_FONT_SIZE = 7
    LABEL_MAX_FONT_SIZE = 11
    LABEL_SIZE_STEP = 1
    
    label_font_size += LABEL_SIZE_STEP
    if label_font_size >= LABEL_MAX_FONT_SIZE:
        label_font_size = LABEL_MIN_FONT_SIZE
    
    for acft in ejercicio:
        acft.vt.l_font_size = label_font_size

    label_font.configure(size=label_font_size)
      
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
        if a.esta_seleccionado():
            d=RaDialog(w,label=str(a.name)+': Matar vuelo',
                       text='Matar '+str(a.name),ok_callback=a.kill,
                       position=do_scale(a.get_coords()))
            break
            
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
    """Show a dialog to set the selected aircraft in a holding pattern over the selected fix"""
    sel = None
    for a in ejercicio:
        if a.esta_seleccionado(): sel=a
    if sel == None:
        RaDialog(w, label='Poner en espera',
                     text='No hay ningún vuelo seleccionado')
        return
        
    global vent_ident_procs
    if vent_ident_procs != None:
        w.delete(vent_ident_procs)
        vent_ident_procs = None
        
    def set_holding(e=None,entries=None):
        error = True
        ent_hold=entries['Fijo Principal:']
        ent_side=entries['Virajes (I/D):']
        fijo = ent_hold.get().upper()
        lado = ent_side.get().upper()
        auxiliar = ''
        # Si la espera está publicada, los datos de la espera
        for [fijo_pub,rumbo,tiempo,lado_pub] in esperas_publicadas:
            if fijo_pub == fijo:
                lado = lado_pub.upper()
                derrota_acerc = rumbo
                tiempo_alej = tiempo/60.0
                for i in range(len(sel.route)):
                    [a,b,c,d] = sel.route[i]
                    if b == fijo:
                        auxiliar = [a,b,c,d]
                        error = False
                        break
                        # En caso contrario, TRK acerc = TRK de llegada y tiempo = 1 min
        if auxiliar == '':
            for i in range(len(sel.route)):
                [a,b,c,d] = sel.route[i]
                if b == fijo:
                    if i == 0: # La espera se inicia en el siguiente punto del avión
                        auxi = sel.pos
                    else:
                        auxi = sel.route[i-1][0]
                    aux1 = r(a,auxi)
                    derrota_acerc = rp(aux1)[1]
                    auxiliar = [a,b,c,d]
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
            error=True
        if error:
            return False  # Not validated correctly
        sel.vfp = False
        sel.to_do = 'hld'
        sel.to_do_aux = [auxiliar, derrota_acerc, tiempo_alej, 0.0, False, giro]
        # Cancelar posible autorización de aproximación
        cancel_app_auth(sel)
        logging.debug ("Holding pattern: "+str(sel.to_do_aux))
        
        # Build the GUI Dialog
    entries=[]
    entries.append({'label':'Fijo Principal:','width':5,'def_value':sel.route[0][1]})
    entries.append({'label':'Virajes (I/D):','width':1,'def_value':'D'})
    RaDialog(w,label=sel.get_callsign()+': Poner en espera',ok_callback=set_holding,entries=entries)    
    
def nueva_ruta():
    """Ask the user to set a new route and destination airdrome for the currently selected aircraft"""
    sel = None
    for a in ejercicio:
        if a.esta_seleccionado(): sel=a
    if sel == None:
        RaDialog(w, label='Nueva ruta',
                 text='No hay ningún vuelo seleccionado')
        return
    def change_fpr(e=None,entries=None):
        ent_route,ent_destino=entries['Ruta:'],entries['Destino:']
        pts=ent_route.get().split(' ')
        logging.debug ('Input route points: '+str(pts))
        aux=[]
        fallo=False
        for a in pts:
            hay_pto=False
            for b in punto:
                if a.upper() == b[0]:
                    aux.append([b[1],b[0],'',0])
                    hay_pto=True
            if not hay_pto:
                fallo=True
        if fallo:
            ent_route['bg'] = 'red'
            ent_route.focus_set()
            return False  # Validation failed
        sel.destino = ent_destino.get().upper()
        cancel_app_auth(sel)
        sel.set_route(aux)
        logging.info ('Cambiando plan de vuelo a '+str(aux))
        sel.set_app_fix()
        # Build the GUI Dialog
    entries=[]
    entries.append({'label':'Ruta:','width':50})
    entries.append({'label':'Destino:','width':5,'def_value':sel.destino})
    RaDialog(w,label=sel.get_callsign()+': Nueva ruta',
                          ok_callback=change_fpr,entries=entries)    
    
def cambiar_viento():
    """Show a dialog to allow the user to change the wind in real time"""
    def change_wind(e=None,entries=None):
        global wind, vent_ident_procs
        ent_dir=entries['Dirección:']
        ent_int=entries['Intensidad (kts):']
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
        if fallo:
            return False  # Validation failed
            
        if vent_ident_procs != None:
            w.delete(vent_ident_procs)
            vent_ident_procs = None
            # Cambiamos el viento en todos los módulos
        wind = [intensidad,rumbo]
        set_global_vars(punto, wind, aeropuertos, esperas_publicadas,rwys,rwyInUse,procedimientos,proc_app,min_sep)
        logging.debug('Viento ahora es (int,rumbo) '+str(wind))
        
        # Build the GUI Dialog
    entries=[]
    entries.append({'label':'Dirección:','width':3,'def_value':int((wind[1]+180.0)%360.0)})
    entries.append({'label':'Intensidad (kts):','width':2,'def_value':int(wind[0])})
    RaDialog(w,label='Definir viento',
            ok_callback=change_wind,entries=entries)    
    
def create_storm():
    global vent_ident_procs, storms
    if vent_ident_procs != None:
        w.delete(vent_ident_procs)
        vent_ident_procs = None
    
    def storm_done(e=None):
        w.configure(cursor="")
        w.bind("<Button-3>",end_def_lad)
    
    class phony_radisplay:
        def __init__(self,canvas, do_scale, undo_scale):
            self.c=canvas
            self.do_scale=do_scale
            self.undo_scale=undo_scale
            self.b2_cb = def_lad
            self.b3_cb = storm_done   
            self.storms = storms
            
    def start_storm(e=None):
        w.configure(cursor="crosshair")
        r=phony_radisplay(w,do_scale,undo_scale)
        s=Storm(r,e)
        
    w.bind("<Button-2>",start_storm)
    w.configure(cursor="crosshair")
 
def destroy_storm():

    def remove_storm(event=None):
        for s in storms[:]:
            if s.selected == True:
                s.delete()
        w.configure(cursor="")
        w.unbind("<Motion>")
        w.unbind("<Button-1>")
        
    def find_closest_storm(event=None):
        for s in storms[:]:
            s.auto_select_storm(event,10)
    
    w.bind("<Button-1>",remove_storm)
    w.bind("<Motion>",find_closest_storm)
    w.configure(cursor="crosshair")    
 
 
    
def hdg_after_fix():
    """Show a dialog to command the selected aircraft to follow a heading after a certain fix"""
    sel = None
    for a in ejercicio:
        if a.esta_seleccionado(): sel=a
    if sel == None:
        RaDialog(w, label='Rumbo después de fijo',
                 text='No hay ningún vuelo seleccionado')
        return
        
    global vent_ident_procs
    if vent_ident_procs != None:
        w.delete(vent_ident_procs)
        vent_ident_procs = None
        
    def set_fix_hdg(e=None,entries=None):
        error = True
        ent_fix=entries['Fijo:']
        ent_hdg=entries['Rumbo:']
        fijo = ent_fix.get().upper()
        hdg = ent_hdg.get().upper()
        for i in range(len(sel.route)):
            [a,b,c,d] = sel.route[i]
            if b == fijo:
                auxiliar = [a,b,c,d]
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
        if error:
            return False  # Validation failed
        sel.vfp = False
        sel.to_do = 'hdg<fix'
        sel.to_do_aux = [auxiliar, hdg]
        logging.debug("Heading after fix: "+str(sel.to_do_aux))
        cancel_app_auth(sel)
        # Build the GUI Dialog
    entries=[]
    entries.append({'label':'Fijo:','width':5,'def_value':str(sel.route[0][1])})
    entries.append({'label':'Rumbo:','width':3})
    RaDialog(w,label=sel.get_callsign()+': Rumbo después de fijo',
            ok_callback=set_fix_hdg,entries=entries)    
    
def int_rdl():
    """Show a dialog to command the selected aircraft to intercept a radial"""
    sel = None
    for a in ejercicio:
        if a.esta_seleccionado(): sel=a
    if sel == None:
        RaDialog(w, label='Rumbo después de fijo',
               text='No hay ningún vuelo seleccionado')
        return
    else:
        global vent_ident_procs
        if vent_ident_procs != None:
            w.delete(vent_ident_procs)
            vent_ident_procs = None
    def set_rdl(e=None,entries=None):
        error = True
        ent_fix=entries['Fijo:']
        ent_rdl=entries['Radial:']
        ent_d_h=entries['Desde/Hacia (D/H)']
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
        if error:
            return False  # Validation failed
        if sel.to_do <> 'hdg':
            sel.hold_hdg = sel.hdg
        sel.vfp = False
        sel.to_do = 'int_rdl'
        sel.to_do_aux = [auxiliar, (rdl + correccion)% 360.]
        logging.debug("Intercep radial: "+str(sel.to_do_aux))
        cancel_app_auth(sel)
        # Build the GUI Dialog
    entries=[]
    entries.append({'label':'Fijo:','width':5,'def_value':str(sel.route[0][1])})
    entries.append({'label':'Radial:','width':3})
    entries.append({'label':'Desde/Hacia (D/H)','width':1,'def_value':'D'})
    RaDialog(w,label=sel.get_callsign()+': Interceptar radial',
            ok_callback=set_rdl,entries=entries)    
    
def b_execute_map():
    """Show a dialog to command the selected aircraft to miss the approach"""
    sel = None
    for a in ejercicio:
        if a.esta_seleccionado(): sel=a
    if sel == None or not sel.app_auth:
        RaDialog(w, label='Ejecutar MAP',
               text='No hay ningún vuelo seleccionado\no el vuelo no está autorizado APP')
        return
    if sel.destino not in rwys.keys():
        RaDialog(w, label='Ejecutar MAP',
                 text='Aeropuerto de destino sin procedimientos de APP')
        return
    global vent_ident_maps
    if vent_ident_maps != None:
        w.delete(vent_ident_maps)
        vent_ident_maps = None
        
    def exe_map(e=None):
        sel._map = True
        logging.debug(sel.get_callsign()+": make MAP")
    RaDialog(w,label=sel.get_callsign()+': Ejecutar MAP',
             text='Ejecutar MAP', ok_callback=exe_map)
    
def b_int_ils():
    """Show a dialog to command the selected aircraft to intercept and follow the ILS"""
    sel = None
    for a in ejercicio:
        if a.esta_seleccionado(): sel=a
    if sel == None:
        RaDialog(w,label='Interceptar ILS',text='No hay ningún vuelo seleccionado')
        return
    elif sel.destino not in rwys.keys():
        RaDialog(w, label=sel.get_callsign()+': Interceptar ILS',
                 text='Aeropuerto de destino sin procedimientos de APP')
        return
    elif sel.fijo_app == 'N/A':
        RaDialog(w,label=sel.get_callsign()+': Interceptar ILS',
                 text='Vuelo sin IAF. Añada la ruta hasta el IAF y reintente')
        return
    global vent_ident_maps
    if vent_ident_maps != None:
        w.delete(vent_ident_maps)
        vent_ident_maps = None
        
    def int_ils(e=None):
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
        logging.debug('Altitud: '+str(puntos_alt[0][3]))
        sel.set_cfl(puntos_alt[0][3]/100.)
        sel.set_std_rate()
        logging.debug(sel.get_callsign()+': Intercepting ILS')
    RaDialog(w,label=sel.get_callsign()+': Interceptar ILS',
             text='Interceptar ILS', ok_callback=int_ils)
    
def b_llz():
    """Show a dialog to command the selected aircraft to intercept and follow \
    the LLZ (not the GP)"""
    sel = None
    for a in ejercicio:
        if a.esta_seleccionado():
            sel=a
            break
    if sel == None:
        RaDialog(w,label='Interceptar LLZ',text='No hay ningún vuelo seleccionado')
        return
    elif sel.destino not in rwys.keys():
        RaDialog(w, label=sel.get_callsign()+': Interceptar LLZ',
                 text='Aeropuerto de destino sin procedimientos de APP')
        return
    elif sel.fijo_app == 'N/A':
        RaDialog(w,label=sel.get_callsign()+': Interceptar LLZ',
                 text='Vuelo sin IAF. Añada la ruta hasta el IAF y reintente')
        return
    global vent_ident_maps
    if vent_ident_maps != None:
        w.delete(vent_ident_maps)
        vent_ident_maps = None
    def int_llz(e=None):
        if sel.to_do <> 'hdg':
            sel.hold_hdg = sel.hdg
            # Se supone que ha sido autorizado previamente
        (puntos_alt,llz,puntos_map) = proc_app[sel.fijo_app]
        [xy_llz ,rdl, dist_ayuda, pdte_ayuda, alt_pista] = llz
        sel.to_do = 'int_rdl'
        sel.to_do_aux = [xy_llz, rdl]
        logging.debug(sel.get_callsign()+': Intercepting LLZ')
    RaDialog(w,label=sel.get_callsign()+': Interceptar LLZ',
             text='Interceptar LLZ', ok_callback=int_llz)
    
def ver_detalles():
    """Show a dialog to view details of the selected flight"""
    sel = None
    for a in ejercicio:
        if a.esta_seleccionado():
            sel=a
            break
    if sel == None:
        RaDialog(w,label='Ver Detalles',text='No hay ningún vuelo seleccionado')
        return
        # TODO The RaDialog should probably export the contents frame
        # and we could use it here to build the contents using a proper grid
    RaDialog(w, label=sel.get_callsign()+': Detalles',
             text='Origen: '+sel.get_origin()+
             '\tDestino: '+sel.get_destination()+
             '\nTipo:   '+sel.get_kind().ljust(4)+
             '\tRFL:     '+str(int(sel.rfl))+
             '\nCallsign: '+sel.radio_callsign)
    
def b_orbitar():
    """Show a dialog to command the selected aircraft to make orbits"""    
    global vent_ident_procs
    if vent_ident_procs != None:
        w.delete(vent_ident_procs)
        vent_ident_procs = None
        win = Frame(w)
    sel = None
    for a in ejercicio:
        if a.esta_seleccionado():
            sel=a
    if sel == None:
        RaDialog(w,label='Orbita inmediata',text='No hay ningún vuelo seleccionado')
        return
    def set_orbit(e=None,sel=sel,entries=None):
        side_aux = entries['Orbitar hacia:']['value']
        sel.to_do = 'orbit'
        if side_aux.upper() == 'IZDA':
            sel.to_do_aux = ['IZDA']
        else:
            sel.to_do_aux = ['DCHA']
        logging.debug(sel.get_callsign()+": Orbittting "+str(side_aux))
    entries=[]
    entries.append({'label':'Orbitar hacia:',
                    'values':('IZDA','DCHA'),
                    'def_value':'IZDA'})
    RaDialog(w,label=sel.get_callsign()+': Orbitar',
             ok_callback=set_orbit, entries=entries)      
    
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
    sel = None
    for a in ejercicio:
        if a.esta_seleccionado(): sel=a
    if sel == None:
        RaDialog(w,label='Autorizar a aproximación',text='No hay ningún vuelo seleccionado')
        return
    elif sel.destino not in rwys.keys():
        RaDialog(w, label=sel.get_callsign()+': Autorizar a aproximación',
                 text='Aeropuerto de destino sin procedimientos de APP')
        return
        
    global vent_ident_maps
    if vent_ident_maps != None:
        w.delete(vent_ident_maps)
        vent_ident_maps = None
        
    def auth_app(e=None,avo=sel, entries=None):
        # TODO Currently we are not checking which destination the
        # user asked for, and just clear for approach to the current destination
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
        # Al autorizar a procedimiento APP no desciende automáticamente.
        #~ #En este paso se desciende el tráfico y se añaden los puntos
        #~ logging.debug('Altitud: '+str(puntos_alt[0][3]))
        #~ avo.set_cfl(puntos_alt[0][3]/100.)
        if avo.to_do == 'hld':
            pass
        else:
            avo.to_do = 'app'
            for i in range(len(avo.route),0,-1):
                if avo.route[i-1][1] == avo.fijo_app:
                    avo.route = sel.route[:i]
                    break
            for [a,b,c,h] in puntos_alt:
                avo.route.append([a,b,c,0.0])
            avo.route.append([llz[0],'_LLZ',''])
        logging.debug("Autorizado aproximación: " +str(avo.route))
        
        # Build entries
    for i in range(len(sel.route),0,-1):
        if sel.route[i-1][1] in proc_app.keys():
            fijo_app = sel.route[i-1][1]
            break
    entries=[]
    entries.append({'label':'Destino:', 'width':4, 'def_value':sel.destino})
    entries.append({'label':'IAF:', 'width':5, 'def_value':fijo_app})
    RaDialog(w,label=sel.get_callsign()+': Autorizar a Aproximación',
             ok_callback=auth_app, entries=entries)      
    
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
            but_tamano_etiq = Button(ventana,bitmap='@'+IMGDIR+'labelsize.xbm',command=b_tamano_fichas)
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
            but_destroy_storm = Button(ventana,text='TS', fg = 'red',command = destroy_storm)
            but_destroy_storm.pack(side=LEFT,expand=1,fill=X)
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
                but_storm = Button(ventana_procs, text = 'Crear tormenta', command = create_storm)
                but_storm.grid(column=0,row=6,sticky=E+W)
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
                but_ils_vec = Button(ventana_maps, text = 'ILS (vectores)', command = b_int_ils)
                but_ils_vec.grid(column=0,row=1,sticky=E+W)
                but_loc = Button(ventana_maps, text = 'LOCALIZADOR', command = b_llz)
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
            but_ver_tabs = Button(ventana, text = 'TABs')
            but_ver_tabs.pack(side=LEFT,expand=1,fill=X)
            def tabs_buttons():
                global vent_ident_tabs
                if vent_ident_tabs != None:
                    w.delete(vent_ident_tabs)
                    vent_ident_tabs = None
                    return
                ventana_tabs = Frame(w,bg='gray')
                but_reports = Button(ventana_tabs, text='Notificaciones',
                                     command = acftnotices.show)
                but_reports.grid(column=0,row=0,sticky=E+W)
                vent_ident_tabs=w.create_window(ventana.winfo_x()+but_ver_tabs.winfo_x(),alto-ventana.winfo_height(),window=ventana_tabs,anchor='sw')
            but_ver_tabs['command'] = tabs_buttons
            def cambia_vect_vel(e=None):
                set_speed_time(float(var_vect_vel.get())/60.)
                for acft in ejercicio:
                    acft.redraw(w)
            cnt_vect_vel = Control(ventana, label="Vel:", min=0, max=5, integer=1, command=cambia_vect_vel, variable=var_vect_vel)
            cnt_vect_vel.pack(side=LEFT,expand=1,fill=X)
            def cambia_vel_reloj(e=None):
                set_vel_reloj(float(var_vel_reloj.get()))
            cnt_vel_reloj = Control(ventana, label="Clock X:", min=0.5, max=99.0, step=0.1, command=cambia_vel_reloj, variable=var_vel_reloj)
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
            but_tamano_etiq = Button(ventana,bitmap='@'+IMGDIR+'labelsize.xbm',command=b_tamano_fichas)
            but_tamano_etiq.grid(column=7,row=1)
            def cambia_vect_vel(e=None):
                set_speed_time(float(var_vect_vel.get())/60.)
                for acft in ejercicio:
                    acft.redraw(w)
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
            but_destroy_storm = Button(ventana,text='TS', fg = 'red',command = destroy_storm)
            but_destroy_storm.grid(column=13,row=1)

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
            but_int_rdl = Button(ventana, text = 'ILS', command = b_int_ils)
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
acftnotices=Pseudopilot.AcftNotices(w,flights=ejercicio)
acftnotices.hide()

get_scale()

if not auto_departures:
    manual_dep_window(last_update/60./60.)
    
def change_widget_size(e):
    global ancho,alto,ver_ventana_auxiliar
    ancho = e.width
    alto = e.height
    w.update_idletasks()
    ventana_auxiliar(None)
    ventana_auxiliar(None)
    
w.bind('<Configure>',change_widget_size)
redraw_all()
timer()

def window_closed(e=None):
    global listening_port
    try: tksupport.uninstall()
    except: pass
    root.destroy()
    try:
        listening_port.stopListening()
        try:
            reactor.GtkMainWindow.present()
        except:
            reactor.stop()
    except:
        pass
    
root.protocol("WM_DELETE_WINDOW", window_closed)

# Start the networked mainloop, or else the normal tkinter mainloop
try:
    class GTA_Protocol(NetstringReceiver):
        
        def __init__(self):
            self._deferred = None
            self.time_string = ''
        
        def connectionMade(self):
            global fir_file, sector
            m={'message':'init',
               'data':{
                'fir_file':fir_file,
                'sector':sector,
                'flights':self.factory.flights}
            }
            self.sendMessage(pickle.dumps(m))
            self.factory.protocols.append(self)
            print ("Got connection")
            
        def sendMessage(self,line):
            line=zlib.compress(line)
            self.sendString(line)
                    
        def send_flights(self):
            m={'message':'flights',
               'data':self.factory.flights}
            self.sendMessage(pickle.dumps(m,bin=True))
            
        def send_time(self,t):
            time_string = '%02d:%02d:%02d' % get_h_m_s(t)
            if time_string != self.time_string:
                m={'message':'time',
                   'data':t}
                self.sendMessage(pickle.dumps(m,bin=True))
                self.time_string=time_string
            
        def connectionLost(self,reason):
            if self._deferred!=None:
                self._deferred.cancel()
            print "Connection lost"
            self.factory.protocols.remove(self)
    
    class GTA_Protocol_Factory(Factory):
    
        protocol = GTA_Protocol
        protocols = []
        
        def __init__(self,flights):
            self.flights=flights

    protocol_factory=GTA_Protocol_Factory(ejercicio)
    try:
        port=conf.server_port
        listening_port = reactor.listenTCP(port, protocol_factory)
        logging.info("Servidor iniciado y esperando conexiones en el puerto "+str(port))
    except:
        logging.warning("No se ha podido iniciar el servidor. El puerto 20123 está ocupado. Verifique si ya hay un servidor corriendo y reinicie la aplicación")
    tksupport.install(root)
    try:
        reactor.GtkMainWindow.hide()
    except:
        reactor.run()
except:
    logging.warning("La biblioteca Twisted no está instalada. No hay soporte de red."+
                    "\nDescarga el archivo marcado como 'Win32 exe Python 2.4'"+
                    "\nde http://twistedmatrix.com/projects/core/")
    root.mainloop()
