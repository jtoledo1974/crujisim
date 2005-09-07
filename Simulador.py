#!/usr/bin/python
#-*- coding:"iso8859-15" -*-

def set_latest_lad(num):
  global latest_lad_event_processed
  print 'Set_latest_lad llamado. Antes despues', latest_lad_event_processed,num
  latest_lad_event_processed = num

from avion import *
from tpv import *
from Tix import *
import Image
import ImageTk
Image._initialized=2
from time import time,sleep
import lads
from math import sqrt

punto = []
ejercicio = []
rutas = []
limites = []
tmas = []
deltas = []
h_inicio=1.
reloj_funciona = False

superlad = None

[punto,ejercicio,rutas,limites,deltas,tmas,h_inicio]=tpv()

# Plot size
size=2

root=Tk()

var_vect_vel = IntVar()
var_vect_vel.set(0)
var_vel_reloj = DoubleVar()
var_vel_reloj.set(1.0)

x0=0.
y0=0.
scale=1.0
ancho=800
alto=600
centro_x=ancho/2
centro_y=alto/2
nombre_fijos = True
var_ver_ptos = IntVar()
var_ver_ptos.set(1)
ver_tmas = False
var_ver_tmas = IntVar()
var_ver_tmas.set(0)
ver_deltas = False
var_ver_deltas = IntVar()
var_ver_deltas.set(0)
auto_sep = False
var_auto_sep = IntVar()
var_auto_sep.set(0)

w=Canvas(root,height=alto,width=ancho,bg='black')
w.pack(expand=1,fill=BOTH)

radius = 30
label_font_size = 11
label_font = tkFont.Font(family="Helvetica",size=label_font_size)
set_label_font(label_font)
set_label_font_size(label_font_size)


# Definición de LAD's en el canvas
class fix_point:
  def __init__(self,coord):
    self.pos = coord
    
  def get_heading(self):
    return 0.01
  
  def get_coords(self):
    return self.pos
  
  def get_speed(self):
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
  print 'Definiendo LAD. Actual, anterior',e.serial,latest_lad_event_processed
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
          time_min = 60.0 * dist / lad_origen.get_speed()
          lad_center_x = (x0 + e.x)/2
          lad_center_y = (y0 + e.y)/2
          canvas.create_line(x0, y0,e.x, e.y, fill="orange", tags="lad_defined")
          lad_text1 = "A: %03d" % angulo
          lad_text2 = "D: %03d" % dist
          if lad_origen.get_speed() < 10.:
            lad_text3 = ""
          else:
            lad_text3 = "T: %03d" % time_min
          lad_rect_width = label_font.measure(lad_text1)
#          lad_rect_width = max(label_font.measure(self.name) + 4,label_font.measure(spd_text+wake_text+eco_text) + 4)
          lad_line_height = label_font.metrics('linespace')
          canvas.create_text(lad_center_x, lad_center_y - lad_line_height, text=lad_text1, fill="orange", tags="lad_defined")
          canvas.create_text(lad_center_x, lad_center_y                  , text=lad_text2, fill="orange", tags="lad_defined")
          canvas.create_text(lad_center_x, lad_center_y + lad_line_height, text=lad_text3, fill="orange", tags="lad_defined")
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
#     # ... ¡salvo que se haya tirado un LAD entre un avión y él mismo!
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
  print 'Definiendo ruta. Actual, anterior',e.serial,latest_lad_event_processed
  # actualizar latest_lad_event
  for avo in ejercicio:
    if avo.last_lad>latest_lad_event_processed: latest_lad_event_processed = avo.last_lad
  if e.serial == latest_lad_event_processed:
      return
  latest_lad_event_processed = e.serial
  # Encontramos la aeronave a la que nos referimos
  acft = get_acft_or_point(e.x,e.y)
  print 'Datos acft or point', acft.get_speed(), acft.get_heading()
  # En caso de ser un punto, anulamos
  if acft.get_speed()<50.:
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
		min_dist_time = lads.compute_mindisttime(xinitA, yinitA, lad.origin.get_heading(), lad.origin.get_speed(), xinitB, yinitB, lad.destination.get_heading(), lad.destination.get_speed())
		if (min_dist_time != None) and (min_dist_time > 0.0):
			# Flights will cross
			min_dist = lads.compute_mindist(xinitA, yinitA, lad.origin.get_heading(), lad.origin.get_speed(), xinitB, yinitB, lad.destination.get_heading(), lad.destination.get_speed())
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
			(posAx, posAy, posBx, posBy) = lads.compute_cross_points(xinitA, yinitA, lad.origin.get_heading(), lad.origin.get_speed(), xinitB, yinitB, lad.destination.get_heading(), lad.destination.get_speed())
			(crossAx, crossAy) = do_scale((posAx, posAy))
			(crossBx, crossBy) = do_scale((posBx, posBy))
			canvas.create_line(x0, y0, crossAx, crossAy, fill='red', tags="crosspoint")
			canvas.create_rectangle(crossAx-size, crossAy-size, crossAx +size, crossAy +size, fill='red', tags="crosspoint")
			canvas.create_line(x1, y1, crossBx, crossBy, fill='red', tags="crosspoint")
			canvas.create_rectangle(crossBx - size, crossBy -size, crossBx + size, crossBy + size, fill='red', tags="crosspoint")
			canvas.tag_lower("crosspoint", "plot")
			canvas.tag_lower("crosspoint", "lad")
	canvas.tag_lower('lad', 'plot')


