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
"""Classes useful for designing a radar display"""

from math import *
from Tix import *
import tkFont
import logging
import sys
from FIR import *
from MathUtil import *
from time import time
from math import floor
from twisted.internet import reactor

# Globals

_radialogs={} # List of all dialogs, to avoid duplicates

# Because tkinter will not free the command for the binding when removing
# binding canvas elements, we have to keep track of every binding to make sure
# the the unbind is properly handled, including the funcid
_tag_binds = []
_binds = []

# Constants
IMGDIR='./img/'
CHANGE_WIDTH = 13


def ra_bind(object, widget, sequence, callback):
    """Creates a TK binding and stores information for later deletion"""
    funcid = widget.bind(sequence, callback)
    _binds.append((object, widget, sequence, funcid),)
    
def ra_unbind(object, widget, sequence):
    for (o, w, s, f) in [(o, w, s, f) for (o, w, s, f) in _binds if (o==object and w==widget and sequence==s)]:
        w.unbind(s, f)
        _binds.remove((o, w, s, f))
        
def ra_clearbinds(object):
    for (o, w, s) in [(o, w, s) for (o, w, s, f) in _binds if (o==object)]:
        ra_unbind(o,w,s)

def ra_tag_bind(canvas, tag_or_id, sequence, func):
    """Creates a tag binding and stores information for later deletion"""
    if tag_or_id==None: return
    funcid = canvas.tag_bind(tag_or_id, sequence, func, add=True)
    _tag_binds.append((canvas, tag_or_id, sequence, funcid))
    
def ra_tag_unbind(canvas_remove, tag_remove, sequence_remove):
    for b in _tag_binds[:]:
        [canvas,tag,seq,funcid] = b
        if (tag == tag_remove) and (canvas == canvas_remove) and (sequence_remove == seq):
            canvas.tag_unbind(tag, seq, funcid)
            _tag_binds.remove(b)
            
def ra_cleartagbinds(tag_to_remove):
    # Because we are messing with the list within the iterator,
    # we iterate over a copy of the list (that's what _tag_binds[:] is, a copy)
    for b in _tag_binds[:]:
        [canvas,tag,seq,funcid] = b
        if tag == tag_to_remove:
            try:
                canvas.tag_unbind(tag,seq,funcid)
            except:
                logging.debug('tag_unbind failed with '+str(tag)+','+str(seq)+','+str(funcid))
            _tag_binds.remove(b)

 
class RaFrame:
    """A moveable window inside a radar display"""
    def __init__(self, master, **kw):
        """Construct a moveable, titled frame inside the parent radar display.
        
        Instantiation arguments:
        master -- parent master
        Options:
            label -- text to use on the window title
            closebutton -- Boolean (default True)
            dockbutton -- Boolean (default True)
            closebuttonhides -- Boolean (default False)
        """
        
        self._master=master
        self._kw=kw  # We need to save it for rebuilding in toggle_windowed
        self._closebutton=self._label=None
        self.bd,self.bg,self.fg='gray50','Black','White'
        self._bindings=[]
        self._x,self._y=(0,0)
        self.showed = True


        # Build the frame
        self._build(master, windowed=False, **kw)
        # Place it
        self._place()
        
        
    def _build(self, master=None, windowed=False, **kw):
        """Build the GUI elements, either as a canvas element, or as a toplevel"""
        if not windowed:
            # Build a frame as a Canvas element
            #if kw.has_key('anchor') and kw['anchor']<>'':
            #    kw2 ={anchor:NW}
            #    kw2['anchor'] = kw['anchor']
            self.container =Frame(master,background=self.bd,borderwidth = 1)

            self.top_bar = Frame(self.container,background = 'magenta' ,borderwidth = 1,relief = FLAT,height=10)
            self.top_bar.pack(fill=X,padx=0,pady=0)
            self.windowtitle = Frame(self.container,background=self.bd,borderwidth = 0,relief = FLAT)
            self.windowtitle.pack(fill=X)
            self.contents = Frame(self.container,background = self.bg)
            self.contents.pack(fill=BOTH,expand=1)
            
              
            def bring_foreground(e=None):
                self.container.tkraise()    

            if kw.has_key('label') and kw['label']<>'':
                self._label=Label(self.windowtitle,text=kw['label'],bg = self.bd,foreground=self.fg,font=("Arial","8","bold"))
                self._label.pack(side=LEFT,ipadx = 2)
                i=self._label.bind('<Button-1>',bring_foreground,add="+")
                self._bindings.append((self._label,i,"<Button-1>"),)


            if not kw.has_key('closebutton') or kw['closebutton']:
                self._closebutton=Label(self.top_bar,text='X',background='gray80',foreground=self.fg,width=2,font=("Arial","5","bold"))
                self._closebutton.pack(side=RIGHT,padx=0,pady=0)
#                self._closebutton.place(anchor=E)
                if (self._kw.has_key('closebuttonhides')
                    and self._kw['closebuttonhides']):
                    i=self._closebutton.bind('<Button-1>',self.hide)
                else:
                    i=self._closebutton.bind('<Button-1>',self.close)                    
                self._bindings.append((self._closebutton,i,"<Button-1>"),)
            else:
                self.top_bar.grid_propagate(0)
            # TODO
            # This is causing problems because it's really not well implemented
            # Better not to have to avoid the crashes it creates until it's
            # properly done.
            #if not kw.has_key('dockbutton') or kw['dockbutton']:
            #    self._undockbutton=Label(self.container,text='O',bg=self.bd,fg='Black')
            #    self._undockbutton.pack(side=RIGHT)
            #    i=self._undockbutton.bind('<Button-1>',self.toggle_windowed)
            #    self._bindings.append((self._undockbutton,i,'<Button-1>'),)
            

                
                # Frame dragging
            #self.top_bar.grid(row=1,column=0,padx=2,pady=2,sticky=N+E+S)
            #self.windowtitle.grid(row=2,column=0,padx=2,pady=2,sticky=N+S+W)
            #self.contents.grid(row=3,column = 0,padx=2,pady=2,sticky=N+E+S+W)
            
            def drag_frame(e=None):
                """Move the frame as many pixels as the mouse has moved"""
                self._master.move(self._master_ident,e.x_root-self._x,e.y_root-self._y)
                self._x=e.x_root
                self._y=e.y_root
                


            def drag_select(e=None):
                #if self._label<>None:
                #    i=self._label.bind('<Motion>',drag_frame)
                #    self._bindings.append((self._label,i,'<Motion>'),)
                i=self.top_bar.bind('<Motion>',drag_frame)
                self._bindings.append((self.top_bar,i,'<Motion>'),)
                self._x=e.x_root
                self._y=e.y_root
                self.top_bar.lift()
            def drag_unselect(e=None):
                #if self._label<>None:
                #    self._label.unbind('<Motion>')
                self.top_bar.unbind('<Motion>')
                self.check_limits()

            
            #if self._label<>None:
            #    i=self._label.bind('<Button-2>',drag_select)
            #    j=self._label.bind('<ButtonRelease-2>',drag_unselect)
            #    self._bindings.append((self._label,i,'<Button-2>'),)
            #    self._bindings.append((self._label,j,'<ButtonRelease-2>'),)
            
            g=self.windowtitle.bind('<Button-1>',bring_foreground,add="+")
            h=self.top_bar.bind('<Button-1>',bring_foreground,add="+")
            i=self.top_bar.bind('<Button-1>',drag_select,add="+")
            j=self.top_bar.bind('<ButtonRelease-1>',drag_unselect)
            self._bindings.append((self.windowtitle,g,'<Button-1>'),)
            self._bindings.append((self.top_bar,h,'<Button-1>'),)
            self._bindings.append((self.top_bar,i,'<Button-1>'),)
            self._bindings.append((self.top_bar,j,'<ButtonRelease-1>'),)
            self.windowed=False
        else:
            # Build a frame as a transient toplevel
            t=Toplevel(bg=self.bg)
            t.transient(master)
            t.resizable(0,0)
            if kw.has_key('label'):
                t.title(kw['label'])
            t.protocol('WM_DELETE_WINDOW', self.toggle_windowed)
            
            self.contents=Frame(t,bg=self.bg)
            self.contents.grid(padx=1,pady=1)
            self.container=t
            self.windowed=True
            
    def check_limits(self):
        x_max = self._master.winfo_width()
        y_max = self._master.winfo_height()

        #Make two iterations to garantee complete window recovery
        for i in (0,1):
            
            if self.container.winfo_x() < 0:
                self._x = 1
                self._y = self.container.winfo_y()
                self._place()
                self.container.update_idletasks ()
            if self.container.winfo_x() > (x_max-self.container.winfo_width()):
                self._x = x_max-self.container.winfo_width()
                self._y = self.container.winfo_y()
                self._place()
                self.container.update_idletasks ()
            if self.container.winfo_y() < 0:
                self._x= self.container.winfo_x()
                self._y = 1
                self._place()
                self.container.update_idletasks ()
            if self.container.winfo_y() > y_max-self.container.winfo_height():
                self._x = self.container.winfo_x()
                self._y = y_max - self.container.winfo_height()
                self._place()
                self.container.update_idletasks ()
            

            
    def _place(self):
        # If we are not given any position info, just use 0,0

        if not self._kw.has_key('position'): pos=(0,0)
        else: pos=self._kw['position']
        if not self._kw.has_key('anchor'): anchor=NW
        else: anchor=self._kw['anchor']

        # We reset x and y only if this is the first time we are placing the
        # frame. If the user moved it himself, then use the last known position.
        if self._x==0 and self._y==0:
            (self._x, self._y) = pos
  
        # Currently the master must be a canvas if not windowed
        if not self.windowed:
            self._master_ident = self._master.create_window((self._x, self._y), window=self.container, anchor=anchor)

            
    def configure(self,**ckw):
        if ckw.has_key('position'):
            x,y=ckw['position']
            self._master.coords(self._master_ident,x,y)
            
    def bind(self,event,callback):
        """bind a callback to the RaFrame"""
        def bind_children(wid, event,callback):
            i=wid.bind(event,callback)
            self._bindings.append((wid,i,event),)
            for w in wid.winfo_children():
                bind_children(w, event, callback)
        bind_children(self.contents,event,callback)
        
    def show(self, e=None):
        """Show the RaFrame (to be used after having been hidden)"""
        if self.windowed:
            self.container.deiconify 
        else:
            self._master_ident = self._master.create_window((self._x, self._y),
                window=self.container)
        self._place()
        self.check_limits()
        self.showed=True
            
        
    def close(self,e=None):
        """Close the RaFrame and completely delete it"""
        logging.debug("Raframe.close")
        if (self._kw.has_key('closebuttonhides')
            and self._kw['closebuttonhides']):
            self.hide()
            return
            
        for t,i,ev in self._bindings:
            t.unbind(ev,i)
        self._bindings=[]
        
        if not self.windowed:                
            self._master.delete(self._master_ident)
        self.contents.destroy()
        if self.windowed:
            self.container.destroy()
            
    def hide(self, e=None):
        """Hide the RaFrame, but don't destroy the contents"""
        self._x=self.container.winfo_x()
        self._y=self.container.winfo_y()
        logging.debug("RaFrame.hide")
        if self.windowed:
            self.container.withdraw()
        else:
            self._master.delete(self._master_ident)
        self.showed = False   
    def toggle_windowed(self,e=None):
        self.close()
        self.windowed=not self.windowed
        self._build(master=self._master, windowed=self.windowed, **self._kw)
        self._place()
        
    def conmuta(self, e=None):
        if self.showed: self.hide()
        else: self.show()
        
    def info_w_h(self,e=None):
        """Returns width and heigth of the container in pixels"""
        x1 = self.container.winfo_width()
        y1 = self.container.winfo_height()
        return (x1,y1)

        
        
    def __del__(self):
        # Print a message to make sure we are freing the memory
        logging.debug("RaFrame.__del__")
        
class RaDialog(RaFrame):
    """A frame whith OK and Cancel buttons and optional entries"""
    
    def __init__(self, master, **kw):
        """Create a frame and associate OK and Cancel bindings
        
        Options
            ok_callback -- If defined, a global binding is defined
                to call this function when enter is pressed
            esc_closes -- If True, a global binding is defined
                to close the frame when escape is pressed. Default True
            type -- if 'command' the frame is positioned on the bottom left corner
        """
        logging.debug ("RaDialog.__init__ "+str(kw))
        
        # The frame constructor method will call _build
        RaFrame.__init__(self,master,**kw)
        self._place()
        
    def _build(self, master=None, windowed=False, **kw):
        """Build the RaDialog GUI elements
        
        The dialog need not not know whether it will be built as a canvas
        element or as a toplevel, since it build on top of self.contents
        """
        
        # If there is already a dialog with the same label
        # close the existing one
        if _radialogs.has_key(kw['label']):
            _radialogs[kw['label']].close()
            return
        _radialogs[kw['label']]=self
        
        RaFrame._build(self, master=master, windowed=windowed, **kw)
        
        # Dialog colors
        self._frame_colors={'background':self.bd,
                            'highlightbackground':self.bg,
                            'highlightcolor':'Black'}
        self._label_colors={'background':self.bd,
                            'highlightbackground':self.bd,
                            'highlightcolor':'Black',
                            'foreground':self.bg,
                            'activebackground':self.bd,
                            'activeforeground':self.fg,
                            'disabledforeground':''}
        self._button_colors={'background':self.bd,
                            'highlightbackground':self.bg,
                            'highlightcolor':self.bd,
                            'foreground':self.fg,
                            'activebackground':self.bg,
                            'activeforeground':self.fg,
                            'disabledforeground':''}
        self._entry_colors={'background':self.fg,
                            'highlightbackground':self.bg,
                            'highlightcolor':'Black',
                            'foreground':self.bg,
                            'selectbackground':self.bg,
                            'selectforeground':self.fg,
                            'insertbackground':self.bd,
                            'insertwidth':5,
                            'relief':FLAT,
                            'borderwidth':0,
                            'insertborderwidth':0}
        
        # Dialog elements
        self.contents.configure(**self._frame_colors)
        f0 = Frame(self.contents, **self._frame_colors) # Text
        f0.pack(side=TOP, pady=1, fill=BOTH)        
        f1 = Frame(self.contents, **self._frame_colors) # Dialog contents
        f1.pack(side=TOP, pady=1, fill=BOTH)
        #f2a = Frame(self.contents, **self._frame_colors) # aux frame
        #f2a.pack(side=BOTTOM, fill=BOTH)

        #f2 = Frame(f2a, **self._frame_colors) # Default dialog buttons
        #f2.pack(side=RIGHT, fill=BOTH)
        self.botom_bar = Frame(self.container,background=self.bd,borderwidth = 1,relief = FLAT)
        self.botom_bar.pack(fill=BOTH,side=BOTTOM)
        f2 = self.botom_bar 
        
        if kw.has_key('text'):
            l=Label(f0,text=kw['text'], **self._label_colors)
            l.pack(side=LEFT)        
        but_accept = Button(f2, text="ACEPTAR",font = ("Arial","6","bold"),width=9,height=1,default='active', **self._button_colors)

        but_accept['command'] = self.accept
        if kw.has_key('ok_callback'):
            #Label(f2,text=' ', **self._label_colors).pack(side=LEFT)
            but_cancel = Button(f2, text="CANCELAR",font = ("Arial","6","bold"),width=9,height=1, **self._button_colors)
            but_cancel.pack(side=RIGHT)
            but_cancel['command'] = self.close
        but_accept.pack(side=RIGHT,ipady=1)    
            # Dialog entries
        if kw.has_key('entries'):
            self.entries={}
            first=None
            spacer=None
            for i in kw['entries']:
                e=i.copy()  # Otherwise next time we get here we would have
                            # modified the entry and we would not have a label,
                            # for instance.
                e_label=e['label']
                entry=None
                Label(f1,text=e_label,**self._label_colors).pack(side=LEFT)
                del e['label']
                if e.has_key('def_value'):
                    def_value=e['def_value']
                    del e['def_value']
                else:
                    def_value=''
                if e.has_key('values'):
                    import Tix
                    entry=Tix.ComboBox(f1,editable=True)
                    maxwidth=0
                    for i in e['values']:
                        if len(i)>maxwidth: maxwidth=len(i)
                        entry.append_history(i)
                    entry.entry['width']=maxwidth
                    entry.slistbox.listbox.configure(width=maxwidth+1,
                                                     height=len(e['values']),
                                                     bg=self.bg,
                                                     fg=self.fg)
                    # We need the master since we can't set the color of the
                    # frame containing the entry and the arrow
                    entry.entry.master['bg']=self.bg
                    entry.label.configure(**self._label_colors)
                    entry.entry.configure(**self._entry_colors)
                    entry.slistbox.configure(**self._frame_colors)
                    entry.arrow.configure(**self._button_colors)
                    entry['value']=def_value
                else:
                    e.update(self._entry_colors)
                    entry=Entry(f1,**e)
                    entry.insert(END,def_value)
                entry.pack(side=LEFT)
                if first==None:  
                    first=entry
                if entry:  # Store the entry widgets to make them available
                    self.entries[e_label]=entry
                spacer=Label(f1,text=' ',**self._label_colors)
                spacer.pack(side=LEFT)
            first.focus_set()  # Place the focus on the first entry
            spacer.destroy()  # The last spacer is unnecesary
        else:
            self.entries=None
            
            # Global bindings
        self._ok_callback=self._esc_closes=False
        i=self._master.bind_all("<Return>",self.accept)
        j=self._master.bind_all("<KP_Enter>",self.accept)
        self._bindings.append((self._master,i,'<Return>'),)
        self._bindings.append((self._master,j,'<KP_Enter>'),)
        if kw.has_key('ok_callback'):
            self._ok_callback=kw['ok_callback']
            
        if not kw.has_key('esc_closes') or kw['esc_closes']:  
            i=self._master.bind_all("<Escape>",self.close)
            self._bindings.append((self._master,i,'<Escape>'),)
            self._esc_closes=True
            
    def _place(self):
        """Place the dialog on the lower left corner or the master"""
        RaFrame._place(self)
        if self._kw.has_key('position') or (self._x<>0 and self._y<>0):
            # If the user already defined a position or has previously moved
            # this frame, don't go any further
            return
        x_padding=y_padding=20
        command_window_height=20
        self.container.update_idletasks() # The geometry manager must be called
                                          # before we know the size of the widget
        x=self.container.winfo_width()/2+x_padding
        y=self._master.winfo_height()-self.container.winfo_height()/2-y_padding-command_window_height
        self.configure(position=(x,y))
        
    def accept(self,e=None):
        """Call the callback and check for results
        
        The callback function should returns False
        if the dialog has not validated correctly
        """
        if self._ok_callback and self.entries:
            # If entries were created we send them as an
            # argument to allow for validation
            if self._ok_callback(entries=self.entries)==False:
                return
        elif self._ok_callback:
            self._ok_callback()        
        self.close()
        
    def close(self, e=None):
        del _radialogs[self._label['text']]
        RaFrame.close(self,e)

             
