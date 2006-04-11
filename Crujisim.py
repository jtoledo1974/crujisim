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

# Setup logging
import logging
def setup_logging():
    # Full logging goes to 'crujisim.log'
    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='crujisim.log',
                    filemode='w')
    l = logging.getLogger()
    # Important log messeges go to the console as well
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(levelname)-6s %(message)s'))
    l.addHandler(console)

if __name__=="__main__":
    setup_logging()

# Import system modules
import sys
sys.path.append("lib")
import random
import locale
import os
from stat import *

# Import libraries
try:
    from twisted.internet import gtk2reactor # for gtk-2.0
    gtk2reactor.install()
    from twisted.internet import reactor, tksupport
    # The label separation code is run within it's own thread
    from twisted.python import threadable
    threadable.init()
except:
    logging.exception("Unable to load Twisted library")
try: 
    import pygtk 
    pygtk.require("2.0") 
except:
    logging.exception("Unable to load pygtk")
try: 
    import gtk
    import gtk.glade
    import gobject
except:
    logging.exception("Unable to load gtk")
    sys.exit(1)
    
# Import program modules
try:
    import Tix
    import banner
    from Exercise import *
    from FIR import *
    import avion  # To load aircraft types
    import UI
    import ConfMgr  
    conf = ConfMgr.CrujiConfig()
    from GTA import GTA
    from RemoteClient import *
except:
    logging.exception("Error loading program modules")
    sys.exit(1)

# TODO this works as it is, but it's probably not the best way to do it.
if sys.platform == "win32": encoding = locale.getpreferredencoding()
else: encoding = "cp1252"
utf8conv = lambda x : unicode(x, encoding).encode('utf8')

# CONSTANTS
EX_DIR = "pasadas"
GLADE_FILE = "glade/crujisim.glade" 
JOKES = "jokes.txt"
AIRCRAFT_FILE = "Modelos_avo.txt"