palote_identifier=None
images = {}
def load_image(image_name):
        new_img = Image.open(image_name+".gif").convert("RGBA")
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
  ymax=-1e8
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
  y_scale=alto/(ymax-ymin)
  scale=min(x_scale,y_scale)*0.8
  return
  
def do_scale(a):
  # Devuelve las coordenadas en a transformadas de real a coordenadas canvas
  return s((centro_x,centro_y),p(r((a[0],-a[1]),(x0,-y0)),scale))

def undo_scale(a):
  # Devuelve las coordenadas en a transformadas de coordenadas canvas a reales
  return s((x0,y0),p(r((a[0],-a[1]),(centro_x,-centro_y)),1/scale))

def redraw_all():
  # Dibujar las rutas y nombre de los puntos
  global x0,y0,scale,centro_x,centro_y
  set_canvas_info(x0,y0,scale,centro_x,centro_y,punto)
  w.delete('puntos')
  w.delete('nombres_puntos')
  w.delete('rutas')
  w.delete('reloj')
  w.delete('tmas')
  w.delete('deltas')
  # Dibujar límites del FIR
  aux=()
  for a in limites:
    aux=aux+do_scale(a)
  w.create_polygon(aux,fill='gray12',tag='rutas')
  # Dibujar las rutas
  for a in rutas:
    aux=()
    for i in range(0,len(a[0]),2):
      aux=aux+do_scale((a[0][i],a[0][i+1]))
    w.create_line(aux,fill='gray50',tag='rutas')
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
  w.delete('fichas')
  # Poner las fichas que se imprimen
  n=1
  for a in ejercicio:
    if a.se_debe_imprimir(last_update/60./60.):
      w.create_text(ancho-10,n*13,text=a.get_callsign(),fill='yellow',tag='fichas',anchor=NE,font='-*-Helvetica-*--*-12-*-')
      n=n+1
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
  w.create_text(10,5,text='%02d:%02d:%02d' % (ho, m, s),fill='yellow',tag='reloj',anchor=NW,font='-*-Times-Bold-*--*-20-*-')
 
fact_t=1.0
t0=fact_t*time()-h_inicio
last_update=0

def tlocal(t):
  return fact_t*time()-t
 
def set_vel_reloj(k):
  global t0,fact_t,h_inicio
  h_inicio=fact_t*time()-t0
  fact_t=k
  t0=fact_t*time()-h_inicio

def se_cortan (i,j):
  # Devuelve si las etiquetas están separadas entre los aviones i y j de ejercicio
  corta = False
  if ejercicio[i].is_flying():
    (xip,yip) = do_scale(ejercicio[i].get_coords())
    xis , yis = xip + ejercicio[i].label_x , yip + ejercicio[i].label_y
    xii , yii = xis + ejercicio[i].label_width , yis + ejercicio[i].label_height
    # Comprobamos las cuatro esquinas del avión j y que no se corten los soportes de etiquetas, así como ningún plot
    if ejercicio[j].is_flying():
      (xjp,yjp) = do_scale(ejercicio[j].get_coords())
      xjs , yjs = xjp + ejercicio[j].label_x , yjp + ejercicio[j].label_y
      xji , yji = xjs + ejercicio[j].label_width , yjs + ejercicio[j].label_height
      for x1 in (xjs,xji):
        for y1 in (yjs,yji):
          if x1>xis and x1<xii and y1>yis and y1<yii:
            corta = True
