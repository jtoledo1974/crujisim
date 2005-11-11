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
"""Classes used by the pseudopilot interface of Crujisim"""

# TODO: Eventualy Pseudopilot should be a subclass of RaDisplay, meaning that it
# is a special case of a Radar Display to be used to control the aircraft as a
# pseudopilot. Currently (2005-10-17) it will just hold classes and functions
# that are related to pseudopiloting

from RaDisplay import *
from avion import *

SNDDIR='./snd/'

class AcftNotices(RaTabular):
    """A tabular window showing reports and requests from aircraft"""
    def __init__(self, master=None, flights=None):
        """Create a tabular showing aircraft reports and requests"""
        RaTabular.__init__(self, master, label='Notificaciones',
                           position=(120,200), closebuttonhides=True)
        self._last_updated=0.
        self._flights=flights

    def update(self,t):
        """Check whether any new message should be printed"""
        # We need only update this tabular at most once a second
        if t-self._last_updated<1/60./60.:
            return
        
        # Check whether the pilots have anything to report.
        for acft in self._flights:
            for i,report in enumerate(acft.reports):
                if t>report['time']:
                    h=int(t)
                    m=int(60*(t-h))
                    report='%02d:%02d %s %s'%(h,m,acft.name,report['text'])
                    self.insert(END, report)
                    self.notify()
                    del acft.reports[i]
        self._last_updated=t

    def notify(self):
        """Make it obvious to the user that there has been a new notification"""
        import sys
        if sys.platform=='win32':
            import winsound
            try:
                winsound.PlaySound(SNDDIR+'/notice.wav', winsound.SND_NOSTOP|winsound.SND_ASYNC)
            except:
                pass