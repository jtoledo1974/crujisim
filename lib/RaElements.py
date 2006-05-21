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
"""Building elements of a radar display"""

from math import floor
import datetime
import logging
import sys

from Tix import *
import tkFont

from twisted.internet import reactor

from FIR import *
from MathUtil import *

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

VOR     = 'VOR'
NDB     = 'NDB'
FIX     = 'FIX'
AD      = 'AD'

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

 
class RaFrame(object):
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
        try:
            if not self.windowed:
                self._master_ident = self._master.create_window((self._x, self._y), window=self.container, anchor=anchor)
        except AttributeError:
            logging.debug('RaFrame has no windowed attribute')

            
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
        self.container.lift()
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
        
        
class VFPVfield:
    """Basic entry field for RaVFPV"""
    def ___init___(self,master,**kw):
        self.flabel = ""                    #title of the entry field
        self.fentry = StringVar()           #data of the entry field
        self.masterframe = master           #master frame or canvas
        self.fsize = None                   #Size of the entry field in characters
        self.fl_fg = "black"                #Label foreground color
        self.fl_bg = "gray"                 #Label background color
        self.fe_fg = "black"                #Entry field foreground color
        self.fe_bg = "white"                #Entry field backgorund color
        
        
        self.frame = f = Frame(master,bg = self.fl_bg, anchor = NW)     #creates the frame container for both widgets
        self._build(**kw)
        #self._entry_colors={'background':self.fe_fg,
        #            'highlightbackground':self.bg,
        #            'highlightcolor':'Black',
        #            'foreground':self.bg,
        #            'selectbackground':self.bg,
        #            'selectforeground':self.fg,
        #            'insertbackground':self.bd,

        
    def _build(self,**kw):
        self._fentry_options={
            'insertwidth':5,
            'relief':FLAT,
            'borderwidth':0,
            'insertborderwidth':0}
        self.label = Label(f, bg = self.fl_bg, fg = self.fl_fg, text = self.flabel)
        self.label.pack(anchor = NW)
        self.entry = Entry(f, bg = self.fe_bg, fg = self.el_fg, textvariable = self.fentry,insertbackground = self.fe_bg,
                           **self._fentry_options)
        self.entry.pack(anchor = NW)
        self.configure(**kw)

            
    def disable(self):
        self.fentry.configure(state = DISABLED)
        
    def enable(self):
        self.fentry.configure(state = NORMAL)
        
    def configure(self,**kw):
        if kw.has_key('entry_bg'): self.entry['bg'] = kw['entry_bg']
        if kw.has_key ('entry_fg'): self.entry['fg'] = kw['entry_fg']
        if kw.has_key('label_bg'): self.label['bg'] = kw['label_bg']
        if kw.has_key ('label_fg'): self.label['fg'] = kw['label_fg']
        if kw.has_key('enable'): self.entry['state'] = NORMAL
        if kw.has_key('disable'): self.entry['state'] = DISABLE
        if kw.has_key('size'): self.entry['size'] = kw['size']
        if kw.has_key('field_label'): self.flabel = kw['field_label']
        if kw.has_key('field_entry'): self.fentry.set(kw['field_entry'])
        
        
        
        
class RaVFPV(RaFrame):
    pass
        
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
        
        RaFrame.__init__(self,master,**kw)
        
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
        x_padding, y_padding = 20, 40
        self.container.update_idletasks() # The geometry manager must be called
                                          # before we know the size of the widget
        x=x_padding
        y=self._master.winfo_height()-self.container.winfo_height()-y_padding
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

