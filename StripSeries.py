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

STRIP_X_SIZE=535    #define el tamaño horizontal de la ficha
STRIP_Y_SIZE=68     #define el tamaño vertical de la ficha


class StripSeries:

        filename=''
    
	def __init__(self, exercise_name="", date="", output_file="strips.pdf"):
		self.canvas = PDFCanvas(size=(500,815), name=output_file)
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
		
		canvas.drawLine(x+11, y+25, x+397, y+25)
		canvas.drawLine(x+5, y+52, x+529, y+52)
		canvas.drawLine(x+142, y+11, x+142, y+52)
		canvas.drawLine(x+184, y+12, x+184, y+52)
		canvas.drawLine(x+225, y+12, x+225, y+52)
		canvas.drawLine(x+279, y+12, x+279, y+52)
		canvas.drawLine(x+334, y+12, x+334, y+52)
		canvas.drawLine(x+389, y+12, x+389, y+52)
		canvas.drawLine(x+142, y+52, x+184, y+25)
		canvas.drawLine(x+184, y+38, x+225, y+38)
		canvas.drawLine(x+255, y+25, x+255, y+52)
		canvas.drawLine(x+255, y+52, x+279, y+25)
		canvas.drawLine(x+310, y+25, x+310, y+52)
		canvas.drawLine(x+310, y+52, x+334, y+25)
		canvas.drawLine(x+364, y+25, x+364, y+52)
		canvas.drawLine(x+364, y+52, x+389, y+25)
		
		canvas.drawLine(x+510, y+8, x+510, y+19)
		canvas.drawLine(x+510, y+19, x+529, y+19)
	
#	def draw_callsign(canvas, x, y, callsign):
#		strips.stringformat.drawString(canvas, callsign, x+33, y+20, Font(face="monospaced", size=18, bold=1))

	def draw_flight_data(self, callsign="",ciacallsign="", model="", wake="", responder="", speed="", cssr="", origin="", destination="", fl="", cfl="", route="", rules="", prev_fix="", fix="", next_fix="", prev_fix_est="", fix_est="", next_fix_est=""):
		x = 30
		y = 40 + 68 * (self.num_strips % STRIPS_PER_PAGE)
		canvas = self.canvas
		if (self.num_strips > 0) and (self.num_strips % STRIPS_PER_PAGE) == 0:
			canvas.flush()
			canvas.clear()
		self.draw_blank_strip(x, y)
		if len(model) < 6: model = model + " "*(6-len(model))
		elif len(model) > 6: model = model[:6]
		if wake=="": wake = " "
		if responder == "": responder = " "
		if speed == "": speed = "    "
		else: speed = "%04d" % int(speed)
		if ciacallsign=="": ciacallsign = " "
		strips.stringformat.drawString(canvas, callsign, x+33, y+20, Font(face="monospaced", size=16, bold=1))
		strips.stringformat.drawString(canvas, ciacallsign, x+15, y+10, Font(face="monospaced", size=8, bold=1))
		firstline = model + "/" + wake + "/" + responder + "/" + speed
		strips.stringformat.drawString(canvas, firstline, x+16, y+35, Font(face="monospaced", size=8, bold=1))
		secondline = origin + "      "+destination+"/"+fl
		strips.stringformat.drawString(canvas, secondline, x+16, y+47, Font(face="monospaced", size=8, bold=1))
		strips.stringformat.drawString(canvas, cssr, x+190, y+50, Font(face="monospaced", size=8, bold=1))
		strips.stringformat.drawString(canvas, route, x+16, y+63, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, rules, x+200, y+23, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, prev_fix, x+240, y+23, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, prev_fix_est, x+230, y+40, Font(face="monospaced", size=8, bold=1))
		
		strips.stringformat.drawString(canvas, fix, x+290, y+23, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, fix_est, x+280, y+40, Font(face="monospaced", size=8, bold=1))
		
		strips.stringformat.drawString(canvas, next_fix, x+345, y+23, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, next_fix_est, x+335, y+40, Font(face="monospaced", size=8, bold=1))
                
                strips.stringformat.drawString(canvas,cfl,x+400,y+23, Font(face="monospaced", size=10, bold=1))
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

