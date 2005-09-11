#!/usr/bin/python
#-*- coding:iso8859-15 -*-

# lads.py

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

from math import sin, cos, sqrt, radians

class LAD:
	def __init__(self, origin, destination):
		self.origin = origin
		self.destination = destination
		self.line_id = None
		self.text_id1 = None
		self.text_id2 = None
		self.text_id3 = None
		self.text_id4 = None

	def destroy(self):
		pass

def compute_mindisttime(xA, yA, headingA, speedA, xB, yB, headingB, speedB):
	# 60.0: miles per minute per knot
	try:
		vxA = speedA/60.0 * sin(radians(headingA))
		vyA = speedA/60.0 * cos(radians(headingA))
		vxB = speedB/60.0 * sin(radians(headingB))
		vyB = speedB/60.0 * cos(radians(headingB))
		t = -((xA-xB)*(vxA-vxB)+(yA-yB)*(vyA-vyB)) / ((vxA-vxB)*(vxA-vxB)+(vyA-vyB)*(vyA-vyB))
		# A veces al dividir entre algo muy pequeï¿œ no se obtiene excepción, sino un valor
		# flotante de "NaN" o de "inf" (error del Python). Forzamos excepción en estos casos.
		dummy = int(t)
		return t
	except:
		return None

def compute_cross_points(xA, yA, headingA, speedA, xB, yB, headingB, speedB):
	time_to_mindist = compute_mindisttime(xA, yA, headingA, speedA, xB, yB, headingB, speedB)
	vxA = speedA/60.0 * sin(radians(headingA))
	vyA = speedA/60.0 * cos(radians(headingA))
	vxB = speedB/60.0 * sin(radians(headingB))
	vyB = speedB/60.0 * cos(radians(headingB))
	posAx = xA + vxA * time_to_mindist
	posAy = yA + vyA * time_to_mindist
	posBx = xB + vxB * time_to_mindist
	posBy = yB + vyB * time_to_mindist
	return (posAx, posAy, posBx, posBy)

def compute_mindist(xA, yA, headingA, speedA, xB, yB, headingB, speedB):
	(posAx, posAy, posBx, posBy) = compute_cross_points(xA, yA, headingA, speedA, xB, yB, headingB, speedB)
	return sqrt((posAx-posBx)*(posAx-posBx) + (posAy-posBy)*(posAy-posBy))
