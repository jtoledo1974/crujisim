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


import sys
sys.path.append ("lib")
import banner
import Metepasadas
import tpv
import logging
import update
import UI

# Define which logging level messages will be output
logging.getLogger('').setLevel(logging.DEBUG)

#dlg=UI.Dialog(master=None,type="accept",transient=False)
class warndlg(UI.Dialog):
    def __init__(self):
        import Tkinter
        UI.Dialog.__init__(self,master=None,type="accept",transient=False)
        t="""ATENCIÓN!!!
El MainMenu.py se considera anticuado. Asegúrate de que tienes instaladas las bibliotecas
que se mencionan en el archivo doc/Guía de instalación en el punto 4
y arranca splash.py en lugar de MainMenu.py

Si tienes dudas pregunta en el foro, pero ten presente que muy pronto este
programa dejará de funcionar y sólo quedará el splash.py"""
        texto=Tkinter.Label(self.content,text=t)
        texto.pack()
        
dlg=warndlg().run()
        
while 1:
    [accion, fir_elegido , sector_elegido , ejercicio_elegido , imprimir_fichas] = banner.seleccion_usuario()
    
    # accion = "ejecutar", "modificar", "nueva", "actualizar"
    
    print "Returned tuple:", [accion, fir_elegido , sector_elegido , ejercicio_elegido , imprimir_fichas]
    
    if accion == "modificar":
        Metepasadas.modificar([fir_elegido , sector_elegido , ejercicio_elegido , imprimir_fichas])
    elif accion == "nueva":
        Metepasadas.nueva()
    elif accion == "ejecutar":
        if "tpv" in sys.modules:
            reload(sys.modules["tpv"])
        else:
            import tpv
        tpv.set_seleccion_usuario([fir_elegido , sector_elegido , ejercicio_elegido , imprimir_fichas])
        if "Simulador" in sys.modules:
            reload(sys.modules["Simulador"])
        else:
            import Simulador
    elif accion == "actualizar":
        update.update_exercises()
        sys.exit(0)
        
