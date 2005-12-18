#!/usr/bin/env python
#-*- coding:iso8859-15 -*-

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

#Constants


import warnings
warnings.filterwarnings('ignore','.*',DeprecationWarning)
import sys
sys.path.insert(0, 'strips.zip')
import strips.stringformat
from strips.colors import *
from strips.pid import Font
from strips.PDF import PDFCanvas

STRIPS_PER_PAGE = 11

STRIP_X_SIZE=560    #define el tamaño horizontal de la ficha
STRIP_Y_SIZE=70     #define el tamaño vertical de la ficha

class FlightData:
     exercice_name=""
     callsign=""
     ciacallsign=""
     model=""
     wake=""
     responder=""
     speed=""
     cssr=""
     origin=""
     eobt=""
     destination=""
     fl=""
     cfl=""
     route=""
     rules=""
     prev_fix=""
     fix=""
     next_fix=""
     prev_fix_est=""
     fix_est=""
     next_fix_est=""
     print_time=0.
     fs_type="enroute"
    
class StripSeries:

        filename=''
    
	def __init__(self, exercise_name="", date="", output_file="strips.pdf"):
		self.canvas = PDFCanvas(size=(560,815), name=output_file)
                # For some strange reason the flight strips will not
                # print correctly on the first page, so we need a dummy
                # first page prior to the actual flight strips
		strips.stringformat.drawString(self.canvas, "Ejercicio:  "+str(exercise_name), 40, 40)
		self.canvas.clear()
		self.num_strips = 0
		self.filename=output_file
		
	def draw_blank_strip(self, x, y, fs_type,form_factor=1.0):
          
                def formfactor(x,rounded=True):
                         x1=x*form_factor
                         if rounded==True: x1=round(x1)
                         return x1
               
                   
		canvas = self.canvas
                #Dibuja el contorno de la ficha
		
		canvas.drawLine(formfactor(x), formfactor(y), formfactor(x+STRIP_X_SIZE), formfactor(y), color=dimgray)
		canvas.drawLine(formfactor(x), formfactor(y+STRIP_Y_SIZE), formfactor(x+STRIP_X_SIZE), formfactor(y+STRIP_Y_SIZE), color=dimgray)
		canvas.drawLine(formfactor(x), formfactor(y), formfactor(x), formfactor(y+STRIP_Y_SIZE), color=dimgray)
		canvas.drawLine(formfactor(x+STRIP_X_SIZE), formfactor(y), formfactor(x+STRIP_X_SIZE), formfactor(y+STRIP_Y_SIZE), color=dimgray)

##		Primera linea horizontal: hacia arriba está el indicativo
		canvas.drawLine(formfactor(x+11), formfactor(y+23), formfactor(x+410), formfactor(y+23))
##		Segunda linea horizontal: hacia abajo está la ruta
		canvas.drawLine(formfactor(x+5), formfactor(y+52), formfactor(x+550), formfactor(y+52))
##		Seis Lineas verticales principales: hora 1 comunicación,respondedor,fijo anterior,fijo,fijo siguiente,instrucciones
		canvas.drawLine(formfactor(x+145), formfactor(y+11), formfactor(x+145), formfactor(y+52))
		canvas.drawLine(formfactor(x+187), formfactor(y+12), formfactor(x+187), formfactor(y+52))
		canvas.drawLine(formfactor(x+227), formfactor(y+12), formfactor(x+227), formfactor(y+52))
		canvas.drawLine(formfactor(x+286), formfactor(y+12), formfactor(x+286), formfactor(y+52))
		canvas.drawLine(formfactor(x+345), formfactor(y+12), formfactor(x+345), formfactor(y+52))
		canvas.drawLine(formfactor(x+404), formfactor(y+12), formfactor(x+404), formfactor(y+52))
##		Linea diagonal casilla primera comunicación
		canvas.drawLine(formfactor(x+144), formfactor(y+52), formfactor(x+187), formfactor(y+23))
##		Linea horizontal divisoria casilla respondedor
		canvas.drawLine(formfactor(x+187), formfactor(y+37), formfactor(x+227), formfactor(y+37))
##		Lineas verticales y diagonales para las casillas de estimada piloto/hora de paso por el fijo
		canvas.drawLine(formfactor(x+257), formfactor(y+23), formfactor(x+257), formfactor(y+52))
		canvas.drawLine(formfactor(x+257), formfactor(y+52), formfactor(x+286), formfactor(y+23))
		canvas.drawLine(formfactor(x+316), formfactor(y+23), formfactor(x+316), formfactor(y+52))
		canvas.drawLine(formfactor(x+316), formfactor(y+52), formfactor(x+345), formfactor(y+23))
		canvas.drawLine(formfactor(x+375), formfactor(y+23), formfactor(x+375), formfactor(y+52))
		canvas.drawLine(formfactor(x+375), formfactor(y+52), formfactor(x+404), formfactor(y+23))
##		Lineas Minuto de transferencia de comunicaciones		
		canvas.drawLine(formfactor(x+529), formfactor(y+8), formfactor(x+529), formfactor(y+17),width=3)
		canvas.drawLine(formfactor(x+531), formfactor(y+19), formfactor(x+550), formfactor(y+19))

		if fs_type=="coord":
                    polypoints=[(formfactor(x+504),formfactor(y+52)),(formfactor(x+504),formfactor(y+30)),
                                (formfactor(x+498),formfactor(y+30)),(formfactor(x+507),formfactor(y+24)),
                                (formfactor(x+516),formfactor(y+30)),(formfactor(x+510),formfactor(y+30)),
                                (formfactor(x+510),formfactor(y+52))]
                    canvas.drawPolygon (polypoints, fillColor=black, closed=1)
                    	
