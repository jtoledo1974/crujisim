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

from twisted.internet import gtk2reactor # for gtk-2.0
gtk2reactor.install()
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
from twisted.internet import reactor

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
        reactor.GtkMainWindow = self.MainWindow  # This is a very dirty trick

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
        
        # Create the model for the exercise list (cols == columns)
        self.ex_ls_cols = {"file": 0,"fir":1,"sector":2,"comment":3,
                               "course":4,"phase":5,"day":6,"pass_no":7,
                               "shift":8,"PDP":9,"course_text":10,"n_flights":11,
                               "CPDP":12,"wind_text":13}
        # els = exercise list store
        els = self.els = gtk.ListStore(str,str,str,str,
                                        int,int,int,int,
                                        str,str,str,int,
                                        str,str)
        # This is the mapping between actually displayed cols and the model cols
        self.ex_tv_cols = (("FIR","fir"),("Sector","sector"),
            ("Prom - Fase - Día - Pasada","CPDP"),("Vuelos","n_flights"),
            ("Viento","wind_text"),("Comentario","comment"))
        
        # Process all exercise files
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
            self.all_ex=[]
            for e in load_exercises(dir):
                els.append(self.get_tvrow_from_ex(e))
                self.all_ex.append(e)
              
        self.etf = etf = els.filter_new()  # Exercise TreeFilter
        self.filters = {"fir":"---","sector":"---","course":"---","phase":"---"}
        etf.set_visible_func(self.ex_is_visible)
        etv = self.etv  # Exercise Tree View
        etv.set_model(gtk.TreeModelSort(etf))
        etv.get_selection().set_mode(gtk.SELECTION_SINGLE)
        renderer = gtk.CellRendererText()
        for i, name in [(self.ex_ls_cols[ls_col],name) for (name,ls_col) in self.ex_tv_cols]:
            column = gtk.TreeViewColumn(utf8conv(name), renderer, text=i) 
            column.set_clickable(True) 
            column.set_sort_column_id(i) 
            column.set_resizable(True) 
            etv.append_column(column)
        renderer.props.ypad=0
        
        self.n_ex = len(els)
        self.statusbar.push(0,utf8conv("Cargados "+str(self.n_ex)+" ejercicios"))
        self.set_filter()  # Load all combos with all options
        self.set_active_text(self.fircombo, conf.fir_option)
        self.set_active_text(self.sectorcombo,conf.sector_option)
        self.set_active_text(self.coursecombo,conf.course_option)
        self.set_active_text(self.phasecombo,conf.phase_option)

        # Everything's ready. Hide Splash, present Main Window
        splash.get_widget("Splash").destroy()
        self.MainWindow.present()
    
    def get_tvrow_from_ex(self,e):
        """Return a row of attributes suitable to create a row in the
        exercise list store from an Exercise object"""
        els = self.els
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
        ia = [(index,attr) for attr,index in self.ex_ls_cols.items()]
        ia.sort()
        for index,attr in ia:
            if attr=="file":
                row.append(e.file)
            elif type(getattr(e,attr)) is str:
                row.append(utf8conv(getattr(e,attr)))
            elif type(getattr(e,attr)) is int:
                row.append(getattr(e,attr))
            elif type(getattr(e,attr)) is NoneType:
                ct = els.get_column_type(index)
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
        
        return row

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

    def set_filter(self,combo=None):
        try:
            if self._updating_combos: return
        except: pass
        self.update_combo("fir",self.fircombo,("sector","course","phase"))
        self.update_combo("sector",self.sectorcombo,("course","phase"))
        self.update_combo("course",self.coursecombo,("phase",))
        self.update_combo("phase",self.phasecombo,("course",))
        ne = len(self.etf)
        self.statusbar.pop(0)
        self.statusbar.push(0,utf8conv("Mostrando "+str(ne)+" de "+str(self.n_ex)+" ejercicios"))

    def update_combo(self,field,combo,childfields):
        self._updating_combos = True
        
        tempfilter={}
        for f in childfields:
            tempfilter[f]="---"
        
        # Find unique values 
        values = {}
        oldfilters = self.filters.copy()
        self.filters.update(tempfilter)
        self.filters[field]="---"
        self.etf.refilter()
        for row in self.etf:
            values[row[self.ex_ls_cols[field]]]=0

        old_value=self.get_active_text(combo)
        self.blank_combo(combo)
        combo.append_text("---")
        combo.set_active(0)
        i=1
        for value in values.keys():
            combo.append_text(utf8conv(str(value)))
            if str(value)==str(old_value):
                combo.set_active(i)
            i += 1
            
        self.filters=oldfilters.copy()
        self.filters[field]=self.get_active_text(combo)
        self.etf.refilter()
        self._updating_combos = False        
            
    def ex_is_visible(self,model,iter,user_data=None):
        for field in self.filters.keys():
            if str(model.get_value(iter,self.ex_ls_cols[field]))== self.filters[field] or \
                self.filters[field] == "---":
                pass
            else:
                return False
        return True
        
    def gtk_main_quit(self,w=None,e=None):
        conf.fir_option=self.get_active_text(self.fircombo)
        conf.sector_option=self.get_active_text(self.sectorcombo)
        conf.course_option=self.get_active_text(self.coursecombo)
        conf.phase_option=self.get_active_text(self.phasecombo)
        conf.save()
        gtk.main_quit()
        # Force exit or the reactor may become hanged
        # due to the loading and unloading of tksupport
        # (a bug entry has been raised against twisted)
        sys.exit()
        
    def list_clicked(self,widget=None,event=None):
        if event.type == gtk.gdk._2BUTTON_PRESS and event.button==1:
            #print str(widget.get_path_at_pos(event.x,event.y))
            #print str((event.x,event.y))
            self.begin_simulation()
        elif event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            tv = self.etv
            pthinfo = tv.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                tv.grab_focus()
                tv.set_cursor( path, col, 0)
                self.MainPopup.popup( None, None, None, event.button, time)

    def edit(self,button=None,event=None):
        sel = self.etv.get_selection()
        (model, iter) = sel.get_selected()
        
        try:
            ex_file = model.get_value(iter,self.ex_ls_cols["file"])
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
        
        ExEditor(ex_file,parent=self.MainWindow)

    def begin_simulation(self,button=None):
        sel = self.etv.get_selection()
        (model, iter) = sel.get_selected()

        try:
            fir_name = model.get_value(iter,self.ex_ls_cols["fir"])
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
        sector_name = model.get_value(iter,self.ex_ls_cols["sector"])
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

        if "Simulador" in sys.modules:
            sys.modules.pop('Simulador')
        import Simulador

