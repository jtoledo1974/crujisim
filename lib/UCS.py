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
"""Classes used by the air traffic controller's interface of Crujisim"""

from RaDisplay import *
import avion

SNDDIR='./snd/'

class UCS(RaDisplay):
    """Air Traffic Controllers' radar display and user interface"""
    
    def __init__(self,flights,title,icon_path,fir,sector,mode='atc'):
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
        
        self.redraw()
        self.separate_labels()
        
    def process_message(self, m):
        
        def update_flight(new):
            try: old = [old for old in self.flights if new.name==old.name][0]
            except:
                logging.warning("Unable to update %s. No local flight so named"%(new.name))
                return
            for name, value in new.__dict__.items():
                setattr(old, name, value)
            return old
        
        if m['message']=='time':
            t = m['data']
            self.update_clock(t)

        if m['message']=='update':
            flights = m['flights']
            for f in flights: update_flight(f)
            self.wind = m['wind']
            self.stop_separating = True

            self.update()


        if m['message']=='update_flight':
            f = update_flight(m['flight'])  # Returns the updated flight
            self.update_track(f)

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
                id_avo = Label(win,text=track.name,bg='blue',fg='white')
                id_pto = Entry (win,width=8,justify = CENTER)
                id_pto.insert(0,point_name)
                but_direct = Button(win, text="Dar directo")
                but_cancel = Button(win, text="Cancelar")
                id_avo.grid(row=0, column=0, columnspan=1,sticky=W+E)
                id_pto.grid(row=1, column=0, columnspan=1,sticky=W+E)
                but_direct.grid(row=2, column=0, columnspan=1,sticky=W+E)
                but_cancel.grid(row=3, column=0, columnspan=1,sticky=W+E)
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
        for f in self.flights:
            self.update_track(f)
            
    def update_track(self, f):
        vt = self._flights_tracks[f]
        vt.alt=f.alt
        vt.cs=f.name
        vt.wake=f.estela
        vt.echo=f.campo_eco
        vt.gs=f.ground_spd
        vt.mach=f.get_mach()
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
        vt.pfl=f.pfl
        if f.atc_pos!=None and f.atc_pos==self.pos_number: vt.assumed = True
        else: vt.assumed = False
        if f.atc_pos != None: vt.flashing = False
        else: vt.flashing = True
        
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
        
    def play(self):
        pass
    
    def pause(self):
        pass
    
    def exit(self):
        self.clock.close()
        del (self.clock)
        del(self.toolbar.master)
        del(self.toolbar)
        RaDisplay.exit(self)
        print sys.getrefcount(self)
        
    def __del__(self):
        logging.debug("PpDisplay.__del__")
    