class RaClock(RaFrame):
    """An uncloseable, moveable frame with adjustable text inside"""
    
    def __init__(self, master, **kw):
        """Create an unclosable frame displaying the clock time
        
        SPECIFIC OPTIONS
        time -- a text string to display
        """
        def_opt={'position':(5,5), 'anchor':NW, 'closebutton':False, 'undockbutton':False}
        def_opt.update(kw)
        # The frame constructor method will call _build
        RaFrame.__init__(self, master, **def_opt)
        
    def _build(self, master=None, windowed=False, **kw):
        if windowed:
            def_opt={'label':'Reloj'}
            def_opt.update(kw)
        else:
            def_opt=kw
        RaFrame._build(self, master=master, windowed=windowed, **def_opt)
        self._time=Label(self.contents,
                    font=('Courier','20','bold'),
                    foreground="#%04x%04x%04x" % (63736,46774,7453),    #Very yellowed orange color
                    background='black')                                 
        self._time.grid(padx=5,pady=2)
        
    def configure(self,**options):
        RaFrame.configure(self,**options)
        if options.has_key('time'):
            self._time['text']=options['time']
            
class RaTabular(RaFrame):
    """Generic frame containing tabular info"""
        


    def __init__(self, master, **kw):
        def_opt={'position':(500,222),}
        def_opt.update(kw)
        self._items=[]  # We need to make a copy of the items to rebuild
                        # the list
        # The frame constructor method will call _build
        self.elements = IntVar()
        self.entry=None
        self.min_width = 0
        self.max_width = 0
        self.min_height = 0
        self.max_height = 0
        RaFrame.__init__(self, master=master, **def_opt)
        
    def _build(self, master=None, windowed=False, **kw):
        import Tix
        RaFrame._build(self, master=master, windowed=windowed, **kw)
        self.n_elementos=Label(self.windowtitle,bg = self.bd,foreground=self.fg,font=("Arial","6","bold"),textvariable=self.elements,relief=GROOVE,borderwidth = 2)
        self.n_elementos.pack(side=RIGHT,padx=0,ipadx=4)
        self.legend=Label(self.contents,font="Courier 8",bg=self.bg,fg=self.fg,height = 0)
        self.legend.pack(padx=7,side=TOP,anchor=NW)
        self._slist=Tix.ScrolledListBox(self.contents,relief = FLAT,borderwidth= 0,highlightthickness =0)
        self._list_colors={'background':self.bg,
                            'highlightbackground':self.bg,
                            'highlightcolor':self.bg,
                            'foreground':self.fg,
                            'selectbackground':self.bg,
                            'selectforeground':'green'}
        #The widget listbox is "encapsulated" by ScrolledListBox
        self.list=self._slist.listbox
        self.list.configure(**self._list_colors)
        self.list.configure(relief = FLAT,)
        #self.list.configure(height=6, width=30)
        self._scroll_bar_configuration={'activebackground':self.bd,
                                        'borderwidth':0,
                                        'width':10,
                                        'activerelief':FLAT,
                                        'troughcolor':self.bd,
                                        'elementborderwidth':0,
                                        'background':self.bg}
        self._slist.hsb.configure(**self._scroll_bar_configuration)
        self._slist.vsb.configure(**self._scroll_bar_configuration)
        for i, elements in enumerate(self._items):
            self.list.insert(i, *elements)

        self._slist.pack(fill=BOTH,expand=1,padx=5,pady=5)
        j=self.n_elementos.bind('<Button-1>',self.set_visible_rows,add="+")
        self._bindings.append((self.n_elementos,j,'<Button-1>'),)
        self.adjust()
        

        
    def set_visible_rows(self,e=None):
        """Show a dialog to allow the user to set the number of visible rows"""
        n_rows=StringVar()
        frame_colors={'background':self.bd,
                            'highlightbackground':self.bd,
                            'highlightcolor':self.bd}
        label_colors={'background':self.bd,
                            'highlightbackground':self.bd,
                            'highlightcolor':self.bd,
                            'foreground':'yellow',
                            'activebackground':self.bd,
                            'activeforeground':self.bd,
                            'disabledforeground':'',
                            'anchor':SE}
        button_colors={'background':self.bd,
                            'highlightbackground':self.bd,
                            'highlightcolor':self.bd,
                            'foreground':self.fg,
                            'activebackground':self.bd,
                            'activeforeground':self.fg,
                            'disabledforeground':''}
        entry_colors={'background':self.bd,
                            'highlightbackground':self.bd,
                            'highlightcolor':self.bd,
                            'foreground':'yellow',
                            'selectbackground':self.bd,
                            'selectforeground':'yellow'}


        def set_rows(e=None,entries=None):
            try:
                self.max_height=int(n_rows.get())
                self.adjust(max_height=self.max_height)
            except:
                pass
            #self.visible_rows=int(n_rows.get())
            

            
        
        if self.entry==None:
            self.entry=ComboBox(self.windowtitle,editable=True)
            self.entry.configure(bg = self.bd,
                                 relief=GROOVE,borderwidth = 0,
                                 height=5,
                                 width=6,
                                 command=set_rows)
            e_entry=self.entry.subwidget_list['entry']
            e_entry.configure(bg = self.bd,
                                   foreground=self.fg,
                                   font=("Arial","7","bold"),
                                   relief=FLAT,width=2,
                                   bd=0,
                                   textvariable=n_rows,
                                   justify = RIGHT)
            e_list=self.entry.subwidget_list['slistbox']
            e_list.configure(bg = self.bd,
                                   relief=FLAT,width=3)
            scroll_bar_configuration={'activebackground':self.bd,
                                'borderwidth':0,
                                'width':6,
                                'activerelief':FLAT,
                                'bg':self.bd}
            e_list.vsb.configure(**self._scroll_bar_configuration)
            e_arrow=self.entry.subwidget_list['arrow']
            e_arrow.configure(bg=self.bd,bd=0,fg=self.fg,height=10)
            e_frame=self.entry.children['frame']
            e_frame.configure(bg=self.bd,bd=0)
            e_shell=self.entry.children['shell']
            e_shell.configure(bg=self.bd,bd=0)
            n_rows.set(str(self.max_height))

            
            for i in range(0,21):
                self.entry.add_history(str(i))

            
            self.entry.entry.master['bg']=self.bd
            self.entry.label.configure(**label_colors)
            self.entry.entry.configure(**entry_colors)
            self.entry.slistbox.configure(**frame_colors)
            self.entry.arrow.configure(**button_colors)
            self.entry.label.configure(font=(("Arial","7",)))
            self.entry.label.configure(text="MAX:")
            self.entry.pack(side=RIGHT)

        else:
            self.entry.destroy()
            self.entry=None
            
        
        #self.entry_rows=Entry(self.windowtitle,bg=self.bd,
        #x1=self.container.winfo_x()+self.container.winfo_width()/2
        #y1=self.container.winfo_y()+self.container.winfo_height()/2
        #entries=[]
        #entries.append({'label':'','width':5,'def_value':self.visible_rows})
        #RaDialog(self.canvas,position=(x1,y1),label='FILAS',ok_callback=set_rows,entries=entries)

    def insert(self, index, *elements):
        """Insert a list item (use text='text to show')"""
        self.list.insert(index, *elements)
        # TODO we should deal with more Tk constants here.
        if index==END:
            index=len(self._items)
        self._items.insert(index, elements)
        self.elements.set(self.list.size())
        
    def delete(self,index):
        """Delete a list item"""
        self.list.delete(index)
        self.elements.set(self.list.size())

        
    def adjust(self,min_height=-1, min_width=-1, max_height=-1, max_width=-1):
        """Reduce the size of the list to the minimum that fits
        or whatever is given as parameters
        max_height = 0 means unlimited"""
        if min_height == -1:min_height = self.min_height
        else: self.min_height = min_height
        if min_width == -1:min_width=self.min_width
        else: self.min_width = min_width
        if max_height == -1:max_height=self.max_height
        else: self.max_height = max_height
        if max_width == -1: max_width = self.max_width
        else: self.max_width = max_width

            
        self.elements.set(self.list.size())
        items = self.list.get(0,END)
        max_item_size = max([len(i) for i in items]+[0])
        if self.min_width == 0: mw = max_item_size
        else: mw = max(self.min_width,max_item_size)
        if self.min_height == 0: mh = self.list.size()
        else: mh = max(self.min_height,len(i))
        
        #mw = max((min([len(i) for i in items]+[0]),self.min_width))
        #mh = max((self.list.size(), self.min_height))
        if self.max_width != 0:
            if mw > self.max_width: mw = self.max_width
            
        if self.max_height != 0:
            if mh > self.max_height: mh = self.max_height 
        #if mw>self.max_width and self.max_width != 0: mw = self.max_width
        #if mh>self.max_height and self.max_height != 0: mh= self.max_height
        self.list.configure(height=mh, width=mw)

        

        


class SmartColor(object):
    """Given a color string and a brightness factor calculates the output color"""
    
    winfo_rgb = None  # This function will be set when Tkinter is initialized
    
    def __init__(self,color='white',intensity=1.0):
        object.__setattr__(self,'color', color)  # displayed  color
        object.__setattr__(self,'basecolor', color)  # master color
        self.intensity = intensity  #Item color intensity
        self.set_intensity(intensity)
            
    def get(self): return self.color
    
    def set(self, c):
        self.basecolor = c
        self.set_intensity(self.intensity)
        
    def get_basecolor(self): return self.basecolor
                 
    def set_intensity(self, factor):
        """Returns a color object with the intensisty changed and string representation"""
        self.intensity = factor
        color = self.basecolor
        
        if color == '' or factor==1:
            self.color = self.basecolor
            return  # If no correction or transparent, simply set the base color
    
        (red, green, blue) = self.winfo_rgb(color)
        
        rgb1=[red,green,blue]
        hsv = self.RGBtoHSV(rgb1,65535.0)
        v = hsv[2]*factor
        if v > 1.0: v = 1.0
        hsv[2] = v
        rgb2=self.HSVtoRGB(hsv,65535.0)
        
        r1=int(rgb2[0])
        g1=int(rgb2[1])
        b1=int(rgb2[2])
    
        self.color = self.rgb_to_string((r1,g1,b1))

    def RGBtoHSV(self, rgb,factor=1):
        """Returns HSV components from rgb (R,G,B)"""
        r1 = float(rgb[0])/factor
        g1 = float(rgb[1])/factor
        b1 = float(rgb[2])/factor
        rgb1=[r1,g1,b1]
    
        max_c = max(rgb1)
        min_c = min(rgb1)
        delta = max_c - min_c
        v = max_c
    
        if delta == 0.0:
            s = 0.0
            h = 0.0
            return [h,s,v]
        else:
            s = delta / max_c
            del_R = ( ( ( max_c - r1) / 6.0 ) + ( delta / 2.0 ) ) / delta
            del_G = ( ( ( max_c - g1) / 6.0 ) + ( delta / 2.0 ) ) / delta
            del_B = ( ( ( max_c - b1) / 6.0 ) + ( delta / 2.0 ) ) / delta
        if r1 == max_c:
            h = del_B - del_G
        elif g1 == max_c:
            h = (1.0/3.0)+del_R - del_B
        elif b1 == max_c:
            h = (2.0/3.0)+del_G - del_R
            
        if h<0.0: h+=1.0
        if h>1.0: h-=1.0
        
        return [h,s,v]
    
    def HSVtoRGB(self, hsv,factor = 1):
        """Returns RGB components scaled by factor, from hsv"""
        [h,s,v]=hsv
        if s==0:
            var_r = v
            var_g = v
            var_b = v
    
        else:
            var_h = h*6.0
            if var_h == 6.0: var_h = 0
            var_i = floor(var_h)
            var_1 = v * ( 1 - s)
            var_2 = v * ( 1 - s * ( var_h - var_i ) )
            var_3 = v * ( 1 - s * ( 1 - ( var_h - var_i ) ) )
            
            if var_i == 0.0:
                var_r = v
                var_g = var_3
                var_b = var_1
            elif var_i == 1.0:
                var_r = var_2
                var_g = v
                var_b = var_1
            elif var_i == 2.0:
                var_r = var_1
                var_g = v
                var_b = var_3
            elif var_i == 3.0:
                var_r = var_1
                var_g = var_2
                var_b = v
            elif var_i == 4.0:
                var_r = var_3
                var_g = var_1
                var_b = v
            else:
                var_r = v
                var_g = var_1
                var_b = var_2
            
        var_r = var_r * factor
        var_g = var_g * factor
        var_b = var_b * factor
            
        return [var_r,var_g,var_b]
        
    def rgb_to_string(self, rgb):
        """Returns a string representing de RGB color passed in rgb"""
        return "#%04x%04x%04x" % rgb
   

