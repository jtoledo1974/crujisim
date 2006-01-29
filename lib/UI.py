#!/usr/bin/env python
#-*- coding:iso8859-15 -*-
# $Id: banner.py 1145 2006-01-06 16:50:03Z toledo $

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
from Tix import *
import logging

class Dialog:
    """Standard dialog to be used with Tkinter"""
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

def blank_combo(combo):
    """Remove all items of a GTK combo with a list store model"""
    while len(combo.get_model())>0:
        combo.remove_text(0)

def get_active_text(combobox):
    """Get the current selected text from a GTK combo with a list store model"""
    model = combobox.get_model()
    active = combobox.get_active()
    if active < 0:
        return None
    return model[active][0]

def set_active_text(combobox, text):
    """Set the option of a combobox to the given text if the option exists"""
    model = combobox.get_model()
    for row, i in zip(model, range(len(model))):
        if row[0] == text:
            combobox.set_active(i)
            break

def alert(text, parent=None):
    """Display a GTK dialog with user defined text"""
    import gtk
    dlg=gtk.MessageDialog(parent=parent,
                          flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                          type=gtk.MESSAGE_INFO,
                          buttons=gtk.BUTTONS_CLOSE,
                          message_format=text)
    dlg.set_position(gtk.WIN_POS_CENTER)
    dlg.connect('response',lambda dlg, r: dlg.destroy())
    dlg.run()
    
def focus_next(w):
    """Sends a tab keypress to the widget to force it to cycle the focus"""
    import gtk
    cont = w.parent
    fc = cont.get_focus_chain()
    next = {}
    for (widget,nextwidget) in zip(fc,fc[1:]+[fc[0]]):
        next[widget]=nextwidget
    n = next[w]
    while not n.props.can_focus or not n.props.editable or not n.props.sensitive:
        n = next[n]
    n.grab_focus()

if __name__=='__main__':
    #alert("testing")
    pass