#       (v1,v2) = (xis-xip , yis-yip)
#       (oa1,oa2) = (xjp-xip , yjp-yip)
#       (ob1,ob2) = (xjs-xip , yjs-yip)
#       norma_v = max((v1 * v1 + v2 * v2)**(0.5),0.00001)
#       (v1,v2) = (v1 / norma_v, v2 / norma_v)
#       oa_x_vperp = oa1 * v2 - oa2 * v1
#       ob_x_vperp = ob1 * v2 - ob2 * v1
#       oa_x_v = oa1 * v1 + oa2 * v2
#       ob_x_v = ob1 * v1 + ob2 * v2
#       cond1 = oa_x_vperp * ob_x_vperp # Negativo si cada uno está a un lado
#       if abs(oa_x_vperp) + abs(ob_x_vperp) > 0.:
#         cond2 = (oa_x_v * abs(ob_x_vperp) + ob_x_v * abs(oa_x_vperp))/(abs(oa_x_vperp) + abs(ob_x_vperp))
#       else:
#         cond2 = norma_v * 2.
#       if cond1 <= 0. and cond2>=0. and cond2 <= norma_v:
#         corta = True
      if xjp>xis and xjp<xii and yjp>yis and yjp<yii:
        corta = True
  return corta

def timer():
  # Subrutina que controla los refrescos de pantalla cada 5 segundos
  global last_update,t0
  refresco=5.
  # Si el reloj está parado actualizamos t0 para ajustarque no corra el tiempo y no actualizamos.
  if not reloj_funciona:
    t0=fact_t*time()-h_inicio
#    return
  etiq1=28
  w.update()
  if tlocal(t0)-last_update<refresco:
    t=float(tlocal(t0))
    ho=int(t/60/60)
    m=int(t/60)-ho*60
    s=int(t)-60*60*ho-60*m
    w.itemconfigure('reloj',text='%02d:%02d:%02d' % (ho, m, s))
  else:
    last_update=tlocal(t0)
    # Mover los aviones con auto-separación
    for a in ejercicio:
      a.next(last_update/60./60.)
      a.redraw(w)
    if auto_sep:
      for i in range(len(ejercicio)):
        moviendo = [i]
        cuenta = [0]
        giro_min = [0]
        intersectan = 0
        for j in range(len(ejercicio)):
          if i == j: continue
          if se_cortan(i,j):
            intersectan = intersectan + 1
            if (j not in moviendo) and (ejercicio[j].auto_separation) and len(moviendo)<4:
              print 'Añadiendo ',ejercicio[j].get_callsign()
              moviendo.append(j)
              cuenta.append(0)
              giro_min.append(0)
            print 'son conflicto con ',ejercicio[i].get_callsign()
        # Si intersectan probamos las posiciones posibles de la etiqueta para ver si libra en alguna. En caso contrario,se escoge 
        # el de menor interferencia
        intersectan_girado = intersectan
        cuenta_menos_inter = 0
        menos_inter = intersectan
        while (intersectan_girado > 0) and (cuenta[-1] < 8):
          for k in range(len(moviendo)):
            if cuenta[k]<8:
              cuenta[k] += 1
              ejercicio[moviendo[k]].rotate_label()
              break
            elif cuenta[k]==8: 
              cuenta[k] = 0 #= giro_min[k]
          # Comprobamos si están separados todos entre ellos
          intersectan_girado = 0
          for j in range(len(moviendo)):
            for k in range(j+1,len(moviendo)):
              if se_cortan(moviendo[j],moviendo[k]):
                intersectan_girado += 1
          print 'cuenta: ',cuenta, intersectan_girado
          if intersectan_girado < menos_inter:
            menos_inter = intersectan_girado
            cuenta_menos_inter = cuenta
          # Comprobamos que no estemos afectando a ningún otro avión con el recién girado. En caso contrario, se añade
          if intersectan_girado == 0:
            giro_min =[]
            for k in cuenta:
              giro_min.append(k)
            for k in moviendo:
              for j in range(len(ejercicio)):
                if (j not in moviendo) and (ejercicio[j].auto_separation) and (len(moviendo)<4) and se_cortan(k,j):
                  print 'Añadiendo ',ejercicio[j].get_callsign()
                  intersectan_girado = intersectan_girado + 1
                  moviendo.append(j)
                  cuenta.append(0)
                  giro_min.append(0)
        # En caso de que haya conflicto, escogemos el giro con menos intersecciones
        if menos_inter >0 and menos_inter < intersectan:
          print 'Girando ',cuenta_menos_inter,' veces'
          for l in range(len(moviendo)):
            for k in range(cuenta_menos_inter[l]):
              ejercicio[moviendo[l]].rotate_label()
        elif not ejercicio[i].auto_separation:
          print ejercicio[i].get_callsign(),' no se rota'
  draw_all_lads(w)
  # Poner las fichas que se imprimen
  w.delete('fichas')
  n=1
  for a in ejercicio:
    if a.se_debe_imprimir(last_update/60./60.):
      w.create_text(ancho-10,n*13,text=a.get_callsign(),fill='yellow',tag='fichas',anchor=NE,font='-*-Helvetica-*--*-12-*-')
      n=n+1
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
        print 'Conflicto entre ',ejercicio[i].get_callsign(),' y ',ejercicio[j].get_callsign(),'a las ',last_update/60./60.
  palote(poner_palote,w)

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
  centro_y=alto/2
  get_scale()
  redraw_all()
  
