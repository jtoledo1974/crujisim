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
"""Container module for the RaDisplay class, a generic radar display"""

from math import floor, sqrt
from time import time
import logging
import sys
from twisted.internet import reactor, threads

from Tix import *
import tkFont

from FIR import *
from MathUtil import *
from RaElements import *


class RaDisplay(object):
    """Generic radar display in which tracks and lads are shown
    
    This class requires that a Tk session is already active
    """
    def __init__(self,conf,title,icon_path,fir,sector,toolbar_height):
        """Instantiate a generic Radar Display
        
        title - window title
        icon_path - path to the windows task bar icon
        fir -- fir object
        sector -- name of the sector to work with
        """
        
        self.fir=fir
        self.sector=sector
        self.conf=conf
        
        self.top_level=Toplevel()
        tl = self.top_level
        if sys.platform.startswith('win'):
            tl.wm_iconbitmap(icon_path)
            tl.wm_state('zoomed')
        tl.wm_title(title)
        
        SmartColor.winfo_rgb = tl.winfo_rgb  # SmartColors needs a valid winfo_rgb function
                                            # which is only available once Tkinter
                                            # in initialized
        
        self.screen_width = tl.winfo_screenwidth()
        self.screen_height = tl.winfo_screenheight()
        screen_width = self.screen_width
        screen_height = self.screen_height
        tl.wm_geometry("%dx%d+%d+%d" % (screen_width, screen_height, 0, 0))
        
        self.c = c = Canvas(tl,bg='gray3')
        c.pack(expand=1,fill=BOTH)
        ra_bind(self, c, '<Configure>', self.change_size)

        # Used to prevent the label separation code to be run nested
        self.separating_labels = False
        # Same thing with the STCA code
        self.stca_running = False
        
        # Screen parameters
        self.width=tl.winfo_width()
        self.height=tl.winfo_height()
        self.toolbar_height = toolbar_height
        self.center_x=self.width/2
        self.center_y=(self.height-self.toolbar_height)/2
        
        # World coordinates parameters
        self.x0=0.  # x0 and y0 define the center of the sector to display
        self.y0=0.  # in world coordinates
        self.scale=1.0  # Scale factor between screen and world coordinates
        
        self.maps               = {}  # Dictionary of map objects
        
        #Get values stored (map = active/non-active) in cujisim.ini
        self.draw_point_names   = self.conf.read_option("Maps","Point_names",True,"bool")
        self.draw_point         = self.conf.read_option("Maps","Points",True,"bool")
        self.draw_routes        = self.conf.read_option("Maps","Routes",True,"bool")
        self.draw_sector        = self.conf.read_option("Maps","Sector",True,"bool")
        self.draw_lim_sector    = self.conf.read_option("Maps","Lim_sector",True,"bool")
        self.draw_tmas          = self.conf.read_option("Maps","TMAs",True,"bool")
        self.draw_deltas        = self.conf.read_option("Maps","Deltas",True,"bool")
        
        self.local_maps_shown = []
        
        self.auto_separation = True  # Separate labels automatically
        self.pac = True
        
        VisTrack.timer_id = None  # Reset the VisTrack class
        self.tracks = []  # List of tracks (VisualTrack instances)
        self.selected_track = None
        self.lads = []  # List of LADs
        self.cancel_lad_serial = -1  # To be used to cancel lad creation after middle clicking some virtual track label item
        self.defining_lad = False

        self.pos_number = None  # Radar position number (identifies this radar display)
        
        self.label_font_size = 8
        self.label_font = tkFont.Font(family="Helvetica",size=self.label_font_size)
        self.label_moved = False  # Whether a label has recently been manually moved
        
        ra_bind(self, self.c, '<Button-1>', self.b1_cb)
        ra_bind(self, self.c, '<Button-2>', self.b2_cb)
        ra_bind(self, self.c, '<Button-3>', self.b3_cb)
        
        self.get_scale() # Calculate initial x0, y0 and scale
        
        self.intensity={"GLOBAL":ConfMgr.CrujiConfig().read_option("Brightness", "GLOBAL", 0 ,"float" ),
                        "TRACKS":ConfMgr.CrujiConfig().read_option("Brightness", "TRACKS", 0 ,"float"),
                        "MAP":ConfMgr.CrujiConfig().read_option("Brightness", "MAP", 0, "float" ),
                        "LADS":ConfMgr.CrujiConfig().read_option("Brightness", "LADS", 0, "float" )}
        
        
        self.rabrightness = RaBrightness(c, self.set_element_intensity,position=(self.width*0.4,self.height*0.8))
        self.rabrightness.hide()

    def change_size(self,e):
        self.width = e.width
        self.height = e.height
        self.c.update_idletasks()

        
    def change_speed_vector(self,minutes,e=None):
        for track in self.tracks:
            track.speed_vector_length=minutes
                    
    def vt_handler(self,vt,item,action,value,e=None):
        """Handle events raised by visual tracks
        Visual tracks have their own GUI code to present the user
        with CFL and ECL dialog, for instance, but then they notify the parent
        about the result using this function"""
        if action=="<Button-2>" and item!='plot':
            self.cancel_lad_serial=e.serial
        pass
        if item=='cs':
            if action=='<Button-1>':
                m={"message":"assume", "cs": vt.cs,
                   "assumed": not vt.assumed or vt.flashing}
                    # If flashing always assume the traffic.
                self.sendMessage(m)
            elif action=='<Motion>':
                self.label_moved = True
            elif action=='<ButtonRelease-2>':
                try: self.selected_track.selected = not self.selected_track.selected
                except: logging.debug("Unselecting previous selected track failed")
                if self.selected_track == vt:
                    self.selected_track = None
                    vt.selected = False
                else:
                    self.selected_track = vt
                    vt.selected = True
                if self.label_moved:
                    reactor.callInThread(self.separate_labels, vt)
                    self.label_moved = False
        elif item=='leader':
            if action=='<Button-1>' or action=='<Button-3>':
                reactor.callInThread(self.separate_labels, vt)
        elif item=='transfer':
            m={"message":"transfer", "cs": vt.cs}
            self.sendMessage(m)
        elif item=='set_echo':
            m={"message":"set_echo","cs":vt.cs,"echo":value}
            self.sendMessage(m)
  

    
    def b1_cb(self,e=None):
        pass
        
    def b2_cb(self,e=None):
        self.def_lad(e)
        
    def b3_cb(self,e=None):
        pass
        
    def def_lad(self,e=None):
        if e.serial==self.cancel_lad_serial or self.defining_lad: return
        self.defining_lad = True
        LAD(self,e)
    
    def delete_lads(self,e=None):
        for lad in self.lads[:]:
            lad.delete()

    def update(self):
        # Tracks are updated by the superclass when it gives them the new coords
        self.update_lads()
        reactor.callInThread(self.update_stca)
        reactor.callInThread(self.separate_labels)
    
    def toggle_auto_separation(self):
        self.auto_separation = not self.auto_separation
        if self.auto_separation:
            reactor.callInThread(self.separate_labels)
        
    def separate_labels(self, single_track=None):
        # TODO This algorithm is currently O(n**2). It needs to be rewritten
        # There are many good ideas in http://en.wikipedia.org/wiki/Collision_detection
        tracks = self.tracks
        width,height = self.width,self.height
        canvas = self.c
        if not self.auto_separation or self.separating_labels: return
        
        self.separating_labels = True
        self.stop_separating = False
        crono = time()
        
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
                
                # If the caller provided a specific track as an argument, we only want
                # to separate that label. Else try to separate everything
                if single_track and ti!=single_track and tj!=single_track:
                    continue
                
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
            while (intersectan_girado > 0) and (cuenta[conflict_list[0]] < rotating_steps) and rotating_labels and (time()-crono)<4.:
                #canvas.update()
                if self.stop_separating:
                    logging.debug("Cancelling label separation after "+str(time()-crono2)+" seconds")
                    self.separating_labels = False
                    return  # Set, for instance, when moving the display
                # Try rotating one of the labels on the list
                for k in range(len(conflict_list)-1,-1,-1):
                    t = conflict_list[k]
                    # If the track is not set to be auto_separated, or if the
                    # label separation algorithem was called because of a manual
                    # label rotation, don't rotate this track
                    if not t.auto_separation or t==single_track:
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
        
        # Once we have reached the result, we can't really update the labels from
        # here, because Tkinter is not thread safe
        
        def move_labels(move_list):
            # Update the labels
            if not self.stop_separating:
                for t in move_list:
                    (x,y)=best_pos[t]
                    t.label_coords(x,y)                
            self.separating_labels = False
        
        # We make sure that the label moving is done from the main thread and event loop    
        reactor.callFromThread(move_labels, move_list)

    def update_stca(self):
        """Process short term collision alert"""
        # Calculate each track's position in 30 and 60 seconds
        
        if self.stca_running:
            logging.warning("update_stca has been called when it was already running.\nWe are falling begind on the processing, and alerts may not be accurate")
            return
        
        self.stca_running = True
        t_alerts = {}  # Alert status for each track
        NONE = 0
        PAC  = 2
        VAC  = 4
        
        for track in self.tracks:
            if not track.visible: continue
            track.future_pos = []
            t_alerts[track] = NONE
            delta = 1./60./6  # delta = 10s
            for t in [delta, delta*2, delta*3, delta*4, delta*5, delta*6]:  
                gtx = sin(radians(track.track))  # Ground track projection on x
                gty = cos(radians(track.track))  # Ground track projection on y
                (x,y,alt) = (track.wx,track.wy,track.alt)  # Current position
                gs = track.gs  # Ground speed
                nx = x + gs*t*gtx  # Future x coord in t hours
                ny = y + gs*t*gty  # Future y coord in t hours
                nalt = alt + track.rate*t
                track.future_pos.append((nx,ny,nalt))
        
        try: min_sep = self.fir.min_sep[self.sector]
        except:
            min_sep = 8.0  # 8 nautical miles
            logging.warning("Sector minimum separation not found. Using 8nm")
        
        minvert = 9.5  # 950 feet minimum vertical distance
                
        # Vertical filter
        vfilter = max([ad.val_elev for ad in self.fir.aerodromes.values()]) + 1  # 1000 feet over the highest AD
                
        for i in range(len(self.tracks)):
            for j in range(i+1,len(self.tracks)):
                ti = self.tracks[i]
                tj = self.tracks[j]
                if not ti.visible or not tj.visible: continue
                
                # Test for conflict
                ix,iy,jx,jy = ti.wx,ti.wy,tj.wx,tj.wy
                dist=sqrt((ix-jx)**2+(iy-jy)**2)        
                if ti.alt < vfilter or tj.alt < vfilter: continue
                if dist<min_sep and abs(ti.alt-tj.alt)<minvert:
                    t_alerts[ti] |= VAC
                    t_alerts[tj] |= VAC
                    continue
                
                # STCA
                if not self.pac: continue
                
                for ((ix,iy,ialt),(jx,jy,jalt)) in zip(ti.future_pos,tj.future_pos):
                    dist=sqrt((ix-jx)**2+(iy-jy)**2)
                    if ialt < vfilter or jalt < vfilter: continue
                    if dist<min_sep and abs(ialt-jalt)<minvert:
                        t_alerts[ti] |= PAC
                        t_alerts[tj] |= PAC
                        continue
        # Once we have reached the result, we can't really update the labels from
        # here, because Tkinter is not thread safe
        
        def set_track_alerts():
            # Update the labels
            for t, v in t_alerts.items():
                if v & PAC: t.pac = True
                else: t.pac = False
                if v & VAC: t.vac = True
                else: t.vac = False
            self.stca_running = False
        
        # We make sure that the label updating is done from the main thread and event loop    
        reactor.callFromThread(set_track_alerts)
        
    def update_lads(self):
        # A lad might be deleted, so we need to iterate over a copy of the list
        for lad in self.lads[:]:
            lad.redraw()
            
    def get_scale(self):
        """Calculates the display center and the scale to display it all"""
        xmax=-1.e8
        xmin=1.e8
        ymax=-1.e8
        ymin=1.e8
        for a in self.fir.boundaries[self.sector]:
            if a[0]>xmax:
                xmax=a[0]
            if a[0]<xmin:
                xmin=a[0]
            if a[1]>ymax:
                ymax=a[1]
            if a[1]<ymin:
                ymin=a[1]
        self.x0=(xmax+xmin)/2
        self.y0=(ymax+ymin)/2
        x_scale=self.width/(xmax-xmin)
        y_scale=(self.height-self.toolbar_height)/(ymax-ymin)
        self.scale=min(x_scale,y_scale)*0.9
        
    def redraw_maps(self):
        
        c = self.c  # Canvas
        fir = self.fir
        sector = self.sector
        do_scale = self.do_scale
        
        # Delete Map objects
        for map in self.maps.values():
            map.destroy()
        self.maps = {}
        
        # Create Map Objects

        map_intensity = self.intensity["GLOBAL"]*self.intensity["MAP"]
        
        # Currect sector background
        sectormap = RaMap(self.c, self.do_scale, intensity = map_intensity)
        kw = {'color': 'black'}
        sectormap.add_polygon(*fir.boundaries[self.sector], **kw)
        self.maps['sector'] = sectormap
        if not self.draw_sector: sectormap.hide()
        

        # TMAs
        map = RaMap(self.c, self.do_scale, intensity = map_intensity)
        kw = {'color': 'gray30'}
        for tma in fir.tmas:
            map.add_polyline(*tma, **kw)
        self.maps['tmas'] = map
        if not self.draw_tmas: map.hide()
        
        # Airways
        map = RaMap(self.c, self.do_scale, intensity = map_intensity)
        kw = {'color': 'gray25'}
        for airway in fir.airways:
            map.add_polyline(*airway, **kw)
        self.maps['airways'] = map
        if not self.draw_routes: map.hide()

        # Special Use Areas
        map = RaMap(self.c, self.do_scale, intensity = map_intensity)
        kw = {'color': 'gray40'}
        for delta in fir.deltas:
            map.add_polyline(*delta, **kw)
        self.maps['SUA'] = map
        if not self.draw_deltas: map.hide()

        # Fixes (VORs, NDBs, FIXes)
        map = RaMap(self.c, self.do_scale, intensity = map_intensity)
        for p in [p for p in fir.points if p[0][0]<>'_']:
            if len(p[0]) == 3:
                map.add_symbol(VOR, p[1], color='gray25')
            elif len(p[0]) == 2:
                map.add_symbol(NDB, p[1], color='gray25')
            else:
                map.add_symbol(FIX, p[1], color='gray25')
        self.maps['points'] = map
        if not self.draw_point: map.hide()

        # Sector border
        seclimitmap = RaMap(self.c, self.do_scale, intensity = map_intensity)
        kw = {'color': 'blue'}
        seclimitmap.add_polyline(*fir.boundaries[self.sector], **kw)
        self.maps['sector_limit'] = seclimitmap
        if not self.draw_lim_sector: seclimitmap.hide()

        # Fix names
        map = RaMap(self.c, self.do_scale, intensity = map_intensity)
        for p in [p for p in fir.points if p[0][0]<>'_']:
            map.add_text(p[0], p[1], color='gray40')
        self.maps['point_names'] = map
        if not self.draw_point_names: map.hide()


        def draw_SID_STAR(map, object):
            
            def draw_single_SID_STAR(single_sid_star,remove_underscored = True):
                rte = single_sid_star.rte
                wp0  = rte[0]
                for i in range(1, len(rte)):
                    wp1 = rte[i]
                    if wp1.fix[0] == '_' and remove_underscored: continue
                    map.add_polyline(wp0.pos(), wp1.pos(), color=color)
                    wp0 = wp1
                    
            sid_star_rwy = object[1]
            sid_star_name = object[2]
            if len(object) > 3: color = object[3]
            else:  color = 'white'

            try:            
                ad = self.fir.aerodromes[sid_star_rwy[:4]]
                rwy_desig = sid_star_rwy[4:]
                rwy = [rwy for rwy in ad.rwy_direction_list if rwy.txt_desig == rwy_desig][0]
            except:
                logging.error("Unable to draw procedure for %s"%sid_star_rwy, exc_info=True)
            if object[0] == 'draw_sid':     dict = rwy.sid_dict
            elif object[0] == 'draw_star':  dict = rwy.star_dict
            
            for proc in (proc for proc in dict.values()
                                if sid_star_name=='' or sid_star_name == proc.txt_desig):
                draw_single_SID_STAR(proc, True)
              
        # Local Maps
        for map_name in fir.local_maps.keys():
            map = RaMap(self.c, self.do_scale, intensity = map_intensity)
            objects = fir.local_maps[map_name]
            for ob in objects:
                if ob[0] == 'linea':
                    cx0 = float(ob[1])
                    cy0 = float(ob[2])
                    cx1 = float(ob[3])
                    cy1 = float(ob[4])
                    if len(ob) > 5:
                        col = ob[5]
                    else:
                        col = 'gray'
                    map.add_polyline((cx0, cy0), (cx1, cy1), color=col)
                elif ob[0] == 'arco':
                    cx0, cy0, cx1, cy1 = float(ob[1]), float(ob[2]), float(ob[3]), float(ob[4])
                    start, extent = float(ob[5]), float(ob[6])
                    if len(ob) > 7: col = ob[7]
                    else: col = 'gray'
                    map.add_arc((cx0, cy0), (cx1, cy1), start, extent, color=col)
                elif ob[0] == 'ovalo':
                    cx0 = float(ob[1])
                    cy0 = float(ob[2])
                    cx1 = float(ob[3])
                    cy1 = float(ob[4])
                    if len(ob) > 5:
                        col = ob[5]
                    else:
                        col = 'gray'
                    map.add_arc(cx0, cy0, cx1, cy1, 0, 360, color=col)
                elif ob[0] == 'rectangulo':
                    cx0 = float(ob[1])
                    cy0 = float(ob[2])
                    cx1 = float(ob[3])
                    cy1 = float(ob[4])
                    if len(ob) > 5:  col = ob[5]
                    else:  col = 'gray'
                    map.add_polyline(cx0, cy0, cx0, cy1, cx1, cy1, cx1, cy0, cx0, cy0, color=col)
                elif ob[0] == 'texto':
                    x, y = float(ob[1]), float(ob[2])
                    txt = ob[3]
                    if len(ob) > 4: col = ob[4]
                    else: col = 'gray'
                    map.add_text(ob[3], (x,y), color = col)
                elif ob[0] == 'draw_star' or ob[0] == 'draw_sid':
                    draw_SID_STAR(map, ob)
                elif ob[0] == 'polyline':
                    object = ob
                    color = object[1]
                    if object[1]=='':
                        color = 'gray'
                    coords = []
                    for p in object[2:]:
                        coords.append(self.fir.get_point_coordinates(p))
                    kw = {'color': color}
                    map.add_polyline(*coords, **kw)
            self.maps[map_name] = map
            if map_name not in self.local_maps_shown: map.hide()
        #_draw_deltas()
        self.c.lift('track')
         
    def redraw(self):
        """Delete and redraw all elements of the radar display"""
        self.redraw_maps()

        # Refresh tracks
        for a in self.tracks:
            a.redraw()

        self.update_lads()
        
    def reposition(self):
        self.stop_separating = True  # If the label separation code is running
                                     # we want to make sure that it will not try to
                                     # move the labels because results would be
                                     # incorrect
        for map_name,map in self.maps.items():
            map.reposition()
        for vt in self.tracks:
            (x,y)=self.do_scale((vt.wx,vt.wy))
            vt.coords(x,y,None)
        self.update_lads()
        self.c.lift('track')
        
    def do_scale(self,a):
        """Convert world coordinates into screen coordinates"""
        # return s((self.center_x,self.center_y),p(r((a[0],-a[1]),(self.x0,-self.y0)),self.scale))
        # Better to do the calculations inline to avoid the overhead of the function calling
        # on this very often called function
        try:
            return (self.center_x+(a[0]-self.x0)*self.scale,self.center_y+(-a[1]+self.y0)*self.scale)
        except:
            logging.error('do_scale: Unable to scale point %s'%a)
            raise
        
    def undo_scale(self,a):
        """Convert screen coodinates into world coordinates"""
        return s((self.x0,self.y0),p(r((a[0],-a[1]),(self.center_x,-self.center_y)),1/self.scale))
        
    def set_active_sectors(self, sector_list):
        # TODO this needs to deal with several possible sectors active at the same time
        if len(sector_list)<1: return
        self.sector = sector_list[0]
        self.redraw_maps()
    
    def toggle_routes(self):
        self.draw_routes = not self.draw_routes
        self.maps['airways'].toggle()
    
    def toggle_point_names(self):
        self.draw_point_names = not self.draw_point_names
        self.maps['point_names'].toggle()
        
    def toggle_point(self):
        self.draw_point = not self.draw_point
        self.maps['points'].toggle()

    def toggle_sector(self):
        self.draw_sector = not self.draw_sector
        self.maps['sector'].toggle()
        
    def toggle_lim_sector(self):
        self.draw_lim_sector = not self.draw_lim_sector
        self.maps['sector_limit'].toggle()

    def toggle_tmas(self):
        self.draw_tmas = not self.draw_tmas
        self.maps['tmas'].toggle()
        
    def toggle_deltas(self):
        self.draw_deltas = not self.draw_deltas
        # Special Use Areas
        self.maps['SUA'].toggle()
        
    def exit(self):
        
        # Save map options 
        self.conf.write_option("Maps","Point_names",self.draw_point_names)
        self.conf.write_option("Maps","Points",self.draw_point)
        self.conf.write_option("Maps","Routes",self.draw_routes)
        self.conf.write_option("Maps","Sector",self.draw_sector)
        self.conf.write_option("Maps","Lim_sector",self.draw_lim_sector)
        self.conf.write_option("Maps","TMAs",self.draw_tmas)
        self.conf.write_option("Maps","Deltas",self.draw_deltas)
        
        # Save brightness options
        ConfMgr.CrujiConfig().write_option("Brightness", "GLOBAL",self.intensity["GLOBAL"])
        ConfMgr.CrujiConfig().write_option("Brightness", "TRACKS",self.intensity["TRACKS"])
        ConfMgr.CrujiConfig().write_option("Brightness", "MAP",self.intensity["MAP"])
        ConfMgr.CrujiConfig().write_option("Brightness", "LADS",self.intensity["LADS"])
        
        
        
        
        # Drop bindings
        ra_clearbinds(self)
        # Delete map objects
        for map in self.maps.values():
            map.destroy()
        del self.maps
        # Delete tracks
        for t in self.tracks:
            t.destroy()
        try:
            self.tracks[0].reset_timer()
        except:
            logging.error("Error resetting timer")
        del self.tracks
        self.top_level.destroy()
        # Avoid memory leaks due to circular references preventing
        # the garbage collector from discarding this object
        try: self.sendMessage = None  # Clear the callback to the protocol
        except: pass
        
    def set_element_intensity(self, v):
        """Changes the brightness of radar elements"""        
        def set_LAD_intensity():
            LAD.lad_color.set_intensity(self.intensity["GLOBAL"]*self.intensity["LADS"])
            LAD.super_lad_color.set_intensity(self.intensity["GLOBAL"]*self.intensity["LADS"])
            self.update_lads()
        
        def set_MAP_intensity():
            for map in self.maps.values():
                map.intensity = self.intensity["GLOBAL"]*self.intensity["MAP"]
        
        def set_TRACKS_intensity():
            for tracks in self.tracks:
                tracks.intensity=self.intensity["GLOBAL"]*self.intensity["TRACKS"]
            
        # Copy the values from the given dictionary into the stored intensity
        previous = self.intensity.copy()
        self.intensity.update(v)

        if v.has_key("GLOBAL") and v["GLOBAL"]!=previous["GLOBAL"]:
            set_LAD_intensity()
            set_MAP_intensity()
            set_TRACKS_intensity()
        if v.has_key("MAP") and v["MAP"]!=previous["MAP"]:
            set_MAP_intensity()
        if v.has_key("TRACKS") and v["TRACKS"]!=previous["TRACKS"]:
            set_TRACKS_intensity()
        if v.has_key("LADS") and v["LADS"]!=previous["LADS"]:
            set_LAD_intensity()
        
    def __del__(self):
        logging.debug("RaDisplay.__del__")


# This is here just for debugging purposes
if __name__ == "__main__":
    import Pseudopilot
    root = Tk()
    canvas = Canvas(root,bg='black')
    def message_handler(*a):
        pass
    def do_scale(a): return a
    def undo_scale(a): return a
    vt = VisTrack(canvas,message_handler, do_scale, undo_scale)
    vt.x = 2
    label = vt.Label(vt)
    label.redraw()
    for i in label.items:
        print label[i].__dict__
    l = canvas.create_line(0,0,1,1)
    ra_tag_bind(canvas,l,"<2>",ra_tag_bind)
    ra_tag_unbind(canvas,l,"<2>")
    ra_cleartagbinds(l)
    