class RaBrightness(RaFrame):
    """Brightness control frame"""
    def __init__(self, master, callback, **kw):
        #def_opt={'position':(512,575)}
        #def_opt.update(kw)
        self.callback = callback
        # The frame constructor method will call _build
        RaFrame.__init__(self, master=master, closebuttonhides=True, **kw)
       
        
    def _build(self, master=None, windowed=False, **kw):

        RaFrame._build(self, master=master, windowed=windowed,  **kw)
        #self.contents["bg"] = self.bd
        #self.contents.pack(fill=BOTH,expand=1)
 
        gvar = DoubleVar()  # General
        tvar = DoubleVar()  # Tracks
        mvar = DoubleVar()  # Maps
        lvar = DoubleVar()  # LADs
        self.scale_colors={'background':self.bd,
                            'highlightbackground':self.bd,
                            'highlightcolor':self.bd,
                            'foreground':self.fg,
                            'troughcolor':self.bd}
                            #'selectbackground':self.bd,
                            #'selectforeground':self.fg}
        cb = self.callback            
        def changed(*args):
            A=(1.0-0.35)/25
            B=1.0
            cb({"GLOBAL":A*gvar.get()+B, "TRACKS":A*tvar.get()+B,
                      "MAP": A*mvar.get()+B, "LADS":A*lvar.get()+B})
            
        for t,v in (("G",gvar), ("P",tvar),
                    ("M",mvar), ("L",lvar)):
            f = Frame(self.contents, background=self.bd)
            l = Label(f,text=t,background=self.bd,fg=self.fg)
            v.set(0)
            v.trace("w", changed)
            w = Scale(f, variable = v)
            l.pack(side=TOP)
            w.pack(side=BOTTOM,fill=BOTH)
            f.pack(side=LEFT)
            w.configure(**self.scale_colors)
            w.configure(showvalue=1, sliderlength=20, from_=50, to=-25, resolution=1, variable = v)
        del(self.callback)
    