def b_inicio():
  global t0,reloj_funciona
  if not reloj_funciona:
    print 'Iniciando simulación'
    t0=fact_t*time()-h_inicio
    reloj_funciona = True
  print reloj_funciona
  
def b_parar():
  global h_inicio,reloj_funciona
  if reloj_funciona:
    print 'Parando la simulación'
    h_inicio=fact_t*time()-t0
    reloj_funciona=False
  

def b_tamano_etiquetas():
  global label_font_size, label_font, radius
  label_font_size += 1
  radius += 5
  if label_font_size >= 13:
  	label_font_size = 10
        radius = 25
  label_font = tkFont.Font(family="Helvetica",size=label_font_size)
  set_label_font(label_font)
  set_label_font_size(label_font_size)
  for a in ejercicio:
    if a.auto_separation:
      a.label_radius = radius
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

def nueva_ruta():
      global win_identifier
      if win_identifier<>None:
        w.delete(win_identifier)
        win_identifier=None
      sel = None
      for a in ejercicio:
        if a.esta_seleccionado():
          sel=a
      if sel == None:
        win = Frame(w)
        txt_ruta = Label (win,text='NO HAY NINGUN VUELO SELECCIONADO ',fg='red')
        but_acept = Button(win, text="Aceptar")
        txt_ruta.pack(side=LEFT)
        but_acept.pack(side=LEFT)
        win_identifier = w.create_window(ancho/2,alto-30, window=win)
        def close_win(ident=win_identifier):
                w.delete(ident)
        but_acept['command'] = close_win
      else:
        win = Frame(w)
        txt_ruta = Label (win,text='Nueva ruta '+sel.get_callsign()+':')
        ent_ruta = Entry(win,width=50)
        but_acept = Button(win, text="Aceptar")
        but_cancel = Button(win, text="Cancelar")
        txt_ruta.pack(side=LEFT)
        ent_ruta.pack(side=LEFT)
        but_acept.pack(side=LEFT)
        but_cancel.pack(side=LEFT)
        win_identifier = w.create_window(ancho/2,alto-30, window=win)
        def close_win(ident=win_identifier):
                w.delete(ident)
        def change_fpr():
                pts=ent_ruta.get().split(' ')
                print 'Puntos son:'
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
                else:
                  sel.set_route(aux)
                  print 'Cambiando plan de vuelo a ',aux
                  close_win()
        but_cancel['command'] = close_win
        but_acept['command'] = change_fpr
        
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
        txt_ruta = Label (win,text='NO HAY NINGUN VUELO SELECCIONADO ',fg='red')
        but_acept = Button(win, text="Aceptar")
        txt_ruta.pack(side=LEFT)
        but_acept.pack(side=LEFT)
        win_identifier = w.create_window(ancho/2,alto-30, window=win)
        def close_win(ident=win_identifier):
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
        win_identifier = w.create_window(ancho/2,alto-30, window=win)
        def close_win(ident=win_identifier):
                w.delete(ident)
        but_cerrar['command'] = close_win

ver_ventana_auxiliar=True