class ExEditor:
    def __init__(self,ex_file=None,parent=None):
        gui = self.gui = gtk.glade.XML(GLADE_FILE, "ExEditor") 
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
        
        if ex_file: self.populate(ex_file)

        if parent: self.ExEditor.set_transient_for(parent)
        self.ExEditor.set_position(gtk.WIN_POS_CENTER)
        self.ExEditor.present()
    
    def populate(self, ex_file):
        try:
            ex=Exercise(ex_file)
        except:
            dlg=gtk.MessageDialog(parent=self.ExEditor,
                                  flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                                  type=gtk.MESSAGE_INFO,
                                  buttons=gtk.BUTTONS_CLOSE,
                                  message_format="Imposible abrir archivo:\n"+utf8conv(ex_file))
            dlg.set_position(gtk.WIN_POS_CENTER)
            dlg.connect('response',lambda dlg, r: dlg.destroy())
            dlg.run()
            self.ExEditor.destroy()
            return
        
        self.ExEditor.set_title("Editor: "+utf8conv(ex_file))
        self.fir.child.props.text=ex.fir
        self.sector.child.props.text=ex.sector
        for attrib in ("da","usu","ejer","course","phase","day","pass_no","shift","comment",
                       "wind_azimuth","wind_knots","start_time"):
            if type(getattr(ex,attrib)) is str:
                getattr(self,attrib).props.text=utf8conv(getattr(ex,attrib))
            else:
                getattr(self,attrib).props.text=getattr(ex,attrib)
        self.flights = ex.flights
        
        for i,f in ex.flights.items():
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
            dlg=gtk.MessageDialog(parent=self.ExEditor,
                                  flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                                  type=gtk.MESSAGE_INFO,
                                  buttons=gtk.BUTTONS_CLOSE,
                                  message_format=utf8conv("No hay ningún vuelo seleccionado"))
            dlg.set_position(gtk.WIN_POS_CENTER)
            dlg.connect('response',lambda dlg, r: dlg.destroy())
            dlg.run()
            return
        
        FlightEditor(self.flights[index],parent=self.ExEditor)
                
    def close(self,w=None,e=None):
        self.ExEditor.destroy()
        
    def __del__(self):
        logging.debug("ExEditor.__del__")
        
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

    def __del__(self):
        logging.debug("FlightEditor.__del__")

Crujisim()
reactor.run()