class VisTrack(object): # ensure a new style class
    """Visual representation of a radar track on either a pseudopilot display
    or a controller display"""
    
    allitems = [ 'cs','alt','rate','cfl','gs','mach','wake','spc','echo','hdg','pac','vac']
    timer_id = None  # Whenever there are timer based callbacks pending, this is set
    timer_callbacks = []  # List of timer based callbacks and args
    ON, OFF = True, False  
    timer_state = ON  # Toggles when there are timers set between ON and OFF
    ASSUMED_COLOR = 'green'
    NONASSUMED_COLOR = 'gray'
    
    def __init__(self, canvas, message_handler, do_scale, undo_scale):
        """Construct a radar track inside the parent display.
        
        Instantiation arguments:
        canvas -- parent canvas
        message_handler -- function that will deal with events generated by the track
        do_scale -- scaling function
        undo_scale -- unscaling function """
        
        self._c=canvas
        self._message_handler=message_handler
        self.do_scale = do_scale
        self.undo_scale = undo_scale
        
        # Defaults
        
        # Track attributes
        self._item_refresh_list = []  # List of label items that need to be refreshed
        # Set the default but don't trigger a redraw
        object.__setattr__(self,'visible',False)
        object.__setattr__(self,'mode', 'pp')
        object.__setattr__(self,'label_format', 'pp')
        object.__setattr__(self,'selected', False)
        object.__setattr__(self,'assumed',False)
        object.__setattr__(self,'plot_only',False)
        object.__setattr__(self,'pac',False)
        object.__setattr__(self,'vac',False)
        
        object.__setattr__(self,'x',0)  # Screen coords
        object.__setattr__(self,'y',0)
        object.__setattr__(self,'wx',0)  # World coords
        object.__setattr__(self,'wy',0)
        object.__setattr__(self,'intensity',1.0)
        self.future_pos = []  # List of future positions. Used for STCA calculations
        self.cs='ABC1234'  # Callsign
        self.mach=.82
        self.gs=250
        self.ias=200
        self.ias_max=340
        self.wake='H'
        self.echo='KOTEX'  # Controller input free text (max 5 letters)
        self.hdg=200
        self.track=200  # Magnetic track
        self.alt=150
        self.draw_cfl=False  # Whether or not to draw the current cfl
        self.cfl=200
        self.pfl=350
        self.rate=2000  # Vertical rate of climb or descent
        self.orig='LEMD'
        self.dest='LEBB'
        self.type='B737'
        self.radio_cs='IBERIA'
        self.rfl=330       
        self.color = SmartColor('gray')
        self.selected_border_color = SmartColor('yellow')
        
        self._last_t = 0  # Last time the radar was updated
        
        # Plot attributes
        self.plotsize=3
        self._pitem = None
        
        # Plot history
        self._h = []  # List of previous positions in real coord (not screen)
        
        # Label
        self._l = self.Label(self)
        object.__setattr__(self,'l_font_size',11)
        self._l_font = tkFont.Font(family="Helvetica",size=self.l_font_size)
        self.label_heading = 117  # Label heading
        self.label_radius = 30  # Label radius
        # lxo and lyo are the offsets of the label with respect to the plot
        self.label_xo = self.label_radius * sin(radians(self.label_heading))
        self.label_yo = self.label_radius * cos(radians(self.label_heading))
        # lx and ly are the actual screen coord of the label
        self.label_x = self.x + self.label_xo
        self.label_y = self.y + self.label_yo
        self.label_width = 0
        self.label_height = 0
        # Alternative versions of the label screen coordinates to try them out
        # while performing label separation
        self.label_x_alt = self.label_x
        self.label_y_alt = self.label_y
        self.label_heading_alt = self.label_heading
        # Find the end of the leader line (it starts in the plot)
        self._ldr_x = self.label_x
        self._ldr_y = self.label_y + 10
        self._lineid = None
        object.__setattr__(self,'flashing',False)
        self.auto_separation=True
        self.last_rotation = 0  # Keeps the serial number of the last rotation event
                                # so that auto rotation will try to move the last manually
                                # moved label last.
        
        # Speed vector
        self.speed_vector=(0,0)  # Final position of the speed vector in screen coords
        object.__setattr__(self,'speed_vector_length',0.)  # Length in minutes
        self._svid=None
            
        self.redraw()
        
    def configure(self,**kw):
        """Configure track options"""
        if kw.has_key('position'):
            x,y=kw['position']
            self.coords(x,y)
            
    def coords(self,x,y,t):
        """Reposition the track using screen coordinates"""
        
        if not self.visible:
            return
            
        s=str(self)
        dx,dy=x-self.x,y-self.y  # Calculate delta
        # Store the position in history if there has been a radar
        # update since the last one (more than five seconds ago)
        # TODO: The last radar update should be stored in a future radar
        # display class, rather than here.
        if t!=None and t>self._last_t+5/60./60.:
            while (len(self._h)>=6): self._h.pop()
            rx,ry=self.undo_scale((x,y))
            self._h.insert(0,(rx,ry))
            self._last_t=t
            
        self.x,self.y=x,y  # New position
        
        # Label items refresh
        for i in self._item_refresh_list:
            self._l.refresh(i)
        self._item_refresh_list=[]
        # Move moveable elements        
        self._c.move(s+'move',dx,dy)
        # Update position variables:
        self.label_x += dx
        self.label_y += dy
        self._ldr_x += dx
        self._ldr_y += dy
        # Recreate history points (a simple move wouldn't take scale into account)
        self.redraw_h()
        # Same with speed vector
        self.redraw_sv()
        
        # Raise all elements
        self._c.lift(s+'track')
        self._c.lift(s+'plot')
        
    def delete(self):
        """Delete the visual track and unbind all bindings"""
        self.delete_p()
        self.delete_h()
        self.delete_sv()
        self.delete_l()
        
    def redraw(self):
        """Draw the visual track with the current options"""
        
        if not self.visible:
            self.delete()
            return
            
        self.redraw_p()  # Plot
        self.redraw_h()  # History
        self.redraw_sv() # Speed vector
        
        # Leader and label
        if self.plot_only:
            self.delete_l()
        else:
            self.redraw_l()
            
        self._c.addtag_withtag('track',str(self)+'track')
        self._c.lift(str(self)+'hist')
        self._c.lift(str(self)+'sv')
        self._c.lift(str(self)+'leader')
        self._c.lift(str(self)+'label')
        self._c.lift(str(self)+'plot')
    
    def refresh(self):
        """Reconfigure VisTrack items with current options
        
        Redrawing is expensive, particularly the label text
        because of everything related to fonts.
        Refreshing updates things like color"""
        if not self.visible:
            return
        # TODO Currently we are only refreshing label items
        for i_name in self.allitems:
            self._l.refresh(i_name)

    def delete_p(self):
        """Delete the visual plot and unbind bindings"""
        if self._pitem:  # Delete old plot
            # Remove bindings
            ra_cleartagbinds(self._pitem)
            # Delete the canvas item
        self._c.delete(self._pitem)
        
    def redraw_p(self):
        """Draw the visual plot with the current options"""
        self.delete_p()
        size=self.plotsize
        x,y=self.x,self.y
        s=str(self)
        if self.assumed:
            size=size+1 # Assumed plots are a litle bigger to appear the same size
            self._pitem = self._c.create_polygon(x-size,y,x,y-size,x+size,y,x,y+size,x-size,y,
                                              outline=self.color.get(),fill='',
                                              tags=(s+'move',s+'color',s+'track',s+'plot'))
            
            
        else:
            self._pitem = self._c.create_polygon(x-size,y-size,x-size,y+size,x+size,y+size,
                                              x+size,y-size,x-size,y-size,
                                              outline=self.color.get(),fill='',
                                              tags=(s+'move',s+'color',s+'track',s+'plot'))
            
        def plot_b1(e=None):
            self._message_handler(self,'plot','<Button-1>',None,e)
        def plot_b3(e=None):
            self.plot_only=not self.plot_only
            
            # (Re)Do the bindings
        ra_tag_bind(self._c,self._pitem,'<Button-1>',plot_b1)
        ra_tag_bind(self._c,self._pitem,'<Button-3>',plot_b3)
        
    def delete_h(self):
        """Delete this track's history plots"""
        self._c.delete(str(self)+'hist')
    def redraw_h(self):
        """Draw the history with the current options"""
        self.delete_h()
        for (rx,ry) in self._h:
            (h0,h1) = self.do_scale([rx,ry])
            self._c.create_rectangle(h0,h1,h0+1,h1+1,outline=self.color.get(),
                                     tags=(str(self)+'hist',str(self)+'color',
                                           str(self)+'track'))
            
    def delete_sv(self):
        """Delete the track's speed vector"""
        # Speed vector
        s=str(self)
        if self._svid!=None: self._c.delete(self._svid)
    def redraw_sv(self):
        """Redraw this track's speed vector"""
        self.delete_sv()
        if not self.visible: return
        st=str(self)
        speed_vector = s((self.wx,self.wy),pr((self.speed_vector_length * self.gs,self.track)))
        screen_sv = self.do_scale(speed_vector)
        (sx,sy) = screen_sv
        
        self._svid=self._c.create_line(self.x, self.y, sx, sy, fill=self.color.get(),
                           tags=(st+'speedvector',st+'move',st+'color',st+'track'))
    def delete_l(self):
        c=self._c
        s=str(self)
        
        if (self._lineid):
            ra_cleartagbinds(self._lineid)
        self._lineid = None
        
        # Delete old label, leader and selection box
        c.delete(s+'selection_box')
        c.delete(s+'leader')
        self._l.delete()
        
    def redraw_l(self):
        """Draw the leader and label of the track using current options"""
        # Helper variables
        c=self._c
        cl=self.color.get()
        s=str(self)
        lf = self._l_font
        
        # Delete old label, leader and selection box
        self.delete_l()
        
        if not self.visible: return
        
        # Label text
        self._l.redraw()
        new_label_x = self.x + self.label_radius * sin(radians(self.label_heading))
        new_label_y = self.y + self.label_radius * cos(radians(self.label_heading))
        self.reposition_label(new_label_x, new_label_y)
        lw = self.label_width
        lh = self.label_height
        lx = self.label_x
        ly = self.label_y
        
        # Selection box
        if self.selected:
            c.create_rectangle(lx, ly, lx + lw, ly + lh, outline=self.selected_border_color.get(),
                               tags=(s+'move',s+'label',s+'track', s+'selection_box'))
        # Leader line
        id=c.create_line(self.x, self.y, self._ldr_x, self._ldr_y, fill=self.color.get(),
                      tags=(s+'move',s+'color',s+'track',s+'leader'))
        self._lineid=id   
        ra_tag_bind(c,self._lineid,"<Button-1>",self.rotate_label)
        ra_tag_bind(c,self._lineid,"<Button-3>",self.counter_rotate_label)
        
    def rotate_label(self, e=None):
        [x,y] = (self.x,self.y)
        self.auto_separation = True
        self.label_heading += 90.0
        self.label_radius = self.l_font_size*3
        new_label_x = x + self.label_radius * sin(radians(self.label_heading))
        new_label_y = y + self.label_radius * cos(radians(self.label_heading))
        self.reposition_label(new_label_x, new_label_y)
        try:  # In case this function was not called by a gui event
            self.last_rotation = e.serial
            self._message_handler(self,'leader','<Button-1>',None,e)
        except: pass
        
    def counter_rotate_label(self, e=None):
        #if e != None:
        #        self.last_lad = e.serial
        [x,y] = (self.x,self.y)
        self.auto_separation = True
        self.label_heading -= 90.0
        self.label_radius = self.l_font_size*3
        new_label_x = x + self.label_radius * sin(radians(self.label_heading))
        new_label_y = y + self.label_radius * cos(radians(self.label_heading))
        self.reposition_label(new_label_x, new_label_y)
        try:  # In case this function was not called by a gui event
            self.last_rotation = e.serial
            self._message_handler(self,'leader','<Button-3>',None,e)
        except: pass
     
    def label_coords(self,newx,newy):
        """Repositions the label given new screen coordinates"""
        dx = newx - self.label_x
        dy = newy - self.label_y
        self.label_x += dx
        self.label_y += dy
        self.label_xo += dx
        self.label_yo += dy
        self._c.move(str(self)+'label', dx, dy)
        # Leader line
        self._ldr_y = self.label_y + 10
        if (self.label_x - self.x) > 0:
            self._ldr_x = self.label_x
        else:
            self._ldr_x = self.label_x + self.label_width
        ldr_x_offset,ldr_y_offset = self._ldr_x-self.x, self._ldr_y-self.y
        self.label_heading = 90.0-degrees(atan2(ldr_y_offset, ldr_x_offset))
        self._c.coords(str(self)+'leader',self.x,self.y,self._ldr_x,self._ldr_y)
                    
    def reposition_label(self, newx, newy):
        """Repositions the label based on the new end of the leader line"""
        #self._l.reformat()  # Make sure we have the current width
        (x,y) = self.x,self.y
        ldr_x_offset = newx - x
        ldr_y_offset = newy - y
        # l_xo and lyo are the offsets of the label with respect to the plot
        if ldr_x_offset > 0.:  
            new_l_x = x+ldr_x_offset
            new_l_y = y+ldr_y_offset -10
        else:
            new_l_x = x+ldr_x_offset - self.label_width
            new_l_y = y+ldr_y_offset -10
        self.label_heading = 90.0-degrees(atan2(ldr_y_offset, ldr_x_offset))
        self.label_radius = sqrt(ldr_y_offset**2+ldr_x_offset**2)
        self._c.coords(str(self)+'leader',self.x,self.y,newx,newy)
        
        dx=new_l_x-self.label_x
        dy=new_l_y-self.label_y
        self.label_x += dx
        self.label_y += dy
        self.label_xo += dx
        self.label_yo += dy
        self._c.move(str(self)+'label', dx, dy)
        
        (self._ldr_x, self._ldr_y)=(newx,newy)
        
    def add_timer_callback(self, f, *kw):
        """Callbacks passed as arguments will be called within the next 500ms"""
        VisTrack.timer_callbacks.append((f, kw))
        
        def timer():
            """Calls each of the callbacks that have been set for this event"""
            tc = self.timer_callbacks
            # Reset the timer so that the callbacks may set up new timer
            # callbacks if required
            VisTrack.timer_callbacks = []
            VisTrack.timer_id = None
            VisTrack.timer_state = not VisTrack.timer_state
            
            if self.timer_state == VisTrack.OFF:
                # Force execution of the timer to make sure
                # VisTrack.timer_state will end up in state ON 
                self.add_timer_callback(lambda: True)
                
            # Call callbacks            
            for f, kw in tc:
                f(*kw)
        
        if not VisTrack.timer_id:
            VisTrack.timer_id = self._c.after(500,timer)
        
    def __setattr__(self,name,value):
        """Capture attribute setting so as to trigger functionality"""
        # Save the old value
        try: oldvalue = self.__dict__[name]
        except: oldvalue = None
        
        object.__setattr__(self,name,value) # This actually sets the attributes
        
        # The TkFont class has a broken eq method, so we can't compare it
        if name=='_l_font' or value==oldvalue or name=='_lineid':
            return
        elif name in ['x','y']:
            (wx,wy) = self.undo_scale((self.x,self.y))
            object.__setattr__(self,'wx',wx)
            object.__setattr__(self,'wy',wy)
        elif (name in self.allitems) and self.visible:
            self._item_refresh_list.append(name)
            # When alt reaches cfl, cfl must be cleared
            if name=='alt': self._item_refresh_list.append('cfl')
            if name=='cfl': self.draw_cfl = True
        elif name in ['wx','wy']:
            (x,y) = self.do_scale((self.wx,self.wy))
            object.__setattr__(self,'x',x)
            object.__setattr__(self,'y',y)            
        elif name=='assumed' and self.visible:
            if value: self.color.set(self.ASSUMED_COLOR)
            else:  self.color.set(self.NONASSUMED_COLOR)
            self._l.cs.color.set(self.color.get_basecolor())
            self.redraw()
        elif name=='mode':
            if value=='pp': self.label_format='pp'
            elif value=='atc': self.label_format='atc'
        elif name=='speed_vector_length':
            self.redraw_sv()
        elif name=='l_font_size':
            if self.auto_separation: self.label_radius=value*3
            self.redraw_l()
        elif name in ['selected', 'label_format','pac','vac'] \
           and self.visible:
            self.redraw_l()
            if name in ['pac','vac'] and value==True and self.plot_only:
                self.plot_only=False
        elif name in ['plot_only','visible']:
            self.redraw()
        elif name=='flashing':
            def flash_timer():
                if self.timer_state: self._l.cs.color.set(self.ASSUMED_COLOR)
                else: self._l.cs.color.set('black')
                if self.flashing: self.add_timer_callback(flash_timer)
                else:
                    self._l.cs.color.set(self.color.get_basecolor())
                self._l.refresh('cs')
            if value:
                self.add_timer_callback(flash_timer)
            else: self.plot_only = False
        elif name=='intensity':
            l = self._l
            for el in self, l.cs, l.vac, l.pac, l.wake:
                el.color.set_intensity(value)
            self.redraw()
            
    def destroy(self):
        if VisTrack.timer_id: self._c.after_cancel(VisTrack.timer_id)
        VisTrack.timer_callbacks = []
        self.delete()
        self._l.destroy()
        del(self._message_handler)
        del(self.do_scale)
        del(self.undo_scale)
            
    def __del__(self):
        logging.debug("VisTrack.__del__")
            
    class Label(object):
        """Contains the information regarding label formatting"""        
        formats={'pp':{-1:['pac','vac'],
                       0:['cs'],                      # pp = Pseudopilot
                       1:['alt','rate','cfl'],
                       2:['hdg'],
                       3:['gs','wake','spc','echo']},
                 'pp-mach':{-1:['pac','vac'],
                            0:['cs'],
                            1:['alt','rate','cfl'],
                            2:['hdg'],
                            3:['mach','wake','spc','echo']},
                'atc':{-1:['pac','vac'],
                            0:['cs'],
                            1:['alt','rate','cfl'],
                            2:['gs','wake','spc','echo']}}
        
        # The __getitem__ function allows us access this class' attributes
        # as if it were a dictionary
        def __getitem__(self,key): return self.__dict__[key]
        
        class LabelItem(object):
            """Contains the attributes of a label item"""
            def __init__(self, master_track):
                self.vt = vt = master_track
                self.color = master_track.color
                self.t = ""  # Item text
                self.w = 0  # Width in pixels
                self.x = 0  # Hor screen coord
                self.y = 0 # Ver screen coord
                self.i = None  # Canvas item id
                
            def __del__(self):
                logging.debug("LabelItem.__del__")
                
        def __init__(self, master_track): 
            self.vt = vt = master_track
            self.c = self.vt._c  # Canvas
            self.cs = self.LabelItem(vt)
            self.cs.color = SmartColor(vt.color.get_basecolor())
            self.alt = self.LabelItem(vt)
            self.rate = self.LabelItem(vt)
            self.cfl = self.LabelItem(vt)
            self.gs = self.LabelItem(vt)
            self.mach = self.LabelItem(vt)
            self.echo = self.LabelItem(vt)
            self.wake = self.LabelItem(vt)
            self.wake.color = SmartColor('')
            self.hdg = self.LabelItem(vt)
            self.spc = self.LabelItem(vt)
            self.spc.t = ' '
            
            self.pac = self.LabelItem(vt)     
            self.pac.t = 'PAC'
            self.pac.color = SmartColor('')
            
            self.vac = self.LabelItem(vt)
            self.vac.t = 'VAC'
            self.vac.color = SmartColor('')
            
            self._old_font_size = 0
                        
            self.format = self.vt.label_format  # By default, 'pp'
            self.items = []  # They are calculated at reformat time

            
        def delete(self):
            """Delete old tag and remove old bindings"""
            c = self.vt._c  # Canvas
            s = str(self.vt)
            
            for i in self.items:
                ra_cleartagbinds(self[i].i)
                self[i].i=None
            c.delete(s+'labelitem')
            self.items=[]
            
        def destroy(self):
            self.delete()
            for i in self.vt.allitems:
                item = getattr(self, i)
                delattr(item, 'vt')
                delattr(item, 'color')
                delattr(self, i)
            del(self.vt)
            
        def redraw(self):
            """Redraw the label and reset bindings"""
            c = self.vt._c  # Canvas
            s = str(self.vt)
            lf = self.vt._l_font
            self.format=self.vt.label_format
            
            # Delete old tag and remove old bindings
            self.delete()
            
            if not self.vt.visible: return
            
            # Create new label
            self.reformat()
            for i_name in self.items:
                i=self[i_name]  # i is an instance of the LabelItem class
                i.i = c.create_text(i.x, i.y, text=i.t, fill=i.color.get(), tag=s+i_name, anchor=NW, font=lf)
                c.itemconfig(i.i,tags=(s+'labelitem',s+'move',s+'color',s+'track', s+'label'))
                    
            #Create bindings
            # Common bindings
            ra_tag_bind(self.c,self.cs.i,"<Button-1>",self.cs_b1)
            ra_tag_bind(self.c,self.cs.i,"<Button-2>",self.cs_b2)
            ra_tag_bind(self.c,self.cs.i,"<Button-3>",self.cs_b3)
            ra_tag_bind(self.c,self.echo.i,"<Button-3>",self.echo_b3)
            ra_tag_bind(self.c,self.alt.i,"<Button-1>",self.change_altitude)
            # PP bindings
            if self.vt.mode=='pp':
                ra_tag_bind(self.c,self.gs.i,"<Button-2>",self.gs_b2)
                ra_tag_bind(self.c,self.mach.i,"<Button-2>",self.mach_b2)
                ra_tag_bind(self.c,self.cfl.i,"<Button-1>",self.change_rate)
                ra_tag_bind(self.c,self.gs.i,"<Button-1>",self.change_speed)
                ra_tag_bind(self.c,self.mach.i,"<Button-1>",self.change_speed)
                ra_tag_bind(self.c,self.hdg.i,"<Button-1>",self.change_heading)
            # ATC bindings
            elif self.vt.mode=='atc':
                ra_tag_bind(self.c,self.cfl.i,"<Button-1>",self.change_altitude)
            
        def reformat(self):
            """Recalculates the text for the label items, and the new label geometry"""
            vt = self.vt  # Parent track object
            lf = vt._l_font  # Label font
            if vt.l_font_size!=self._old_font_size:
                lf.configure(size=vt.l_font_size)
                self._old_font_size=vt.l_font_size
                
            # Refresh items text and color
            for i_name in vt.allitems:
                self.refresh(i_name)
                
            # Label geometry
            lw = mlw = 20  # Label Width initially Minimum label width
            lh = 4  # Initial label height
            line_height = lf.metrics('ascent')
            for line_no,items in self.formats[self.format].items():
                line_width=4
                x_offset=vt.label_x+2
                for item in items:
                    self[item].w=lf.measure(self[item].t)
                    line_width += self[item].w
                    self[item].x = x_offset
                    x_offset += self[item].w
                    self[item].y = vt.label_y + line_no * line_height
                    self.items.append(item)
                lw = max (lw, line_width)
                lh = lh + line_height
            vt.label_width = lw
            # We are assumming here that all label formats
            # have a -1 line to contain pac and vac
            # TODO This is NOT CORRECT
            vt.label_height = lh - line_height
                
            # Update label items position
            for i in self.items:
                if self[i].i!=None:
                    vt._c.coords(self[i].i,self[i].x,self[i].y)
                    
        def refresh(self,i):
            """Change text and color of a specific label item"""
            vt = self.vt  # Parent track object
            lf = vt._l_font  # Label font
            
            # Text
            if i=='cs': 
                self.cs.t = vt.cs
            elif i=='mach':
                self.mach.t = '.'+str(int(round(vt.mach*100)))
            elif i=='gs':
                self.gs.t = str(int(round(vt.gs/10)))
            elif i=='wake':
                self.wake.t = vt.wake
                if vt.wake == 'H': self.wake.color.set('yellow')
                else: self.wake.color.set(vt.color.get())
            elif i=='hdg':
                self.hdg.t='%03d'%(int(vt.hdg))
            elif i=='alt':
                self.alt.t='%03d'%(int(vt.alt+0.5))
            elif i=='rate':
                if vt.rate>0.:
                    self.rate.t=unichr(8593)  # Vertical direction
                elif vt.rate<0.:
                    self.rate.t=unichr(8595)
                else: self.rate.t = '  '  # Two spaces, as wide as the arrow,
                                          # so that a reformat is not necessary
            elif i=='cfl':
                if vt.draw_cfl:
                    if vt.cfl-vt.alt>2.:
                        self.cfl.t='%03d'%(int(vt.cfl+0.5))  # Vertical direction
                    elif vt.cfl-vt.alt<-2.:
                        self.cfl.t='%03d'%(int(vt.cfl+0.5))
                    else:
                        vt.draw_cfl = False
                        self.cfl.t = ''
                else:
                    self.cfl.t = ''
            elif i=='echo':
                self.echo.t = vt.echo
            elif i=='pac':
                self.pac.color.set('red')
                if vt.pac: self.pac.t="PAC"
                else: self.pac.t=""

            elif i=='vac':
                self.vac.color.set('red')
                if vt.vac: self.vac.t="VAC"
                else: self.vac.t=""
                
            item=self[i]
            if i=='pac':
                if vt.pac:
                    if self.vt.timer_state: self.pac.color.set('red')
                    else: self.pac.color.set('')
                    self.vt.add_timer_callback(self.refresh, i)
                else: self.pac.color.set('')
            if i=='vac':
                if vt.vac:
                    if self.vt.timer_state: self.vac.color.set('red')
                    else: self.vac.color.set('')
                    self.vt.add_timer_callback(self.refresh, i)
                else: self.vac.color.set('')
                
                # Refresh the item
            if item.i!=None:
                vt._c.itemconfig(item.i,text=item.t,fill=item.color.get())
                
        def cs_moved(self,e):
            self.vt.reposition_label(e.x, e.y)
            self.vt.auto_separation=False
            self.vt._message_handler(self.vt,'cs','<Motion>',None,e)
        def cs_released(self,e):
            ra_tag_unbind(self.c, self.cs.i, "<Motion>")
            ra_tag_unbind(self.c, self.cs.i, "<ButtonRelease-2>")
            self.vt._message_handler(self.vt,'cs','<ButtonRelease-2>',None,e)
        def cs_b2(self,e):
            self.reformat()  # We redraw the text to reset the width
            ra_tag_bind(self.c, self.cs.i, "<Motion>", self.cs_moved)
            ra_tag_bind(self.c, self.cs.i, "<ButtonRelease-2>", self.cs_released)            
            self.vt._message_handler(self.vt,'cs','<Button-2>',None,e)
        def cs_b1(self,e):
            if self.vt.assumed and self.vt.flashing: self.vt.flashing = False
            else: self.vt.assumed = not self.vt.assumed
            self.vt._message_handler(self.vt,'cs','<Button-1>',None,e)
        def cs_b3(self,e):
            self.vt._message_handler(self.vt,'cs','<Button-3>',None,e)
            def ok():
                self.vt.assumed = False
                self.vt._message_handler(self.vt,'transfer',None,None,e)
                
            #Only assumed traffic is allowed to be transferred
            if self.vt.assumed == True: RaDialog(self.c, label=self.cs.t+": Transferir", ok_callback=ok,
                                        position=(self.vt.x, self.vt.y))
        def gs_b2(self,e):
            self.vt.label_format='pp-mach'
            self.vt._message_handler(self.vt,'gs','<Button-2>',None,e)
        def mach_b2(self,e):
            self.vt.label_format='pp'
            self.vt._message_handler(self.vt,'mach','<Button-2>',None,e)
        def echo_b3(self,e):
            self.vt._message_handler(self.vt,'echo','<Button-3>',None,e)
            
        
        def change_altitude(self,e=None):
            win = Frame(self.c)
            lbl_cls = Label(win, text=self.cs.t,bg='blue',fg='white',width = CHANGE_WIDTH-1)
            lbl_CFL = Label(win, text="CFL:")
            ent_CFL = Entry(win, width=3)
            ent_CFL.insert(0, str(int(self.vt.cfl)))
            ent_CFL.select_range(0, END)
            lbl_PFL = Label(win, text="PFL:")
            ent_PFL = Entry(win, width=3)
            ent_PFL.insert(0, str(int(self.vt.pfl)))
            but_Comm = Button(win, text="COMUNICAR")
            but_Acp = Button(win, text="ACP")
            but_Can = Button(win, text="CNL")
            lbl_cls.grid(row=0,columnspan=2,sticky=W+E)
            lbl_CFL.grid(row=1, column=0)
            ent_CFL.grid(row=1, column=1)
            lbl_PFL.grid(row=2, column=0)
            ent_PFL.grid(row=2, column=1)
            but_Comm.grid(row=3, column=0, columnspan=2,sticky=W+E)
            but_Acp.grid(row=4, column=0, columnspan=1,sticky=W+E)
            but_Can.grid(row=4, column=1, columnspan=1,sticky=W+E)
            window_ident = self.c.create_window(e.x, e.y, window=win)
            ent_CFL.focus_set()
            def close_win(e=None, ident=window_ident, w=self.c):
                w.unbind_all("<Return>")
                w.unbind_all("<KP_Enter>")
                w.unbind_all("<Escape>")
                self.c.delete(ident)
            def set_FLs(cfl,pfl):
                self.vt.pfl=int(pfl)
                self.vt._message_handler(self.vt,'pfl','update',pfl,e)
                d = self.vt._message_handler(self.vt,'cfl','update',cfl,e)
                def result((r, cfl_max)):
                    if r:
                        self.vt.cfl=int(cfl)
                        self.reformat()
                        close_win()
                    else:
                        ent_CFL.delete(0,END)
                        ent_CFL.insert(0, str(abs(int(cfl_max))))
                        ent_CFL['bg'] = 'red'
                        ent_CFL.focus_set()
                if self.vt.mode == 'atc': result((True, None))
                else: d.addCallback(result)
            def aceptar(e=None):
                cfl = ent_CFL.get()
                pfl = ent_PFL.get()
                set_FLs(cfl,pfl)
            def comm(e=None):
                cfl=pfl=ent_PFL.get()
                set_FLs(cfl,pfl)
            but_Comm['command'] = comm
            but_Acp['command'] = aceptar
            but_Can['command'] = close_win
            self.c.bind_all("<Return>",aceptar)
            self.c.bind_all("<KP_Enter>",aceptar)
            self.c.bind_all("<Escape>",close_win)
            self.vt._message_handler(self.vt,'alt','<Button-1>',None,e)
            
        def change_rate(self,e):
            win = Frame(self.c,width=10)
            lbl_cls = Label(win, text=self.cs.t,bg='blue',fg='white',width = CHANGE_WIDTH-1)
            lbl_rate = Label(win, text="Rate:")
            ent_rate = Entry(win, width=4)
            ent_rate.insert(0, str(abs(int(self.vt.rate))))
            ent_rate.select_range(0, END)
            but_Acp = Button(win, text="Aceptar")
            but_Can = Button(win, text="Cancelar")
            but_Std = Button(win,text="Estandar")
            lbl_cls.grid(row=0,columnspan=2,sticky=W+E)
            lbl_rate.grid(row=1, column=0)
            ent_rate.grid(row=1, column=1)
            but_Acp.grid(row=2, column=0, columnspan=2,sticky=W+E)
            but_Can.grid(row=3, column=0, columnspan=2,sticky=W+E)
            but_Std.grid(row=4, column=0, columnspan=2,sticky=W+E)
            window_ident = self.c.create_window(e.x, e.y, window=win)
            ent_rate.focus_set()
            def close_win(e=None,ident=window_ident,w=self.c):
                w.unbind_all("<Return>")
                w.unbind_all("<KP_Enter>")
                w.unbind_all("<Escape>")
                self.c.delete(ident)
            def set_rate(e=None):
                rate = ent_rate.get()
                d = self.vt._message_handler(self.vt,'rate','update',rate,e)
                def result((r, max_rate)):
                    if r:
                        self.vt.rate=int(rate)
                        close_win()
                    else:
                        ent_rate.delete(0,END)
                        ent_rate.insert(0, str(abs(int(max_rate))))
                        ent_rate['bg'] = 'red'
                        ent_rate.select_range(0, END)
                        ent_rate.focus_set()
                d.addCallback(result)
            def set_std():
                self.vt._message_handler(self.vt,'rate','update','std',e)
                close_win()
            but_Acp['command'] = set_rate
            but_Can['command'] = close_win
            but_Std['command'] = set_std
            self.c.bind_all("<Return>",set_rate)
            self.c.bind_all("<KP_Enter>",set_rate)
            self.c.bind_all("<Escape>",close_win)
            
        def change_heading(self,e):
            win = Frame(self.c,width=10)
            lbl_cls = Label(win, text=self.cs.t,bg='blue',fg='white',width = CHANGE_WIDTH)
            lbl_hdg = Label(win, text="Heading:")
            ent_hdg = Entry(win, width=3)
            ent_hdg.insert(0, str(int(self.vt.hdg)))
            ent_hdg.select_range(0, END)
            ent_side = OptionMenu (win,bg='white',width=20)
            num = 0
            for opc in ['ECON','DCHA','IZDA']:
                ent_side.add_command(opc)
                num=num+1
            ent_side['value'] = 'ECON'
            but_Acp = Button(win, text="Aceptar")
            but_Can = Button(win, text="Cancelar")
            lbl_cls.grid(row=0,columnspan=2,sticky=W+E)
            lbl_hdg.grid(row=1, column=0)
            ent_hdg.grid(row=1, column=1)
            ent_side.grid(row=4,column=0,columnspan=2,sticky=W+E)
            but_Acp.grid(row=2, column=0, columnspan=2,sticky=W+E)
            but_Can.grid(row=3, column=0, columnspan=2,sticky=W+E)
            window_ident = self.c.create_window(e.x, e.y, window=win)
            ent_hdg.focus_set()
            def close_win(e=None,ident=window_ident,w=self.c):
                w.unbind_all("<Return>")
                w.unbind_all("<KP_Enter>")
                w.unbind_all("<Escape>")
                self.c.delete(ident)
            def set_heading(e=None):
                hdg = ent_hdg.get()
                opt = ent_side.cget('value')
                self.vt._message_handler(self.vt,'hdg','update',(hdg,opt),e)
                close_win()
            but_Acp['command'] = set_heading
            but_Can['command'] = close_win
            self.c.bind_all("<Return>",set_heading)
            self.c.bind_all("<KP_Enter>",set_heading)
            self.c.bind_all("<Escape>",close_win)
            
        def change_speed(self,e):
            # TODO we should look for server reply to confirm value setting
            # in the same way we do for cfl and rate
            
            if self.vt.label_format == 'pp':
                win = Frame(self.c)
                lbl_cls = Label(win, text=self.cs.t,bg='blue',fg='white',width = CHANGE_WIDTH-2)
                lbl_spd = Label(win, text="IAS:")
                ent_spd = Entry(win, width=3)
                ent_spd.insert(0, str(int(self.vt.ias)))
                ent_spd.select_range(0, END)
            elif self.vt.label_format == 'pp-mach':
                win = Frame(self.c)
                lbl_cls = Label(win, text=self.cs.t,bg='blue',fg='white',width = CHANGE_WIDTH-2)
                lbl_spd = Label(win, text="MACH:")
                ent_spd = Entry(win, width=3)
                ent_spd.insert(0, str(int(round(float(self.mach.t)*100.0))))
                ent_spd.select_range(0, END)
            
            but_Acp = Button(win, text="Aceptar")
            but_Can = Button(win, text="Cancelar")
            but_Std = Button(win, text="Estandar")
            lbl_cls.grid(row=0,columnspan=2,sticky=W+E)
            lbl_spd.grid(row=1, column=0)
            ent_spd.grid(row=1, column=1)
            but_Acp.grid(row=2, column=0, columnspan=2,sticky=W+E)
            but_Can.grid(row=3, column=0, columnspan=2,sticky=W+E)
            but_Std.grid(row=4, column=0, columnspan=2,sticky=W+E)
            window_ident = self.c.create_window(e.x, e.y, window=win)
            ent_spd.focus_set()
            def close_win(e=None,ident=window_ident,w=self.c):
                w.unbind_all("<Return>")
                w.unbind_all("<KP_Enter>")
                w.unbind_all("<Escape>")
                self.c.delete(ident)
            def set_speed(e=None):
                if self.vt.label_format == 'pp':
                    spd = ent_spd.get()
                    # If entry was already displaying maximum available, let
                    # the user force the desired speed, forcing whatever speed
                    # he requested.
                    if ent_spd['bg'] == 'red':
                        force_speed = True
                    else:
                        force_speed = False
                    d = self.vt._message_handler(self.vt,'ias','update',(spd,force_speed),e)
                    def result((r, ias_max)):
                        if r:
                            close_win()
                        else:
                            ent_spd.delete(0,END)
                            ent_spd.insert(0, str(abs(int(ias_max))))
                            ent_spd['bg'] = 'red'
                            ent_spd.focus_set()
                    d.addCallback(result)
                    
                elif self.vt.label_format == 'pp-mach':
                    spd = ent_spd.get()
                    spd = spd
                    # If entry was already displaying maximum available, let
                    # the user force the desired speed, forcing whatever speed
                    # he requested.
                    if ent_spd['bg'] == 'red':
                        force_speed = True
                    else:
                        force_speed = False
                    d = self.vt._message_handler(self.vt,'mach','update',(int(spd)/100.,force_speed),e)
                    def result((r, mach_max)):
                        if r:
                            close_win()
                        else:
                            ent_spd.delete(0,END)
                            ent_spd.insert(0, str(abs(int(mach_max*100))))
                            ent_spd['bg'] = 'red'
                            ent_spd.focus_set()
                    d.addCallback(result)

            def set_std():
                if self.vt.label_format == 'pp':
                    self.vt._message_handler(self.vt,'ias','update',('std',None),e)
                elif self.vt.label_format == 'pp-mach':
                    self.vt._message_handler(self.vt,'mach','update',('std',None),e)
                close_win()
            but_Acp['command'] = set_speed
            but_Can['command'] = close_win
            but_Std['command'] = set_std
            self.c.bind_all("<Return>",set_speed)
            self.c.bind_all("<KP_Enter>",set_speed)
            self.c.bind_all("<Escape>",close_win)
            
        def __del__(self):
            logging.debug("Label.__del__")

