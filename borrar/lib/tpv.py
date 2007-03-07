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
# Functionality here is now implemented in GTA.py, Aircraft.py and TLPV.py
# and this file is left here only for reference for tidbits of functionality
# not yet ported to the new architecture (namely, flight strips)
#
#############################


# Module imports
import warnings
warnings.filterwarnings('ignore','.*',DeprecationWarning)
from StripSeries import StripSeries, FlightData
from ConfigParser import *
from Aircraft import *
from FIR import FIR
import BADA
import glob
from Tix import *
import Image
import ImageTk
import PngImagePlugin
import sys
import logging

# Constants
IMGDIR='./img/'
CRUJISIMICO=IMGDIR+'crujisim.ico'

def set_seleccion_usuario(seleccion_usuario):
    global g_seleccion_usuario
    g_seleccion_usuario = seleccion_usuario
    
def calc_eto(d):
    # Cálculo del tiempo entre fijos
    estimadas=[0.0]
    last_point=False
    t=0.
    n_puntos=len(d.route)
    inc_t=15./60./60.
    while not last_point:
        t=t+inc_t
        d.next(t)
        if len(d.route)<n_puntos:
            estimadas.append(t)
            n_puntos=len(d.route)
        if not d.to_do == 'fpr':
            estimadas.append(t)
            last_point = True
    return estimadas
    
