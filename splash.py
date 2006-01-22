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

import sys
sys.path.append("lib")
import logging
import random
import locale
import os
from stat import *

try: 
    import pygtk 
    pygtk.require("2.0") 
except:
    logging.error("Unable to load pygtk")
try: 
    import gtk
    import gtk.glade
    import gobject
except:
    logging.error("unable to load gtk")
    sys.exit(1)
from banner import *
from Exercise import *
import ConfMgr
conf = ConfMgr.CrujiConfig()

encoding = locale.getpreferredencoding()
utf8conv = lambda x : unicode(x, encoding).encode('utf8')

# CONSTANTS
EX_DIR = "pasadas"
GLADE_FILE = "glade/crujisim.glade" 
JOKES = "jokes.txt"

# Define which logging level messages will be output
logging.getLogger('').setLevel(logging.DEBUG)

class Crujisim:
    
    def __init__(self): 
        gladefile = GLADE_FILE 
        self.windowname = "splash" 

        splash = self.splash = gtk.glade.XML(gladefile, "Splash") 
        splash.signal_autoconnect(self)

        gui = self.gui = gtk.glade.XML(gladefile, "MainWindow") 
        gui.signal_autoconnect(self)

        # Automatically make every widget in the window an attribute of this class
        for w in gui.get_widget_prefix(''):
            name = w.get_name()
            # make sure we don't clobber existing attributes
            try:
                assert not hasattr(self, name)
            except:
                logging.error("Failed with attr "+name)
            setattr(self, name, w)

        popup = self.popup = gtk.glade.XML(gladefile, "MainPopup") 
        popup.signal_autoconnect(self)
        self.MainPopup = popup.get_widget('MainPopup')

        # Place the joke
        lines = open(JOKES, 'rt').readlines()
        try:
            j = random.choice(lines)
        except:
            j = ''
        joke = ""
        for l in j.split("|"): joke += l+"\n"
        joke = joke[:-1]
        splash.get_widget('jokelabel').set_text(utf8conv(joke))
        splash_window = splash.get_widget("Splash")
        splash_window.set_position(gtk.WIN_POS_CENTER)
        splash_window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
                
        #splash.get_widget('Splash').idle_add(self.load)
        splash.get_widget("progressbar").set_text("Obteniendo lista de ejercicios")
        gobject.idle_add(self.load)        
                
    def load(self):
        splash, gui = self.splash, self.gui
        
        # Create the model for the excercise list (cols == columns)
        self.exc_ls_cols = {"file": 0,"fir":1,"sector":2,"comment":3,
                               "course":4,"phase":5,"day":6,"pass_no":7,
                               "shift":8,"PDP":9,"course_text":10,"n_flights":11,
                               "CPDP":12,"wind_text":13}
        exc_list = self.exc_list = gtk.ListStore(str,str,str,str,
                                                 int,int,int,int,
                                                 str,str,str,int,
                                                 str,str)
        # This is the mapping between actually displayed cols and the model cols
        self.exc_tv_cols = (("FIR","fir"),("Sector","sector"),
            ("Prom - Fase - Día - Pasada","CPDP"),("Vuelos","n_flights"),
            ("Viento","wind_text"),("Comentario","comment"))
        
        # Process all excercise files
        pb = splash.get_widget("progressbar")
        pb.set_text('Cargando ejercicios')
        dirs = [dir for dir in os.listdir(EX_DIR) if dir[-4:]!=".svn"
                and S_ISDIR(os.stat(os.path.join(EX_DIR,dir))[ST_MODE])]
        n_dirs = len(dirs)
        i=0.
        for dir in dirs:  # File includes the path, filename doesn't
            pb.set_text(dir)
            i += 1./n_dirs
            dir = os.path.join(EX_DIR,dir)
            pb.set_fraction(i)
            while gtk.events_pending():
                gtk.main_iteration()
            for e in load_exercises(dir):
                # Add columns to the exercise list suitable for display
                if (e.wind_azimuth,e.wind_knots)!=(0,0):
                    e.wind_text="%03dº%02dkt"%(e.wind_azimuth,e.wind_knots)
                else: e.wind_text=""
                try: e.PDP="Fase %d - Día %02d - Pasada %d"%(e.phase,e.day,e.pass_no)
                except: e.PDP=""
                try: e.course_text="Prom. %02d"%(e.course)
                except: e.course_text=""
                if e.PDP=="" or e.course_text=="":
                    e.CPDP=""
                    # We need to be able to show the user something
                    # so that he can reconstruct the missing data
                    e.comment=e.oldcomment
                else:
                    e.CPDP=e.course_text+" - "+e.PDP

                row=[]
                ia = [(index,attr) for attr,index in self.exc_ls_cols.items()]
                ia.sort()
                for index,attr in ia:
                    if attr=="file":
                        row.append(e.file)
                    elif type(getattr(e,attr)) is str:
                        row.append(utf8conv(getattr(e,attr)))
                    elif type(getattr(e,attr)) is int:
                        row.append(getattr(e,attr))
                    elif type(getattr(e,attr)) is NoneType:
                        ct = exc_list.get_column_type(index)
                        # I don't really know how to map GTypes to python types,
                        # so rather than doing "if ct is int", I have to
                        # do this ugly hack
                        if str(ct).find("gint")>0:
                            row.append(0)
                        elif str(ct).find("gchar")>0:
                            row.append("")
                        else:
                            logging.error("Unknown type in liststore column")
                    else:
                        row.append(None)
                exc_list.append(row)
              
        self.exc_filter = exc_filter = exc_list.filter_new()
        self.filters = {"fir":"---","sector":"---","course":"---"}
        exc_filter.set_visible_func(self.exc_is_visible)
        exc_view = self.exc_view
        exc_view.set_model(gtk.TreeModelSort(exc_filter))
        exc_view.get_selection().set_mode(gtk.SELECTION_SINGLE)
        renderer = gtk.CellRendererText()
        for i, name in [(self.exc_ls_cols[ls_col],name) for (name,ls_col) in self.exc_tv_cols]:
            column = gtk.TreeViewColumn(utf8conv(name), renderer, text=i) 
            column.set_clickable(True) 
            column.set_sort_column_id(i) 
            column.set_resizable(True) 
            exc_view.append_column(column)
        renderer.props.ypad=0
        
        # Fill up the FIRs combo with the unique FIRs available
        firs = {}
        for fir in [row[1] for row in self.exc_list]:
            firs[fir]=0
        fircombo=self.fircombo
        for f in firs.keys():
            fircombo.append_text(f)
        self.filters = {"fir":conf.fir_option,"sector":conf.sector_option}        
        self.set_active_text(fircombo, conf.fir_option)
        self.set_active_text(self.sectorcombo,conf.sector_option)

        # Everything's ready. Hide Splash, present Main Window
        self.n_exc = len(exc_list)
        self.statusbar.push(0,utf8conv("Cargados "+str(self.n_exc)+" ejercicios"))
        splash.get_widget("Splash").destroy()
        self.MainWindow.present()
    

    def get_active_text(self,combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            return None
        return model[active][0]
    
    def set_active_text(self, combobox, text):
        model = combobox.get_model()
        for row, i in zip(model, range(len(model))):
            if row[0] == text:
                combobox.set_active(i)
                break
    
    def blank_combo(self,combo):
        while len(combo.get_model())>0:
            combo.remove_text(0)

    def update_combos(self):
        self._updating_combos = True
        
        # Find unique FIRs, Sectors and promociones
        
        sectors = {}
        oldfilter = self.filters["sector"]
        self.filters["sector"]="---"
        self.exc_filter.refilter()
        for row in self.exc_filter:
            sectors[row[2]]=0
        gui = self.gui

        def update_combo(combo,values):
            old_value=self.get_active_text(combo)
            self.blank_combo(combo)
            combo.append_text("---")
            combo.set_active(0)
            i=1
            for value in values:
                combo.append_text(value)
                if value==old_value:
                    combo.set_active(i)
                i += 1
            
        update_combo(self.sectorcombo,sectors.keys())
        self.filters["fir"]=self.get_active_text(self.fircombo)
        self.filters["sector"]=self.get_active_text(self.sectorcombo)
        self.exc_filter.refilter()
        self._updating_combos = False

    def set_filter(self,combo=None):
        try:
            if self._updating_combos: return
        except: pass
        self.filters["fir"]=self.get_active_text(self.fircombo)
        #self.filters["sector"]=self.get_active_text(self.sectorcombo)
        #self.exc_filter.refilter()
        self.update_combo("sector",self.sectorcombo)

    def update_combo(self,field,combo):
        self._updating_combos = True
        
        # Find unique values 
        values = {}
        oldfilter = self.filters[field]
        self.filters[field]="---"
        self.exc_filter.refilter()
        for row in self.exc_filter:
            values[row[self.exc_ls_cols[field]]]=0

        old_value=self.get_active_text(combo)
        self.blank_combo(combo)
        combo.append_text("---")
        combo.set_active(0)
        i=1
        for value in values.keys():
            combo.append_text(utf8conv(str(value)))
            if value==old_value:
                combo.set_active(i)
            i += 1
            
        self.filters[field]=self.get_active_text(combo)
        self.exc_filter.refilter()
        self._updating_combos = False

        
    def set_fir(self,combo):
        try:
            if self._updating_combos: return
        except: pass
        gui=self.gui
        self.filters["fir"]=self.get_active_text(self.fircombo)
        self.filters["sector"]="---"
        self.exc_filter.refilter()
        self.update_combos()
        
            
    def exc_is_visible(self,model,iter,user_data=None):
        f = self.filters
        if (model.get_value(iter,1) == f["fir"] or f["fir"]=="---") \
          and (model.get_value(iter,2) == f["sector"] or f["sector"]=="---"):
            return True
        else:
            return False
        
    def gtk_main_quit(self,w=None,e=None):
        gui = self.gui
        conf.fir_option=self.get_active_text(self.fircombo)
        conf.sector_option=self.get_active_text(self.sectorcombo)
        conf.save()
        gtk.main_quit()
        
    def list_clicked(self,widget=None,event=None):
        if event.type == gtk.gdk._2BUTTON_PRESS and event.button==1:
            #print str(widget.get_path_at_pos(event.x,event.y))
            #print str((event.x,event.y))
            self.begin_simulation()
        elif event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            tv = self.exc_view
            pthinfo = tv.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                tv.grab_focus()
                tv.set_cursor( path, col, 0)
                self.MainPopup.popup( None, None, None, event.button, time)

    def edit(self,button=None,event=None):
        sel = self.exc_view.get_selection()
        (model, iter) = sel.get_selected()
        
        try:
            exc_file = model.get_value(iter,0)
        except:
            dlg=gtk.MessageDialog(parent=self.MainWindow,
                                  flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                                  type=gtk.MESSAGE_INFO,
                                  buttons=gtk.BUTTONS_CLOSE,
                                  message_format="No hay ninguna pasada seleccionada")
            dlg.set_position(gtk.WIN_POS_CENTER)
            dlg.connect('response',lambda dlg, r: dlg.destroy())
            dlg.run()
            return
        
        ExcEditor(exc_file,parent=self.MainWindow)

    def begin_simulation(self,button=None):
        sel = self.exc_view.get_selection()
        (model, iter) = sel.get_selected()
        
        try:
            fir_name = model.get_value(iter,1)
        except:
            dlg=gtk.MessageDialog(parent=self.MainWindow,
                                  flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                                  type=gtk.MESSAGE_INFO,
                                  buttons=gtk.BUTTONS_CLOSE,
                                  message_format="No hay ninguna pasada seleccionada")
            dlg.set_position(gtk.WIN_POS_CENTER)
            dlg.connect('response',lambda dlg, r: dlg.destroy())
            dlg.run()
            return
        for (fir,fir_file) in get_fires():
            if fir_name==fir:
                fir_elegido=(fir, fir_file)
                break
        sector_name = model.get_value(iter,2)
        for (sector, section) in get_sectores(fir_name):
            if sector==sector_name:
                sector_elegido=(sector,section)
                break            
        ejercicio_elegido = model.get(iter,3,0)
        if "tpv" in sys.modules:
            sys.modules.pop('tpv')
        
        import tpv
        print "importing tpv"
        #import tpv
        tpv.set_seleccion_usuario([fir_elegido , sector_elegido , ejercicio_elegido , 1])

        self.MainWindow.hide()
        while gtk.events_pending():
            gtk.main_iteration()
        if "Simulador" in sys.modules:
            sys.modules.pop('Simulador')
        import Simulador
        self.MainWindow.present()

class ExcEditor:
    def __init__(self,exc_file=None,parent=None):
        gui = self.gui = gtk.glade.XML(GLADE_FILE, "ExcEditor") 
        gui.signal_autoconnect(self)
        
        # Automatically make every widget in the window an attribute of this class
        for w in gui.get_widget_prefix(''):
            name = w.get_name()
            # make sure we don't clobber existing attributes
            try:
                assert not hasattr(self, name)
            except:
                logging.error("Failed with attr "+name)
            setattr(self, name, w)
            
        # Create the flights treeview
        fls = self.fls = gtk.ListStore(int,str,str,str,str)  # Flights list store
              
        self.ftv.set_model(fls)
        renderer = gtk.CellRendererText()
        # Column 0 of the model is the key in the flights dictionary
        for i,name in zip(range(1,5),('Callsign','Orig','Dest','Route')):
            column = gtk.TreeViewColumn(name, renderer, text=i) 
            column.set_clickable(True) 
            column.set_sort_column_id(i) 
            column.set_resizable(True) 
            self.ftv.append_column(column)
        renderer.props.ypad=0
        
        if exc_file: self.populate(exc_file)

        if parent: self.ExcEditor.set_transient_for(parent)
        self.ExcEditor.set_position(gtk.WIN_POS_CENTER)
        self.ExcEditor.present()
    
    def populate(self, exc_file):
        try:
            exc=Exercise(exc_file)
        except:
            dlg=gtk.MessageDialog(parent=self.ExcEditor,
                                  flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                                  type=gtk.MESSAGE_INFO,
                                  buttons=gtk.BUTTONS_CLOSE,
                                  message_format="Imposible abrir archivo:\n"+utf8conv(exc_file))
            dlg.set_position(gtk.WIN_POS_CENTER)
            dlg.connect('response',lambda dlg, r: dlg.destroy())
            dlg.run()
            self.ExcEditor.destroy()
            return
        
        self.ExcEditor.set_title("Editor: "+utf8conv(exc_file))
        self.fir.child.props.text=exc.fir
        self.sector.child.props.text=exc.sector
        for attrib in ("da","usu","ejer","course","phase","day","pass_no","shift","comment",
                       "wind_azimuth","wind_knots","start_time"):
            if type(getattr(exc,attrib)) is str:
                getattr(self,attrib).props.text=utf8conv(getattr(exc,attrib))
            else:
                getattr(self,attrib).props.text=getattr(exc,attrib)
        self.flights = exc.flights
        
        for i,f in exc.flights.items():
            # Column 0 of the model is the key in the flights dictionary
            self.fls.append((i,f.callsign,f.orig,f.dest,f.route))

    def list_clicked(self,w=None,event=None):
        if event.type == gtk.gdk._2BUTTON_PRESS:
            self.edit()
        pass
    
    def edit(self,w=None):
        sel = self.ftv.get_selection()
        (model, iter) = sel.get_selected()
        
        try:
            index = model.get_value(iter,0)
        except:
            dlg=gtk.MessageDialog(parent=self.ExcEditor,
                                  flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                                  type=gtk.MESSAGE_INFO,
                                  buttons=gtk.BUTTONS_CLOSE,
                                  message_format=utf8conv("No hay ningún vuelo seleccionado"))
            dlg.set_position(gtk.WIN_POS_CENTER)
            dlg.connect('response',lambda dlg, r: dlg.destroy())
            dlg.run()
            return
        
        FlightEditor(self.flights[index],parent=self.ExcEditor)
                
    def close(self,w=None,e=None):
        self.ExcEditor.destroy()
        
class FlightEditor:
    def __init__(self,flight=None,parent=None):
        gui = self.gui = gtk.glade.XML(GLADE_FILE, "FlightEditor") 
        gui.signal_autoconnect(self)
        
        # Automatically make every widget in the window an attribute of this class
        for w in gui.get_widget_prefix(''):
            name = w.get_name()
            # make sure we don't clobber existing attributes
            try:
                assert not hasattr(self, name)
            except:
                logging.error("Failed with attr "+name)
            setattr(self, name, w)

        if parent: self.FlightEditor.set_transient_for(parent)
        self.FlightEditor.set_position(gtk.WIN_POS_CENTER)
        self.FlightEditor.present()
                        
        self.stripcontainer.set_focus_chain((self.callsign,self.type,self.orig, self.eobt,
                                             self.dest,self.rfl,self.route,self.fix,self.eto,
                                             self.firstlevel,self.cfl))        

        # Populate the dialog
        if not flight: flight=Flight()

        # I use the __dict_[attr] is another way to reference an some objects attr
        # object.__dict__["callsign"] == object.callsign
        for attr in ["callsign","orig","dest","fix","firstlevel","rfl","cfl","wtc","tas","type"]:
            getattr(self,attr).props.text = getattr(flight,attr)
        self.route.child.props.text = flight.route.replace(","," ")
        self.eto.props.text = hhmmss_to_hhmm(flight.eto)
        self.set_firstfix(flight.route)
    
    def set_firstfix(self,route):
        self.firstfix.props.label=route.split(",")[0]

    def close(self,w=None,e=None):
        self.FlightEditor.destroy()
        logging.debug("In FlightEditor.close")

Crujisim()
gtk.main()