#	def draw_callsign(canvas, x, y, callsign):
#		strips.stringformat.drawString(canvas, callsign, x+33, y+20, Font(face="monospaced", size=18, bold=1))

	def draw_flight_data(self,fd,form_factor=1.0,font_factor=1.0,font_fixed=False,font_fixed_size=8,on_screen_strip=False):
          
                def formfactor(x,rounded=True):
                         x1=x*form_factor
                         if rounded==True: x1=round(x1)
                         return x1
                
                def fontfactor(x):
                     if font_fixed:
                         x1=font_fixed_size
                     else:
                         x1=x*font_factor
                     return x1
                    
		x = formfactor(25)
                if not(on_screen_strip):
                     x = formfactor(25)
                     dummy = STRIPS_PER_PAGE/form_factor
                     y = formfactor(40) + formfactor((STRIP_Y_SIZE * (self.num_strips%dummy)/form_factor))
                else:
                     x = 1
                     y = 1
                     
		canvas = self.canvas
		if (self.num_strips > 0) and (self.num_strips % (round(STRIPS_PER_PAGE/form_factor)))== 0:
			canvas.flush()
			canvas.clear()
		self.draw_blank_strip(x, y, fd.fs_type,form_factor)
		if len(fd.model) < 6: fd.model = fd.model + " "*(6-len(fd.model))
		elif len(fd.model) > 6: fd.model = fd.model[:6]
		if fd.wake=="": fd.wake = " "
		if fd.responder == "": fd.responder = " "
		if fd.speed == "": fd.speed = "    "
		else: fd.speed = "%04d" % int(fd.speed)
		if fd.ciacallsign=="": fd.ciacallsign = " "
		if fd.exercice_name=="": fd.exercice_name= " "
		strips.stringformat.drawString(canvas, fd.callsign, formfactor(x+30), formfactor(y+22), Font(face="monospaced", size=fontfactor(20), bold=1))
		if not(on_screen_strip):
                     strips.stringformat.drawString(canvas, fd.ciacallsign, formfactor(x+15), formfactor(y+10), Font(face="monospaced", size=fontfactor(8), bold=1))
		firstline = fd.model + "/" + fd.wake + "/" + fd.responder + "/" + fd.speed
		strips.stringformat.drawString(canvas, firstline, formfactor(x+16), formfactor(y+35), Font(face="monospaced", size=fontfactor(9), bold=1))
		if fd.eobt=="":
                    secondline = fd.origin + "      "+fd.destination+"/"+fd.fl
                else:
                    secondline = fd.origin + "/" + fd.eobt + "  "+fd.destination+"/"+fd.fl
		strips.stringformat.drawString(canvas, secondline, formfactor(x+16), formfactor(y+49), Font(face="monospaced", size=fontfactor(10), bold=1))
		strips.stringformat.drawString(canvas, fd.cssr, formfactor(x+190), formfactor(y+50), Font(face="monospaced", size=fontfactor(8), bold=1))
		strips.stringformat.drawString(canvas, fd.route, formfactor(x+16), formfactor(y+61), Font(face="monospaced", size=fontfactor(10), bold=1))
		strips.stringformat.drawString(canvas, fd.rules, formfactor(x+200), formfactor(y+22), Font(face="monospaced", size=fontfactor(10), bold=1))

		strips.stringformat.drawString(canvas, fd.prev_fix, formfactor(x+240), formfactor(y+22), Font(face="monospaced", size=fontfactor(10), bold=1))
		strips.stringformat.drawString(canvas, fd.prev_fix_est, formfactor(x+230), formfactor(y+35), Font(face="monospaced", size=fontfactor(9), bold=1))
		
		strips.stringformat.drawString(canvas, fd.fix, formfactor(x+300), formfactor(y+22), Font(face="monospaced", size=fontfactor(12), bold=1))
		strips.stringformat.drawString(canvas, fd.fix_est, formfactor(x+286), formfactor(y+50), Font(face="monospaced", size=fontfactor(12), bold=1))
		
		strips.stringformat.drawString(canvas, fd.next_fix, formfactor(x+358), formfactor(y+22), Font(face="monospaced", size=fontfactor(10), bold=1))
		strips.stringformat.drawString(canvas, fd.next_fix_est, formfactor(x+348), formfactor(y+35), Font(face="monospaced", size=fontfactor(9), bold=1))
                
                strips.stringformat.drawString(canvas,fd.cfl,formfactor(x+405),formfactor(y+22), Font(face="monospaced", size=fontfactor(12), bold=1))
                if not(on_screen_strip):
                     strips.stringformat.drawString(canvas,fd.exercice_name,formfactor(x+5),formfactor(y+68), Font(face="monospaced", size=fontfactor(6), bold=0))
                     strips.stringformat.drawString(canvas,fd.print_time,formfactor(x+490),formfactor(y+61), Font(face="monospaced", size=fontfactor(10), bold=1))

                if fd.fs_type=="coord":
                    strips.stringformat.drawString(canvas, 'COORD', formfactor(x+150), formfactor(y+23), Font(face="monospaced", size=fontfactor(10), bold=1))
                if not(on_screen_strip): self.num_strips += 1
                else: self.num_strips=1

	def save(self):
                #We try to open the file for writing and throw an exception if unable
                try:
                    f=open(self.filename,'wb')
                    f.close()
                    self.canvas.save()
                    return True
                except:
                    print 'Failed printing flight strips. Unable to open '+self.filename+' for writing'
                    return False

