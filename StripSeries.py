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
    
class StripSeries:

        filename=''
    
	def __init__(self, exercise_name="", date="", output_file="strips.pdf"):
		self.canvas = PDFCanvas(size=(560,815), name=output_file)
		strips.stringformat.drawString(self.canvas, "Ejercicio:  "+str(exercise_name), 40, 40)
		self.canvas.clear()
		self.num_strips = 0
		self.filename=output_file
		
	def draw_blank_strip(self, x, y):
		canvas = self.canvas
                #Dibuja el contorno de la ficha
		canvas.drawLine(x, y, x+STRIP_X_SIZE, y, color=dimgray)
		canvas.drawLine(x, y+STRIP_Y_SIZE, x+STRIP_X_SIZE, y+STRIP_Y_SIZE, color=dimgray)
		canvas.drawLine(x, y, x, y+STRIP_Y_SIZE, color=dimgray)
		canvas.drawLine(x+STRIP_X_SIZE, y, x+STRIP_X_SIZE, y+STRIP_Y_SIZE, color=dimgray)

##		Primera linea horizontal: hacia arriba está el indicativo
		canvas.drawLine(x+11, y+23, x+410, y+23)
##		Segunda linea horizontal: hacia abajo está la ruta
		canvas.drawLine(x+5, y+52, x+550, y+52)
##		Seis Lineas verticales principales: hora 1 comunicación,respondedor,fijo anterior,fijo,fijo siguiente,instrucciones
		canvas.drawLine(x+145, y+11, x+145, y+52)
		canvas.drawLine(x+187, y+12, x+187, y+52)
		canvas.drawLine(x+227, y+12, x+227, y+52)
		canvas.drawLine(x+286, y+12, x+286, y+52)
		canvas.drawLine(x+345, y+12, x+345, y+52)
		canvas.drawLine(x+404, y+12, x+404, y+52)
##		Linea diagonal casilla primera comunicación
		canvas.drawLine(x+144, y+52, x+187, y+23)
##		Linea horizontal divisoria casilla respondedor
		canvas.drawLine(x+187, y+37, x+227, y+37)
##		Lineas verticales y diagonales para las casillas de estimada piloto/hora de paso por el fijo
		canvas.drawLine(x+257, y+23, x+257, y+52)
		canvas.drawLine(x+257, y+52, x+286, y+23)
		canvas.drawLine(x+316, y+23, x+316, y+52)
		canvas.drawLine(x+316, y+52, x+345, y+23)
		canvas.drawLine(x+375, y+23, x+375, y+52)
		canvas.drawLine(x+375, y+52, x+404, y+23)
##		Lineas Minuto de transferencia de comunicaciones		
		canvas.drawLine(x+529, y+8, x+529, y+17,width=3)
		canvas.drawLine(x+531, y+19, x+550, y+19)
	
#	def draw_callsign(canvas, x, y, callsign):
#		strips.stringformat.drawString(canvas, callsign, x+33, y+20, Font(face="monospaced", size=18, bold=1))

	def draw_flight_data(self,fd):
		x = 25
		y = 40 + STRIP_Y_SIZE * (self.num_strips % STRIPS_PER_PAGE)
		canvas = self.canvas
		if (self.num_strips > 0) and (self.num_strips % STRIPS_PER_PAGE) == 0:
			canvas.flush()
			canvas.clear()
		self.draw_blank_strip(x, y)
		if len(fd.model) < 6: fd.model = fd.model + " "*(6-len(fd.model))
		elif len(fd.model) > 6: fd.model = fd.model[:6]
		if fd.wake=="": fd.wake = " "
		if fd.responder == "": fd.responder = " "
		if fd.speed == "": fd.speed = "    "
		else: fd.speed = "%04d" % int(fd.speed)
		if fd.ciacallsign=="": fd.ciacallsign = " "
		if fd.exercice_name=="": fd.exercice_name= " "
		strips.stringformat.drawString(canvas, fd.callsign, x+30, y+22, Font(face="monospaced", size=20, bold=1))
		strips.stringformat.drawString(canvas, fd.ciacallsign, x+15, y+10, Font(face="monospaced", size=8, bold=1))
		firstline = fd.model + "/" + fd.wake + "/" + fd.responder + "/" + fd.speed
		strips.stringformat.drawString(canvas, firstline, x+16, y+35, Font(face="monospaced", size=9, bold=1))
		secondline = fd.origin + "      "+fd.destination+"/"+fd.fl
		strips.stringformat.drawString(canvas, secondline, x+16, y+49, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, fd.cssr, x+190, y+50, Font(face="monospaced", size=8, bold=1))
		strips.stringformat.drawString(canvas, fd.route, x+16, y+61, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, fd.rules, x+200, y+22, Font(face="monospaced", size=10, bold=1))

		strips.stringformat.drawString(canvas, fd.prev_fix, x+240, y+22, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, fd.prev_fix_est, x+230, y+35, Font(face="monospaced", size=9, bold=1))
		
		strips.stringformat.drawString(canvas, fd.fix, x+300, y+22, Font(face="monospaced", size=12, bold=1))
		strips.stringformat.drawString(canvas, fd.fix_est, x+286, y+50, Font(face="monospaced", size=12, bold=1))
		
		strips.stringformat.drawString(canvas, fd.next_fix, x+358, y+22, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, fd.next_fix_est, x+348, y+35, Font(face="monospaced", size=9, bold=1))
                
                strips.stringformat.drawString(canvas,fd.cfl,x+405,y+22, Font(face="monospaced", size=12, bold=1))
                strips.stringformat.drawString(canvas,fd.exercice_name,x+5,y+68, Font(face="monospaced", size=6, bold=0))
		self.num_strips += 1

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