def tpv():
    global h_inicio,fir_elegido,sector_elegido,ejercico_elegido, g_seleccion_usuario,rwyInUse
    
    h_inicio=0.
    imprimir_fichas=False
    #Elección del fir,sector y ejercicio
    [fir_elegido,sector_elegido,ejercicio_elegido,imprimir_fichas] = g_seleccion_usuario
    logging.debug('Total escogido: '+str(fir_elegido)+" "+str(sector_elegido)+" "+
                  str(ejercicio_elegido))

    ejercicio = []
    incidencias = []
    fir = FIR(fir_elegido[1])
    punto = fir.points
    rutas = fir.routes
    limites = fir.boundaries[sector_elegido[0]]
    tmas = fir.tmas
    deltas = fir.deltas
    aeropuertos = fir.aerodromes
    esperas_publicadas = fir.holds
    rwys = fir.rwys
    rwyInUse = fir.rwyInUse
    procedimientos = fir.procedimientos
    proc_app = fir.proc_app
    auto_departures = fir.auto_departures[sector_elegido[0]]
    min_sep = fir.min_sep[sector_elegido[0]]
    local_maps = fir.local_maps
        
    ask_tag = False
    for airp in rwys.keys():
        if len(rwys[airp].split(','))>1:
            ask_tag = True
            break
    if ask_tag:
        rwy_chg = Tk()
        txt_titulo = Label (rwy_chg, text = 'ESPECIFIQUE PISTA(S) EN USO')
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
        but_acept = Button(rwy_chg,text='Aceptar')
        but_acept.grid(column=0,row=line,columnspan=2)
        def close_rwy_chg(e=None,window=rwy_chg):
            global rwyInUse
            com_airp.pop(0)
            for [airp,num] in com_airp:
                print 'Pista en uso de ',airp,' es ahora: ',num.cget('value'),'. Cambiando los procedimientos'
                rwyInUse[airp] = num.cget('value')
                window.destroy()
                window.quit()
        but_acept['command']= close_rwy_chg
        window_width = rwy_chg.winfo_reqwidth()
        window_height = rwy_chg.winfo_reqheight()
        screen_width = rwy_chg.winfo_screenwidth()
        screen_height = rwy_chg.winfo_screenheight()
        px = (screen_width - window_width) / 2
        py = (screen_height - window_height) / 2
        rwy_chg.wm_geometry("+%d+%d" % (px,py))
        rwy_chg.mainloop()

    # Lectura del fichero de performances
    config=ConfigParser()
    config.readfp(open(fir_elegido[1]))
    
    config.readfp(open('Modelos_avo.txt','r'))
    
    # Ahora se crean los planes de vuelo del ejercicio
    logging.debug('Leyendo archivo '+ejercicio_elegido[1])
    config.readfp(open(ejercicio_elegido[1],'r'))
    hora = config.get('datos','hora_inicio')
    if hora=='':
        # incidencias.append('No hay hora de inicio en ejercicio')
        logging.critical('No hay hora de inicio')
        return    
    h_inicio = float(hora[0:2])*60.*60.+ float(hora[3:5])*60.
    try:
        [rumbo,intensidad] = config.get('datos','viento').split(',')
        intensidad,rumbo = float (intensidad),(float(rumbo)+180.0)%360.0
        wind = [intensidad,rumbo] #[intensidad * sin(rumbo), -intensidad * cos (rumbo)]
    except:
        wind = [0.0 , 0.0]
    # Inicialización de variables en avión.py
    set_global_vars(punto, wind, aeropuertos, esperas_publicadas,rwys,rwyInUse,procedimientos,proc_app,min_sep)
    
    aviones = config.items('vuelos')
    for (nombre,resto) in aviones:
        logging.debug('Leyendo avión '+nombre.upper()+'...')
        auxi=False
        lista=resto.split(',')
        d=Airplane()
        d.set_callsign(nombre.upper())
        d.set_kind(lista[0])
        try:
            d.perf = BADA.Performance(lista[0], "bada.txt")
        except: 
            logging.warning("No BADA info for "+nombre.upper()+" ("+lista[0]+")")
        d.set_wake(lista[1])
        d.set_origin(lista[2])
        d.set_destination(lista[3])
        d.set_rfl(float(lista[4]))
        
        cfl = float(lista[5])
        d.set_cfl(float(lista[4]))
        d.ecl=d.cfl
        ruta=[]
        for p in lista[6:]:
            if len(p)==15:
                alt=float(p[8:11])
                d.set_alt(alt)
                spd=float(p[12:15])
                d.set_filed_tas(spd)
                ias=spd/(1.+0.002*d.rfl)
                d.set_std_spd()
                fijo=fijo_ant
                hora=float(p[1:3])+float(p[3:5])/60.+float(p[5:7])/60/60
                d.set_initial_t(0.)  #
            elif len(p)>10 and p[0]=='H':
                # incidencias.append(d.get_callsign()+': Grupo HhhmmssFfffVvvv no está comleto')
                logging.warning('Grupo HhhmmssFfffVvvv no está completo')
                auxi=True
                return
            else:
                punto_esta=False
                for q in punto:
                    if p==q[0]:
                        ruta.append([q[1],q[0],'00:00'])
                        fijo_ant=q[0]
                        punto_esta=True
                if not punto_esta:
                    # incidencias.append(d.get_callsign()+': Punto ' + p + ' no encontrado')
                    logging.warning('Punto '+p+' no encontrado')
                    auxi=False
            if auxi:
                logging.debug('ok')
                # Ahora incluimos las performances del avión
        if d.get_wake() == 'H':
            d.turn = 2.4 * 60. * 60.
        elif d.get_wake() == 'L':
            d.turn = 3.75 * 60. * 60.
        else:
            d.turn = 3.0 * 60. * 60.
        kind_aux =d.get_kind()
        while kind_aux[0].isdigit():
            kind_aux = kind_aux[1:]
        if config.has_option('performances',kind_aux):
            aux=config.get('performances',kind_aux).split(',')
            d.fl_max = float(aux[1])
            d.rate_climb_max = float(aux[2])/100.*60.
            d.rate_climb_std = float(aux[3])/100.*60.
            d.rate_desc_max = float(aux[4])/100.*60.
            d.rate_desc_std = float(aux[5])/100.*60.
            d.spd_std = float(aux[6])
            d.spd_max = float(aux[7])
            d.spd_tma = float(aux[8])
            d.spd_app = float(aux[9])
        else:
            #incidencias.append(d.get_callsign()+': No tengo parámetros del modelo ' + d.get_kind() + '. Usando datos estándar')
            logging.warning('No tengo parámetros del modelo '+d.get_kind()+'. Usando datos estándar')
            if config.has_option('performances','estandar'+d.estela.upper()):
                aux=config.get('performances','estandar'+d.estela.upper()).split(',')
                d.fl_max = float(aux[1])
                d.rate_climb_max = float(aux[2])/100.*60.
                d.rate_climb_std = float(aux[3])/100.*60.
                d.rate_desc_max = float(aux[4])/100.*60.
                d.rate_desc_std = float(aux[5])/100.*60.
                d.spd_std = float(aux[6])
                d.spd_max = float(aux[7])
                d.spd_tma = float(aux[8])
                d.spd_app = float(aux[9])
        # Load the aircraft requirements
        if config.has_section('req') and config.has_option('req',nombre):
            req=config.get('req',nombre)
            req_time_str=req[:4]
            req=req[5:]
            if (req[0]=='"' and req[-1]=='"') or (req[0]=="'" and req[-1]=="'"):
                req=req[1:-1]
                # TODO this should be done in a helper function
            req_time=float(req_time_str[0:2])+float(req_time_str[2:4])/60.
            d.reports.append({'time':req_time,'text':'Request: '+req})
            
            # Cálculo de la estimada al primer punto
        d.route = ruta
        pos=ruta[0][0]
        logging.debug('Antes del recálculo '+fijo+' '+str(hora)+' '+str(ruta))
        d.set_position(pos)
        route=[]
        for a in ruta:
            route.append(a)
        route.pop(0)
        d.set_route(route)
        d.set_initial_heading()
        estimadas = calc_eto(d)
        logging.debug('Estimadas en primera vuelta '+str(estimadas))
        # Cálculo de la estimada ajustada
        for i in range(len(ruta)):
            if ruta[i][1]==fijo:
                desfase=hora-estimadas[i]
                break
        aux=[]
        for i in range(len(ruta)):
            eto=desfase+estimadas[i]
            h=int(eto)
            m=int((eto*60.+0.5)-h*60.)
            aux.append([ruta[i][0],ruta[i][1],'%02d:%02d'%(h,m),eto])
        aux.pop(0)
        d.set_route(aux)
        d.set_alt(alt)
        d.set_cfl(cfl)
        d.spd = 0.0
        d.set_std_spd()
        d.set_initial_t(desfase)
        d.set_position(pos)
        d.set_initial_heading()
        # Recálculo para el caso de que al aplicar las SIDs o STARs cambien los puntos de la ruta
        # Mantendremos la eto sobre el primer punto de la ruta
        fijo = ruta [0][1]
        hora = d.t
        d.set_initial_t(0.0)
        d.route = ruta
        d.set_se_pinta(False)   # Some previous function has incorrectly set this to True
                                # We need it to be false so that SID and STARs are
                                # added correctly
        complete_flight_plan(d)
        ruta = d.route
        logging.debug('Después del recálculo '+str(fijo)+' '+str(hora)+' '+str(ruta))
        pos=ruta[0][0]
        d.set_position(pos)
        route=[]
        for a in ruta:
            route.append(a)
        # I'm not sure why by default we want to eliminate the first element of the route,
        # but certainly we do not want to be doing that with our departures
        if d.get_origin in fir.release_required_ads[sector_elegido[0]]:
            logging.debug("local dep, not popping route point")
        else:
            route.pop(0)
        d.set_route(route)
        d.set_initial_heading()
        estimadas = calc_eto(d)
        logging.debug('Estimadas en segunda vuelta: '+str(estimadas))
        # Cálculo de la estimada ajustada
        for i in range(len(ruta)):
            if ruta[i][1]==fijo:
                desfase=hora-estimadas[i]
                break
        aux=[]
        for i in range(len(ruta)):
            eto=desfase+estimadas[i]
            h=int(eto)
            m=int((eto*60.+0.5)-h*60.)
            aux.append([ruta[i][0],ruta[i][1],'%02d:%02d'%(h,m),eto])
        aux.pop(0)
        d.set_route(aux)
        d.set_alt(alt)
        d.set_cfl(cfl)
        d.spd = 0.0
        d.set_std_spd()
        d.set_initial_t(desfase)
        d.set_position(pos)
        d.set_initial_heading()
        
        hist=[]
        d.set_campo_eco(d.route[-1][1][0:3])
        for dest in aeropuertos:
            if d.destino==dest:
                d.set_campo_eco(dest[2:4])
        d.set_app_fix()
        ejercicio.append(d)
        logging.debug('ok')
        
    # Set the EOBT, calculate the sector entry time and sort aircraft by
    # their flight strip printing time
    orden=[]
    for s in range(len(ejercicio)):
        a=ejercicio[s]
        # Set EOBT
        if a.get_origin() in fir.local_ads[sector_elegido[0]]:
            # As of revision 326 there is no place where to store the EOBT of a departing flight,
            # so the ETO of the first route point is taken
            a.set_eobt(a.route[0][3])
        # Calculate sector entry time
        for i in range(len(a.route)):
            if a.get_sector_entry_fix()==None and \
              a.route[i][1] in fir.boundaries[sector_elegido[0]]: 
            #  a.route[i][1] in firdef.get(sector_elegido[1],'limites').split(','):
                a.set_sector_entry_fix(a.route[i][1])
                a.set_sector_entry_time(a.route[i][3])  # The ETO over the point
            elif a.get_sector_entry_fix()==None and \
              a.route[i][1] in fijos_impresion_secundarios:
                a.set_sector_entry_fix(a.route[i][1])
                a.set_sector_entry_time(a.route[i][3])  # The ETO over the point
        if a.get_sector_entry_time()==None:
            a.set_sector_entry_fix(a.route[0][1])
            a.set_sector_entry_time(a.route[0][3])  # If all else fails, use the first ETO
            # Set the flight strip printing time
        if a.get_eobt()<>None:
            a.t_impresion=a.get_eobt()-10./60.  # 10min before EOBT
        else:
            a.t_impresion=a.get_sector_entry_time()-10./60.  # 10min before sector entry time
        orden.append((a.t_impresion,s))
        logging.debug (a.name+"\tSector entry:\t"+a.get_sector_entry_fix())
    orden.sort()
    
    
    # Manejo de la impresión de fichas
    #if imprimir_fichas==1:     
    if True:
        parseraux=ConfigParser()
        parseraux.readfp(open(ejercicio_elegido[1],'r'))
        if parseraux.has_option('datos','comentario'):
            name = parseraux.get('datos','comentario')
        else:
            name = ejercicio_elegido[1]
            
        ss = StripSeries(exercise_name = name, output_file="fichas.pdf")
        ss2 = StripSeries(exercise_name = name, output_file="minifichas.pdf")
        for (aux,s) in orden:
            a = ejercicio[s]
            # Nombre contiene el indicativo OACI para sacar el callsign
            nombre = ''
            for i in range(len(a.name)):
                if nombre == '' or a.name[i].isalpha() or a.name[i]=="*":
                    #remove * from the callsign
                    if a.name[i]<>"*": nombre=nombre+a.name[i].upper()
                else:
                    break
            if config.has_option('indicativos_de_compania',nombre):
                callsign = config.get('indicativos_de_compania',nombre)
            else:
                callsign = ''
            a.radio_callsign=callsign
            logging.debug (a.name+'\t'+nombre+'\t'+callsign)
            ruta=''
            for f in a.route:
                if f[1][0]!='_':
                    ruta=ruta+' '+f[1]
                    
            # Flight Strip creation
            
            # First we determine whether this flight will pass any of the
            # primary flight strip printing points. If it doesn't, then
            # it will use the secondary flight strip printing points instead
            current_printing_fixes = fir.fijos_impresion_secundarios[sector_elegido[0]]
            at_least_one_strip_printed = False
            for i in range(len(a.route)):
                for fix in fir.fijos_impresion[sector_elegido[0]]:
                    if a.route[i][1]==fix:
                        current_printing_fixes = fir.fijos_impresion[sector_elegido[0]]
                        
            # Print a coord flight strip if it's a departure from an AD we have to release
            if a.get_origin() in fir.local_ads[sector_elegido[0]]:
                fd=FlightData()
                fd.callsign=a.name
                fd.exercice_name=name
                fd.ciacallsign=callsign
                fd.model=a.tipo
                fd.wake=a.estela
                fd.speed=a.filed_tas
                fd.responder="C"
                fd.origin=a.origen
                fd.destination=a.destino
                fd.fl=str(int(a.rfl))
                fd.cssr="----"
                fd.route=ruta
                fd.rules=""
                t=a.t_impresion
                fd.print_time='%02d%02d'%(int(t),int((t*60.+0.5)-int(t)*60.))
                t=a.get_eobt()
                try:
                    fd.eobt='%02d%02d'%(int(t),int((t*60.+0.5)-int(t)*60.))
                except:
                    logging.warning('Cannot obtain EOBT for flight %s', a.name)
                    fd.eobt='????'
                fd.fs_type="coord"
                ss.draw_flight_data(fd)
                
            # Print a flight strip for every route point which is any of the
            # current_printing_fixes
                
            if a.get_origin() in fir.release_required_ads[sector_elegido[0]]:
                prev=a.get_origin()
                t=a.get_eobt()
                try:
                    prev_t='%02d%02d'%(int(t),int((t*60.+0.5)-int(t)*60.))
                except:
                    logging.warning('Cannot get EOBT for flight %s', a.name)
                    prev_t=''
            else:
                prev=prev_t=''
            for i in range(len(a.route)):
                if prev=='' and a.route[i][1] in fir.fijos_impresion_secundarios[sector_elegido[0]]:
                    prev=a.route[i][1]
                    prev_t=a.route[i][2][0:2]+a.route[i][2][3:5]
                elif prev=='':
                    prev='ENTRAD'
                    prev_t=''
                if a.route[i][1] in current_printing_fixes:
                  # Main flight strip fix 
                    fijo=a.route[i][1]
                    fijo_t=a.route[i][2][0:2]+a.route[i][2][3:5]
                    # Calculate next flight strip fix
                    #if i==len(a.route)-1 and firdef.has_option(sector_elegido[1],'local_ads') and \
                    #  a.get_destination() in firdef.get(sector_elegido[1],'local_ads').split(','):
                    if i==len(a.route)-1 and a.get_destination() in fir.local_ads[sector_elegido[0]]:
                        next=a.get_destination()
                        next_t=''
                    elif i==len(a.route)-1:
                        next='SALIDA'
                        next_t=''
                    else:
                        next=a.route[i+1][1]
                        next_t=a.route[i+1][2][0:2]+a.route[i+1][2][3:5]
                        
                    fd=FlightData()
                    fd.callsign=a.name
                    fd.exercice_name=name
                    fd.ciacallsign=callsign
                    fd.prev_fix=prev
                    fd.fix=fijo
                    fd.next_fix=next
                    fd.prev_fix_est=prev_t
                    fd.fix_est=fijo_t
                    fd.next_fix_est=next_t
                    fd.model=a.tipo
                    fd.wake=a.estela
                    fd.speed=a.filed_tas
                    fd.responder="C"
                    fd.origin=a.origen
                    fd.destination=a.destino
                    fd.fl=str(int(a.rfl))
                    fd.cfl=str(int(a.cfl))
                    fd.cssr="----"
                    fd.route=ruta
                    fd.rules=""
                    fd.print_time='%02d%02d'%(int(a.t_impresion),int((a.t_impresion*60.+0.5)-int(a.t_impresion)*60.))
                    ss.draw_flight_data(fd)
                    if not at_least_one_strip_printed :
                        ss2.draw_flight_data(fd,0.5,0.6,num_colums=2)
                        at_least_one_strip_printed= True
                    prev=fijo
                    prev_t=fijo_t
    if not ss.save() :
        while DlgPdfWriteError().result=='retry' and not ss.save():
            pass  
            
    if not ss2.save() :
        while DlgPdfWriteError().result=='retry' and not ss2.save():
            pass 
            # Cerrar ficheros
    if len(incidencias) != 0:
        visual = Tk()
        texto = Text(visual, height = 20, width = 80, bg = 'white')
        texto.insert('end','Fichero con datos del FIR: '+ fir_elegido[1]+'\n')
        texto.insert('end','Fichero con ejercicio: ' + ejercicio_elegido[1]+'\n')
        texto.insert('end','\n')
        texto.insert('end','Errores encontrados\n')
        texto.insert('end','-------------------\n')
        for error in incidencias:
            texto.insert('end',error+'\n')
        but_roger = Button (visual, text='Continuar')
        def inicio_ejer(e=None):
            visual.destroy()
            visual.quit()
        but_roger ['command'] = inicio_ejer
        texto.pack()
        but_roger.pack()
        but_roger.focus_set()
        visual.mainloop()
        
        
    return [punto,ejercicio,rutas,limites,deltas,tmas,local_maps,h_inicio,wind,aeropuertos,esperas_publicadas,rwys,procedimientos,proc_app,rwyInUse,auto_departures,min_sep]
    