class LAD(object):
    """Línea azimut distance = azimut distance line
    
    A graphical line showing distance, bearing, and if aircraft are involved,
    minimum crossing time, and minimum crossing distance"""
    
    # Color is a class attribute
    lad_color = SmartColor("#%04x%04x%04x" % (250*257,158*257,20*257))  #Lighter orange than the 'orange'
    super_lad_color = SmartColor('red')
    
    def __init__(self,radisplay,e):
    
        rd=self.radisplay=radisplay
        c=radisplay.c
        
        # No se estaba definiendo un LAD. Comenzar a definir uno
        self.orig = self.get_acft_or_point(e.x,e.y)
        ra_unbind(rd, c, '<Motion>')
        ra_unbind(rd, c, '<Button-2>')
        ra_unbind(rd, c, '<Button-3>')
        ra_bind(rd, c, '<Motion>', self.update_lad_being_defined)
        ra_bind(rd, c, '<Button-2>', self.cancel_def_lad)
        ra_bind(rd, c, '<Button-3>', self.end_def_lad)
        
        self.superlad = False
        self.text_id1 = None
        self.text_id2 = None
        self.text_id3 = None
        self.text_id4 = None
        
    def __del__(self):
        logging.debug("LAD.__del__")
        
    class fix_point:
        """This class acts as a stationary radar track"""
        def __init__(self,world_pos,screen_pos):
            self.wx,self.wy=world_pos
            self.x,self.y=screen_pos
            self.visible = True
            self.track = 0.01
            self.gs=0.01

    def get_anchor(self,angulo=0.0):
        if (angulo >= 0.0 and angulo < 90.0) or (angulo == 360.0): return {'anchor':NW}
        if angulo >= 90.0 and angulo < 180.0: return {'anchor':NE}
        if angulo >= 180.0 and angulo < 270.0: return {'anchor':NW}
        if angulo >= 270.0 and angulo < 360.0: return {'anchor':NE}
        
    def get_lad_label_position(self,angulo,lad_center_x,lad_center_y,distance):
        if angulo == 360.0: angulo = 0.0
        if (angulo >= 0.0 and angulo < 90.0) or (angulo >= 180.0 and angulo < 270.0):
            x1 = lad_center_x+distance/sqrt(2.0)
            y1 = lad_center_y+distance/sqrt(2.0)
        
        if (angulo >= 90.0 and angulo < 180.0) or (angulo >= 270.0 and angulo < 360.0):
            x1 = lad_center_x-distance/sqrt(2.0)
            y1 = lad_center_y+distance/sqrt(2.0)
            
        return (x1,y1)
            
    def get_acft_or_point(self,x,y):
        # Returns the closest acft to (x,y) or otherwise a point
        min_snap_distance = 8.
        closest_track = None
        for track in self.radisplay.tracks:
            if track.visible:
                (x0,y0) = (track.x,track.y)
                dist = sqrt((x - x0)**2 + (y - y0)**2)
                if dist < min_snap_distance:
                    closest_track = track
                    min_snap_distance = dist
        if closest_track == None:
            closest_track = self.fix_point(self.radisplay.undo_scale((x,y)),(x,y))
        return closest_track
        
    def cancel_def_lad(self,e=None):
        rd = self.radisplay
        c = rd.c
        c.delete('lad_defined')
        ra_unbind(rd, c, '<Motion>')
        ra_unbind(rd, c, '<Button-2>')
        ra_unbind(rd, c, '<Button-3>')
        ra_bind(rd, c, '<Button-2>', rd.b2_cb)
        ra_bind(rd, c, '<Button-3>', rd.b3_cb)
        rd.b2_cb(e)
        rd.defining_lad = False
        
    def update_lad_being_defined(self,e=None):
        canvas=self.radisplay.c        
        canvas.delete('lad_defined')
        (x0, y0) = self.orig.x,self.orig.y
        dest = self.radisplay.undo_scale((e.x, e.y))
        lad_xsize = dest[0] - self.orig.wx
        lad_ysize = dest[1] - self.orig.wy
        angulo = 90.0 - degrees( atan2( lad_ysize, lad_xsize ) )
        if angulo < 0.0: angulo += 360.0
        dist = sqrt( lad_xsize * lad_xsize + lad_ysize * lad_ysize)
        time_min = 60.0 * dist / self.orig.gs
        lad_center_x = (x0 + e.x)/2
        lad_center_y = (y0 + e.y)/2
        canvas.create_line(x0, y0,e.x, e.y, fill=self.lad_color.get(), tags="lad_defined")
        lad_text1 = "A: %03d" % angulo
        lad_text2 = "D: %03d" % dist
        # Check if LAD begins in a point or in a plane
        if self.orig.gs < 10.:
            lad_text3 = ""
            lad_lines = 2  # LAD will show 2 lines with information (Azimuth, Distance)
        else:
            lad_text3 = "T: %03d" % time_min
            lad_lines = 3  # LAD will show 3 lines with information (Azimuth, Distance and Time to reach)
        label_font=self.radisplay.label_font
        lad_rect_width = self.radisplay.label_font.measure(lad_text1)
        lad_line_height = label_font.metrics('ascent')
        anchor_= self.get_anchor(angulo)
        lad_text = lad_text1+"\n"+lad_text2
        if lad_text3 <> "":lad_text += "\n"+lad_text3
        (lad_x,lad_y)=self.get_lad_label_position(angulo,lad_center_x,lad_center_y,5)
        canvas.create_text(lad_x, lad_y, text=lad_text, fill=self.lad_color.get(), tags="lad_defined",justify=LEFT,**anchor_)
    

    def end_def_lad(self,e=None):
        rd = self.radisplay
        c = rd.c
        c.delete('lad_defined')
        ra_unbind(rd, c, '<Motion>')
        ra_unbind(rd, c, '<Button-2>')
        ra_unbind(rd, c, '<Button-3>')
        self.dest=self.get_acft_or_point(e.x,e.y)
        self.radisplay.lads.append(self)
        ra_bind(rd, c, '<Button-2>', rd.b2_cb)
        ra_bind(rd, c, '<Button-3>', rd.b3_cb)
        rd.b3_cb(e)
        rd.defining_lad = False
        self.redraw()
        
    def delete(self,e=None):
        canvas=self.radisplay.c
        s=str(self)
        
        if self.text_id1!=None:
            ra_cleartagbinds(self.text_id1)
        #if self.text_id2!=None: ra_cleartagbinds(self.text_id2)
        #if self.text_id3!=None: ra_cleartagbinds(self.text_id3)
        #if self.text_id4!=None: ra_cleartagbinds(self.text_id4)
        canvas.delete(s+'lad')
        self.radisplay.lads.remove(self)
        if e!=None:
            self.radisplay.cancel_lad_serial = e.serial
            
    def redraw(self):
        canvas=self.radisplay.c
        do_scale=self.radisplay.do_scale
        label_font=self.radisplay.label_font
        s=str(self)
        
        self.delete()
        
        # Create a new LAD
        self.radisplay.lads.append(self)
        
        (xinitA, yinitA) = (self.orig.wx,self.orig.wy)
        (xinitB, yinitB) = (self.dest.wx,self.dest.wy)
        lad_xdif = xinitB - xinitA
        lad_ydif = yinitB - yinitA
        current_azimuth = 90.0 - degrees( atan2 (lad_ydif, lad_xdif) )
        if current_azimuth < 0.0: current_azimuth += 360.0
        lad_lines = 2 # 2 lines of text if planes won't cross; 4 if they will cross
        text1 = "A: %03d" % current_azimuth
        current_distance = sqrt(lad_xdif*lad_xdif + lad_ydif*lad_ydif)
        text2 = "D: %05.1f" % current_distance
        text_lad = text1+"\n"+text2
        (x0, y0) = do_scale((xinitA, yinitA))
        (x1, y1) = do_scale((xinitB, yinitB))
        if self.superlad == True:
            color =  self.super_lad_color.get()

        else:
            color = self.lad_color.get()
        self.line_id = canvas.create_line(x0, y0, x1, y1, fill=color, tags=(s+'lad',s+'line'))
        xm = (x0+x1) / 2
        ym = (y0+y1) / 2
        min_dist_time = self.compute_mindisttime(xinitA, yinitA, self.orig.track, self.orig.gs, xinitB, yinitB, self.dest.track, self.dest.gs)
        # Limit min_dist_time<500 to avoid overflow problems when min_dist_time is too high
        if (min_dist_time != None) and (min_dist_time > 0.0)and (min_dist_time<500.0):
                # Flights will cross
            min_dist = self.compute_mindist(xinitA, yinitA, self.orig.track, self.orig.gs, xinitB, yinitB, self.dest.track, self.dest.gs)
            lad_lines = 4 # 4 lines of text in LAD square

            text3 = "T: %03d" % min_dist_time
            text4 = "C: %05.1f" % min_dist
            text_lad += "\n"+text3+"\n"+text4
            
        lad_line_height = label_font.metrics('ascent')
        lad_label_anchor=self.get_anchor(current_azimuth)
        (x_lad,y_lad) = self.get_lad_label_position(current_azimuth,xm,ym,10)
        self.text_id1 = canvas.create_text(x_lad,y_lad,text=text_lad, fill=self.lad_color.get(), tags=(s+'lad',s+'text'),justify=LEFT,**lad_label_anchor)
        #self.text_id1 = canvas.create_text(xm, ym - lad_lines * lad_line_height,     text=text1, fill=self.lad_color.get(), tags=(s+'lad',s+'text'))
        #self.text_id2 = canvas.create_text(xm, ym - (lad_lines-1) * lad_line_height, text=text2, fill=self.lad_color.get(), tags=(s+'lad',s+'text'))
        #if lad_lines == 4:
        #    self.text_id3 = canvas.create_text(xm, ym - (lad_lines-2) * lad_line_height, text=text3, fill=self.lad_color.get(), tags=(s+'lad',s+'text'))
        #    self.text_id4 = canvas.create_text(xm, ym - (lad_lines-3) * lad_line_height, text=text4, fill=self.lad_color.get(), tags=(s+'lad',s+'text'))
            
        ra_tag_bind(canvas,self.text_id1,'<Button-1>',self.toggle_superlad)
        #ra_tag_bind(canvas,self.text_id2,'<Button-1>',self.toggle_superlad)
        ra_tag_bind(canvas,self.text_id1,'<Button-2>',self.delete)
        #ra_tag_bind(canvas,self.text_id2,'<Button-2>',self.delete)
        #if lad_lines == 4:
        #    ra_tag_bind(canvas,self.text_id3,'<Button-1>',self.toggle_superlad)
        #    ra_tag_bind(canvas,self.text_id4,'<Button-1>',self.toggle_superlad)
        #    ra_tag_bind(canvas,self.text_id3,'<Button-2>',self.delete)
        #    ra_tag_bind(canvas,self.text_id4,'<Button-2>',self.delete)
            
        if (self.superlad) and (min_dist_time != None) and (min_dist_time > 0.0):
            # Flights will cross
            size=2
            (posAx, posAy, posBx, posBy) = self.compute_cross_points(xinitA, yinitA, self.orig.track, self.orig.gs, xinitB, yinitB, self.dest.track, self.dest.gs)
            (crossAx, crossAy) = do_scale((posAx, posAy))
            (crossBx, crossBy) = do_scale((posBx, posBy))
            canvas.create_line(x0, y0, crossAx, crossAy, fill=self.super_lad_color.get(), tags=(s+'lad',s+'crosspoint'))
            canvas.create_rectangle(crossAx-size, crossAy-size, crossAx +size, crossAy +size, fill=self.super_lad_color.get(), tags=(s+'lad',s+'crosspoint'))
            canvas.create_line(x1, y1, crossBx, crossBy, fill=self.super_lad_color.get(), tags=(s+'lad',s+'crosspoint'))
            canvas.create_rectangle(crossBx - size, crossBy -size, crossBx + size, crossBy + size, fill=self.super_lad_color.get(), tags=(s+'lad',s+'crosspoint'))
            
        canvas.addtag_withtag('lad',s+'lad')
        canvas.lift('lad')
        canvas.lift('track')
            
    def toggle_superlad(self, e=None):
        self.superlad = not self.superlad
        self.redraw()
        
    def compute_mindisttime(self,xA, yA, headingA, speedA, xB, yB, headingB, speedB):
        # 60.0: miles per minute per knot
        try:
            vxA = speedA/60.0 * sin(radians(headingA))
            vyA = speedA/60.0 * cos(radians(headingA))
            vxB = speedB/60.0 * sin(radians(headingB))
            vyB = speedB/60.0 * cos(radians(headingB))
            t = -((xA-xB)*(vxA-vxB)+(yA-yB)*(vyA-vyB)) / ((vxA-vxB)*(vxA-vxB)+(vyA-vyB)*(vyA-vyB))
            # A veces al dividir entre algo muy pequeño no se obtiene excepción, sino un valor
            # flotante de "NaN" o de "inf" (error del Python). Forzamos excepción en estos casos.
            dummy = int(t)
            return t
        except:
            return None
            
    def compute_cross_points(self,xA, yA, headingA, speedA, xB, yB, headingB, speedB):
        time_to_mindist = self.compute_mindisttime(xA, yA, headingA, speedA, xB, yB, headingB, speedB)
        vxA = speedA/60.0 * sin(radians(headingA))
        vyA = speedA/60.0 * cos(radians(headingA))
        vxB = speedB/60.0 * sin(radians(headingB))
        vyB = speedB/60.0 * cos(radians(headingB))
        posAx = xA + vxA * time_to_mindist
        posAy = yA + vyA * time_to_mindist
        posBx = xB + vxB * time_to_mindist
        posBy = yB + vyB * time_to_mindist
        return (posAx, posAy, posBx, posBy)
        
    def compute_mindist(self,xA, yA, headingA, speedA, xB, yB, headingB, speedB):
        (posAx, posAy, posBx, posBy) = self.compute_cross_points(xA, yA, headingA, speedA, xB, yB, headingB, speedB)
        return sqrt((posAx-posBx)*(posAx-posBx) + (posAy-posBy)*(posAy-posBy))
        
