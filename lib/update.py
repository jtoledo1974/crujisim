
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
# Do not edit this code. This code is considered old and deprecated
# This is currently not in use since everybody should use SVN clients for now
# and will eventually be implemented inside Crujisim.py using GTK
#
#############################

from Tix import *
import tkMessageBox
import urllib
import logging
import ConfMgr
import httplib
import zipfile
import sys

_version_url = ConfMgr.read_option("NetUpdate", "version_url", "http://80.25.47.120/crujisim/exercises-version.txt")
_update_url = ConfMgr.read_option("NetUpdate", "resource_url", "http://80.25.47.120/crujisim/exercises.zip")

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
        # Names of files in ZIP are encoded in codepage 437. Therefore...
        unicode_filename = filename.decode('cp437')
        outputfilename=os.path.join(path, unicode_filename)
        outputbasename=os.path.basename(outputfilename)
        try:
            if outputbasename=='':
                    # Output "file" is a directory. Create it.
                os.makedirs(outputfilename)
            else:
                dirname = os.path.dirname(outputfilename)
                # If parent directory to extracted file does not exist, create it!
                if not(os.path.isdir(dirname)):
                    os.makedirs(dirname)
                file = open(outputfilename, 'w+b')
                file.write(zfile.read(unicode_filename))
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
        progress = Toplevel()
        progress.title("CrujiSim")
        lblProgress = Label(progress, text="Descargando...")
        lblProgress.pack()
        lblProgress2 = Label(progress, text="")
        lblProgress2.pack()
        def hook(a, b, c):
            letras = "|/-\\"
            lblProgress2.config(text=letras[a%4])
            progress.update()
        urllib.urlretrieve(_update_url, 'tmp-exercises.zip', hook)
        zfile = zipfile.ZipFile('tmp-exercises.zip')
        test_result = zfile.testzip()
        zfile.close()
        if test_result == None:
            os.rename('tmp-exercises.zip', 'exercises.zip')
            unziptobasepath('exercises.zip')
            return True
        else:
            mb = tkMessageBox.Message(type=tkMessageBox.OK, message="Archivo de ejercicios erróneo...\nSeguimos con la versión anterior")
            mb.show()
            return False
    except:
        mb = tkMessageBox.Message(type=tkMessageBox.OK, message="No puedo bajarme el archivo de la web...\nSeguimos con la versión anterior")
        mb.show()
        return False
        
def update_exercises():
    root = Tk()
    root.title("CrujiSim")
    lblUpdate = Label(root, text="Actualización automática", font='-*-Helvetica-*--*-20-*-')
    lblUpdate.pack()
    root.update()
    if os.path.lexists('./.svn/'):
        if not tkMessageBox.askyesno(message="Parece que estás usando una versión de crujisim\nactualizada a través de SVN (la tortuga)\nNo se recomienda que te actualices las pasadas\na través de este procedimiento, sino haciendo\nhaciendo update con la tortuga.\n¿Estás seguro de que deseas continuar?"):
            return
    current_version = get_installed_version_string()
    logging.info("Current version: '"+str(current_version)+"'")
    online_version = get_latest_online_version_string()
    logging.info("Online version: '"+str(online_version)+"'")
    if online_version == None:
        tkMessageBox.showinfo(message="No puedo descargar la última versión.\nSeguimos con la versión anterior")
    elif online_version > current_version:
        if tkMessageBox.askyesno(message="Hay nuevos ejercicios en la web. ¿Los quieres?"):
            if retrieve_and_unzip_latest_version() == True:
                set_installed_version_string(online_version)
                tkMessageBox.showinfo(message="Nuevos ejercicios descargados. Vuelve a entrar para utilizarlos.")
            else:
                tkMessageBox.showinfo(message="Seguimos con la versión anterior de los ejercicios")
        else:
            tkMessageBox.showinfo(message="Seguimos con la versión anterior de los ejercicios")
    else:
        tkMessageBox.showinfo(message="No hay versiones nuevas para descargar")