class DlgPdfWriteError:

    def __init__(self):
    
        dlg=self.dlg=Tk()
        f1=Frame(dlg)
        f2=Frame(dlg)
        texto=Label(f1,text='Ha sido imposible guardar el archivo de fichas (fichas.pdf) o (mini_fichas.pdf)\n Es probable que tenga abierto el archivo.')
        photo=ImageTk.PhotoImage(Image.open(IMGDIR+"stock_dialog-warning.png"))
        icono=Label(f1, image=photo)
        icono.photo=photo
        butretry=Button(f2, text='     Reintentar    ', command=self.retry)
        butcancel=Button(f2,text='      Cancelar      ', command=self.cancel)
        
        f1.grid()
        f2.grid(padx=5, pady=5)
        texto.grid(row=0,column=1, padx=10, pady=5)
        icono.grid(row=0,column=0, padx=10, pady=5)
        butretry.grid(row=0,column=0, padx=10)
        butcancel.grid(row=0,column=1, padx=10)
        
        if sys.platform.startswith('win'):
            dlg.wm_iconbitmap(CRUJISIMICO)
        dlg.wm_title('Crujisim')
        
        dlg.protocol("WM_DELETE_WINDOW", self.cancel)
        dlg.focus_set()
        
        dlg.mainloop()
        
    def retry(self):
        self.dlg.destroy()
        self.result = 'retry'
        
    def cancel(self):
        self.dlg.destroy()
        self.result = 'cancel'
