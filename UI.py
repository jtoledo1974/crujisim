#!/usr/bin/env python
#-*- coding:iso8859-15 -*-
# $Id: banner.py 1145 2006-01-06 16:50:03Z toledo $

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

class Dialog:

    def __init__(self,master,type,transient=True):
    
        dlg=self.dlg=Toplevel()
        if transient: dlg.transient(master)
        content=Frame(dlg)
        buttonbar=Frame(dlg)
        
        content.grid()
        buttonbar.grid(padx=5, pady=5)

        if type=='retry-cancel':
            butretry=Button(buttonbar, text='     Reintentar    ', command=self.retry)
            butcancel=Button(buttonbar,text='      Cancelar      ', command=self.cancel)
            butretry.grid(row=0,column=0, padx=10)
            butcancel.grid(row=0,column=1, padx=10)
        elif type=='accept':
            butaccept=Button(buttonbar, text='     Aceptar    ', command=self.accept, default="active")
            butaccept.grid(row=0,column=0, padx=10)
            dlg.bind("<Return>", lambda event: self.accept())
                
        dlg.protocol("WM_DELETE_WINDOW", self.cancel)
        dlg.focus_set()
        dlg.after_idle(self.set_window_size)
        
        self.dlg=dlg
        self.content=content
        self.master=master
    
    def accept(self):
        self.dlg.destroy()
        self.result = 'accept'
        
    def retry(self):
        self.dlg.destroy()
        self.result = 'retry'
        
    def cancel(self):
        self.dlg.destroy()
        self.result = 'cancel'

    def set_window_size(self):
        window_width = self.master.winfo_reqwidth()
        window_height = self.master.winfo_reqheight()
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        px = (screen_width - window_width) / 2
        py = (screen_height - window_height) / 2
        self.dlg.wm_geometry("+%d+%d" % (px,py))