class GeneralInformationWindow(RaFrame):
    """A window containing generic information related to the position"""
    def __init__(self, radisplay, sectors, activesectors, **kw):
        """RaFrame containing info such as the QNH and the active sectors
        """
        def_opt={'position':(5,5), 'anchor':NW, 'closebutton':False, 'undockbutton':False}
        def_opt.update(kw)
        self.radisplay = radisplay
        master = radisplay.c
        self._qnh = 1013.8
        # The frame constructor method will call _build
        RaFrame.__init__(self, master, **def_opt)

        # Sector selection window
        self.sector_vars = {}
        self.sector_win = sw = RaFrame(master, position=(250,250), closebuttonhides=True)
        swc = sw.contents
        font = ('Arial', '9', 'bold')
        fg = 'gray90'
        bg = 'black'
        l = Label(swc, text='SECTORES', font=font, fg=fg, bg=bg)
        l.pack(side=TOP)
        for s in sectors:
            v = self.sector_vars[s] = IntVar()
            if s in activesectors: v.set(1)
            l = Checkbutton(swc, text=s, font=font, fg=fg, bg=bg, selectcolor=bg, variable=v, command=self.sector_set)
            l.pack(side=TOP, anchor=W)
        self.sector_win.hide()
        
    def _build(self, master=None, windowed=False, **kw):
        if windowed:
            def_opt={'label':'Reloj'}
            def_opt.update(kw)
        else:
            def_opt=kw
        RaFrame._build(self, master=master, windowed=windowed, **def_opt)
        font = ('Arial','9','bold')
        fg = 'gray90'
        bg = 'black'
        self.qnh_b = Button(self.contents, font=font,
                    foreground = fg,    #Very yellowed orange color
                    background = bg, text="QNH: %d"%floor(self._qnh))
        self.tl_b = Button(self.contents, font = font, fg = fg, bg=bg, text = 'TL: xx', state=DISABLED)
        self.mr_b = Button(self.contents, font = font, fg = fg, bg=bg, text = 'MULTIRAD', state=DISABLED)
        self.vid_b = Button(self.contents, font = font, fg = fg, bg=bg, text = 'SIN VIDEO', state=DISABLED)
        self.ac_b = Button(self.contents, font = font, fg = 'green', bg=bg, text = 'AC', command=self.toggle_pac)
        self.mode_b = Button(self.contents, font = font, fg = 'green', bg=bg, text = 'AUTONOMO', state=DISABLED)
        self.sect_b = Button(self.contents, font = font, fg = fg, bg=bg, text = 'SECT', command=self.toggle_sectors_window)
        
        self.qnh_b.pack(side= LEFT, padx=1, pady=1)
        self.tl_b.pack(side=LEFT, padx = 1, pady=1)
        #self.mr_b.pack(side=LEFT, padx = 1, pady=1)
        #self.vid_b.pack(side=LEFT, padx = 1, pady=1)
        self.ac_b.pack(side=LEFT, padx = 1, pady=1)
        #self.mode_b.pack(side=LEFT, padx = 1, pady=1)
        self.sect_b.pack(side=LEFT, padx = 1, pady=1)
        
    
    def toggle_sectors_window(self):
        self.sector_win.conmuta()
        self.sector_win.configure(position=self.sect_b.winfo_pointerxy())
    
    def toggle_pac(self):
        if self.ac_b['fg']=='green':
            self.ac_b['fg']='red'
            self.radisplay.pac = False
        else:
            self.ac_b['fg']='green'
            self.radisplay.pac = True    
        
    def sector_set(self):
        """Method called whenever sector checkboxes are modified"""
        self.radisplay.set_active_sectors([s for s, v in self.sector_vars.items()
                                           if v.get()])   
    def get_qnh(self):
        return self._qnh
    def set_qnh(self, value):
        self._qnh = value
        try: self.qnh_b['text'] = "QNH: %d"%floor(self._qnh)
        except AttributeError: pass            
    qnh = property(get_qnh, set_qnh)
        
    def configure(self,**options):
        RaFrame.configure(self,**options)
        
    def exit(self):
        del self.radisplay
    