class RaDisplay(object):
    """Generic radar display in which tracks and lads are shown
    
    This class requires that a Tk session is already active
    """
    def __init__(self,title,icon_path,fir,sector,toolbar_height):
        """Instantiate a generic Radar Display
        
        title - window title
        icon_path - path to the windows task bar icon
        fir -- fir object
        sector -- name of the sector to work with
        """
        
        self.fir=fir
        self.sector=sector
        
        self.top_level=Toplevel()
        tl = self.top_level
        if sys.platform.startswith('win'):
            tl.wm_iconbitmap(icon_path)
            tl.wm_state('zoomed')
        tl.wm_title(title)
        
        SmartColor.winfo_rgb = tl.winfo_rgb  # SmartColors needs a valid winfo_rgb function
                                            # which is only available once Tkinter
                                            # in initialized
        
        self.screen_width = tl.winfo_screenwidth()
        self.screen_height = tl.winfo_screenheight()
        screen_width = self.screen_width
        screen_height = self.screen_height
        tl.wm_geometry("%dx%d+%d+%d" % (screen_width, screen_height, 0, 0))
        
        self.c = c = Canvas(tl,bg='black')
        c.pack(expand=1,fill=BOTH)
        ra_bind(self, c, '<Configure>', self.change_size)

        # Used to prevent the label separation code to be run nested
        self.separating_labels = False
        
        # Screen parameters
        self.width=tl.winfo_width()
        self.height=tl.winfo_height()
        self.toolbar_height = toolbar_height
        self.center_x=self.width/2
        self.center_y=(self.height-self.toolbar_height)/2
        
        # World coordinates parameters
        self.x0=0.  # x0 and y0 define the center of the sector to display
        self.y0=0.  # in world coordinates
        self.scale=1.0  # Scale factor between screen and world coordinates
        
        self.draw_routes = True
        self.draw_point = True
        self.draw_sector = True
        self.draw_lim_sector = True
        self.draw_point_names = True
        self.draw_tmas = True
        self.draw_deltas = False

        
        self.intensity={"GLOBAL":1.0,"MAP":1.0,"TRACKS":1.0,"LADS":1.0}
        self.local_maps_shown = []
        
        self.maps_colors = {}
        self.maps_colors['sector']=SmartColor('gray9')
        self.maps_colors['lim_sector']=SmartColor('blue')
        self.maps_colors['tma']=SmartColor('gray30')
        self.maps_colors['routes']=SmartColor('gray25')
        self.maps_colors['fix']=SmartColor('gray25')
        self.maps_colors['fix_names']=SmartColor('gray40')
        self.maps_colors['deltas']=SmartColor('gray40')
        
        self.auto_separation = True  # Separate labels automatically
        
        VisTrack.timer_id = None  # Reset the VisTrack class
        self.tracks = []  # List of tracks (VisualTrack instances)
        self.selected_track = None
        self.lads = []  # List of LADs
        self.cancel_lad_serial = -1  # To be used to cancel lad creation after middle clicking some virtual track label item
        self.defining_lad = False

        self.pos_number = None  # Radar position number (identifies this radar display)
        
        self.label_font_size = 9
        self.label_font = tkFont.Font(family="Helvetica",size=self.label_font_size)
        self.label_moved = False  # Whether a label has recently been manually moved
        
        ra_bind(self, self.c, '<Button-1>', self.b1_cb)
        ra_bind(self, self.c, '<Button-2>', self.b2_cb)
        ra_bind(self, self.c, '<Button-3>', self.b3_cb)
        
        self.get_scale() # Calculate initial x0, y0 and scale
        
        self.intensity={"GLOBAL":1.0,"MAP":1.0,"TRACKS":1.0,"LADS":1.0}
        self.rabrightness = RaBrightness(c, self.set_element_intensity,position=(self.width*0.4,self.height*0.8))
        self.rabrightness.hide()


    def draw_polyline(self,object):
        """draw a series of lines from point to point defined in object[2:]. object[2:] contains
        points' names and points_definition contains de names and coordinates."""
        color = object[1]
        if object[1]=='':
            color = 'white'
        color=SmartColor(color, self.intensity["MAP"]*self.intensity["GLOBAL"]).get()
        if len(object) > 3:
            point_name = str(object[2])
            (px0, py0) = self.do_scale(self.fir.get_point_coordinates(point_name))
            for point in object[3:]:
                (px1, py1) = self.do_scale(self.fir.get_point_coordinates(point))
                self.c.create_line(px0, py0, px1, py1, fill=color, tag='local_maps')
                (px0, py0) = (px1,py1)
                
    def draw_SID_STAR(self,object):
        
        def draw_single_SID_STAR(single_sid_star,remove_underscored = True):
            for i in range(0,len(single_sid_star[1])-1):
                #We are not going to plot points which name starts with undescore
                first_point_chosen = False
                last_point_chosen = False
                if single_sid_star[1][i][1][0]<>'_' or not remove_underscored:
                    cx0 = float(single_sid_star[1][i][0][0])
                    cy0 = float(single_sid_star[1][i][0][1])
                    first_point_chosen = True
                    for j in range(i+1,len(single_sid_star[1])):
                        if single_sid_star[1][j][1][0]<>'_' or not remove_underscored:
                            cx1 = float(single_sid_star[1][j][0][0])
                            cy1 = float(single_sid_star[1][j][0][1])
                            last_point_chosen = True
                            break
                if first_point_chosen and last_point_chosen:
                    (px0, py0) = self.do_scale((cx0,cy0))
                    (px1, py1) = self.do_scale((cx1,cy1))
                    self.c.create_line(px0, py0, px1, py1, fill=color, tag='local_maps')
        
        sid_star_index = 0              #plot SID by default
        if object[0] == 'draw_sid':
            sid_star_index = 0
        elif object[0] == 'draw_star':
            sid_star_index = 1
            
        sid_star_rwy = object[1]
        sid_star_name = object[2]
        if len(object) > 3:
            color = object[3]
        else:
            color = 'white'
            
        color=SmartColor(color, self.intensity["MAP"]*self.intensity["GLOBAL"]).get()   
        for sid_star_index_word in self.fir.procedimientos[sid_star_rwy][sid_star_index]:              #cycle through al SID's or STAR's of one RWY
            sid_star=self.fir.procedimientos[sid_star_rwy][sid_star_index][sid_star_index_word]
            if (sid_star_name == '') or (sid_star_name == sid_star[0]):
                draw_single_SID_STAR(sid_star,True)

      
    def change_size(self,e):
        self.width = e.width
        self.height = e.height
        self.c.update_idletasks()

        
    def change_speed_vector(self,minutes,e=None):
        for track in self.tracks:
            track.speed_vector_length=minutes
                    
    def vt_handler(self,vt,item,action,value,e=None):
        """Handle events raised by visual tracks
        Visual tracks have their own GUI code to present the user
        with CFL and PFL dialog, for instance, but then they notify the parent
        about the result using this function"""
        if action=="<Button-2>" and item!='plot':
            self.cancel_lad_serial=e.serial
        pass
        if item=='cs':
            if action=='<Button-1>':
                m={"message":"assume", "cs": vt.cs, "assumed": vt.assumed}
                self.sendMessage(m)
            elif action=='<Motion>':
                self.label_moved = True
            elif action=='<ButtonRelease-2>':
                try: self.selected_track.selected = not self.selected_track.selected
                except: logging.debug("Unselecting previous selected track failed")
                if self.selected_track == vt:
                    self.selected_track = None
                    vt.selected = False
                else:
                    self.selected_track = vt
                    vt.selected = True
                if self.label_moved:
                    reactor.callInThread(self.separate_labels, vt)
                    self.label_moved = False
        if item=='leader':
            if action=='<Button-1>' or action=='<Button-3>':
                reactor.callInThread(self.separate_labels, vt)
        if item=='transfer':
            m={"message":"transfer", "cs": vt.cs}
            self.sendMessage(m)

    
    def b1_cb(self,e=None):
        pass
        
    def b2_cb(self,e=None):
        self.def_lad(e)
        
    def b3_cb(self,e=None):
        pass
        
    def def_lad(self,e=None):
        if e.serial==self.cancel_lad_serial or self.defining_lad: return
        self.defining_lad = True
        LAD(self,e)
    
    def delete_lads(self,e=None):
        for lad in self.lads[:]:
            lad.delete()

    def update(self):
        # Tracks are updated by the superclass when it gives them the new coords
        self.update_lads()
        self.update_stca()
        reactor.callInThread(self.separate_labels)
    
    def toggle_auto_separation(self):
        self.auto_separation = not self.auto_separation
        if self.auto_separation:
            reactor.callInThread(self.separate_labels)
        
    def separate_labels(self, single_track=None):
        tracks = self.tracks
        width,height = self.width,self.height
        canvas = self.c
        if not self.auto_separation or self.separating_labels: return
        
        self.separating_labels = True
        self.stop_separating = False
        crono = time()
        
        # Find the tracks that we have to separate
        sep_list = []  # List of track whose labels we must separate
        o = 0  # Amount of label overlap that we can accept
        new_pos = {}  # For each track, maintain the coords of the label position being tested
        best_pos = {} # These are the best coodinates found for each label track
        
        for track in tracks:
            x,y=track.label_x,track.label_y
            h,w=track.label_height,track.label_width
            if not track.visible or track.plot_only or x<0 or y<0 or x+w>width or y+h>height:
                continue
            sep_list.append(track)
            track.label_x_alt,track.label_y_alt=x,y  # Set the alternate coords to be used later
            track.label_heading_alt = track.label_heading
            new_pos[track]=(x,y)
            
        best_pos = new_pos
        move_list = []        
    
        #print [t.cs for t in sep_list]
        # Find intersecting labels
        for i in range (len(sep_list)):
            if time()-crono > 3:
                break
            ti = sep_list[i]  # Track i
            # Find vertices of track label i
            ix0,iy0 = ti.x,ti.y
            ix1,iy1 = ti.label_x,ti.label_y
            ix2,iy2 = ix1+ti.label_width, iy1+ti.label_height
            # Lists of conflicted labels and other helper lists
            conflict_list = [ti]
            cuenta = {ti:0}
            giro_min = [0]
            intersectan = 0
            
            for j in range(i+1,len(sep_list)):
                tj = sep_list[j]  # Track j
                # Find vertices of track label j
                jx0,jy0 = tj.x,tj.y
                jx1,jy1 = tj.label_x,tj.label_y
                jx2,jy2 = jx1+tj.label_width, jy1+tj.label_height
                
                # If the caller provided a specific track as an argument, we only want
                # to separate that label. Else try to separate everything
                if single_track and ti!=single_track and tj!=single_track:
                    continue
                
                conflict = False
                # Check whether any of the vertices, or the track plot of
                # track j is within label i
                # o is the label overlap. Defined at the beginning of the function
                for (x,y) in [(jx0,jy0),(jx1,jy1),(jx2,jy1),(jx2,jy2),(jx1,jy2)]:
                    if x-o>ix1 and x+o<ix2 and y-o>iy1 and y+o<iy2:
                        conflict = True
                        break
                # Check whether the plot of track i is within the label j
                x,y=ix0,iy0
                if x-o>jx1 and x+o<jx2 and y-o>jy1 and y+o<jy2:
                    conflict = True
                
                #canvas.create_line(jx0,jy0,jx1,jy1,jx2,jy1,jx2,jy2,jx1,jy2,fill='blue',tags='sep')
                
                if conflict == True:
                    intersectan = intersectan + 1
                    if (tj not in conflict_list) and len(conflict_list)<10:
                        conflict_list.append(tj)
                        cuenta[tj]=0
                        giro_min.append(0)
            # Si intersectan probamos las posiciones posibles de la etiqueta para ver si libra en alguna. En caso contrario,se escoge 
            # el de menor interferenci
            #print("Intersecting labels: "+str([t.cs for t in conflict_list]))
            intersectan_girado = intersectan
            cuenta_menos_inter = cuenta
            menos_inter = intersectan
            crono2 = time()
            rotating_labels = len(conflict_list)
            rotating_steps = 8
            rotating_angle = 360./rotating_steps
            # We want to try rotating first the tracks that were manually rotated,
            # and last those that were more recently manually rotated
            # last_rotation is bigger for the more recently rotated
            conflict_list.sort(lambda x,y: -cmp(x.last_rotation,y.last_rotation))
            #if len(conflict_list)>1:
            #    logging.debug("Conflict among "+str([t.cs for t in conflict_list]))
            while (intersectan_girado > 0) and (cuenta[conflict_list[0]] < rotating_steps) and rotating_labels:
                #canvas.update()
                if self.stop_separating:
                    logging.debug("Cancelling label separation after "+str(time()-crono2)+" seconds")
                    self.separating_labels = False
                    return  # Set, for instance, when moving the display
                # Try rotating one of the labels on the list
                for k in range(len(conflict_list)-1,-1,-1):
                    t = conflict_list[k]
                    # If the track is not set to be auto_separated, or if the
                    # label separation algorithem was called because of a manual
                    # label rotation, don't rotate this track
                    if not t.auto_separation or t==single_track:
                        rotating_labels -= 1
                        continue  # Don't move labels that don't want to be moved
                    if cuenta[t]<rotating_steps:
                        cuenta[t] += 1
                        # Find the alternative position of the label after the rotation
                        [x,y] = (t.x,t.y)
                        t.label_heading_alt += rotating_angle
                        ldr_x = x + t.label_radius * sin(radians(t.label_heading_alt))
                        ldr_y = y + t.label_radius * cos(radians(t.label_heading_alt))
    
                        ldr_x_offset = ldr_x - x
                        ldr_y_offset = ldr_y - y
                        # l_xo and lyo are the offsets of the label with respect to the plot
                        if ldr_x_offset > 0.:  
                            new_l_x = x+ldr_x_offset
                        else:
                            new_l_x = x+ldr_x_offset - t.label_width
                        new_l_y = y+ldr_y_offset -10
                        t.label_heading_alt = 90.0-degrees(atan2(ldr_y_offset, ldr_x_offset))
                        
                        t.label_x_alt = new_l_x
                        t.label_y_alt = new_l_y
                        new_pos[t]=(new_l_x,new_l_y)
    
                        break
                    
                    elif cuenta[t]==rotating_steps: 
                        cuenta[t] = 0 
                # Comprobamos si está separados todos entre ellos
                # We can't afford to call a function in here because this is
                # very deeply nested, and the function calling overhead
                # would be too much
                intersectan_girado = 0
                #logging.debug("Rotations: "+str([(t.cs, cuenta[t]) for t in conflict_list]))
                for k in range(len(conflict_list)):
                    ti = conflict_list[k]  # Track i
                    # Find vertices of track label i
                    ix0,iy0 = ti.x,ti.y
                    ix1,iy1 = ti.label_x_alt,ti.label_y_alt
                    ix2,iy2 = ix1+ti.label_width, iy1+ti.label_height
                    for j in range(k+1,len(conflict_list)):            
                        tj = conflict_list[j]  # Track j
                        # Find vertices of track label j
                        jx0,jy0 = tj.x,tj.y
                        jx1,jy1 = tj.label_x_alt,tj.label_y_alt
                        jx2,jy2 = jx1+tj.label_width, jy1+tj.label_height
                        
                        conflict = False
                        # Check whether any of the vertices, or the track plot of
                        # track j is within label i
                        # o is the label overlap. Defined at the beginning of the function
                        for (x,y) in [(jx0,jy0),(jx1,jy1),(jx2,jy1),(jx2,jy2),(jx1,jy2)]:
                            if x-o>ix1 and x+o<ix2 and y-o>iy1 and y+o<iy2:
                                conflict = True
                                break
                        # Check whether the plot of track i is within the label j
                        x,y=ix0,iy0
                        if x-o>jx1 and x+o<jx2 and y-o>jy1 and y+o<jy2:
                            conflict = True
                        
                        #logging.debug("Checking "+ti.cs+","+tj.cs+": "+str(conflict))    
                        if conflict == True:
                            intersectan_girado += 1
                            
                # Comprobamos que no estemos afectando a ningn otro avión con el reción girado. En caso contrario, se añ
                if intersectan_girado == 0:
                    for ti in conflict_list:
                        if len(conflict_list)>=10: break
                        # Find vertices of track label i
                        ix0,iy0 = ti.x,ti.y
                        ix1,iy1 = ti.label_x_alt,ti.label_y_alt
                        ix2,iy2 = ix1+ti.label_width, iy1+ti.label_height                        
                        for tj in sep_list:
                            if (ti==tj) or (tj in conflict_list): continue
    
                            # Find vertices of track label j
                            jx0,jy0 = tj.x,tj.y
                            jx1,jy1 = tj.label_x_alt,tj.label_y_alt
                            jx2,jy2 = jx1+tj.label_width, jy1+tj.label_height
                            
                            conflict = False
                            # Check whether any of the vertices, or the track plot of
                            # track j is within label i
                            # o is the label overlap. Defined at the beginning of the function
                            for (x,y) in [(jx0,jy0),(jx1,jy1),(jx2,jy1),(jx2,jy2),(jx1,jy2)]:
                                if x-o>ix1 and x+o<ix2 and y-o>iy1 and y+o<iy2:
                                    conflict = True
                                    break
                            # Check whether the plot of track i is within the label j
                            x,y=ix0,iy0
                            if x-o>jx1 and x+o<jx2 and y-o>jy1 and y+o<jy2:
                                conflict = True
    
                            if conflict:
                                intersectan_girado += 1
                                conflict_list.append(tj)
                                cuenta[tj]=0
                                #logging.debug("Added to conflict list: "+tj.cs)
    
                # En caso de que haya conflicto, escogemos el giro con menos interseccione
                if intersectan_girado < menos_inter:
                    menos_inter = intersectan_girado
                    cuenta_menos_inter = cuenta
                    best_pos = new_pos.copy()
                    
            if intersectan_girado>0:
                logging.debug("Unable to separate "+str(intersectan_girado)+" label(s)")
                if cuenta[conflict_list[0]] >= rotating_steps:
                    logging.debug("No solution found after checking all posibilities")
                if not rotating_labels:
                    logging.debug("No autorotating labels left")
                if (time()-crono2>=1):
                    logging.debug("No solution found after 1 second")
            
            move_list += conflict_list
            
        # We need to force redrawing of track labels that have moved
        # First we eliminate duplicates
        d = {}
        for track in move_list:
            d[track]=1
        move_list = d.keys()
        #logging.debug("Moving labels: "+str([t.cs for t in move_list if ((t.label_x,t.label_y)!=best_pos[t])]))
        
        # Once we have reached the result, we can't really update the labels from
        # here, because Tkinter is not thread safe
        
        def move_labels(move_list):
            # Update the labels
            for t in move_list:
                (x,y)=best_pos[t]
                t.label_coords(x,y)
                
            self.separating_labels = False
        
        # We make sure that the label moving is done from the main thread and event loop    
        reactor.callFromThread(move_labels, move_list)

    def update_stca(self):
        """Process short term collision alert"""
        # Calculate each track's position in 30 and 60 seconds
        
        redraw_list = []
        
        for track in self.tracks:
            if not track.visible: continue
            if track.vac or track.pac: redraw_list.append(track)
            track.future_pos = []
            track.vac = track.pac = False
            delta = 1./60./6  # delta = 10s
            for t in [delta, delta*2, delta*3, delta*4, delta*5, delta*6]:  
                gtx = sin(radians(track.track))  # Ground track projection on x
                gty = cos(radians(track.track))  # Ground track projection on y
                (x,y,alt) = (track.wx,track.wy,track.alt)  # Current position
                gs = track.gs  # Ground speed
                nx = x + gs*t*gtx  # Future x coord in t hours
                ny = y + gs*t*gty  # Future y coord in t hours
                nalt = alt + track.rate*t
                track.future_pos.append((nx,ny,nalt))
        
        try: min_sep = self.fir.min_sep[self.sector]
        except:
            min_sep = 8.0  # 8 nautical miles
            logging.warning("Sector minimum separation not found. Using 8nm")
        
        minvert = 9.5  # 950 feet minimum vertical distance
                
        for i in range(len(self.tracks)):
            for j in range(i+1,len(self.tracks)):
                ti = self.tracks[i]
                tj = self.tracks[j]
                if not ti.visible or not tj.visible: continue
                
                # Test for conflict
                ix,iy,jx,jy = ti.wx,ti.wy,tj.wx,tj.wy
                dist=sqrt((ix-jx)**2+(iy-jy)**2)        
                if dist<min_sep and abs(ti.alt-tj.alt)<minvert:
                    ti.vac = True
                    tj.vac = True
                    ti.pac = False
                    tj.pac = False
                    redraw_list.append(ti)
                    redraw_list.append(tj)
                    continue
                
                # STCA
                for ((ix,iy,ialt),(jx,jy,jalt)) in zip(ti.future_pos,tj.future_pos):
                    dist=sqrt((ix-jx)**2+(iy-jy)**2)
                    if dist<min_sep and abs(ialt-jalt)<minvert:
                        ti.pac = True
                        tj.pac = True
                        redraw_list.append(ti)
                        redraw_list.append(tj)
                        continue

        # We need to force redrawing of track labels that have or had a PAC or VAC
        # First we eliminate duplicates
        d = {}
        for track in redraw_list:
            d[track]=1
        redraw_list = d.keys()
        # Update the labels
        for track in redraw_list:
            track._l.reformat()

    def update_lads(self):
        # A lad might be deleted, so we need to iterate over a copy of the list
        for lad in self.lads[:]:
            lad.redraw()
            
    def get_scale(self):
        """Calculates the display center and the scale to display it all"""
        xmax=-1.e8
        xmin=1.e8
        ymax=-1.e8
        ymin=1.e8
        for a in self.fir.boundaries[self.sector]:
            if a[0]>xmax:
                xmax=a[0]
            if a[0]<xmin:
                xmin=a[0]
            if a[1]>ymax:
                ymax=a[1]
            if a[1]<ymin:
                ymin=a[1]
        self.x0=(xmax+xmin)/2
        self.y0=(ymax+ymin)/2
        x_scale=self.width/(xmax-xmin)
        y_scale=(self.height-self.toolbar_height)/(ymax-ymin)
        self.scale=min(x_scale,y_scale)*0.9
        
    def redraw_maps(self):
        
        c = self.c  # Canvas
        fir = self.fir
        sector = self.sector
        do_scale = self.do_scale
        
        self.c.delete('radisplay')        
        
        def _draw_sector():
            # Dibujar SECTOR
            if self.draw_sector:
                aux=()
                for a in self.fir.boundaries[self.sector]:
                    aux=aux+do_scale(a)
                    
                color = self.maps_colors['sector'].get()
                c.create_polygon(aux,fill=color,outline=color,tag=('sector','radisplay'))
                
        def _draw_lim_sector():
            # Dibujar límites del SECTOR
            if self.draw_lim_sector:
                aux=()
                for a in self.fir.boundaries[self.sector]:
                    aux=aux+do_scale(a)
                #c.create_polygon(aux,fill='',outline='blue',tag=('sector','radisplay'))
                color = self.maps_colors['lim_sector'].get()
                c.create_line(aux,fill=color,tag=('boundary','radisplay'))
                
        def _draw_tma():
            # Dibujar TMA's
            if self.draw_tmas:
                for a in fir.tmas:
                    aux=()
                    for i in range(0,len(a[0]),2):
                        aux=aux+do_scale((a[0][i],a[0][i+1]))
                    #c.create_line(aux,fill='gray60',tag=('tmas','radisplay'))
                    color = self.maps_colors['tma'].get()
                    c.create_line(aux,fill=color,tag=('tmas','radisplay'))
                    
                    
        def _draw_routes():
            # Dibujar las rutas
            if self.draw_routes:
                for a in fir.airways:
                    aux=()
                    for i in range(0,len(a[0]),2):
                        aux=aux+do_scale((a[0][i],a[0][i+1]))
                    color = self.maps_colors['routes'].get()
                    c.create_line(aux,fill=color,tag=('routes','radisplay'))
        def _draw_fix():
            # Dibujar fijos
            color = self.maps_colors['fix'].get()
            if self.draw_point:
                for a in fir.points:
                    if a[0][0]<>'_':
                        if len(a[0]) == 3:
                            (cx,cy) = do_scale(a[1])
                            radio = 5.0
                            c.create_oval(cx-radio,cy-radio,cx+radio,cy+radio,outline=color,fill='',width=2,tag=('points','radisplay'))
                            radio = 5.0/1.3
                            c.create_line(cx+radio,cy-radio,cx-radio,cy+radio,fill=color,tag=('points','radisplay'))
                            c.create_line(cx-radio,cy-radio,cx+radio,cy+radio,fill=color,tag=('points','radisplay'))
                        elif len(a[0]) == 2:
                            (cx,cy) = do_scale(a[1])
                            radio = 4.5
                            c.create_oval(cx-radio,cy-radio,cx+radio,cy+radio,outline=color,fill='',width=1,tag=('points','radisplay'))
                        else:    
                            (cx,cy) = do_scale(a[1])
                            coord_pol = (cx,cy-3.,cx+3.,cy+2.,cx-3.,cy+2.,cx,cy-3.)
                            c.create_polygon(coord_pol,outline=color,fill='',tag=('points','radisplay'),width=1)
        def _draw_fix_names():
            # Dibujar el nombre de los puntos
            color = self.maps_colors['fix_names'].get()
            if self.draw_point_names:
                for a in fir.points:
                    if a[0][0]<>'_':
                        c.create_text(do_scale(a[1]),text=a[0],fill=color,tag=('pointnames','radisplay'),anchor=SW,font='-*-Helvetica-Bold-*--*-9-*-')
        # Dibujar zonas delta
        def _draw_deltas():
            color = self.maps_colors['deltas'].get()
            if self.draw_deltas:
                for a in fir.deltas:
                    aux=()
                    for i in range(0,len(a[0]),2):
                        aux=aux+do_scale((a[0][i],a[0][i+1]))
                    c.create_line(aux,fill=color,tag=('deltas','radisplay'))

        def _draw_local_maps():   
            # Dibujar mapas locales
            for map_name in self.local_maps_shown:
                objects = fir.local_maps[map_name]
                for ob in objects:
                    if ob[0] == 'linea':
                        cx0 = float(ob[1])
                        cy0 = float(ob[2])
                        cx1 = float(ob[3])
                        cy1 = float(ob[4])
                        if len(ob) > 5:
                            col = ob[5]
                        else:
                            col = 'white'
                        (px0, py0) = do_scale((cx0,cy0))
                        (px1, py1) = do_scale((cx1,cy1))
                        col=SmartColor(col, self.intensity["MAP"]*self.intensity["GLOBAL"]).get()
                        c.create_line(px0, py0, px1, py1, fill=col, tag='local_maps')
                    elif ob[0] == 'arco':
                        cx0 = float(ob[1])
                        cy0 = float(ob[2])
                        cx1 = float(ob[3])
                        cy1 = float(ob[4])
                        start_value = float(ob[5])
                        extent_value = float(ob[6])
                        if len(ob) > 7:
                            col = ob[7]
                        else:
                            col = 'white'
                        (px0, py0) = do_scale((cx0,cy0))
                        (px1, py1) = do_scale((cx1,cy1))
                        col=SmartColor(col, self.intensity["MAP"]*self.intensity["GLOBAL"]).get()
                        c.create_arc(px0, py0, px1, py1, start=start_value, extent=extent_value, outline=col, style='arc', tag='local_maps')
                    elif ob[0] == 'ovalo':
                        cx0 = float(ob[1])
                        cy0 = float(ob[2])
                        cx1 = float(ob[3])
                        cy1 = float(ob[4])
                        if len(ob) > 5:
                            col = ob[5]
                        else:
                            col = 'white'
                        (px0, py0) = do_scale((cx0,cy0))
                        (px1, py1) = do_scale((cx1,cy1))
                        col=SmartColor(col, self.intensity["MAP"]*self.intensity["GLOBAL"]).get()
                        c.create_oval(px0, py0, px1, py1, fill=col, tag='local_maps')
                    elif ob[0] == 'rectangulo':
                        cx0 = float(ob[1])
                        cy0 = float(ob[2])
                        cx1 = float(ob[3])
                        cy1 = float(ob[4])
                        if len(ob) > 5:
                            col = ob[5]
                        else:
                            col = 'white'
                        (px0, py0) = do_scale((cx0,cy0))
                        (px1, py1) = do_scale((cx1,cy1))
                        col=SmartColor(col, self.intensity["MAP"]*self.intensity["GLOBAL"]).get()
                        c.create_rectangle(px0, py0, px1, py1, fill=col, tag='local_maps')
                    elif ob[0] == 'texto':
                        x = float(ob[1])
                        y = float(ob[2])
                        txt = ob[3]
                        if len(ob) > 4:
                            col = ob[4]
                        else:
                            col = 'white'
                        (px, py) = do_scale((x,y))
                        col=SmartColor(col, self.intensity["MAP"]*self.intensity["GLOBAL"]).get()
                        c.create_text(px, py, text=txt, fill=col,tag='local_maps',anchor=SW,font='-*-Times-Bold-*--*-10-*-')
                    elif ob[0] == 'draw_star' or ob[0] == 'draw_sid':
                        self.draw_SID_STAR(ob)
                    elif ob[0] == 'polyline':
                        self.draw_polyline(ob)
            c.addtag_withtag('radisplay','local_maps')
            c.lower('radisplay')

        _draw_sector()
        _draw_routes()
        _draw_local_maps()
        _draw_deltas()
        _draw_fix()
        _draw_fix_names()
        _draw_tma()
        _draw_lim_sector()
         
    def redraw(self):
        """Delete and redraw all elements of the radar display"""

        self.redraw_maps()
        
        # Refresh tracks
        for a in self.tracks:
            a.redraw()

        self.update_lads()
                
        return
        # Comprobar si hay PAC o VAC
        # First we reset state
        for acft in ejercicio:
            acft.vt.pac=acft.vt.vac=False
        for i in range(len(ejercicio)):
            for j in range(i+1,len(ejercicio)):
                if pac(ejercicio[i],ejercicio[j]):
                    ejercicio[i].vt.pac=True
                    ejercicio[j].vt.pac=True
                    
        c.delete('vac')
        poner_palote=False
        palote(poner_palote,c)
        for i in range(len(ejercicio)):
            for j in range(i+1,len(ejercicio)):
                line=()
                if vac(ejercicio[i],ejercicio[j]):
                    poner_palote=True
                    ejercicio[i].vt.vac=True
                    ejercicio[i].vt.pac=False
                    line=do_scale(ejercicio[i].get_coords())
                    ejercicio[j].vt.vac=True
                    ejercicio[j].vt.pac=False
                    line=line+do_scale(ejercicio[j].get_coords())
                    c.create_line(line,fill='red',tag='vac')
                    
        palote(poner_palote,c)
        #t=float(tlocal(t0))
        #ho=int(t/60/60)
        #m=int(t/60)-ho*60
        #s=int(t)-60*60*ho-60*m
        
    def reposition(self):
        self.redraw_maps()
        for vt in self.tracks:
            (x,y)=self.do_scale((vt.wx,vt.wy))
            vt.coords(x,y,None)
        self.update_lads()
        self.stop_separating = True  # If the repositioning code
                    # when refreshing the display while running
                    # the label separation algorithm, we want it
                    # to stop or there will be artifacts
        
    def do_scale(self,a):
        """Convert world coordinates into screen coordinates"""
        # return s((self.center_x,self.center_y),p(r((a[0],-a[1]),(self.x0,-self.y0)),self.scale))
        # Better to do the calculations inline to avoid the overhead of the function calling
        # on this very often called function
        return (self.center_x+(a[0]-self.x0)*self.scale,self.center_y+(-a[1]+self.y0)*self.scale)
        
    def undo_scale(self,a):
        """Convert screen coodinates into world coordinates"""
        return s((self.x0,self.y0),p(r((a[0],-a[1]),(self.center_x,-self.center_y)),1/self.scale))
        
    def toggle_routes(self):
        self.draw_routes = not self.draw_routes
        self.redraw_maps()    
    
    def toggle_point_names(self):
        self.draw_point_names = not self.draw_point_names
        self.redraw_maps()
        
    def toggle_point(self):
        self.draw_point = not self.draw_point
        self.redraw_maps()

    def toggle_sector(self):
        self.draw_sector = not self.draw_sector
        self.redraw_maps()
        
    def toggle_lim_sector(self):
        self.draw_lim_sector = not self.draw_lim_sector
        self.redraw_maps()

    def toggle_tmas(self):
        self.draw_tmas = not self.draw_tmas
        self.redraw_maps()
        
    def toggle_deltas(self):
        self.draw_deltas = not self.draw_deltas
        self.redraw_maps()
        
    def exit(self):
        ra_clearbinds(self)
        for t in self.tracks:
            t.destroy()
        del self.tracks
        self.top_level.destroy()
        # Avoid memory leaks due to circular references preventing
        # the garbage collector from discarding this object
        try: self.sendMessage = None  # Clear the callback to the protocol
        except: pass
        
    def set_element_intensity(self, v):
        """Changes the brightness of radar elements"""        
        def set_LAD_intensity():
            LAD.lad_color.set_intensity(self.intensity["GLOBAL"]*self.intensity["LADS"])
            LAD.super_lad_color.set_intensity(self.intensity["GLOBAL"]*self.intensity["LADS"])
            self.update_lads()
        
        def set_MAP_intensity():
            for sc in self.maps_colors.values():
                sc.set_intensity(self.intensity["GLOBAL"]*self.intensity["MAP"])
            self.redraw_maps()
        
        def set_TRACKS_intensity():
            for tracks in self.tracks:
                tracks.intensity=self.intensity["GLOBAL"]*self.intensity["TRACKS"]
            
        # Copy the values from the given dictionary into the stored intensity
        previous = self.intensity.copy()
        self.intensity.update(v)

        if v.has_key("GLOBAL") and v["GLOBAL"]!=previous["GLOBAL"]:
            set_LAD_intensity()
            set_MAP_intensity()
            set_TRACKS_intensity()
        if v.has_key("MAP") and v["MAP"]!=previous["MAP"]:
            set_MAP_intensity()
        if v.has_key("TRACKS") and v["TRACKS"]!=previous["TRACKS"]:
            set_TRACKS_intensity()
        if v.has_key("LADS") and v["LADS"]!=previous["LADS"]:
            set_LAD_intensity()
        
    def __del__(self):
        logging.debug("RaDisplay.__del__")