class Crujisim:
    
    def __init__(self):
        
        root = Tix.Tk()
        root.withdraw()
        tksupport.install(root)
        self.tkroot = root

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
                
        splash.get_widget("progressbar").set_text("Obteniendo lista de ejercicios")
        self.load()
        self.check_backup()
                
    def load(self):
        splash, gui = self.splash, self.gui
        
        # Create the model for the exercise list (cols == columns)
        self.ex_ls_cols = {"file": 0,"fir":1,"sector":2,"comment":3,
                               "course":4,"phase":5,"day":6,"pass_no":7,
                               "shift":8,"PDP":9,"course_text":10,"n_flights":11,
                               "CPDP":12,"wind_text":13,"exercise_id":14,
                               "ejer":15}
        # els = exercise list store
        els = self.els = gtk.ListStore(str,str,str,str,
                                        int,int,int,int,
                                        str,str,str,int,
                                        str,str,str,
                                        int)
        # This is the mapping between actually displayed cols and the model cols
        self.ex_tv_cols = (("FIR","fir"),("Sector","sector"),
            ("Prom - Fase - Día - Pasada","CPDP"),
            ("Ejer.","ejer"),("Vuelos","n_flights"),
            ("Viento","wind_text"),("Comentario","comment"))
        
        # Process all exercise and fir files
        self.exercises = []
        self.firs = []

        # Find possible directories containing exercices
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
                els.append(self.get_tvrow_from_ex(e))
                self.exercises.append(e)
            self.firs += load_firs(dir)
              
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
        self.sb.push(0,utf8conv("Cargados "+str(self.n_ex)+" ejercicios"))
        self.set_filter()  # Load all combos with all options
        UI.set_active_text(self.fircombo, conf.fir_option)
        UI.set_active_text(self.sectorcombo,conf.sector_option)
        UI.set_active_text(self.coursecombo,conf.course_option)
        UI.set_active_text(self.phasecombo,conf.phase_option)
        
        # Load aircraft type information
        self.types = avion.load_types(AIRCRAFT_FILE)

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
            elif attr=="exercise_id":
                row.append(str(id(e)))
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

    def set_filter(self,combo=None):
        try:
            if self._updating_combos: return
        except: pass
        self.update_combo("fir",self.fircombo,("sector","course","phase"))
        self.update_combo("sector",self.sectorcombo,("course","phase"))
        self.update_combo("course",self.coursecombo,("phase",))
        self.update_combo("phase",self.phasecombo,("course",))
        ne = len(self.etf)
        self.sb.pop(0)
        self.sb.push(0,utf8conv("Mostrando "+str(ne)+" de "+str(self.n_ex)+" ejercicios"))

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

        old_value=UI.get_active_text(combo)
        UI.blank_combo(combo)
        combo.append_text("---")
        combo.set_active(0)
        i=1
        for value in values.keys():
            combo.append_text(utf8conv(str(value)))
            if str(value)==str(old_value):
                combo.set_active(i)
            i += 1
            
        self.filters=oldfilters.copy()
        self.filters[field]=UI.get_active_text(combo)
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

    def check_backup(self):
        """If there is a backup file from a previous session offer the user to continue editing it"""
        import cPickle
        import zlib
        try:
            f = open("backup.eje","rb")
            e = cPickle.loads(zlib.decompress(f.read()))
            f.close()
            r = UI.alert(utf8conv("""Crujisim se cerró sin haber guardado un ejercicio.
¿Desea editar la copia de seguridad?"""),
                     parent = self.MainWindow,
                     type = gtk.MESSAGE_QUESTION,
                     buttons = gtk.BUTTONS_YES_NO)
            if r==gtk.RESPONSE_YES:
                ee=ExEditor(e,parent=self.MainWindow, firs=self.firs, types=self.types)
                ee.run()
                ee.destroy()
            else:
                try: os.remove("backup.eje")
                except: logging.info("Unable to delete backup file")
            self.MainWindow.present()
        except: pass
        
    def gtk_main_quit(self,w=None,e=None):
        logging.info("Exiting...")
        conf.fir_option=UI.get_active_text(self.fircombo)
        conf.sector_option=UI.get_active_text(self.sectorcombo)
        conf.course_option=UI.get_active_text(self.coursecombo)
        conf.phase_option=UI.get_active_text(self.phasecombo)
        conf.save()

        # Calling gtk.main_quit() actually hanged here.
        # Just reactor.stop() seems to do the trick, though.
        reactor.stop()
        
    def list_clicked(self,widget=None,event=None):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
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
            exercise_id = model.get_value(iter,self.ex_ls_cols["exercise_id"])
        except:
            UI.alert("No hay ninguna pasada seleccionada",parent=self.MainWindow)
            return
        
        e = [e for e in self.exercises if str(id(e))==exercise_id][0]
        
        ee=ExEditor(e,parent=self.MainWindow, firs=self.firs, types=self.types)
        r = ee.run()
        if r == ee.SAVE:
            # Should update exercise information here
            self.els.clear()
            for e in self.exercises:
                self.els.append(self.get_tvrow_from_ex(e))
            self.etf.refilter()
            
        ee.destroy()
        self.MainWindow.present()

    def add(self,button=None,event=None):
        e = Exercise()
        e.fir = UI.get_active_text(self.fircombo)
        e.sector = UI.get_active_text(self.sectorcombo)
        ee = ExEditor(e, parent=self.MainWindow, firs=self.firs, types=self.types)
        r = ee.run()
        if r == ee.SAVE:
            self.exercises.append(e)    
            self.els.clear()
            for e in self.exercises:
                self.els.append(self.get_tvrow_from_ex(e))
            self.etf.refilter()
        ee.destroy()
        self.MainWindow.present()

    def connect(self,button=None,event=None):
        output = {"host": "", "type": ""}
        cd = ConnectDialog(e, parent=self.MainWindow, output=output)
        r = cd.run()
        cd.destroy()
        if r == cd.CANCEL: return
        try: s = output["host"].strip()
        except: s = ""
        try: (host, port) = s.split(":")
        except: host, port = s, 20123
        
        # Save MRU
        if s!="" and s not in conf.connect_mru:
            conf.connect_mru.append(s)
            conf.connect_mru = conf.connect_mru[-10:]  # Keep only the last 10
            conf.save()
            
        # Launch the client

        def exit(var=None):
            self.MainWindow.present()
        def failed(var=None):
            self.MainWindow.present()
            UI.alert(utf8conv("Imposible conectar con "+host+":"+str(port)),
                     parent=self.MainWindow,
                     type = gtk.MESSAGE_WARNING)
            
        self.MainWindow.hide()
        try:
            defer = RemoteClient().connect(host, int(port), output["type"])
        except:
            failed()
        defer.addCallback(exit).addErrback(failed)
    
    def begin_simulation(self,button=None):
        sel = self.etv.get_selection()
        (model, iter) = sel.get_selected()

        try:
            fir_name = model.get_value(iter,self.ex_ls_cols["fir"])
        except:
            UI.alert("No hay ninguna pasada seleccionada", parent=self.MainWindow)
            return
        for (fir,fir_file) in banner.get_fires():
            if fir_name==fir:
                fir_elegido=(fir, fir_file)
                break
        sector_name = model.get_value(iter,self.ex_ls_cols["sector"])
        for (sector, section) in banner.get_sectores(fir_name):
            if sector==sector_name:
                sector_elegido=(sector,section)
                break            
        ejercicio_elegido = model.get(iter,3,0)  # (comment, exercise_file)
        exc_file = model.get_value(iter, self.ex_ls_cols["file"])
        if "tpv" in sys.modules:
            sys.modules.pop('tpv')

        import tpv
        su = [fir_elegido , sector_elegido , ejercicio_elegido , 1]
        tpv.set_seleccion_usuario(su)

        #if "Simulador" in sys.modules:
        #    sys.modules.pop('Simulador')
        #import Simulador
        
        # TODO The following should be done using a deferred
        [punto,ejercicio,rutas,limites,deltas,tmas,local_maps,h_inicio,wind,aeropuertos,esperas_publicadas,rwys,procedimientos,proc_app,rwyInUse,auto_departures,min_sep] = tpv.tpv()
        fir = FIR(su[0][1])
        sector = su[1][0]

        def exit(var):
            self.MainWindow.present()
            pass
            
        gta = GTA(fir,sector,ejercicio,h_inicio, wind, exc_file)
        gta.start().addCallback(exit)
        
        self.MainWindow.hide()
        RemoteClient().connect("localhost",conf.server_port, PSEUDOPILOT)