class SmartColor(object):
    """Given a color string and a brightness factor calculates the output color"""
    
    # TODO this should probably be rewritten using properties as the VisTrack
    
    winfo_rgb       = None  # This function will be set when Tkinter is initialized
    known_values    = {}    # We keep a cache of calculations
    
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
        
        if self.known_values.has_key((color, factor)):
            self.color = self.known_values[(color, factor)]
            return
    
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
        self.known_values[(color, factor)] = self.color

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
        
        self.id = 'track'+str(id(self))    
        self._c             = canvas
        self._message_handler = message_handler
        self.do_scale       = do_scale
        self.undo_scale     = undo_scale
        
        # Defaults
        
        # Track attributes
        self._item_refresh_list = []  # List of label items that need to be refreshed
        # Set the default but don't trigger a redraw
        self._visible       = False
        self._mode          = 'pp'
        self._label_format  = 'pp'
        self._selected      = False
        self._assumed       = False
        self._plot_only     = False
        self._pac           = False
        self._vac           = False
        
        #object.__setattr__(self,'x',0)  # Screen coords
        # Can't set x directly until we also have a y
        self._x             = 0.  # X screen coordinate
        self._y             = 0.  # Y screen coordinate
        self._wx            = 0.  # X world coordinate
        self._wy            = 0.  # Y world coordinate
        self._intensity     = 1.0 # Color intensity
        self.future_pos = []  # List of future positions. Used for STCA calculations
        self.cs             = 'ABC1234'  # Callsign
        self.mach           = .82
        self.gs             = 250
        self.ias            = 200
        self.ias_max        = 340
        self.wake           = 'H'
        self.echo           = 'KOTEX'  # Controller input free text (max 5 letters)
        self.hdg            = 200
        self.track          = 200  # Magnetic track
        self.alt            = 150
        self.draw_cfl       = False  # Whether or not to draw the current cfl
        self.cfl            = 200
        self.pfl            = 350
        self.rate           = 2000  # Vertical rate of climb or descent
        self.adep           = 'LEMD'
        self.ades           = 'LEBB'
        self.type           = 'B737'
        self.radio_cs       = 'IBERIA'
        self.rfl            = 330       
        self.color          = SmartColor('gray')
        self.selected_border_color = SmartColor('yellow')
        
        self._last_t = datetime.datetime.today() - datetime.timedelta(days=1)  # Last time the radar was updated
        
        # Plot attributes
        self.plotsize=3
        self._pitem = None
        
        # Plot history
        self._h = []  # List of previous positions in real coord (not screen),
                      # and the associated canvas rectangle
        
        # Label
        self._l                     = self.Label(self)
        self._l_font_size           = 11
        self._l_font                = tkFont.Font(family="Helvetica",size=self.l_font_size)
        self.label_heading          = 117  # Label heading
        self.label_radius           = 30  # Label radius
        # lxo and lyo are the offsets of the label with respect to the plot
        self.label_xo               = self.label_radius * sin(radians(self.label_heading))
        self.label_yo               = self.label_radius * cos(radians(self.label_heading))
        # lx and ly are the actual screen coord of the label
        self.label_x                = self.x + self.label_xo
        self.label_y                = self.y + self.label_yo
        self.label_width            = 0
        self.label_height           = 0
        # Alternative versions of the label screen coordinates to try them out
        # while performing label separation
        self.label_x_alt            = self.label_x
        self.label_y_alt            = self.label_y
        self.label_heading_alt      = self.label_heading
        # Find the end of the leader line (it starts in the plot)
        self._ldr_x                 = self.label_x
        self._ldr_y                 = self.label_y + 10
        self._lineid                = None
        self._flashing              = False
        self.auto_separation        = True
        self.last_rotation          = 0  # Keeps the serial number of the last rotation event
                                         # so that auto rotation will try to move the last manually
                                         # moved label last.
        # Speed vector
        self.speed_vector           = (0,0)  # Final position of the speed vector in screen coords
        self._speed_vector_length   = 0.  # Length in minutes
            
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
            
        st=self.id
        dx,dy=x-self.x,y-self.y  # Calculate delta
        # Store the position in history if there has been a radar
        # update since the last one (more than five seconds ago)
        # TODO: The last radar update should be stored in a future radar
        # display class, rather than here.
        if t!=None and t>self._last_t+datetime.timedelta(seconds=5):
            while (len(self._h)>=6):
                (pos, rect_id) = self._h.pop()
                self._c.delete(rect_id)
            rx,ry=self.undo_scale((x,y))
            rect_id = self.draw_h_plot((x,y))
            self._h.insert(0,[(rx,ry), rect_id])
            self._last_t=t
            
        self.x,self.y=x,y  # New position
        
        # Label items refresh
        for i in self._item_refresh_list:
            self._l.refresh(i)
        self._item_refresh_list=[]
        # Move moveable elements        
        self._c.move(st,dx,dy)
        # Update position variables:
        self.label_x += dx
        self.label_y += dy
        self._ldr_x += dx
        self._ldr_y += dy
        # Reposition history points
        for (rpos, rect_id) in self._h:
            (x, y) = self.do_scale(rpos)
            self._c.coords(rect_id, x, y, x+1, y+1) 
        # Same with speed vector
        speed_vector = s((self.wx,self.wy),pr((self.speed_vector_length * self.gs,self.track)))
        (sx, sy) = self.do_scale(speed_vector)
        self._c.coords(st+'speedvector', self.x, self.y, sx, sy)
        
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
            
        self.redraw_h()  # History
        self.redraw_sv() # Speed vector
        # Leader and label
        if self.plot_only:
            self.delete_l()
        else:
            self.redraw_l()
        self.redraw_p()  # Plot

            
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
        s=self.id
        if self.assumed:
            size=size+1 # Assumed plots are a litle bigger to appear the same size
            self._pitem = self._c.create_polygon(x-size,y,x,y-size,x+size,y,x,y+size,x-size,y,
                                              outline=self.color.get(),fill='',
                                              tags=(s,s+'plot','track','plot'))
        else:
            self._pitem = self._c.create_polygon(x-size,y-size,x-size,y+size,x+size,y+size,
                                              x+size,y-size,x-size,y-size,
                                              outline=self.color.get(),fill='',
                                              tags=(s,s+'plot','track','plot'))
            
        def plot_b1(e=None):
            self._message_handler(self,'plot','<Button-1>',None,e)
        def plot_b3(e=None):
            self.plot_only=not self.plot_only
            
            # (Re)Do the bindings
        ra_tag_bind(self._c,self._pitem,'<Button-1>',plot_b1)
        ra_tag_bind(self._c,self._pitem,'<Button-3>',plot_b3)
        
    def delete_h(self):
        """Delete this track's history plots"""
        self._c.delete(self.id+'hist')
    def redraw_h(self):
        """Draw the history with the current options"""
        self.delete_h()
        for i in range(len(self._h)):
            (rx,ry), rect_id = self._h[i]
            (h0,h1) = self.do_scale((rx,ry))
            rect_id = self.draw_h_plot((h0,h1))
            self._h[i][1] = rect_id

    def draw_h_plot(self,(h0,h1)):
        s = self.id
        item = self._c.create_rectangle(h0,h1,h0+1,h1+1,outline=self.color.get(),
                                 tags=(s,s+'hist','track'))
        return item
            
    def delete_sv(self):
        """Delete the track's speed vector"""
        # Speed vector
        s = self.id
        self._c.delete(s+'speedvector')
    def redraw_sv(self):
        """Redraw this track's speed vector"""
        self.delete_sv()
        if not self.visible: return
        st = self.id
        speed_vector = s((self.wx,self.wy),pr((self.speed_vector_length * self.gs,self.track)))
        screen_sv = self.do_scale(speed_vector)
        (sx,sy) = screen_sv
        self._c.create_line(self.x, self.y, sx, sy, fill=self.color.get(),
                           tags=(st,st+'speedvector','track'))
    def delete_l(self):
        c = self._c
        s = self.id
        
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
        c  = self._c
        cl = self.color.get()
        s  = self.id
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
                               tags=(s,s+'label', s+'selection_box', 'track'))
        # Leader line
        id=c.create_line(self.x, self.y, self._ldr_x, self._ldr_y, fill=self.color.get(),
                      tags=(s,s+'leader','track'))
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
        self._c.move(self.id+'label', dx, dy)
        # Leader line
        self._ldr_y = self.label_y + 10
        if (self.label_x - self.x) > 0:
            self._ldr_x = self.label_x
        else:
            self._ldr_x = self.label_x + self.label_width
        ldr_x_offset,ldr_y_offset = self._ldr_x-self.x, self._ldr_y-self.y
        self.label_heading = 90.0-degrees(atan2(ldr_y_offset, ldr_x_offset))
        self._c.coords(self.id+'leader',self.x,self.y,self._ldr_x,self._ldr_y)
                    
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
        self._c.coords(self.id+'leader',self.x,self.y,newx,newy)
        
        dx=new_l_x-self.label_x
        dy=new_l_y-self.label_y
        self.label_x += dx
        self.label_y += dy
        self.label_xo += dx
        self.label_yo += dy
        self._c.move(self.id+'label', dx, dy)
        
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
                try: f(*kw)
                except:
                    logging.debug("Error while executing timer", exc_info=True)
        
        if not VisTrack.timer_id:
            VisTrack.timer_id = reactor.callLater(0.5,timer)
            
    def reset_timer(self):
        if VisTrack.timer_id: self.timer_id.cancel()
        VisTrack.timer_callbacks = []                    
    
    # Getters and setters. This gives much better perfomance than
    # using the __setattr__ method
        
    def get_visible(self): return self._visible
    def set_visible(self, value):
        if value == self._visible: return
        self._visible = value
        self.redraw()
    visible = property(get_visible, set_visible)
    
    def get_mode(self): return self._mode
    def set_mode(self, value):
        if value == self._mode: return
        self._mode = value
        if value=='pp': self.label_format='pp'
        elif value=='atc': self.label_format='atc'
    mode = property(get_mode, set_mode)
    
    def get_label_format(self): return self._label_format
    def set_label_format(self, value):
        if value == self._label_format: return
        self._label_format = value
        if self.visible:
            self.redraw_l()        
    label_format = property(get_label_format, set_label_format)
    
    def get_selected(self): return self._selected
    def set_selected(self, value):
        if value == self._selected: return
        self._selected = value
        if self.visible: self.redraw_l()
    selected = property(get_selected, set_selected)    
    
    def get_assumed(self): return self._assumed
    def set_assumed(self, value):
        if value == self._assumed: return
        self._assumed = value
        if self.visible:
            if value: self.color.set(self.ASSUMED_COLOR)
            else:  self.color.set(self.NONASSUMED_COLOR)
            self._l.cs.color.set(self.color.get_basecolor())
            self.redraw()
    assumed = property(get_assumed, set_assumed)
        
    def get_plot_only(self): return self._plot_only
    def set_plot_only(self, value):
        if value == self._plot_only: return
        self._plot_only = value
        self.redraw()
    plot_only = property(get_plot_only, set_plot_only)
        
    def get_pac(self): return self._pac
    def set_pac(self, value):
        if value == self._pac: return
        self._pac = value
        if self.visible:
            self._item_refresh_list.append('pac')
            self.redraw_l()
            if value and self.plot_only:
                self.plot_only = False
    pac = property(get_pac, set_pac)
        
    def get_vac(self): return self._vac
    def set_vac(self, value):
        if value == self._vac: return
        self._vac = value
        if self.visible:
            self._item_refresh_list.append('vac')
            self.redraw_l()
            if value and self.plot_only:
                self.plot_only = False
    vac = property(get_vac, set_vac)

    def get_x(self): return self._x
    def set_x(self, value):
        if value == self._x: return
        self._x = value
        (self._wx,self._wy) = self.undo_scale((self.x,self.y))
    x = property(get_x, set_x)
        
    def get_y(self): return self._y
    def set_y(self, value):
        if value == self._y: return
        self._y = value
        (self._wx, self._wy) = self.undo_scale((self.x, self.y))
    y = property(get_y, set_y)

    def get_wx(self): return self._wx
    def set_wx(self, value):
        if value == self._wx: return
        self._wx = value
        (self._x, self._y) = self.do_scale((self.wx, self.wy))
    wx = property(get_wx, get_wx)
    
    def get_wy(self): return self._wy
    def set_wy(self, value):
        if value == self._wy: return
        self._wy = value
        (self._x, self._y) = self.do_scale((self.wx, self.wy))
    wy = property(get_wy, get_wy)
    
    def get_intensity(self): return self._intensity
    def set_intensity(self, value):
        # TODO setting the intensity should not force a full redraw.
        # only item reconfiguration, the same way that RaMap does.
        # Redrawing each track is not scalable at all
        if value == self._intensity: return
        self._intensity = value
        l = self._l
        for el in self, l.cs, l.vac, l.pac, l.wake:
            el.color.set_intensity(value)
        self.redraw()
    intensity = property(get_intensity, set_intensity)
   
    def get_l_font_size(self): return self._l_font_size
    def set_l_font_size(self, value):
        if value == self._l_font_size: return
        self._l_font_size = value
        if self.auto_separation: self.label_radius=value*3
        #self.redraw_l()
        self._l.reformat()
    l_font_size = property(get_l_font_size, set_l_font_size)
   
    def get_flashing(self): return self._flashing
    def set_flashing(self, value):
        if value == self._flashing: return
        self._flashing = value
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
    flashing = property(get_flashing, set_flashing)
   
    def get_speed_vector_length(self): return self._speed_vector_length
    def set_speed_vector_length(self, value):
        if value == self._speed_vector_length: return
        self._speed_vector_length = value
        self.redraw_sv()
    speed_vector_length = property(get_speed_vector_length, set_speed_vector_length)

    def get_label_item(self, item): return getattr(self, '_'+item)
    def set_label_item(self, item, value):
        try:
            if value == getattr(self, '_'+item): return
        except: pass  # This is to account for the first time it is set
        setattr(self, '_'+item, value)
        if self.visible:
            self._item_refresh_list.append(item)
            if item=='alt': self._item_refresh_list.append('cfl')
            if item=='cfl': self.draw_cfl = True
    cs   = property(lambda s: s.get_label_item('cs'),   lambda s,v: s.set_label_item('cs', v))
    alt  = property(lambda s: s.get_label_item('alt'),  lambda s,v: s.set_label_item('alt', v))
    rate = property(lambda s: s.get_label_item('rate'), lambda s,v: s.set_label_item('rate', v))
    cfl  = property(lambda s: s.get_label_item('cfl'),  lambda s,v: s.set_label_item('cfl', v))
    gs   = property(lambda s: s.get_label_item('gs'),   lambda s,v: s.set_label_item('gs', v))
    mach = property(lambda s: s.get_label_item('mach'), lambda s,v: s.set_label_item('mach', v))
    wake = property(lambda s: s.get_label_item('wake'), lambda s,v: s.set_label_item('wake', v))
    spc  = property(lambda s: s.get_label_item('spc'),  lambda s,v: s.set_label_item('spc', v))
    echo = property(lambda s: s.get_label_item('echo'), lambda s,v: s.set_label_item('echo', v))
    hdg  = property(lambda s: s.get_label_item('hdg'),  lambda s,v: s.set_label_item('hdg', v))

    def destroy(self):
        self.delete()
        self._l.destroy()
        del(self._message_handler)
        del(self.do_scale)
        del(self.undo_scale)
        
    def __del__(self):
        logging.debug("VisTrack.__del__ %s"%self.cs)
            
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
                
            #def __del__(self):
            #    logging.debug("LabelItem.__del__")
                
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
            s = self.vt.id
            
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
            s = self.vt.id
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
                c.itemconfig(i.i,tags=(s,s+'labelitem', s+'label','track'))
                    
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
                self.gs.t = "%02d"%round(vt.gs/10)
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
            self.vt._message_handler(self.vt,'cs','<Button-1>',None,e)
        def cs_b3(self,e):
            self.vt._message_handler(self.vt,'cs','<Button-3>',None,e)
            def ok():
                self.vt._message_handler(self.vt,'transfer',None,None,e)
            # Only assumed traffic may be transferred
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
                if ent_rate['bg'] == 'red':
                    force = True
                else:
                    force = False
                d = self.vt._message_handler(self.vt,'rate','update',(rate, force),e)
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
                self.vt._message_handler(self.vt,'rate','update',('std', None),e)
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
            
        #def __del__(self):
        #    logging.debug("Label.__del__")

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
        self.adep = self.get_acft_or_point(e.x,e.y)
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
        (x0, y0) = self.adep.x,self.adep.y
        ades = self.radisplay.undo_scale((e.x, e.y))
        lad_xsize = ades[0] - self.adep.wx
        lad_ysize = ades[1] - self.adep.wy
        angulo = 90.0 - degrees( atan2( lad_ysize, lad_xsize ) )
        if angulo < 0.0: angulo += 360.0
        dist = self.round_down(sqrt( lad_xsize * lad_xsize + lad_ysize * lad_ysize))
        time_min = 60.0 * dist / self.adep.gs
        lad_center_x = (x0 + e.x)/2
        lad_center_y = (y0 + e.y)/2
        canvas.create_line(x0, y0,e.x, e.y, fill=self.lad_color.get(), tags="lad_defined")
        lad_text1 = "A: %03d" % angulo
        lad_text2 = "D: %03d" % dist
        # Check if LAD begins in a point or in a plane
        if self.adep.gs < 10.:
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
        self.ades=self.get_acft_or_point(e.x,e.y)
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
        
        (xinitA, yinitA) = (self.adep.wx,self.adep.wy)
        (xinitB, yinitB) = (self.ades.wx,self.ades.wy)
        lad_xdif = xinitB - xinitA
        lad_ydif = yinitB - yinitA
        current_azimuth = 90.0 - degrees( atan2 (lad_ydif, lad_xdif) )
        if current_azimuth < 0.0: current_azimuth += 360.0
        lad_lines = 2 # 2 lines of text if planes won't cross; 4 if they will cross
        text1 = "A: %03d" % current_azimuth
        current_distance = self.round_down(sqrt(lad_xdif*lad_xdif + lad_ydif*lad_ydif))
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
        min_dist_time = self.compute_mindisttime(xinitA, yinitA, self.adep.track, self.adep.gs, xinitB, yinitB, self.ades.track, self.ades.gs)
        # Limit min_dist_time<500 to avoid overflow problems when min_dist_time is too high
        if (min_dist_time != None) and (min_dist_time > 0.0)and (min_dist_time<500.0):
            # Flights will cross
            min_dist = self.compute_mindist(xinitA, yinitA, self.adep.track, self.adep.gs, xinitB, yinitB, self.ades.track, self.ades.gs)
            lad_lines = 4 # 4 lines of text in LAD square

            text3 = "T: %03d" % min_dist_time
            text4 = "C: %05.1f" % min_dist
            text_lad += "\n"+text3+"\n"+text4
            
        lad_line_height = label_font.metrics('ascent')
        lad_label_anchor=self.get_anchor(current_azimuth)
        (x_lad,y_lad) = self.get_lad_label_position(current_azimuth,xm,ym,10)
        self.text_id1 = canvas.create_text(x_lad,y_lad,text=text_lad, fill=self.lad_color.get(), tags=(s+'lad',s+'text'),justify=LEFT,**lad_label_anchor)
            
        ra_tag_bind(canvas,self.text_id1,'<Button-1>',self.toggle_superlad)
        ra_tag_bind(canvas,self.text_id1,'<Button-2>',self.delete)
            
        if (self.superlad) and (min_dist_time != None) and (min_dist_time > 0.0):
            # Flights will cross
            size=2
            (posAx, posAy, posBx, posBy) = self.compute_cross_points(xinitA, yinitA, self.adep.track, self.adep.gs, xinitB, yinitB, self.ades.track, self.ades.gs)
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
        return self.round_down(sqrt((posAx-posBx)*(posAx-posBx) + (posAy-posBy)*(posAy-posBy)))
    
    def round_down(self,a):
        b = int(10.0*a)
        return b / 10.0