class ventana_auxiliar:
    def __init__(self,master):
        self.master=master
        self.opened_windows=[]
        self.vr = IntVar()
        self.vr.set(master.draw_routes)
        self.vf = IntVar()
        self.vf.set(master.draw_point)
        self.vfn = IntVar()
        self.vfn.set(master.draw_point_names)
        self.vs = IntVar()
        self.vs.set(master.draw_sector)
        self.vsl = IntVar()
        self.vsl.set(master.draw_lim_sector)
        self.vt = IntVar()
        self.vt.set(master.draw_tmas)
        self.vd = IntVar()
        self.vd.set(master.draw_deltas)
        self.var_ver_localmap = {}
        
        for map_name in master.fir.local_maps:
            self.var_ver_localmap[map_name] = IntVar()
            self.var_ver_localmap[map_name].set(0)
        
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


        MINIMUM_DISPLACEMENT = 80
        NORMAL_DISPLACEMENT = 10
        MAXIMUM_DISPLACEMENT = 3
        
        def set_displacement(mouse_pressed_button):
            if mouse_pressed_button == 1:
                return NORMAL_DISPLACEMENT
            elif mouse_pressed_button == 2:
                return MAXIMUM_DISPLACEMENT
            elif mouse_pressed_button == 3:
                return MINIMUM_DISPLACEMENT
        
        def b_izquierda(event):
            master.x0 -= ancho/set_displacement(event.num)/scale
            master.reposition()
            
        def b_derecha(event):
            master.x0 += ancho/set_displacement(event.num)/scale
            master.reposition()
            
        def b_arriba(event):
            master.y0 += ancho/set_displacement(event.num)/scale
            master.reposition()
            
        def b_abajo(event):
            master.y0 -= ancho/set_displacement(event.num)/scale
            master.reposition()
            
        MINIMUM_SCALE_FACTOR = 1.01
        NORMAL_SCALE_FACTOR = 1.1
        MAXIMUM_SCALE_FACTOR = 1.5
        
        LABEL_MIN_FONT_SIZE = 7
        LABEL_MAX_FONT_SIZE = 11
        LABEL_SIZE_STEP = 1

        def set_zoom_scale_on_event (event_number=1):
            if event_number==3:
                return MINIMUM_SCALE_FACTOR
            elif event_number==2:
                return MAXIMUM_SCALE_FACTOR
            elif event_number==1:
                return NORMAL_SCALE_FACTOR
            
        def b_zoom_mas(event):
            master.scale *= set_zoom_scale_on_event(event.num)
            master.reposition()
            
        def b_zoom_menos(event):
            master.scale /= set_zoom_scale_on_event(event.num)
            master.reposition()
            
        def b_standard():
            master.center_x=ancho/2
            master.center_y=(alto-40.)/2
            master.get_scale()
            master.reposition()
                            
        def b_tamano_etiquetas(event):
            if event.num == 1:
                step_increment = LABEL_SIZE_STEP
            elif event.num == 3:
                step_increment = -LABEL_SIZE_STEP
            elif event.num == 2:
                step_increment = LABEL_MIN_FONT_SIZE
                
            font_size = master.label_font_size
            font_size += step_increment
            if font_size > LABEL_MAX_FONT_SIZE:
                font_size = LABEL_MIN_FONT_SIZE
            elif font_size < LABEL_MIN_FONT_SIZE:
                font_size = LABEL_MAX_FONT_SIZE
            master.label_font_size = font_size
            
            for vt in self.master.tracks:
                vt.l_font_size = font_size
            master.label_font.configure(size=master.label_font_size)
                        
        def b_show_hide_localmaps():
            master.local_maps_shown = []
            for map_name in master.fir.local_maps:
                if self.var_ver_localmap[map_name].get() != 0:
                    master.local_maps_shown.append(map_name)
            master.redraw_maps()
            
        def b_auto_separationaration():
            global auto_separation
            auto_separation = not auto_separation
                                
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
            

        ventana=Frame(w,bg='gray',width=ancho)
        self.but_inicio = Button(ventana,bitmap='@'+IMGDIR+'start.xbm',state=DISABLED)
        self.but_inicio.pack(side=LEFT,expand=1,fill=X)
        self.but_parar = Button(ventana,bitmap='@'+IMGDIR+'pause.xbm',state=DISABLED)
        self.but_parar.pack(side=LEFT,expand=1,fill=X)
        
        self.but_izq = Button(ventana,bitmap='@'+IMGDIR+'left.xbm')
        self.but_izq.pack(side=LEFT,expand=1,fill=X)
        self.but_izq.bind("<Button-1>",b_izquierda)
        self.but_izq.bind("<Button-2>",b_izquierda)
        self.but_izq.bind("<Button-3>",b_izquierda)

        self.but_arriba = Button(ventana,bitmap='@'+IMGDIR+'up.xbm')
        self.but_arriba.pack(side=LEFT,expand=1,fill=X)
        self.but_arriba.bind("<Button-1>",b_arriba)
        self.but_arriba.bind("<Button-2>",b_arriba)
        self.but_arriba.bind("<Button-3>",b_arriba)            
        
        self.but_abajo = Button(ventana,bitmap='@'+IMGDIR+'down.xbm')
        self.but_abajo.pack(side=LEFT,expand=1,fill=X)
        self.but_abajo.bind("<Button-1>",b_abajo)
        self.but_abajo.bind("<Button-2>",b_abajo)
        self.but_abajo.bind("<Button-3>",b_abajo)            
    
        self.but_derecha = Button(ventana,bitmap='@'+IMGDIR+'right.xbm')
        self.but_derecha.pack(side=LEFT,expand=1,fill=X)
        self.but_derecha.bind("<Button-1>",b_derecha)
        self.but_derecha.bind("<Button-2>",b_derecha)
        self.but_derecha.bind("<Button-3>",b_derecha)            
        
        self.but_zoom_mas = Button(ventana,bitmap='@'+IMGDIR+'zoom.xbm')
        self.but_zoom_mas.pack(side=LEFT,expand=1,fill=X)
        self.but_zoom_mas.bind("<Button-1>",b_zoom_mas)
        self.but_zoom_mas.bind("<Button-2>",b_zoom_mas)
        self.but_zoom_mas.bind("<Button-3>",b_zoom_mas)
        
        self.but_zoom_menos = Button(ventana,bitmap='@'+IMGDIR+'unzoom.xbm')
        self.but_zoom_menos.pack(side=LEFT,expand=1,fill=X)
        self.but_zoom_menos.bind("<Button-1>",b_zoom_menos)
        self.but_zoom_menos.bind("<Button-2>",b_zoom_menos)
        self.but_zoom_menos.bind("<Button-3>",b_zoom_menos)
        
        self.but_standard = Button(ventana,bitmap='@'+IMGDIR+'center.xbm',command=b_standard)
        self.but_standard.pack(side=LEFT,expand=1,fill=X)
        
        self.but_tamano_etiq = Button(ventana,bitmap='@'+IMGDIR+'labelsize.xbm')
        self.but_tamano_etiq.pack(side=LEFT,expand=1,fill=X)
        self.but_tamano_etiq.bind("<Button-1>",b_tamano_etiquetas)
        self.but_tamano_etiq.bind("<Button-2>",b_tamano_etiquetas)
        self.but_tamano_etiq.bind("<Button-3>",b_tamano_etiquetas)
        
        self.but_term = Button(ventana,text='Kill',state=DISABLED)
        self.but_term.pack(side=LEFT,expand=1,fill=X)
        self.but_ruta = Button(ventana,text='Ruta',state=DISABLED)
        self.but_ruta.pack(side=LEFT,expand=1,fill=X)
        self.but_datos = Button(ventana,text='Datos',command=ver_detalles)
        self.but_datos.pack(side=LEFT,expand=1,fill=X)
        self.but_quitar_lads = Button(ventana,text='LADs', fg = 'red',command = self.master.delete_lads)
        self.but_quitar_lads.pack(side=LEFT,expand=1,fill=X)
        self.but_quitar_fpr = Button(ventana,text='Rutas', fg = 'red',command = self.master.delete_routes)
        self.but_quitar_fpr.pack(side=LEFT,expand=1,fill=X)
        self.but_ver_proc = Button(ventana, text = 'PROCs',state=DISABLED)
        self.but_ver_proc.pack(side=LEFT,expand=1,fill=X)
        self.but_ver_app = Button(ventana, text = 'APP',state=DISABLED)
        self.but_ver_app.pack(side=LEFT,expand=1,fill=X)

        self.but_auto_separation = Checkbutton(ventana, text = 'SEP', variable = self.auto_sep, command=lambda: master.toggle_auto_separation())
        self.but_auto_separation.pack(side=LEFT,expand=1,fill=X)

        self.but_bri = Button(ventana, text = 'BRI', command = master.rabrightness.conmuta)
        self.but_bri.pack(side=LEFT,expand=1,fill=X)

        self.but_ver_maps = Button(ventana, text = 'MAPAS')
        self.but_ver_maps.pack(side=LEFT,expand=1,fill=X)
        def mapas_buttons():
            self.close_windows()
            ventana_mapas = Frame(w)
            myrow = 0
            self.but_ver_nombrs_ptos = Checkbutton(ventana_mapas, text = 'Nombres Fijos', variable=self.vfn, command=self.master.toggle_point_names)
            self.but_ver_nombrs_ptos.grid(column=0,row=myrow,sticky=W)
            myrow+= 1
            self.but_ver_ptos = Checkbutton(ventana_mapas, text = 'Fijos', variable=self.vf, command=self.master.toggle_point)
            self.but_ver_ptos.grid(column=0,row=myrow,sticky=W)
            myrow+= 1
            self.but_ver_routes = Checkbutton(ventana_mapas, text = 'Aerovias', variable=self.vr, command=self.master.toggle_routes)
            self.but_ver_routes.grid(column=0,row=myrow,sticky=W)
            myrow+= 1
            self.but_ver_sector = Checkbutton(ventana_mapas, text = 'Sector', variable=self.vs, command=self.master.toggle_sector)
            self.but_ver_sector.grid(column=0,row=myrow,sticky=W)
            myrow+= 1
            self.but_ver_lim_sector = Checkbutton(ventana_mapas, text = 'Lim. Sector', variable=self.vsl, command=self.master.toggle_lim_sector)
            self.but_ver_lim_sector.grid(column=0,row=myrow,sticky=W)
            myrow+= 1
            self.but_ver_tmas = Checkbutton(ventana_mapas, text = 'TMAs',  variable=self.vt, command=self.master.toggle_tmas)
            self.but_ver_tmas.grid(column=0,row=myrow,sticky=W)
            myrow+= 1
            self.but_ver_deltas = Checkbutton(ventana_mapas, text = 'Deltas', variable=self.vd, command=self.master.toggle_deltas)
            self.but_ver_deltas.grid(column=0,row=myrow,sticky=W)
            
            myrow += 1
            #map_name_list = master.fir.local_maps.keys()
            #map_name_list.sort()
            for map_name in master.fir.local_maps_order:
                self.but_ver_local_map = Checkbutton(ventana_mapas, text = map_name, variable = self.var_ver_localmap[map_name], command=b_show_hide_localmaps)
                self.but_ver_local_map.grid(column=0,row=myrow,sticky=W)
                myrow += 1

            i=w.create_window(ventana.winfo_x()+self.but_ver_maps.winfo_x(),alto-ventana.winfo_height(),window=ventana_mapas,anchor='sw')
            self.opened_windows.append(i)
        self.but_ver_maps['command'] = mapas_buttons

        self.but_ver_tabs = Button(ventana, text = 'TABs',state=DISABLED)
        self.but_ver_tabs.pack(side=LEFT,expand=1,fill=X)
        def cambia_vect_vel(e=None):
            master.change_speed_vector(self.speed_vector_var.get()/60.)
        cnt_vect_vel = Control(ventana, label="Vel:", min=0, max=5, integer=1, command=cambia_vect_vel, variable=self.speed_vector_var)
        cnt_vect_vel.pack(side=LEFT,expand=1,fill=X)
        cnt_vel_reloj = Control(ventana, label="Clock X:", min=0.5, max=99.0, step=0.1, state=DISABLED)
        cnt_vel_reloj.pack(side=LEFT,expand=1,fill=X)
        
        self.toolbar_id=w.create_window(0,alto,width=ancho,window=ventana,anchor='sw')
        ventana.update_idletasks()
        logging.debug ('Auxiliary window width: '+str(ventana.winfo_width()))