class ExEditor:
    # Response constants
    CANCEL = gtk.RESPONSE_CANCEL
    SAVE = 2
    def __init__(self,exercise = None, parent=None, firs=None, types=None):
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

        self.ExEditor.connect("response", self.on_exeditor_response)
                
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

        # Populate FIR and Sector dropdowns
        # self.firs is a list of firs
        # self.fir is the combobox showing fir options
        self.firs = firs  # Save firs list
        UI.blank_combo(self.fircombo)
        for fir in [fir.name for fir in self.firs]:
            self.fircombo.append_text(utf8conv(str(fir)))
        UI.set_active_text(self.fircombo,[fir.name for fir in self.firs][0])
        
        # Store types list
        self.types = types
        
        self.ex = exercise
        if not hasattr(self.ex,"flights"):
            self.ex.reload_flights()
        self.ex_copy = self.ex.copy()  # To be used to check for modifications
        self.populate(exercise)

        if parent: self.ExEditor.set_transient_for(parent)
        self.ExEditor.set_position(gtk.WIN_POS_CENTER)
        self.ExEditor.present()

    def run(self): return self.ExEditor.run()

    def destroy(self): self.ExEditor.destroy()

    def update_sectors(self,combo=None):

        sel_fir = UI.get_active_text(self.fircombo)
        for (fir, firname) in [(fir, fir.name) for fir in self.firs]:
            if firname == sel_fir:
                self.fir = fir
                break;
            
        UI.blank_combo(self.sectorcombo)
        first = True
        for sector in self.fir.sectors:
            self.sectorcombo.append_text(utf8conv(str(sector)))
            if first:
                self.sectorcombo.set_active(0)
                first = False
        
        try:
            UI.set_active_text(self.sectorcombo,self.ex.sector)
        except:
            pass
            
    def populate(self, ex):

        ex_file = ex.file
        
        self.ExEditor.set_title("Editor: "+utf8conv(ex_file))
        UI.set_active_text(self.fircombo,ex.fir)  # Also sets the sector automatically
        for attrib in ("da","usu","ejer","course","phase","day","pass_no","shift","comment",
                       "wind_azimuth","wind_knots","start_time"):
            try:
                if type(getattr(ex,attrib)) is str:
                    getattr(self,attrib).props.text=utf8conv(getattr(ex,attrib))
                else:
                    getattr(self,attrib).props.text=getattr(ex,attrib)
            except:
                logging.debug("Unable to populate field "+attrib+". Using blank")
                getattr(self,attrib).props.text=""
        self.flights = ex.flights
        
        self.populate_flights()

    def populate_flights(self):
        self.fls.clear() 
        for i,f in self.ex.flights.items():
            # Column 0 of the model is the key in the flights dictionary
            self.fls.append((i,f.callsign,f.orig,f.dest,f.route.replace(","," ")))

    def list_clicked(self,w=None,event=None):
        if event.type == gtk.gdk._2BUTTON_PRESS:
            self.edit()
    
    def edit(self,w=None):
        sel = self.ftv.get_selection()
        (model, iter) = sel.get_selected()        
        try:
            index = model.get_value(iter,0)
        except:
            UI.alert(utf8conv("No hay ningún vuelo seleccionado"), parent=self.ExEditor)
            return
        firname = UI.get_active_text(self.fircombo)
        fir = [fir for fir in self.firs if fir.name == firname][0]
        sectorname = UI.get_active_text(self.sectorcombo)
        fe=FlightEditor(action="edit",flight=self.flights[index], flights=self.flights.values(),
                     parent=self.ExEditor, types=self.types,
                     fir=fir, sector=sectorname)
        r = fe.run()
        if r == fe.SAVE:
            self.populate_flights()  # Make sure the list is updated
            self.save_backup()
        fe.destroy()
        self.ExEditor.present()
        
    def add(self,w=None):
        firname = UI.get_active_text(self.fircombo)
        fir = [fir for fir in self.firs if fir.name == firname][0]
        sectorname = UI.get_active_text(self.sectorcombo)
        while True:
            f = Flight()
            fe=FlightEditor(action="add", flight=f, flights=self.flights.values(),
                            parent=self.ExEditor, types=self.types, fir=fir,
                            sector=sectorname)
            r=fe.run()
            fe.destroy()
            if r==FlightEditor.ADD or r==FlightEditor.SAVE:
                self.ex.add_flight(f)
                self.save_backup()
                self.populate_flights()  # Make sure the list is updated
            if r!=FlightEditor.ADD:
                break
        self.ExEditor.present()
        self.populate_flights()  # Make sure the list is updated
                
    def delete(self,w=None):
        sel = self.ftv.get_selection()
        (model, iter) = sel.get_selected()        
        try:
            index = model.get_value(iter,0)
        except:
            UI.alert(utf8conv("No hay ningún vuelo seleccionado"), parent=self.ExEditor)
            return
        del self.ex.flights[index]
        self.fls.remove(iter)
        
    def save_backup(self):
        import cPickle
        import zlib
        cache = open("backup.eje",'wb')
        cache.write(zlib.compress(cPickle.dumps(self.ex)))
        cache.close
        
    def check_numeric(self,w):
        text=w.props.text
        if text.isdigit() or text=="":
            w.previous_value = text
            self.sb.pop(0)
            return
        try: w.props.text=w.previous_value
        except: w.props.text=""
        gtk.gdk.beep()
        self.sb.push(0,utf8conv("Introduzca únicamente caracteres numéricos"))
        
    def on_shift_changed(self,w):
        text=w.props.text=w.props.text.upper()
        if text not in ("T","M",""):
            gtk.gdk.beep()
            self.sb.push(0,utf8conv("Introduzca T o M"))
            try: w.props.text=w.previous_value
            except: w.props.text=""
            return
        self.sb.pop(0)
        w.previous_value = text
            
    def on_start_time_changed(self,w):
        text=w.props.text
        import time
        t = text.replace(":","")
        try:
            if time.strftime("%H%M",time.strptime(t.ljust(4,"0"),"%H%M")) == t.ljust(4,"0"):
                w.previous_value = text
                self.sb.pop(0)
        except:
            try: w.props.text=w.previous_value
            except: w.props.text=""
            gtk.gdk.beep()                
            self.sb.push(0,utf8conv("Introduzca una hora en formato hhmm o hh:mm"))        

    def fill_ex(self, e):
        """Copies data from the dialog into the given exercise object"""
        # File is more delicate and we don't edit it here

        # Change the start time to the proper format
        st = self.start_time.props.text.strip()
        if len(st)==4: st=st[:2]+":"+st[2:]
        self.start_time.props.text = st

        for field, combo in [("fir", self.fircombo), ("sector", self.sectorcombo)]:
            setattr(e,field, UI.get_active_text(combo))
        for field in ("start_time", "shift", "comment"):
            value = getattr(self,field).props.text
            setattr(e,field,value)
        for field in ("da","usu","ejer","course", "phase", "day", "pass_no"):
            value = getattr(self,field).props.text
            try:
                setattr(e,field,int(value))
            except:
                setattr(e,field,None)
        for field in ("wind_azimuth","wind_knots"):
            value = getattr(self,field).props.text
            try:
                setattr(e,field,int(value))
            except:
                setattr(e,field,0)
        return e

    def on_exeditor_delete_event(self, w, e):
        # Since we are dealing with the delete event from the response handler
        # don't do anything here, and do not propagate
        return True
    
    def on_exeditor_response(self, dialog, response, **args):
        if response==gtk.RESPONSE_DELETE_EVENT:
            dialog.emit_stop_by_name("response")
            dialog.response(gtk.RESPONSE_CANCEL)
            return
        elif response!=gtk.RESPONSE_CANCEL and not self.validate():
            dialog.emit_stop_by_name("response")
            return
        elif response==gtk.RESPONSE_CANCEL:
            if self.fill_ex(self.ex.copy()) != self.ex_copy:
                r = UI.alert(utf8conv("Se ha modificado el ejercicio. ¿Desea abandonar los cambios?"),
                             type = gtk.MESSAGE_WARNING,
                             buttons = gtk.BUTTONS_OK_CANCEL)
                if r!=gtk.RESPONSE_OK:
                    dialog.emit_stop_by_name("response")
                    return
        else:
            # Save the exercise
            if self.fill_ex(self.ex.copy()) != self.ex_copy :
                ex = self.ex
                self.fill_ex(ex)
                if ex.file=="":
                    name = str(ex.course)+"-Fase-"+str(ex.phase)+"-Dia-"+"%02d"%ex.day+"-Pasada-"+str(ex.pass_no)+"-"+ex.shift+"-"+ex.sector+".eje"
                    ex.file=os.path.join(os.path.dirname(self.fir.file),name)
                ex.oldcomment = os.path.basename(ex.file)+" ("+str(len(ex.flights.keys()))+")"
                ex.n_flights = len(ex.flights.keys())
                try:
                    ex.save(ex.file)
                except:
                    logging.exception("Unable to save exercise"+ex.file)
                    UI.alert("Imposible guardar ejercicio en archivo "+ex.file)
                    return
            else:
                logging.debug("User clicked save but exercise was not modified")
            # Upload exercise file
            r = UI.alert(utf8conv("""¿Desea subir el archivo a la Tortuga?"""),
                     parent = self.ExEditor,
                     type = gtk.MESSAGE_QUESTION,
                     buttons = gtk.BUTTONS_YES_NO)
            if r==gtk.RESPONSE_YES:
                tsvn_add_commit(ex.file)
            self.ExEditor.present()

        
        # Remove backup file
        try: os.remove("backup.eje")
        except: pass

    def validate(self):
        import re
        valid = True
        self.sb.pop(0)
        checklist = [
            #("da","^\d{1,3}$"),("usu","^\d{1,3}$"),("ejer","^\d{1,3}$"),
            ("course","^\d{2}$"),("phase","^\d{1}$"),("day","^\d{1,2}$"),
            ("pass_no","^\d{1,2}$"),("shift","^[MT]$"),
            ("wind_azimuth","^\d{1,3}$"),("wind_knots","^\d{1,3}$"),
            ("start_time","^\d{2}:{0,1}\d{2}$")]

        for (field, pattern) in checklist:
            widget = getattr(self,field)
            value = widget.props.text
            if not re.match(pattern,value):
                culprit = widget
                valid = False
                break
        if not valid:            
            gtk.gdk.beep()
            UI.flash_red(culprit)
            culprit.grab_focus()
        return valid

    def __del__(self):
        logging.debug("ExEditor.__del__")

