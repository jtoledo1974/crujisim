#!/usr/bin/python
#-*- coding:"iso8859-15" -*-

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

def get_hdg_obj(self,deriva):
  # Da el rumbo objetivo en funci� de la demanda
  if self.to_do = 'fpr':
    self.pto=self.route[0][0] #Punto al que se dirige con correcci� de deriva
    self.vect=rp(r(self.pto,self.pos))
    # Correci� de deriva
    r_obj=self.vect[1] - deriva
  elif self.to_do = 'hdg':
    self.pto=s(self.pos,pr((2*self.ground_spd,self.hold_hdg)))
    self.vect=rp(r(self.pto,self.pos))
    r_obj=self.vect[1]

    
