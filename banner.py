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

def get_fires():
    # Devuleve una cadena con los fires disponibles y el nombre del fichero asociado
    fir_uir=glob.glob('*.fir')
    if len(fir_uir)==0:
      print 'Error, no hay ficheros .fir en este directorio'
    else:
      config=ConfigParser()
      lista=[]
      for nombre in fir_uir:
        config.readfp(open(nombre,'r'))
        lista.append([config.get('datos','nombre'),nombre])
    # Ahora sólo hay que ordenarlos
    lista.sort()
    return lista

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
      if sector[0:6]=='SECTOR':
        lista.append([config.get(sector,'nombre'),sector])
    # Ahora ordeno alfabéticamente los sectores
    lista.sort()
    return lista

def get_ejercicios(fir,sector):
    # Devuelve lista con los ejercicios que corresponden al fir y al sector
    ejercicio_total=glob.glob('./pasadas/*.eje')
    lista=[]
    config=ConfigParser()
    for a in ejercicio_total:
      config.readfp(open(a))
      fir_eje=config.get('datos','fir')
      sector_eje=config.get('datos','sector')
      if fir_eje==fir and sector_eje==sector:
        lista.append([config.get('datos','comentario'),a])
      aux=config.sections()
      for a in aux:
        config.remove_section(a)
    # Ahora toca ordenarlos
    lista.sort()
    print "Ejercicios:", lista
    return lista


images = {}
def load_image(image_name):
        new_img = Image.open(image_name+".gif").convert("RGBA")
        tkimg = ImageTk.PhotoImage(image=new_img)
	images[image_name] = tkimg
        return tkimg

def seleccion_usuario():
	global sector_list, ejer_list
	
	root = Tk()	
	banner_image = load_image("banner")
	w = banner_image.width()
	h = banner_image.height()
	root.title("CrujiSim")
	root.wm_overrideredirect(1)
	banner_canvas = Canvas(root, width=w, height=h)
	banner_canvas.create_image(0, 0, image=banner_image, anchor=N+W)
	banner_canvas.pack(side=TOP)
	
	fir_list = [x[0] for x in get_fires()]
	print "FIRes:", fir_list
	varFIR = StringVar()
	omFIR = OptionMenu(root, label="FIR:", variable=varFIR)
	omFIR.pack(side=TOP)
	for f in fir_list:
		omFIR.add_command(f)
	
	sector_list = ["--------"]
	varSector = StringVar()
	omSector = OptionMenu(root, label="Sector:", variable=varSector)
	omSector.pack(side=TOP)
	for s in sector_list:
		omSector.add_command(s)
	
	ejer_list = ["--------"]
	varEjercicio = StringVar()
	if sys.platform.startswith('linux'):
		omEjercicio = ComboBox(root, label="Ejercicio:", variable=varEjercicio)
		omEjercicio.subwidget('listbox').configure(width=40)
		omEjercicio.subwidget('entry').configure(width=40)
	else:
		omEjercicio = OptionMenu(root, label="Ejercicio:", variable=varEjercicio)
	omEjercicio.pack(side=TOP)
	if sys.platform.startswith('linux'):
		for e in ejer_list:
			omEjercicio.insert(END, e)
	else:
		for e in ejer_list:
			omEjercicio.add_command(e)

	butAceptar = Button(root, text="Aceptar")
	butAceptar.pack(side=TOP)

        def salir(e=None):
                sys.exit(0)
        butSalir = Button(root, text="Salir", command=salir)
        butSalir.pack(side=TOP)

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
		ejercicio_elegido = varEjercicio.get()
		print "Ejercicio: '"+ejercicio_elegido+"'"
		if not(ejercicio_elegido in ["", "--------", '()']):
			root.destroy()
	butAceptar['command'] = devolver_seleccion
	
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
	return [fir_elegido, sector_elegido, ejercicio_elegido, 1]