class FlightEditor:
    
    # Response constants
    CANCEL = gtk.RESPONSE_CANCEL
    SAVE = 2
    ADD = 3
    
    def __init__(self,action="add",flight=None, flights=None,
                 parent=None, types=None, fir=None, sector=""):
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
                        
        self.stripcontainer.set_focus_chain((self.callsign,self.type,self.wtc,self.tas,
                                             self.orig, self.eobt,
                                             self.dest, self.rfl,self.route,self.fix,self.eto,
                                             self.firstlevel,self.cfl, self.addbutton,
                                             self.savebutton))        
        self.FlightEditor.connect("response", self.on_flighteditor_response)

        self.types = types
        self.fir = fir
        self.sector = sector
        self.flights = flights

        if action=="edit":
            self.addbutton.hide()
            self.FlightEditor.set_default_response(self.SAVE)
        self.flight = flight
        
        # Create completion widget
        self.completion = completion = gtk.EntryCompletion()
        completion.set_match_func(lambda c,k,i: True)
        completion.hid = completion.connect("match-selected",
                            lambda c,m,i: UI.focus_next(self.route))
        completion.set_model(gtk.ListStore(str))
        completion.set_text_column(0)
        self.route.set_completion(completion)

        # Populate the dialog
        self.route.props.text = flight.route.replace(","," ")
        for attr in ["callsign","orig","dest","fix","firstlevel","rfl","cfl","wtc","tas","type"]:
            getattr(self,attr).props.text = getattr(flight,attr)
        try: self.eto.props.text = hhmmss_to_hhmm(flight.eto)
        except: self.eto.props.text = flight.eto
        self.firstfix.props.label=self.flight.route.split(",")[0]
        
        self.set_departure(False)  # By default maintain the old format so that we can edit old flights
        self.callsign.grab_focus()
        
        # Saves a copy of the flight to check for modifications later
        self.flightcopy = self.flight.copy()  

    def run(self): return self.FlightEditor.run()

    def destroy(self): self.FlightEditor.destroy()
    
    def on_callsign_changed(self,w):
        w.props.text=w.props.text.upper()
    
    def on_callsign_focusout(self,w,e=None):
        import re
        text = w.props.text
        if not re.match("^$|(\*){0,2}[a-zA-Z0-9]{3,8}",text):
            gtk.gdk.beep()
            w.grab_focus()
            self.sb.push(0,"Formato incorrecto del indicativo")
            return
        try:
            if text in [f.callsign for f in self.flights] and text!=self.flight.callsign:
                gtk.gdk.beep()
                w.grab_focus()
                self.sb.push(0,"Vuelo ya introducido")
                return
        except:
            logging.debug("Unable to check for repeated callsign")
            pass
                
        w.props.text = text.upper()
        self.sb.pop(0)

    def on_type_changed(self,w):
        type = self.type.props.text = self.type.props.text.upper()
        if type not in self.types.keys():
            self.wtc.props.sensitive = self.wtc.props.editable = True
        else:
            (wtc,tas) = self.types[type].wtc,self.types[type].cruise_tas
            self.wtc.props.text = wtc
            self.wtc.props.sensitive = self.wtc.props.editable = False
            #self.tas.props.text = tas
        if len(self.type.props.text)>=4: UI.focus_next(w)
            
    def on_wtc_changed(self,w):
        wtc=self.wtc.props.text
        self.wtc.props.text=wtc.upper()
        if wtc.upper() not in ("H","M","L",""):
            self.wtc.props.text=""
            gtk.gdk.beep()
            self.sb.push(0,utf8conv("Categoría de estela turbulenta debe ser H, M o L"))
            return
        self.sb.pop(0)
        if len(wtc)==1: UI.focus_next(w)
        
    def on_tas_changed(self,w):
        tas=self.tas.props.text
        if not tas.isdigit() and not tas=="":
            try: w.props.text=w.previous_value
            except: w.props.text=""
            gtk.gdk.beep()
            self.sb.push(0,"Introduzca TAS en nudos")
            return
        self.sb.pop(0)
        w.previous_value = tas
        # Find whether the input tas is reasonably close to the standard
        try:
            type_tas = self.types[self.type.props.text].cruise_tas
            if not type_tas<int(tas)*1.5 or not type_tas>int(tas)/1.5: return
            else:
                UI.focus_next(w)
                return
        except: pass
        # If we don't have any info on the standard tas, focus next after four digits
        if len(tas)==w.props.max_length: UI.focus_next(w)
        
    def on_orig_changed(self,w):
        orig = text = w.props.text
        w.props.text = text.upper()
        if not text.isalpha() and text!="":
            try: w.props.text=w.previous_value
            except: w.props.text=""
            gtk.gdk.beep()
            self.sb.push(0,utf8conv("Formato incorrecto de aeródromo de origen"))
            return
        w.previous_value = text
        self.sb.pop(0)
        if orig.upper() in self.fir.local_ads[self.sector]:
            self.set_departure(True)
        else:
            self.set_departure(False)
        if w.props.max_length==len(text):
            UI.focus_next(w)
            self.fill_completion()
        
    def set_departure(self,dep):
        eobt, eobt_separator = self.eobt.props, self.eobt_separator.props
        arrow, fix, eto = self.arrow.props, self.fix.props, self.eto.props
        firstlevel, firstfix = self.firstlevel.props, self.firstfix.props
        fl_label, fl_separator = self.fl_label.props, self.fl_separator.props
        if dep:
            eobt.sensitive = eobt.visible = eobt_separator.visible = arrow.visible = True
            fix.sensitive = fix.visible = eto.sensitive = eto.visible = False
            firstlevel.sensitive = firstlevel.visible = firstfix.visible = False
            fl_label.visible = fl_separator.visible = False
            self.departure = True
        else:
            eobt.sensitive = eobt.visible = eobt_separator.visible = arrow.visible = False
            fix.sensitive = fix.visible = eto.sensitive = eto.visible = True
            firstlevel.sensitive = firstlevel.visible = firstfix.visible = True
            fl_label.visible = fl_separator.visible = True
            self.departure = False

    def on_route_changed(self,w):
        text=w.props.text
        text=text.replace(','," ").upper()       
        valid = True
        for c in text:
            if c.isalnum() or c=="_" or c==" " or c==",": continue
            valid = False
            err = "Caracter no válido en la ruta"
            break
        if self.orig.props.text==text.split(" ")[0] and text!="" and self.orig.props.text!="":
            valid = False
            err = "El aeropuerto de origen no puede formar parte de la ruta. Use el VOR (p. ej: LEMD -> BRA)"
        if not valid:
            try: w.props.text=w.previous_value
            except: w.props.text=""
            self.sb.push(0,utf8conv(err))
            gtk.gdk.beep()
            w.grab_focus()
            return        
        self.sb.pop(0)
        w.props.text = text
        w.previous_value = text
        l = len(text.split(" ")[-1])  # Refill matches after we have finished writing a fix
        if l in (2,3,5):  # eg, GE PDT DOBAN
            self.fill_completion()
        self.firstfix.props.label=text.split(" ")[0]
        if self.fix.props.text not in text.split(" ") and text!="":
            self.eto.props.text = self.fix.props.text = ""
            # If we grabbed the focus here selecting a match on the completion
            # list wouldn't automatically focus cycle to the next item
            #w.grab_focus()
            
        
    def fill_completion(self):
        # Fill up the completion list
        self.completion.get_model().clear()
        fix_list = [f for f in self.route.props.text.split(" ") if f!=""]
        if fix_list == []: fix_list = [""]
        for r in self.fir.routedb.matching_routes(fix_list,self.orig.props.text,self.dest.props.text):
            self.completion.get_model().append([r.replace(","," ")])
        
    def on_fix_changed(self,w, event=None):
        text =  w.props.text = w.props.text.upper()
        valid = False
        for f in self.route.props.text.split(" "):
            if f==text:
                w.previous_value = text
                self.sb.pop(0)
                UI.focus_next(w)
                return
            if f.startswith(text):
                valid = True
                break
        if not valid and text!="":
            try: w.props.text=w.previous_value
            except: w.props.text=""
            gtk.gdk.beep()
            self.sb.push(0,utf8conv("El fijo debe pertenecer a la ruta"))
            return
        w.previous_value = text
        self.sb.pop(0)

    def check_numeric(self,w):
        text=w.props.text
        if text.isdigit() or text=="":
            w.previous_value = text
            if w.props.max_length==len(text): UI.focus_next(w)
            self.sb.pop(0)
            return
        try: w.props.text=w.previous_value
        except: w.props.text=""
        gtk.gdk.beep()
        self.sb.push(0,utf8conv("Introduzca únicamente caracteres numéricos"))
        
    def check_alpha(self,w):
        text=w.props.text
        valid = True
        for c in text:
            if c.isalpha() or c=="_": continue
            valid = False
            break
        if not valid:
            try: w.props.text=w.previous_value
            except: w.props.text=""
            gtk.gdk.beep()
            return
        w.props.text = text.upper()
        w.previous_value = text
        if w.props.max_length==len(text):
            UI.focus_next(w)
            self.fill_completion()    
    
    def check_time(self,w):
        import time
        t = w.props.text
        try:
            if time.strftime("%H%M",time.strptime(t.ljust(4,"0"),"%H%M")) == t.ljust(4,"0"):
                w.previous_value = t
                self.sb.pop(0)
                if len(t)==4: UI.focus_next(w)
        except:
            try: w.props.text=w.previous_value
            except: w.props.text=""
            gtk.gdk.beep()                
            self.sb.push(0,utf8conv("Introduzca una hora en formato hhmm"))

    def fill_flight(self, f):
        """Copies data from the dialog into the given flight object"""
        f.route = self.route.props.text.strip().replace(" ",",")
        for attr in ["callsign","orig","dest","rfl","cfl","wtc","tas","type"]:
            setattr(f, attr, getattr(self,attr).props.text)
        if self.departure:
            eto, fix = self.eobt.props.text, f.route.split(",")[0]
            try:
                firstlevel = "%03d"%self.fir.ad_elevations[f.orig]
            except:
                firstlevel = "000"
        else:
            eto, firstlevel, fix = self.eto.props.text, self.firstlevel.props.text, self.fix.props.text
        f.eto , f.firstlevel, f.fix = eto, firstlevel, fix
        return f

    def on_flighteditor_delete_event(self, w, e):
        # Since we are dealing with the delete event from the response handler
        # don't do anything here, and do not propagate
        return True
    
    def on_flighteditor_response(self, dialog, response, **args):
        if response==gtk.RESPONSE_DELETE_EVENT:
            dialog.emit_stop_by_name("response")
            dialog.response(gtk.RESPONSE_CANCEL)
            return
        elif response!=gtk.RESPONSE_CANCEL and not self.validate():
            dialog.emit_stop_by_name("response")
            return
        elif response==gtk.RESPONSE_CANCEL:
            if self.flight != self.fill_flight(self.flight.copy()):
                r = UI.alert(utf8conv("Se ha modificado el vuelo. ¿Desea abandonar los cambios?"),
                             type = gtk.MESSAGE_WARNING,
                             buttons = gtk.BUTTONS_OK_CANCEL)
                if r!=gtk.RESPONSE_OK:
                    dialog.emit_stop_by_name("response")
                    return
        else:
            f = self.flight
            self.fill_flight(f)  # Copy the validated form data into the given flight
            self.fir.routedb.append(f.route,f.orig,f.dest)

        self.completion.disconnect(self.completion.hid)

    def validate(self):
        import re
        valid = True
        self.sb.pop(0)
        checklist = [("callsign","^(\*){0,2}[a-zA-Z0-9]{3,8}$"),
            ("type","^[A-Z0-9-]{2,4}$"),("wtc","^[HML]$"),("tas","^\d{2,4}$"),
            ("orig","^[A-Z]{4}$"),("dest","^[A-Z]{4}$"),
            ("route","^([A-Z0-9_]{2,6} {0,1})+$"),
            ("rfl","^\d{2,3}$"),("cfl","^\d{2,3}$")]
        if self.departure:
            checklist += [("eobt","^\d{4}$")]
        else:
            checklist += [("fix","^[A-Z0-9_]{2,6}$"),("eto","^\d{4}$"),
                ("firstlevel","^\d{2,3}$")]
            fix = self.fix.props.text
            route = self.route.props.text
            if fix not in route.split(" "):
                culprit = self.fix
                valid = False                
                self.sb.push(0,utf8conv("El fijo debe pertenecer a la ruta"))
        for (field, pattern) in checklist:
            widget = getattr(self,field)
            value = widget.props.text
            if not re.match(pattern,value):
                culprit = widget
                valid = False
                break
        if not valid:            
            gtk.gdk.beep()
            UI.flash_red(culprit)
            culprit.grab_focus()
        return valid

    def __del__(self):
        logging.debug("FlightEditor.__del__")