class RaMap(object):
    """A static radar map"""
    
    def __init__(self, canvas, do_scale, intensity=1.0):
        self.id                 = 'map'+str(id(self))
        self.canvas             = canvas
        self.do_scale           = do_scale
        self.texts              = {}  # Text items attributes
        self.polylines          = {}  # Polyline items attributes
        self.polygons           = {}  # Polygon items attributes
        self.arcs               = {}  # Arc items attributes
        self.symbols            = {}  # Symbol items attributes
        self._intensity         = intensity
        self.hidden             = False
    
    def add_text(self, text, pos, color='gray'):
        c = SmartColor(color, self.intensity).get()
        i = self.canvas.create_text(self.do_scale(pos), text=text, fill=c,
                          tag=(self.id, self.id+'text','map'),anchor=SW,font='-*-Helvetica-Bold-*--*-9-*-')
        self.texts[i] = (text, pos, color)
        
    def add_polyline(self, *coords, **kw):
        try: color = kw['color']
        except: color = 'gray'
        c = SmartColor(color, self.intensity).get()
        kw = {"fill": c, 'tag': (self.id, 'map')}
        new_coords = [self.do_scale(p) for p in coords]
        i = self.canvas.create_line(*new_coords, **kw)
        self.polylines[i] = (color, coords)
        
    def add_polygon(self, *coords, **kw):
        try: color = kw['color']
        except: color = 'gray'
        c = SmartColor(color, self.intensity).get()
        kw = {"fill": c, 'tag': (self.id, 'map')}
        new_coords = [self.do_scale(p) for p in coords]
        i = self.canvas.create_polygon(*new_coords, **kw)
        self.polygons[i] = (color, coords)    
        
    def add_arc(self, top_left, bottom_right, start, extent, color='gray'):
        c = SmartColor(color, self.intensity).get()
        tl, br = self.do_scale(top_left), self.do_scale(bottom_right)
        i = self.canvas.create_arc(tl, br, start=start, extent=extent,
                     outline=c, style='arc', tag=(self.id, self.id+'arc','map'))
        self.arcs[i] = (top_left, bottom_right, start, extent, color)
        
    def add_symbol(self, type, pos, color='gray'):
        c = SmartColor(color, self.intensity).get()
        (cx,cy) = self.do_scale(pos)
        tags = [self.id, self.id+'symbol', 'map']
        canvas = self.canvas
        if type == VOR:
            radio = 5.0
            i = canvas.create_oval(cx-radio,cy-radio,cx+radio,cy+radio,outline=c,
                          fill='',width=2)
            tags.append(self.id+'symbol'+str(i))
            tags_outline = tags + [self.id+'symbol'+str(i)+'outline', self.id+'symboloutline']
            canvas.itemconfigure(i, tag=tuple(tags_outline))
            radio = 5.0/1.3
            tags = tuple(tags + [self.id+'symbol'+str(i)+'fill'])
            canvas.create_line(cx+radio,cy-radio,cx-radio,cy+radio,fill=c,tag=tags)
            canvas.create_line(cx-radio,cy-radio,cx+radio,cy+radio,fill=c,tag=tags)
        elif type == NDB:
            radio = 4.5
            i = canvas.create_oval(cx-radio,cy-radio,cx+radio,cy+radio,outline=c,fill='',width=1)
            tags += [self.id+'symbol'+str(i), self.id+'symbol'+str(i)+'outline', self.id+'symboloutline']
            tags = tuple(tags)
            canvas.itemconfigure(i, tag=tags)
        elif type == FIX:
            coord_pol = (cx,cy-3.,cx+3.,cy+2.,cx-3.,cy+2.,cx,cy-3.)
            i = canvas.create_polygon(coord_pol,outline=c,fill='',width=1)
            tags += [self.id+'symbol'+str(i), self.id+'symbol'+str(i)+'outline', self.id+'symboloutline']
            tags = tuple(tags)
            canvas.itemconfigure(i, tag=tags)
        self.symbols[i]=(type, pos, color, (cx,cy))
        
    def reposition(self):
        """Reset coordinates according to the parent's coordinate system"""
        for item, (color, coords) in self.polylines.items()+self.polygons.items():
            new_coords = [c for p in coords for c in self.do_scale(p)]
            self.canvas.coords(item, *new_coords)
        for item, (type, pos, color, screen_pos) in self.symbols.items():
            new_screen_pos = self.do_scale(pos)
            (dx, dy) = r(new_screen_pos, screen_pos)
            self.canvas.move(self.id+'symbol'+str(item), dx, dy)
            self.symbols[item] = (type, pos, color, new_screen_pos)
        for item, (text, pos, color) in self.texts.items():
            new_coords = [c for c in self.do_scale(pos)]
            self.canvas.coords(item, *new_coords)
        for item, (top_left, bottom_right, start, extent, color) in self.arcs.items():
            new_coords = [c for p in (top_left, bottom_right) for c in self.do_scale(p)]
            self.canvas.coords(item, *new_coords)
            
    def hide(self):
        if self.hidden: return()
        for item in self.polylines.keys()+self.polygons.keys()+self.texts.keys():
            self.canvas.itemconfigure(item, fill='')
        self.canvas.itemconfigure(self.id+'symbol', fill='')
        self.canvas.itemconfigure(self.id+'symboloutline', outline='')
        self.canvas.itemconfigure(self.id+'arc', outline = '')
        self.hidden = True
            
    def show(self, force=False):
        if not self.hidden and not force: return
        # For performance reasons we want to group the itemconfig
        # so first we set temporary tags, and then do the itemconfig for each group
        # of items with the same color
        tags = {}  
        for item, (color, coords) in self.polylines.items()+self.polygons.items():
            color = SmartColor(color, self.intensity).get()
            tag = 'refill'+color
            self.canvas.addtag_withtag(tag, item)
            tags[tag] = color
        for item, (type, pos, color, screen_pos) in self.symbols.items():
            color = SmartColor(color, self.intensity).get()
            tag = 'refill'+color
            self.canvas.addtag_withtag(tag, self.id+'symbol'+str(item)+'fill')
            tags[tag] = color
            tag = 'reoutline'+color
            self.canvas.addtag_withtag(tag, self.id+'symbol'+str(item)+'outline')
            tags[tag] = color
        for item, (text, pos, color) in self.texts.items():
            color = SmartColor(color, self.intensity).get()
            tag = 'refill'+color
            self.canvas.addtag_withtag(tag, item)
            tags[tag] = color
        for item, (top_left, bottom_right, start, extent, color) in self.arcs.items():
            color = SmartColor(color, self.intensity).get()
            tag = 'reoutline'+color
            self.canvas.addtag_withtag(tag, item)
            tags[tag] = color

        for (tag, color) in tags.items():
            if tag.startswith('refill'):
                self.canvas.itemconfigure(tag, fill=color)
            elif tag.startswith('reoutline'):
                self.canvas.itemconfigure(tag, outline=color)
            else:
                logging.error("Impossible scenario in RaMap.show()")
            self.canvas.dtag(tag, tag)
        self.hidden = False
            
    def toggle(self):
        if self.hidden: self.show()
        else: self.hide()
            
    def get_intensity(self): return self._intensity
    def set_intensity(self, value):
        self._intensity = value
        if not self.hidden: self.show(force=True)
    intensity = property(get_intensity, set_intensity)
        
    def destroy(self):
        self.canvas.delete(self.id)
        del self.canvas
        del self.do_scale    

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
    canvas = Canvas(root,bg='black')
    def message_handler(*a):
        pass
    def do_scale(a): return a
    def undo_scale(a): return a
    vt = VisTrack(canvas,message_handler, do_scale, undo_scale)
    vt.x = 2
    label = vt.Label(vt)
    label.redraw()
    for i in label.items:
        print label[i].__dict__
    l = canvas.create_line(0,0,1,1)
    ra_tag_bind(canvas,l,"<2>",ra_tag_bind)
    ra_tag_unbind(canvas,l,"<2>")
    ra_cleartagbinds(l)
    