def ventana_auxiliar(e):
  global ver_ventana_auxiliar,vent_ident
  if ver_ventana_auxiliar:
    ventana=Frame(w,bg='gray')
    but_inicio = Button(ventana,bitmap='@start.xbm',command=b_inicio)
    but_inicio.grid(column=0,row=0,sticky=E+W)
    but_parar = Button(ventana,bitmap='@pause.xbm',command=b_parar)
    but_parar.grid(column=2,row=0,sticky=E+W)
    but_arriba = Button(ventana,bitmap='@up.xbm',command=b_arriba)
    but_arriba.grid(column=1,row=2,sticky=E+W)
    but_izq = Button(ventana,bitmap='@left.xbm',command=b_izquierda)
    but_izq.grid(column=0,row=3,sticky=E+W)
    but_abajo = Button(ventana,bitmap='@down.xbm',command=b_abajo)
    but_abajo.grid(column=1,row=3,sticky=E+W)
    but_derecha = Button(ventana,bitmap='@right.xbm',command=b_derecha)
    but_derecha.grid(column=2,row=3,sticky=E+W)
    but_zoom_mas = Button(ventana,bitmap='@zoom.xbm',command=b_zoom_mas)
    but_zoom_mas.grid(column=0,row=5,sticky=E+W)
    but_zoom_menos = Button(ventana,bitmap='@unzoom.xbm',command=b_zoom_menos)
    but_zoom_menos.grid(column=1,row=5,sticky=E+W)
    but_standard = Button(ventana,bitmap='@center.xbm',command=b_standard)
    but_standard.grid(column=2,row=5,sticky=E+W)
    but_tamano_etiq = Button(ventana,bitmap='@labelsize.xbm',command=b_tamano_etiquetas)
    but_tamano_etiq.grid(column=0,row=7,columnspan=3)
    def cambia_vect_vel(e=None):
	set_speed_time(float(var_vect_vel.get())/60.)
	redraw_all()
    cnt_vect_vel = Control(ventana, label="Velocidad:", min=0, max=5, integer=1, command=cambia_vect_vel, variable=var_vect_vel)
    cnt_vect_vel.grid(column=0,row=8,columnspan=3)
    def cambia_vel_reloj(e=None):
	set_vel_reloj(float(var_vel_reloj.get()))
    cnt_vel_reloj = Control(ventana, label="Vel reloj:", min=0.5, max=9.0, step=0.1, command=cambia_vel_reloj, variable=var_vel_reloj)
    cnt_vel_reloj.grid(column=0,row=9,columnspan=3)
    separador1 = Label(ventana,text='-----PSEUDOPILOTO-----')
    separador1.grid(column=0,row=10,columnspan=3,sticky=E+W)
    but_term = Button(ventana,text='Kill',command=kill_acft)
    but_term.grid(column=0,row=11,columnspan=3)
    but_ruta = Button(ventana,text='Ruta',command=nueva_ruta)
    but_ruta.grid(column=0,row=12,columnspan=3)
    but_datos = Button(ventana,text='Datos',command=ver_detalles)
    but_datos.grid(column=0,row=13,columnspan=3)
    but_quitar_lads = Button(ventana,text='Quitar LADs', command = quitar_lads)
    but_quitar_lads.grid(column=0,row=14,columnspan=3)
    but_quitar_fpr = Button(ventana,text='Quitar Rutas', command = quitar_fpr)
    but_quitar_fpr.grid(column=0,row=15,columnspan=3)
    but_auto_sep = Checkbutton(ventana, text = 'AUTO SEP', variable = var_auto_sep, command=b_auto_separation)
    but_auto_sep.grid(column=0,row=16,columnspan=3,sticky = W)
    separador1 = Label(ventana,text='---------MAPA---------')
    separador1.grid(column=0,row=17,columnspan=3,sticky=E+W)
    but_ver_ptos = Checkbutton(ventana, text = 'Nombre Fijos', variable = var_ver_ptos, command=b_show_hide_points)
    but_ver_ptos.grid(column=0,row=18,columnspan=3,sticky = W)
    but_ver_tmas = Checkbutton(ventana, text = 'TMAs', variable = var_ver_tmas, command=b_show_hide_tmas)
    but_ver_tmas.grid(column=0,row=19,columnspan=3,sticky = W)
    but_ver_deltas = Checkbutton(ventana, text = 'Deltas', variable = var_ver_deltas, command=b_show_hide_deltas)
    but_ver_deltas.grid(column=0,row=20,columnspan=3,sticky = W)
    vent_ident=w.create_window(80,235,window=ventana)
  
  else:
    w.delete(vent_ident)
  ver_ventana_auxiliar = not ver_ventana_auxiliar
  

w.tag_bind('reloj','<Button-1>',ventana_auxiliar)

ventana_auxiliar(None)

get_scale()

redraw_all()

timer()

def change_widget_size(e):
  global ancho,alto
  ancho = e.width
  alto = e.height
  
w.bind('<Configure>',change_widget_size)

root.mainloop()

