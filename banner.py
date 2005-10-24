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

# Module imports
from Tix import *
from Tkconstants import *
import Image
import ImageTk
import GifImagePlugin
Image._initialized=2
import sys
import glob
from ConfigParser import *
import zipfile
from os import rename

# Global variables
exercises_root = 'pasadas'

# Constants
IMGDIR='./img/'

def get_fires():
    # Devuelve una lista con los fires disponibles y los nombres de ficheros asociados
    fir_list = []
    directories_from_root = os.listdir(exercises_root)
    for directory in directories_from_root:
        fir_description_file = os.path.join(exercises_root,directory,directory+".fir")
        if os.path.exists(fir_description_file):
            print "FIR OK:", fir_description_file
            # Extract FIR name from FIR description file
            config = ConfigParser()
            fir_file = open(fir_description_file, 'r')
            config.readfp(fir_file)
            fir_name = config.get('datos', 'nombre')
            fir_file.close()
            # Append name and file name to FIR list
            fir_list.append([fir_name, fir_description_file])
    # Sort FIR list
    fir_list.sort()
    return fir_list

def get_sectores(fir):
    # para un FIR dado, ver sus sectores fir
    fir_pairs = get_fires()
    archivo = None
    for (fir_desc, fir_file) in fir_pairs:
    	if fir == fir_desc:
		archivo = fir_file
    config=ConfigParser()
    lista=[]
    config.readfp(open(archivo,'r'))
    for sector in config.sections():
      if sector[0:6]=='sector':
        lista.append([config.get(sector,'nombre'),sector])
    # Ahora ordeno alfabéticamente los sectores
    lista.sort()
    return lista

def get_ejercicios(fir, sector):
    # Devuelve lista con los ejercicios que corresponden al fir y al sector
    # La lista contiene el comentario del ejercicio y el path del archivo

    fir_list = get_fires()
    fir_file = None
    for (desc, file) in fir_list:
        if fir == desc:
            fir_file = file
    if fir_file == None: return []

    exercises_directory = os.path.dirname(fir_file)
    fir_exercises = os.listdir(exercises_directory)
    sector_exercises = []

    for exercise_file_name in fir_exercises:
      if os.path.splitext(exercise_file_name)[1].upper() != '.EJE': continue
      config=ConfigParser()
      exercise_file_path = os.path.join(exercises_directory, exercise_file_name)
      exercise_filep = open(exercise_file_path, 'r')
      config.readfp(exercise_filep)
      exercise_filep.close()
      fir_eje=config.get('datos','fir')
      sector_eje=config.get('datos','sector')
      if fir_eje.upper()==fir.upper() and sector_eje.upper()==sector.upper():
        if config.has_option('datos','comentario'):
          exercise_description = config.get('datos','comentario')
        else:
          exercise_description = exercise_file_name
        sector_exercises.append([exercise_description,exercise_file_path])
    # Ahora toca ordenarlos
    sector_exercises.sort()
    return sector_exercises


images = {}
def load_image(image_name):
        new_img = Image.open(IMGDIR+image_name+".gif").convert("RGBA")
        tkimg = ImageTk.PhotoImage(image=new_img)
	images[image_name] = tkimg
        return tkimg