class Storm(object):
    def __init__(self,radisplay,e):
    
        self.radisplay=radisplay
        #dummy canvas
        canvas=radisplay.c
        
        # Start defining a storm
        self.x,self.y=e.x,e.y
        (self.wx, self.wy) = self.radisplay.undo_scale((e.x,e.y))
        self._motion_id = canvas.bind('<Motion>', self.update_storm_being_defined)
        self._button2_id = canvas.bind('<Button-2>', self.cancel_def_storm)
        self._button3_id = canvas.bind('<Button-3>', self.end_def_storm)
        self.selected = False

    def update_storm_being_defined(self,e=None):
        canvas=self.radisplay.c        
        canvas.delete('storm_defined')
        x,y=self.x,self.y
        r=sqrt((x-e.x)**2+(y-e.y)**2)
        x0,x1,y0,y1=x-r,x+r,y-r,y+r
        canvas.create_oval(x0, y0,x1,y1, fill="", outline="yellow", tags="storm_defined")
        r *= 1.4
        x0,x1,y0,y1=x-r,x+r,y-r,y+r
        canvas.create_oval(x0, y0,x1,y1, fill="", outline="yellow", tags="storm_defined", dash=(10,10))
        
    def cancel_def_storm(self,e=None):
        canvas=self.radisplay.c
        canvas.delete('storm_defined')
        canvas.unbind('<Motion>',self._motion_id)
        canvas.unbind('<Button-2>',self._button2_id)
        canvas.unbind('<Button-3>',self._button3_id)
        canvas.bind('<Button-2>',self.radisplay.b2_cb)
        canvas.bind('<Button-3>',self.radisplay.b3_cb)
        self.radisplay.b3_cb(e)

    def end_def_storm(self,e=None):
        canvas=self.radisplay.c
        canvas.delete('storm_defined')
        canvas.unbind('<Motion>',self._motion_id)
        canvas.unbind('<Button-2>',self._button2_id)
        canvas.unbind('<Button-3>',self._button3_id)
        x,y=self.x,self.y
        wx,wy=self.wx,self.wy
        self.wrx,self.wry=self.radisplay.undo_scale((e.x,e.y))
        self.r=sqrt((x-e.x)**2+(y-e.y)**2)
        canvas.bind('<Button-2>', self.radisplay.b2_cb)
        canvas.bind('<Button-3>', self.radisplay.b3_cb)
        self.radisplay.b3_cb(e)
        self.redraw()

    def delete(self):
        try:
            self.radisplay.storms.remove(self)
        except:
            pass
        s=str(self)
        self.radisplay.c.delete(s+'storm')

    def redraw(self):
        canvas=self.radisplay.c
        do_scale=self.radisplay.do_scale
        s=str(self)
        self.delete()
        
        # Create a new storm
        self.radisplay.storms.append(self)

        (x,y)=(self.x,self.y)=do_scale((self.wx,self.wy))
        rx,ry=do_scale((self.wrx,self.wry))
        r=sqrt((x-rx)**2+(y-ry)**2)
        x0,x1,y0,y1=x-r,x+r,y-r,y+r
        if self.selected == True:
            ts_color = 'red'
        else:
            ts_color = 'yellow'
        canvas.create_oval(x0, y0,x1,y1, fill="", outline=ts_color, tags=(s+'storm','storm'))
        r *= 1.4
        x0,x1,y0,y1=x-r,x+r,y-r,y+r
        canvas.create_oval(x0, y0,x1,y1, fill="", outline=ts_color, tags=(s+'storm','storm'), dash=(10,10))
        
    def auto_select_storm(self,event=None,min_pixel_distance=50):
        former_selection = self.selected
        distance = sqrt((self.x-event.x)**2+(self.y-event.y)**2)
        if distance < min_pixel_distance:
            self.selected = True
        else:
            self.selected = False
        if former_selection != self.selected:self.redraw()
        
        
        

    

# This is here just for debugging purposes
if __name__ == "__main__":
    import Pseudopilot
    root = Tk()
    #canvas = Canvas(root,bg='black')
    #vt = VisTrack(canvas,None)
    #label = vt.Label(vt)
    #label.redraw()
    #for i in label.items:
    #    print label[i].__dict__
    #l = canvas.create_line(0,0,1,1)
    #ra_tag_bind(canvas,l,"<2>",ra_tag_bind)
    #ra_tag_unbind(canvas,l,"<2>")
    #ra_cleartagbinds(l)
    fir=FIR('pasadas/Ruta-FIRMadrid/Ruta-FIRMadrid.fir')
    logging.getLogger('').setLevel(logging.DEBUG)    
    display=Pseudopilot.PpDisplay([],'testing','./img/crujisim.ico',fir,'CASTEJON')
    root.mainloop()