def tsvn_add_commit(file):
    found = False
    for f in ("c:\\Program Files\\TortoiseSVN\\bin\\TortoiseProc.exe",
              "c:\\Archivos de Programa\\TortoiseSVN\\bin\\TortoiseProc.exe"):
        if os.path.exists(f):
            tsvn = '"'+f.replace("\\\\","\\")+'"'
            found = True
            break
    if not found: return
    fileop = "/path:"+'"'+file+'"'
    addcommand = tsvn+" /command:add "+fileop+" /notempfile /closeonend:1"
    commitcommand = tsvn+" /command:commit "+fileop+" /notempfile /closeonend"
    try:
        name = os.path.basename(file)+".svn-base"
        svncopy = os.path.join(os.path.dirname(file),".svn","text-base",name)
        if not os.path.exists(svncopy):
            os.system('"'+addcommand+'"')
        os.system('"'+commitcommand+'"')
    except:
        pass

class ConnectDialog:
    CANCEL = gtk.RESPONSE_CANCEL

    def __init__(self,exercise = None, parent=None, output={}):
        gui = self.gui = gtk.glade.XML(GLADE_FILE, "ConnectDialog") 
        gui.signal_autoconnect(self)
        
        # Automatically make every widget in the window an attribute of this class
        for w in gui.get_widget_prefix(''):
            name = w.get_name()
            # make sure we don't clobber existing attributes
            try: assert not hasattr(self, name)
            except: logging.error("Failed with attr "+name)
            setattr(self, name, w)

        self.ConnectDialog.connect("response", self.on_connectdialog_response)
        if parent: self.ConnectDialog.set_transient_for(parent)
        #self.ConnectDialog.set_position(gtk.WIN_POS_CENTER)
        #self.ConnectDialog.present()
        
        self.output = output
        # Fill combobox.
        UI.blank_combo(self.hostcombo)
        for l in conf.connect_mru:
            if l.strip() == "": continue
            self.hostcombo.append_text(l)
            
        
    def run(self): return self.ConnectDialog.run()
    def destroy(self): self.ConnectDialog.destroy()

    def on_connectdialog_delete_event(self, w, e):
        # Since we are dealing with the delete event from the response handler
        # don't do anything here, and do not propagate
        return True
    
    def on_connectdialog_response(self, dialog, response, **args):
        if response==gtk.RESPONSE_DELETE_EVENT:
            dialog.emit_stop_by_name("response")
            dialog.response(gtk.RESPONSE_CANCEL)
            return
        elif response==gtk.RESPONSE_CANCEL:
            return
        else:
            h=self.hostcombo.child.get_text()
            if h.strip()=="":
                dialog.emit_stop_by_name("response")
            self.output["host"]=h
            if self.radiobutATC.get_active(): type = ATC
            else: type = PSEUDOPILOT
            self.output["type"]=type
            
if __name__=="__main__":
    logging.info("Arrancando crujisim")
    try:
        Crujisim()
        reactor.run()
    except:
        logging.exception("An error occurred")