def seleccion_usuario():
	global sector_list, ejer_list, accion
	accion = '' # Will indicate if user wishes to run ("ejecutar") / modify ("modificar") the
	            # selected simulation, create a new ("nueva") one,
                    #or update exercises via network ("actualizar")
	
	root = Tk()	
	banner_image = load_image("banner")
	w = banner_image.width()
	h = banner_image.height()
	root.title("CrujiSim")
	root.wm_overrideredirect(1)
	banner_canvas = Canvas(root, width=w, height=h)
	banner_canvas.create_image(0, 0, image=banner_image, anchor=N+W)
	banner_canvas.grid(row=0,columnspan=2, sticky=N)
	
	Label(root, text="FIR:").grid(row=1,column=0, sticky=E)
	fir_list = [x[0] for x in get_fires()]
	print "FIRes:", fir_list
	varFIR = StringVar()
	omFIR = OptionMenu(root, variable=varFIR)
	omFIR.grid(row=1,column=1, sticky=W)
	for f in fir_list:
		omFIR.add_command(f)
	
	Label(root, text="Sector:").grid(row=2,column=0, sticky=E)
	sector_list = ["--------"]
	varSector = StringVar()
	omSector = OptionMenu(root, variable=varSector)
	omSector.grid(row=2, column=1, sticky=W)
	for s in sector_list:
		omSector.add_command(s)
	
	Label(root, text="Ejercicio:").grid(row=3,column=0, sticky=E)
	ejer_list = ["--------"]
	varEjercicio = StringVar()
	if sys.platform.startswith('linux'):
		omEjercicio = ComboBox(root, variable=varEjercicio)
		omEjercicio.subwidget('listbox').configure(width=40)
		omEjercicio.subwidget('entry').configure(width=40)
	else:
		omEjercicio = OptionMenu(root, variable=varEjercicio)
	omEjercicio.grid(row=3, column=1, sticky=W)
	if sys.platform.startswith('linux'):
		for e in ejer_list:
			omEjercicio.insert(END, e)
	else:
		for e in ejer_list:
			omEjercicio.add_command(e)

	frmAcciones = Frame(root)
	butAceptar = Button(frmAcciones, text="Practicar")
	butAceptar.grid(row=0, column=0, padx=1)
	
	butModificar = Button(frmAcciones, text="Modificar")
	butModificar.grid(row=0,column=1, padx=1)
	
	butCrear = Button(frmAcciones, text="Crear pasada")
	butCrear.grid(row=0,column=2, padx=1)

	butActualizar = Button(frmAcciones, text="Actualizar")
	butActualizar.grid(row=0, column=3, padx=1)
	frmAcciones.grid(row=4, column=0, columnspan=4, sticky=E, padx=5, pady=5)

        def salir(e=None):
                sys.exit(0)
        butSalir = Button(frmAcciones, text="Salir", command=salir)
        butSalir.grid(row=0, column=4, padx=1)

	def change_fir(e=None):
		global sector_list
		for s in sector_list:
			omSector.delete(s)
		sector_list = [x[0] for x in get_sectores(varFIR.get())]
		for s in sector_list:
			omSector.add_command(s)
	
	omFIR.configure(command=change_fir)
	
	def change_sector(e=None):
		global ejer_list
		if sys.platform.startswith('linux'):
			omEjercicio.subwidget('listbox').delete(0, END)
		else:
			for e in ejer_list:
				omEjercicio.delete(e)
		ejer_list = [x[0] for x in get_ejercicios(varFIR.get(), varSector.get())]
		
		if sys.platform.startswith('linux'):
			for e in ejer_list:
				omEjercicio.insert(END, e)
			if len(ejer_list) > 0:
				omEjercicio.pick(0)
		else:
			for e in ejer_list:
				omEjercicio.add_command(e)
	
	omSector.configure(command=change_sector)
	omFIR.subwidget_list['menu'].invoke(0)
	
	def set_splash_size():
		splash_width = root.winfo_reqwidth()
		splash_height = root.winfo_reqheight()
		screen_width = root.winfo_screenwidth()
		screen_height = root.winfo_screenheight()
		px = (screen_width - splash_width) / 2
		py = (screen_height - splash_height) / 2
		root.wm_geometry("+%d+%d" % (px,py))
	root.after_idle(set_splash_size)
	
	def devolver_seleccion(e=None):
		global accion
		ejercicio_elegido = varEjercicio.get()
		print "Ejercicio: '"+ejercicio_elegido+"'"
		if not(ejercicio_elegido in ["", "--------", '()']):
			accion = "ejecutar"
			root.destroy()
	butAceptar['command'] = devolver_seleccion
	
	def devolver_modificar(e=None):
		global accion
		ejercicio_elegido = varEjercicio.get()
		print "Ejercicio: '"+ejercicio_elegido+"'"
		if not(ejercicio_elegido in ["", "--------", '()']):
			accion = "modificar"
			root.destroy()
	butModificar['command'] = devolver_modificar
	
	def devolver_nueva(e=None):
		global accion
		ejercicio_elegido = varEjercicio.get()
		print "Ejercicio: '"+ejercicio_elegido+"'"
		if not(ejercicio_elegido in ["", "--------", '()']):
			accion = "nueva"
			root.destroy()
	butCrear['command'] = devolver_nueva
	
	def devolver_actualizar(e=None):
		global accion
		accion = "actualizar"
		root.destroy()
	butActualizar['command'] = devolver_actualizar

	root.mainloop()
	fir = varFIR.get()
        print 'Fir:',fir
	fir_elegido = [x for x in get_fires() if x[0]==fir][0]
	print 'Fir elegido:',fir_elegido
	sector = varSector.get()
	print 'Sector:',sector
	sector_elegido = [x for x in get_sectores(fir) if x[0]==sector][0]
	print 'Sector elegido:',sector_elegido
	ejercicio = varEjercicio.get()
	print 'Ejercicio:',ejercicio
	ejercicio_elegido = [x for x in get_ejercicios(fir, sector) if x[0]==ejercicio][0]
	print 'Ejercicio elegido:',ejercicio_elegido
	print "Exiting with selection:", (fir_elegido, sector_elegido, ejercicio_elegido)
	return [accion, fir_elegido, sector_elegido, ejercicio_elegido, 1]
