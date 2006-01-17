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
"""Classes used by the pseudopilot interface of Crujisim"""

# TODO: Eventualy Pseudopilot should be a subclass of RaDisplay, meaning that it
# is a special case of a Radar Display to be used to control the aircraft as a
# pseudopilot. Currently (2005-10-17) it will just hold classes and functions
# that are related to pseudopiloting

from RaDisplay import *
from avion import *

SNDDIR='./snd/'

class PpDisplay(RaDisplay):
    """Radar display with a pseudopilot interface"""
    
    def __init__(self,flights,title,icon_path,fir,sector,mode='pp'):
        """Instantiate a Pseudopilot Radar Display
        
        title - window title
        icon_path - path to the windows task bar icon
        fir -- fir object
        sector -- name of the sector to work with
        """
        self.toolbar_height = 60  # Pseudopilot display toolbar height
        self._flights_tracks = {}
        self._tracks_flights = {}
        RaDisplay.__init__(self,title,icon_path,fir,sector, self.toolbar_height)
        self.flights = flights
        self.mode = mode
        
        # Create the list of tracks from the flights
        for f in flights:
            vt = VisTrack(self.c,self.vt_handler,self.do_scale,self.undo_scale)
            vt.l_font_size=self.label_font_size
            if mode=='atc':
                vt.mode='atc'
                vt.cfl=f.cfl
                vt.pfl=f.pfl
            self.tracks.append(vt)
            self._flights_tracks[f] = vt
            self._tracks_flights[vt] = f
        
        self.routes = []  # List of tracks whose routes are displayed
        self.waypoints = []  # List of tracks whose waypoints are displayed 
        
        self.speed_vector_var = IntVar()
        self.speed_vector_var.set(0)
        self.clock_speed_var = DoubleVar()
        self.clock_speed_var.set(1.0)
            
        self.update_tracks()
        self.toolbar = ventana_auxiliar(self)
        self.toolbar.redraw()
        
        self.t=0
        self.clock=RaClock(self.c)
        self.clock.configure(time='%02d:%02d:%02d' % get_h_m_s(self.t))
        
        self.separate_labels()
        
    def delete_routes(self,e=None):
        for track in self.tracks:
            self.c.delete(track.cs+'fpr')
            self.c.delete(track.cs+'wp')
            self.routes=[]
            self.waypoints=[]
            
    def draw_fpr(self,track):
        canvas=self.c
        line=()
        if track.vfp:
            line=line+self.do_scale(track.pos)
        for a in track.route:
            pto=self.do_scale(a[0])
            if a[1][0] <> '_' or a[1] in self.fir.proc_app.keys():
                canvas.create_text(pto,text=a[1],fill='orange',tag=track.name+'fpr',anchor=SE,font='-*-Helvetica-*--*-10-*-')
                canvas.create_text(pto,text=a[2],fill='orange',tag=track.name+'fpr',anchor=NE,font='-*-Helvetica-*--*-10-*-')
            line=line+pto
        if len(line)>3: canvas.create_line(line,fill='orange',tags=track.name+'fpr')
        self.routes.append(track)
        self.c.lift(track.name+'fpr')
        self.c.lift('track')

    def show_hide_fpr(self,track):
        canvas=self.c
        if canvas.itemcget(track.name+'fpr',"fill")=='orange':
            canvas.delete(track.name+'fpr')
            self.routes.remove(track)
        else:
            self.draw_fpr(track)
    
    def draw_way_point(self,track):
        canvas=self.c
        do_scale=self.do_scale

        canvas.delete(track.name+'fpr')
        canvas.delete(track.name+'wp')
        line=()
        if track.vfp:
            line=line+do_scale(track.pos)
        for a in track.route:
            pto=do_scale(a[0])
            if a[1][0] <> '_':
                canvas.create_text(pto,text=a[1],fill='yellow',tag=track.name+'wp',anchor=SE,font='-*-Helvetica-*--*-10-*-')
                canvas.create_text(pto,text=a[2],fill='yellow',tag=track.name+'wp',anchor=NE,font='-*-Helvetica-*--*-10-*-')
            line=line+pto
        if len(line)>3: canvas.create_line(line,fill='yellow',tags=track.name+'wp')
        size=2
        for a in track.route:
            (rect_x, rect_y) = do_scale(a[0])
            point_ident = canvas.create_rectangle(rect_x-size, rect_y-size, rect_x+size, rect_y+size,fill='yellow',outline='yellow',tags=track.name+'wp')
            def clicked_on_waypoint(e, point_coord=a[0],point_name=a[1]):
                # Display window offering "Direct to..." and "Cancel" options.
                track.last_lad = e.serial
                win = Frame(canvas)
                id_avo = Label(win,text=track.name)
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
                    pto=id_pto.get()
                    # Caso de dar directo al punto seleccionado
                    if pto == point_name:
                        print "Selected plane should fly direct to point", point_coord
                        for i in range(len(track.route)):
                            if point_coord==track.route[i][0]:
                                aux=track.route[i:]
                        track.set_route(aux)
                        close_win()
                        canvas.delete(track.name+'wp')
                    else:
                        aux = None
                        # Si es un punto intermedio de la ruta, lo detecta
                        for i in range(len(track.route)):
                            if track.route[i][1] == pto.upper():
                                aux = track.route[i:]
                                # Si no estáen la ruta, insertamos el punto como n 1
                        if aux == None:
                            for [nombre,coord] in self.fir.points:
                                if nombre == pto.upper():
                                    aux = [[coord,nombre,'']]
                                    print "Selected plane should fly direct to point", nombre,coord
                                    for a in track.route:
                                        aux.append(a)
                                        # Si no encuentra el punto, fondo en rojo y no hace nada
                        if aux == None:
                            id_pto.config(bg='red')
                            print 'Punto ',pto.upper(),' no encontrado'
                        else:
                            track.set_route(aux)
                            close_win()
                            canvas.delete(track.name+'wp')
                            show_hide_fpr()
                but_cancel['command'] = close_win
                but_direct['command'] = direct_to
            canvas.tag_bind(point_ident, "<1>", clicked_on_waypoint)
        self.waypoints.append(track)
        self.c.lift(track.name+'wp')
        self.c.lift('track')
        
            
    def show_hide_way_point(self,track):
        canvas=self.c
        do_scale=self.do_scale
        
        if canvas.itemcget(track.name+'wp',"fill")=='yellow':
            canvas.delete(track.name+'wp')
            self.waypoints.remove(track)
            return
        
        self.draw_way_point(track)   

    def change_size(self,e):
        RaDisplay.change_size(self,e)
        self.toolbar.redraw()
            
    def update(self):
        self.update_tracks()
        self.update_clock()
        RaDisplay.update(self)
                            
    def update_clock(self,t=None):
        if t==None: t=self.t
        else: self.t=t
        self.clock.configure(time='%02d:%02d:%02d' % get_h_m_s(t))
            
    def update_tracks(self):
        for f,vt in self._flights_tracks.items():
            vt.alt=f.alt
            vt.cs=f.name
            vt.wake=f.estela
            vt.echo=f.campo_eco
            vt.gs=f.ground_spd
            vt.hdg=f.hdg
            vt.track=f.track
            vt.rate=f.get_rate_descend()
            vt.ias=f.get_ias()
            vt.ias_max=f.get_ias_max()
            vt.visible=f.se_pinta
            vt.orig = f.origen
            vt.dest = f.destino
            vt.type = f.tipo
            vt.radio_cs = f.radio_callsign
            vt.rfl = f.rfl
            if self.mode=='pp':
                vt.cfl=f.cfl
                vt.pfl=f.pfl
                
            
            [x0,y0]=self.do_scale(f.pos)
            vt.coords(x0,y0,f.t)
            self.c.lift(str(vt)+'track')
            
    def vt_handler(self,vt,item,action,value,e=None):
        RaDisplay.vt_handler(self,vt,item,action,value,e)
        track=self._tracks_flights[vt]
        if item=='plot':
            if action=='<Button-1>': self.show_hide_fpr(track)
        if item=='cs':
            if action=='<Button-1>':
                pass
                #if action=='<ButtonRelease-2>':
                #    seleccionar(e)
                #if item=='pfl':
                #    if action=='update':
                #        self.set_pfl(int(value))
                #if item=='cfl':
                #    if action=='<Button-1>':
                #        self.last_lad=e.serial
                #    if action=='update':
                #        flag=self.set_cfl(int(value))
                #        if flag: self.redraw(canvas)
                #        return flag
                #if item=='rate':
                #    if action=='update':
                #        if value=='std':
                #            self.set_std_rate()
                #        else:
                #            return self.set_rate_descend(int(value))
                #if item=='hdg':
                #    if action=='<Button-1>':
                #        self.last_lad=e.serial
                #    if action=='update':
                #        (hdg,opt)=value
                #        self.set_heading(int(hdg),opt)
                #if item=='ias':
                #    if action=='update':
                #        (spd,force_speed)=value
                #        if spd=='std':
                #            self.set_std_spd()
                #        else:
                #            return self.set_spd(spd, force=force_speed)
        if item=='echo':
            if action=='<Button-3>':
                self.show_hide_way_point(track)
                
    def reposition(self):
        RaDisplay.reposition(self)
        r=self.routes[:]
        w=self.waypoints[:]
        self.delete_routes()
        for track in r:
            self.draw_fpr(track)
        for track in w:
            self.draw_way_point(track)

    def redraw(self):
        RaDisplay.redraw(self)
        self.update_tracks()

    def b1_cb(self,e):
        RaDisplay.b1_cb(self,e)
        self.toolbar.close_windows()
    
    def b2_cb(self,e):
        RaDisplay.b2_cb(self,e)
        self.toolbar.close_windows()
    
    def b3_cb(self,e):
        RaDisplay.b3_cb(self,e)
        self.toolbar.close_windows()
    
    
