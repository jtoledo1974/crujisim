
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

from Tix import *
import tkMessageBox
import urllib
import logging
import ConfMgr
import httplib
import zipfile

_version_url = ConfMgr.read_option("NetUpdate", "version_url", "http://personales.ya.com/nanomago/exercises-version.txt")
_update_url = ConfMgr.read_option("NetUpdate", "resource_url", "http://personales.ya.com/nanomago/exercises.zip")

def get_installed_version_string():
	current_version = ConfMgr.read_option("NetUpdate", "installed_version", "")
	return current_version

def set_installed_version_string(new_version_string):
	ConfMgr.write_option("NetUpdate", "installed_version", new_version_string)

def get_latest_online_version_string():
	try:
		online_version_resource = urllib.urlopen(_version_url)
		online_version = online_version_resource.read()
		online_version_resource.close()
		splitted_online_version = online_version.split("\n")
		return splitted_online_version[0]
	except:
		logging.warning("Cannot open online version resource.")
		return None

def unziptobasepath(zipfilename, path="."):
    """Unzips filename to path (overwriting files if present)"""
    zfile = zipfile.ZipFile(zipfilename,'r')
    print zfile.namelist()
    for filename in zfile.namelist():
	outputfilename=os.path.join(path, filename)
	outputbasename=os.path.basename(outputfilename)
	try:
		if outputbasename=='':
			# Output "file" is a directory.
			os.makedirs(outputfilename)
		else:
        		file = open(outputfilename, 'w+b')
        		file.write(zfile.read(filename))
        		file.close()
	except:
		logging.warning("Cannot unzip to "+outputfilename)

def retrieve_and_unzip_latest_version():
	try:
		os.remove('tmp-exercises.zip')
		os.remove('exercises.zip')
	except:
		pass
	try:
		urllib.urlretrieve(_update_url, 'tmp-exercises.zip')
		zfile = zipfile.ZipFile('tmp-exercises.zip')
		test_result = zfile.testzip()
		zfile.close()
		if test_result == None:
			os.rename('tmp-exercises.zip', 'exercises.zip')
			unziptobasepath('exercises.zip')
		else:
			mb = tkMessageBox.Message(type=tkMessageBox.OK, message="Archivo de ejercicios erróneo...\nSeguimos con la versión anterior")
			mb.show()
	except:
		mb = tkMessageBox.Message(type=tkMessageBox.OK, message="No puedo bajarme el archivo de la web...\nSeguimos con la versión anterior")
		mb.show()

def update_exercises():
	root = Tk()

	current_version = get_installed_version_string()
	logging.info("Current version: '"+current_version+"'")
	online_version = get_latest_online_version_string()
	logging.info("Online version: '"+online_version+"'")
	if online_version == None:
		mb = tkMessageBox.Message(type=tkMessageBox.OK, message="No puedo descargar la última versión.\nSeguimos con la versión anterior")
		mb.show()
	elif online_version > current_version:
		lbl = Label(root, text="Hay nuevos ejercicios en la web")
		def descarga(e=None):
			retrieve_and_unzip_latest_version()
			set_installed_version_string(online_version)
			root.destroy()
			mb = tkMessageBox.Message(type=tkMessageBox.OK, message="Nuevos ejercicios descargados. Sal del programa y vuelve a entrar para utilizarlos.")
			mb.show()
		butSi = Button(root, text="ACTUALIZAR", command=descarga)
		def no_descarga(e=None):
			root.destroy()
		butNo = Button(root, text="CANCELAR", command=no_descarga)
		lbl.grid(row=0, column=0, columnspan=2)
		butSi.grid(row=1, column=0)
		butNo.grid(row=1, column=1)
	else:
		mb = tkMessageBox.Message(type=tkMessageBox.OK, message="No hay versiones nuevas para descargar")
		mb.show()
	root.mainloop()