class ventana_auxiliar:
    def __init__(self,master):
        self.master=master
        self.opened_windows=[]
        self.vf = IntVar()
        self.vf.set(self.master.draw_point_names)
        self.vt = IntVar()
        self.vt.set(self.master.draw_tmas)
        self.vd = IntVar()
        self.vd.set(self.master.draw_deltas)
        self.auto_sep = IntVar()
        self.auto_sep.set(self.master.auto_separation)
        self.speed_vector_var = IntVar()
        self.speed_vector_var.set(0)
        self.clock_speed_var = DoubleVar()
        self.clock_speed_var.set(1.0)        
        self.toolbar_id = None
    
    def close_windows(self):
        for w in self.opened_windows[:]:
            self.master.c.delete(w)
            self.opened_windows.remove(w)
        
    def redraw(self):
        master=self.master
        w=master.c
        ancho=master.width
        alto=master.height
        scale=master.scale
        
        w.delete(self.toolbar_id)

        def b_izquierda():
            master.x0 -= ancho/10/scale
            master.reposition()
            
        def b_derecha():
            master.x0 += ancho/10/scale
            master.reposition()
            
        def b_arriba():
            master.y0 += ancho/10/scale
            master.reposition()
            
        def b_abajo():
            master.y0 -= ancho/10/scale
            master.reposition()
            
        def b_zoom_mas():
            master.scale *= 1.1
            master.reposition()
            
        def b_zoom_menos():
            master.scale /= 1.1
            master.reposition()
            
        def b_standard():
            master.center_x=ancho/2
            master.center_y=(alto-40.)/2
            master.get_scale()
            master.reposition()
            
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
            LABEL_MIN_FONT_SIZE = 7
            LABEL_MAX_FONT_SIZE = 11
            LABEL_SIZE_STEP = 1
            for vt in self.master.tracks:
                vt.l_font_size += LABEL_SIZE_STEP
                if vt.l_font_size >= LABEL_MAX_FONT_SIZE:
                    vt.l_font_size = LABEL_MIN_FONT_SIZE
            master.label_font_size += LABEL_SIZE_STEP
            if master.label_font_size >= LABEL_MAX_FONT_SIZE:
                master.label_font_size = LABEL_MIN_FONT_SIZE
            master.label_font.configure(size=master.label_font_size)
                        
        def b_show_hide_localmaps():
            global local_maps_shown
            local_maps_shown = []
            for map_name in local_maps:
                print var_ver_localmap[map_name].get()
                if var_ver_localmap[map_name].get() != 0:
                    local_maps_shown.append(map_name)
            redraw_all()
                        
        def b_show_hide_tmas():
            global ver_tmas
            ver_tmas = not ver_tmas
            redraw_all()
            
        def b_show_hide_deltas():
            global ver_deltas
            ver_deltas = not ver_deltas
            redraw_all()
            
        def b_auto_separationaration():
            global auto_separation
            auto_separation = not auto_separation
            
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
            sel = self.master.selected_track
            if sel == None:
                RaDialog(w,label='Ver Detalles',text='No hay ningún vuelo seleccionado')
                return
            # TODO The RaDialog should probably export the contents frame
            # and we could use it here to build the contents using a proper grid
            RaDialog(self.master.c, label=sel.cs+': Detalles',
                     text='Origen: '+sel.orig+
                     '\tDestino: '+sel.dest+
                     '\nTipo:   '+sel.type.ljust(4)+
                     '\tRFL:     '+str(int(sel.rfl))+
                     '\nCallsign: '+sel.radio_cs)
            
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

        #if ancho > 800.:
        if True:
            ventana=Frame(w,bg='gray',width=ancho)
            self.but_inicio = Button(ventana,bitmap='@'+IMGDIR+'start.xbm',command=b_inicio,state=DISABLED)
            self.but_inicio.pack(side=LEFT,expand=1,fill=X)
            self.but_parar = Button(ventana,bitmap='@'+IMGDIR+'pause.xbm',command=b_parar,state=DISABLED)
            self.but_parar.pack(side=LEFT,expand=1,fill=X)
            self.but_izq = Button(ventana,bitmap='@'+IMGDIR+'left.xbm',command=b_izquierda)
            self.but_izq.pack(side=LEFT,expand=1,fill=X)
            self.but_arriba = Button(ventana,bitmap='@'+IMGDIR+'up.xbm',command=b_arriba)
            self.but_arriba.pack(side=LEFT,expand=1,fill=X)
            self.but_abajo = Button(ventana,bitmap='@'+IMGDIR+'down.xbm',command=b_abajo)
            self.but_abajo.pack(side=LEFT,expand=1,fill=X)
            self.but_derecha = Button(ventana,bitmap='@'+IMGDIR+'right.xbm',command=b_derecha)
            self.but_derecha.pack(side=LEFT,expand=1,fill=X)
            self.but_zoom_mas = Button(ventana,bitmap='@'+IMGDIR+'zoom.xbm',command=b_zoom_mas)
            self.but_zoom_mas.pack(side=LEFT,expand=1,fill=X)
            self.but_zoom_menos = Button(ventana,bitmap='@'+IMGDIR+'unzoom.xbm',command=b_zoom_menos)
            self.but_zoom_menos.pack(side=LEFT,expand=1,fill=X)
            self.but_standard = Button(ventana,bitmap='@'+IMGDIR+'center.xbm',command=b_standard)
            self.but_standard.pack(side=LEFT,expand=1,fill=X)
            self.but_tamano_etiq = Button(ventana,bitmap='@'+IMGDIR+'labelsize.xbm',command=b_tamano_etiquetas)
            self.but_tamano_etiq.pack(side=LEFT,expand=1,fill=X)
            self.but_term = Button(ventana,text='Kill',command=kill_acft,state=DISABLED)
            self.but_term.pack(side=LEFT,expand=1,fill=X)
            self.but_ruta = Button(ventana,text='Ruta',command=nueva_ruta,state=DISABLED)
            self.but_ruta.pack(side=LEFT,expand=1,fill=X)
            self.but_datos = Button(ventana,text='Datos',command=ver_detalles)
            self.but_datos.pack(side=LEFT,expand=1,fill=X)
            self.but_quitar_lads = Button(ventana,text='LADs', fg = 'red',command = self.master.delete_lads)
            self.but_quitar_lads.pack(side=LEFT,expand=1,fill=X)
            self.but_quitar_fpr = Button(ventana,text='Rutas', fg = 'red',command = self.master.delete_routes)
            self.but_quitar_fpr.pack(side=LEFT,expand=1,fill=X)
            self.but_ver_proc = Button(ventana, text = 'PROCs',state=DISABLED)
            self.but_ver_proc.pack(side=LEFT,expand=1,fill=X)
            def procs_buttons():
                ventana_procs = Frame(w,bg='gray')
                self.but_espera = Button(ventana_procs, text='Esperas', command = define_holding)
                self.but_espera.grid(column=0,row=0,sticky=E+W)
                self.but_hdg_fix = Button(ventana_procs, text = 'HDG despues fijo', command = hdg_after_fix)
                self.but_hdg_fix.grid(column=0,row=1,sticky=E+W)
                self.but_int_rdl = Button(ventana_procs, text = 'Int. RDL', command = int_rdl)
                self.but_int_rdl.grid(column=0,row=2,sticky=E+W)
                self.but_chg_rwy = Button(ventana_procs, text = 'Cambio RWY', command = b_rwy_change)
                self.but_chg_rwy.grid(column=0,row=3,sticky=E+W)
                self.but_orbit = Button(ventana_procs, text = 'Orbitar aquí', command = b_orbitar)
                self.but_orbit.grid(column=0,row=4,sticky=E+W)
                self.but_wind = Button(ventana_procs, text = 'Cambiar viento', command = cambiar_viento)
                self.but_wind.grid(column=0,row=5,sticky=E+W)
                vent_ident_procs=w.create_window(ventana.winfo_x()+self.but_ver_proc.winfo_x(),alto-ventana.winfo_height(),window=ventana_procs,anchor='sw')
            self.but_ver_proc['command'] = procs_buttons
            self.but_ver_app = Button(ventana, text = 'APP',state=DISABLED)
            self.but_ver_app.pack(side=LEFT,expand=1,fill=X)
            def maps_buttons():
                global vent_ident_maps
                if vent_ident_maps != None:
                    w.delete(vent_ident_maps)
                    vent_ident_maps = None
                    return
                ventana_maps = Frame(w,bg='gray')
                self.but_app_proc = Button(ventana_maps, text = 'APP PROC.', command = b_auth_approach)
                self.but_app_proc.grid(column=0,row=0,sticky=E+W)
                self.but_ils_vec = Button(ventana_maps, text = 'ILS (vectores)', command = b_int_ils)
                self.but_ils_vec.grid(column=0,row=1,sticky=E+W)
                self.but_loc = Button(ventana_maps, text = 'LOCALIZADOR', command = b_llz)
                self.but_loc.grid(column=0,row=2,sticky=E+W)
                self.but_exe_map = Button(ventana_maps, text = 'EJECUTAR MAP', command = b_execute_map)
                self.but_exe_map.grid(column=0,row=3,sticky=E+W)
                vent_ident_maps=w.create_window(ventana.winfo_x()+self.but_ver_app.winfo_x(),alto-ventana.winfo_height(),window=ventana_maps,anchor='sw')
            self.but_ver_app['command'] = maps_buttons

            self.but_auto_separation = Checkbutton(ventana, text = 'SEP', variable = self.auto_sep, command=lambda: master.toggle_auto_separation())
            self.but_auto_separation.pack(side=LEFT,expand=1,fill=X)

            self.but_ver_maps = Button(ventana, text = 'MAPAS')
            self.but_ver_maps.pack(side=LEFT,expand=1,fill=X)
            def mapas_buttons():
                self.close_windows()
                ventana_mapas = Frame(w,bg='gray')
                self.but_ver_ptos = Checkbutton(ventana_mapas, text = 'Fijos', variable=self.vf, command=self.master.toggle_point_names)
                self.but_ver_ptos.grid(column=0,row=0,sticky=E+W)
                self.but_ver_tmas = Checkbutton(ventana_mapas, text = 'TMAs',  variable=self.vt, command=self.master.toggle_tmas)
                self.but_ver_tmas.grid(column=0,row=1,sticky=E+W)
                self.but_ver_deltas = Checkbutton(ventana_mapas, text = 'Deltas', variable=self.vd, command=self.master.toggle_deltas)
                self.but_ver_deltas.grid(column=0,row=2,sticky=E+W)
                
                myrow = 3
                #map_name_list = local_maps.keys()
                #map_name_list.sort()
                #for map_name in map_name_list:
                #    self.but_ver_local_map = Checkbutton(ventana_mapas, text = map_name, variable = var_ver_localmap[map_name], command=b_show_hide_localmaps)
                #    self.but_ver_local_map.grid(column=0,row=myrow,sticky=E+W)
                #    myrow += 1
                #    
                i=w.create_window(ventana.winfo_x()+self.but_ver_maps.winfo_x(),alto-ventana.winfo_height(),window=ventana_mapas,anchor='sw')
                self.opened_windows.append(i)
            self.but_ver_maps['command'] = mapas_buttons

            self.but_ver_tabs = Button(ventana, text = 'TABs',state=DISABLED)
            self.but_ver_tabs.pack(side=LEFT,expand=1,fill=X)
            def tabs_buttons():
                global vent_ident_tabs
                if vent_ident_tabs != None:
                    w.delete(vent_ident_tabs)
                    vent_ident_tabs = None
                    return
                ventana_tabs = Frame(w,bg='gray')
                self.but_reports = Button(ventana_tabs, text='Notificaciones',
                                     command = acftnotices.show)
                self.but_reports.grid(column=0,row=0,sticky=E+W)
                vent_ident_tabs=w.create_window(ventana.winfo_x()+self.but_ver_tabs.winfo_x(),alto-ventana.winfo_height(),window=ventana_tabs,anchor='sw')
            self.but_ver_tabs['command'] = tabs_buttons
            def cambia_vect_vel(e=None):
                master.change_speed_vector(self.speed_vector_var.get()/60.)
            cnt_vect_vel = Control(ventana, label="Vel:", min=0, max=5, integer=1, command=cambia_vect_vel, variable=self.speed_vector_var)
            cnt_vect_vel.pack(side=LEFT,expand=1,fill=X)
            def cambia_vel_reloj(e=None):
                set_vel_reloj(float(master.clock_speed_var.get()))
            cnt_vel_reloj = Control(ventana, label="Clock X:", min=0.5, max=99.0, step=0.1, command=cambia_vel_reloj, variable=master.clock_speed_var, state=DISABLED)
            cnt_vel_reloj.pack(side=LEFT,expand=1,fill=X)
            
            self.toolbar_id=w.create_window(0,alto,width=ancho,window=ventana,anchor='sw')
            ventana.update_idletasks()
            logging.debug ('Auxiliary window width: '+str(ventana.winfo_width()))
            
        #else:
        #    ventana=Frame(w,bg='gray')
        #    button_width = 25 + (ancho - 804)/7
        #    self.but_inicio = Button(ventana,bitmap='@'+IMGDIR+'start.xbm',command=b_inicio)
        #    self.but_inicio.grid(column=0,row=0,sticky=E+W)
        #    self.but_parar = Button(ventana,bitmap='@'+IMGDIR+'pause.xbm',command=b_parar)
        #    self.but_parar.grid(column=1,row=0,sticky=E+W)
        #    self.but_arriba = Button(ventana,bitmap='@'+IMGDIR+'up.xbm',command=b_arriba)
        #    self.but_arriba.grid(column=1,row=1,sticky=E+W)
        #    self.but_izq = Button(ventana,bitmap='@'+IMGDIR+'left.xbm',command=b_izquierda)
        #    self.but_izq.grid(column=0,row=1,sticky=E+W)
        #    self.but_abajo = Button(ventana,bitmap='@'+IMGDIR+'down.xbm',command=b_abajo)
        #    self.but_abajo.grid(column=2,row=1,sticky=E+W)
        #    self.but_derecha = Button(ventana,bitmap='@'+IMGDIR+'right.xbm',command=b_derecha)
        #    self.but_derecha.grid(column=3,row=1,sticky=E+W)
        #    self.but_zoom_mas = Button(ventana,bitmap='@'+IMGDIR+'zoom.xbm',command=b_zoom_mas)
        #    self.but_zoom_mas.grid(column=4,row=1,sticky=E+W)
        #    self.but_zoom_menos = Button(ventana,bitmap='@'+IMGDIR+'unzoom.xbm',command=b_zoom_menos)
        #    self.but_zoom_menos.grid(column=5,row=1,sticky=E+W)
        #    self.but_standard = Button(ventana,bitmap='@'+IMGDIR+'center.xbm',command=b_standard)
        #    self.but_standard.grid(column=6,row=1,sticky=E+W)
        #    self.but_tamano_etiq = Button(ventana,bitmap='@'+IMGDIR+'labelsize.xbm',command=b_tamano_etiquetas)
        #    self.but_tamano_etiq.grid(column=7,row=1)
        #    def cambia_vect_vel(e=None):
        #        set_speed_time(float(master.speed_vector_var.get())/60.)
        #        redraw_all()
        #    cnt_vect_vel = Control(ventana, label="Velocidad:", min=0, max=5, integer=1, command=cambia_vect_vel, variable=master.speed_vector_var)
        #    cnt_vect_vel.grid(column=2,row=0,columnspan=4)
        #    def cambia_vel_reloj(e=None):
        #        set_vel_reloj(float(master.clock_speed_var.get()))
        #    cnt_vel_reloj = Control(ventana, label="Vel reloj:", min=0.5, max=9.0, step=0.1, command=cambia_vel_reloj, variable=master.clock_speed_var)
        #    cnt_vel_reloj.grid(column=6,row=0,columnspan=3)
        #    #     separador1 = Label(ventana,text='-----PSEUDOPILOTO-----')
        #    #     separador1.grid(column=0,row=10,columnspan=3,sticky=E+W)
        #    self.but_term = Button(ventana,text='Kill',command=kill_acft)
        #    self.but_term.grid(column=8,row=1)
        #    self.but_ruta = Button(ventana,text='Ruta',command=nueva_ruta)
        #    self.but_ruta.grid(column=9,row=1)
        #    self.but_datos = Button(ventana,text='Datos',command=ver_detalles)
        #    self.but_datos.grid(column=10,row=1)
        #    self.but_quitar_lads = Button(ventana,text='LADs', fg = 'red',command = quitar_lads)
        #    self.but_quitar_lads.grid(column=11,row=1)
        #    self.but_quitar_fpr = Button(ventana,text='Rutas', fg = 'red',command = quitar_fpr)
        #    self.but_quitar_fpr.grid(column=12,row=1)
        #    self.but_espera = Button(ventana, text='HLD', command = define_holding)
        #    self.but_espera.grid(column=13,row=1)
        #    self.but_hdg_fix = Button(ventana, text = 'HDG<FIX', command = hdg_after_fix)
        #    self.but_hdg_fix.grid(column=14,row=1)
        #    self.but_int_rdl = Button(ventana, text = 'RDL', command = int_rdl)
        #    self.but_int_rdl.grid(column=15,row=1)
        #    self.but_int_rdl = Button(ventana, text = 'RWY', command = b_rwy_change)
        #    self.but_int_rdl.grid(column=16,row=1)
        #    #       self.but_int_rdl = Button(ventana, text = 'DEP', command = None)
        #    #       self.but_int_rdl.grid(column=17,row=1)
        #    self.but_int_rdl = Button(ventana, text = 'APP', command = b_auth_approach)
        #    self.but_int_rdl.grid(column=18,row=1)
        #    self.but_int_rdl = Button(ventana, text = 'ILS', command = b_int_ils)
        #    self.but_int_rdl.grid(column=17,row=1)
        #    self.but_int_rdl = Button(ventana, text = 'MAP', command = b_execute_map)
        #    self.but_int_rdl.grid(column=18,row=0)
        #    self.but_auto_separation = Checkbutton(ventana, text = 'AUTO SEP', variable = self.master.auto_separation, command=b_auto_separationaration)
        #    self.but_auto_separation.grid(column=9,row=0,columnspan=2,sticky = W+E)
        #    self.but_ver_ptos = Checkbutton(ventana, text = 'Nombre Fijos', variable = var_ver_ptos, command=b_show_hide_points)
        #    self.but_ver_ptos.grid(column=11,row=0,columnspan=2,sticky = W+E)
        #    self.but_ver_tmas = Checkbutton(ventana, text = 'TMAs', variable = var_ver_tmas, command=b_show_hide_tmas)
        #    self.but_ver_tmas.grid(column=13,row=0,columnspan=2,sticky = W+E)
        #    self.but_ver_deltas = Checkbutton(ventana, text = 'Deltas', variable = var_ver_deltas, command=b_show_hide_deltas)
        #    self.but_ver_deltas.grid(column=15,row=0,columnspan=2,sticky = W+E)
        #    
        #    vent_ident=w.create_window(0,alto,window=ventana,anchor='sw')
        #    ventana.update_idletasks()

class AcftNotices(RaTabular):
    """A tabular window showing reports and requests from aircraft"""
    def __init__(self, master=None, flights=None):
        """Create a tabular showing aircraft reports and requests"""
        RaTabular.__init__(self, master, label='Notificaciones',
                           position=(120,200), closebuttonhides=True)
        self._last_updated=0.
        self._flights=flights
        
    def update(self,t):
        """Check whether any new message should be printed"""
        # We need only update this tabular at most once a second
        if t-self._last_updated<1/60./60.:
            return
            
            # Check whether the pilots have anything to report.
        for acft in self._flights:
            for i,report in enumerate(acft.reports):
                if t>report['time']:
                    h=int(t)
                    m=int(60*(t-h))
                    report='%02d:%02d %s %s'%(h,m,acft.name,report['text'])
                    self.insert(END, report)
                    self.notify()
                    del acft.reports[i]
        self._last_updated=t
        
    def notify(self):
        """Make it obvious to the user that there has been a new notification"""
        import sys
        if sys.platform=='win32':
            import winsound
            try:
                winsound.PlaySound(SNDDIR+'/chime.wav', winsound.SND_NOSTOP|winsound.SND_ASYNC)
            except:
                pass
