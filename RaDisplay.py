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
"""Classes useful for designing a radar display"""

from math import *
from Tkinter import *
import tkFont
import logging
from Tix import *
import avion  # Needed for do_scale and do_unscale because unfortunately
              # we are not using the native canvas scaling

_radialogs={} # List of all dialogs, to avoid duplicates

# Because tkinter will not free the command for the binding when removing
# binding canvas elements, we have to keep track of every binding to make sure
# the the unbind is properly handled, including the funcid
_tag_binds = []
def ra_tag_bind(canvas, tag_or_id, sequence, func):
    """Creates a tag binding and stores information for later deletion"""
    if tag_or_id==None: return
    funcid = canvas.tag_bind(tag_or_id, sequence, func, add=True)
    _tag_binds.append([canvas, tag_or_id, sequence, funcid])

def ra_tag_unbind(canvas_remove, tag_remove, sequence_remove):
    for b in _tag_binds:
        [canvas,tag,seq,funcid] = b
        if (tag == tag_remove) and (canvas == canvas_remove) and (sequence_remove == seq):
            canvas.tag_unbind(tag, seq, funcid)
            _tag_binds.remove(b)

def ra_clearbinds(tag_to_remove):
    for b in _tag_binds:
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
            closebutton -- Boolean (default true)
            dockbutton -- Boolean (default True)
            closebuttonhides -- Boolean (default False)
        """

        self._master=master
        self._kw=kw  # We need to save it for rebuilding in toggle_windowed
        self._closebutton=self._label=None
        self.bd,self.bg,self.fg='#006c35','#003d1e','#bde20B'
        self._bindings=[]
        self._x,self._y=(0,0)

        # Build the frame
        self._build(master, windowed=False, **kw)
        # Place it
        self._place()
                            
    def _build(self, master=None, windowed=False, **kw):
        """Build the GUI elements, either as a canvas element, or as a toplevel"""
        if not windowed:
            # Build a frame as a Canvas element
            self.container=Frame(master,background=self.bd)
            self.contents=Frame(self.container,background=self.bg,borderwidth=5)
            self.contents.pack(padx=5,pady=5,side=BOTTOM,fill=BOTH,expand=1)
            if kw.has_key('label') and kw['label']<>'':
                self._label=Label(self.container,text=kw['label'],background=self.bd,foreground='Black')
                self._label.pack(side=LEFT,padx=5)
            if not kw.has_key('closebutton') or kw['closebutton']:
                self._closebutton=Label(self.container,text='X',background=self.bd,foreground='Black')
                self._closebutton.pack(side=RIGHT)
                if (self._kw.has_key('closebuttonhides')
                    and self._kw['closebuttonhides']):
                    i=self._closebutton.bind('<Button-1>',self.hide)
                else:
                    i=self._closebutton.bind('<Button-1>',self.close)                    
                self._bindings.append((self._closebutton,i,"<Button-1>"),)
            if not kw.has_key('dockbutton') or kw['dockbutton']:
                self._undockbutton=Label(self.container,text='O',bg=self.bd,fg='Black')
                self._undockbutton.pack(side=RIGHT)
                i=self._undockbutton.bind('<Button-1>',self.toggle_windowed)
                self._bindings.append((self._undockbutton,i,'<Button-1>'),)

            # Frame dragging
            def drag_frame(e=None):
                """Move the frame as many pixels as the mouse has moved"""
                self._master.move(self._master_ident,e.x_root-self._x,e.y_root-self._y)
                self._x=e.x_root
                self._y=e.y_root
            def drag_select(e=None):
                if self._label<>None:
                    i=self._label.bind('<Motion>',drag_frame)
                    self._bindings.append((self._label,i,'<Motion>'),)
                i=self.container.bind('<Motion>',drag_frame)
                self._bindings.append((self.container,i,'<Motion>'),)
                self._x=e.x_root
                self._y=e.y_root
                self.container.lift()
            def drag_unselect(e=None):
                if self._label<>None:
                    self._label.unbind('<Motion>')
                self.container.unbind('<Motion>')
            if self._label<>None:
                i=self._label.bind('<Button-2>',drag_select)
                j=self._label.bind('<ButtonRelease-2>',drag_unselect)
                self._bindings.append((self._label,i,'<Button-2>'),)
                self._bindings.append((self._label,j,'<ButtonRelease-2>'),)
            i=self.container.bind('<Button-2>',drag_select)
            j=self.container.bind('<ButtonRelease-2>',drag_unselect)
            self._bindings.append((self.container,i,'<Button-2>'),)
            self._bindings.append((self.container,j,'<ButtonRelease-2>'),)

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
            self.contents.pack(padx=5,pady=5)
            self.container=t
            self.windowed=True
            
    def _place(self):
        # If we are not given any position info, just use 0,0
        if not self._kw.has_key('position'):
            pos=(0,0)
        else:
            pos=self._kw['position']
        # We reset x and y only if this is the first time we are placing the
        # frame. If the user moved it himself, then use the las known position.
        if self._x==0 and self._y==0:
            (self._x, self._y) = pos

        # Currently the master must be a canvas if not windowed
        if not self.windowed:
            self._master_ident = self._master.create_window((self._x, self._y), window=self.container)

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

    def close(self,e=None):
        """Close the RaFrame and completely delete it"""
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
        logging.debug("RaFrame.hide")
        if self.windowed:
            self.container.withdraw()
        else:
            self._master.delete(self._master_ident)
        
    def toggle_windowed(self,e=None):
        self.close()
        self.windowed=not self.windowed
        self._build(master=self._master, windowed=self.windowed, **self._kw)
        self._place()
        
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
            esc_closes -- If true, a global binding is defined
                to close the frame when escape is pressed. Default true
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
        self._frame_colors={'background':self.bg,
                            'highlightbackground':self.bg,
                            'highlightcolor':'Black'}
        self._label_colors={'background':self.bg,
                            'highlightbackground':self.bd,
                            'highlightcolor':'Black',
                            'foreground':self.fg,
                            'activebackground':self.bd,
                            'activeforeground':self.fg,
                            'disabledforeground':''}
        self._button_colors={'background':self.bd,
                            'highlightbackground':self.bg,
                            'highlightcolor':'Black',
                            'foreground':self.fg,
                            'activebackground':self.bg,
                            'activeforeground':self.fg,
                            'disabledforeground':''}
        self._entry_colors={'background':self.bg,
                            'highlightbackground':self.bg,
                            'highlightcolor':'Black',
                            'foreground':self.fg,
                            'selectbackground':self.bd,
                            'selectforeground':self.fg}
        
        # Dialog elements
        f0 = Frame(self.contents, **self._frame_colors) # Text
        f0.pack(side=TOP, pady=1, fill=BOTH)        
        f1 = Frame(self.contents, **self._frame_colors) # Dialog contents
        f1.pack(side=TOP, pady=1, fill=BOTH)
        f2a = Frame(self.contents, **self._frame_colors) # aux frame
        f2a.pack(side=BOTTOM, fill=BOTH)
        f2 = Frame(f2a, **self._frame_colors) # Default dialog buttons
        f2.pack(side=RIGHT, fill=BOTH)

        if kw.has_key('text'):
            l=Label(f0,text=kw['text'], **self._label_colors)
            l.pack(side=LEFT)        
        but_accept = Button(f2, text="Aceptar", default='active', **self._button_colors)
        but_accept.pack(side=LEFT)
        but_accept['command'] = self.accept
        if kw.has_key('ok_callback'):
            Label(f2,text=' ', **self._label_colors).pack(side=LEFT)
            but_cancel = Button(f2, text="Cancelar", **self._button_colors)
            but_cancel.pack(side=LEFT)
            but_cancel['command'] = self.close
            
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
        def_opt={'position':(50,22), 'closebutton':False, 'undockbutton':False}
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
                    font='-*-Times-Bold-*--*-20-*-',
                    foreground='Yellow',
                    background=self.bg)
        self._time.grid()
        
    def configure(self,**options):
        RaFrame.configure(self,**options)
        if options.has_key('time'):
            self._time['text']=options['time']

class RaTabular(RaFrame):
    """Generic frame containing tabular info"""
    def __init__(self, master, **kw):
        def_opt={'position':(500,222)}
        def_opt.update(kw)
        self._items=[]  # We need to make a copy of the items to rebuild
                        # the list
        # The frame constructor method will call _build
        RaFrame.__init__(self, master=master, **def_opt)
    
    def _build(self, master=None, windowed=False, **kw):
        import Tix
        RaFrame._build(self, master=master, windowed=windowed, **kw)
        self._slist=Tix.ScrolledListBox(self.contents)
        self._list_colors={'background':self.bg,
                            'highlightbackground':self.bg,
                            'highlightcolor':'Black',
                            'foreground':self.fg,
                            'selectbackground':self.bd,
                            'selectforeground':self.fg}
        self.list=self._slist.listbox
        self.list.configure(**self._list_colors)
        self.list.configure(height=6, width=30)
        for i, elements in enumerate(self._items):
            self.list.insert(i, *elements)
        self._slist.grid()
        
    def insert(self, index, *elements):
        """Insert a list item (use text='text to show')"""
        self.list.insert(index, *elements)
        # TODO we should deal with more Tk constants here.
        if index==END:
            index=len(self._items)
        self._items.insert(index, elements)
        
    
class VisTrack(object): # ensure a new style class
    """Visual representation of a radar track on either a pseudopilot display
    or a controller display"""
    
    allitems = [ 'cs','alt','cfl','gs','mach','wake','spc','echo','hdg','pac','vac']                
    
    def __init__(self, canvas, message_handler, **kw):
        """Construct a radar track inside the parent display.

        Instantiation arguments:
        canvas -- parent canvas
        message_handler -- function that will deal with events generated by the track
        Options:
            position -- (x,y) tuple with screen coordinates of the plot
        """
        self._c=canvas
        self._message_handler=message_handler
        self._kw=kw  # We save it just in case
        
        # Defaults

        # Track attributes
        self._item_refresh_list = []  # List of label items that need to be refreshed
        # Set the default but don't trigger a redraw
        object.__setattr__(self,'visible',False)
        object.__setattr__(self,'label_format', 'pp')
        object.__setattr__(self,'selected', False)
        object.__setattr__(self,'assumed',False)
        object.__setattr__(self,'plot_only',False)
        object.__setattr__(self,'pac',False)
        object.__setattr__(self,'vac',False)

        self.x,self.y = 0,0
        self.cs='ABC1234'  # Callsign
        self.mach=.82
        self.gs=250
        self.ias=200
        self.ias_max=340
        self.wake='H'
        self.echo='KOTEX'  # Controller input free text (max 5 letters)
        self.hdg=200
        self.alt=150
        self.cfl=200
        self.pfl=350
        self.rate=2000  # Vertical rate of climb or descent        
        
        
        self.assumedcolor='green'
        self.nonassumedcolor='gray'
        self.color=self.nonassumedcolor
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
        # Find the end of the leader line (it starts in the plot)
        self._ldr_x = self.label_x
        self._ldr_y = self.label_y + 10
        self._lineid = None
        self.auto_separation=True
        
        # Speed vector
        self.speed_vector=(0,0)  # Final position of the speed vector in screen coords
        self._svid=None

        
        if kw.has_key('position'):
            (x,y)=(self.x,self.y)=kw['position']
            
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
        if (t>self._last_t+5/60./60.):
            while (len(self._h)>=6): self._h.pop()
            rx,ry=avion.do_unscale((x,y))
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
        # Reposition speed vector
        (sx,sy)=self.speed_vector
        self._c.coords(self._svid,self.x,self.y,sx,sy)

        # Raise all elements
        self._c.lift(s+'track')
        self._c.lift(s+'plot')
        
    def delete(self):
        """Delete the visual track and unbind all bindings"""
        self.delete_p()
        self.delete_h()
        self.delete_sp()
        self.delete_l()

    def redraw(self):
        """Draw the visual track with the current options"""
        
        if not self.visible:
            self.delete()
            return
        
        self.redraw_p()  # Plot
        self.redraw_h()  # History
        self.redraw_sp() # Speed vector

        # Leader and label
        if self.plot_only:
            self.delete_l()
        else:
            self.redraw_l()
            
    def delete_p(self):
        """Delete the visual plot and unbind bindings"""
        if self._pitem:  # Delete old plot
            # Remove bindings
            ra_clearbinds(self._pitem)
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
                                              outline=self.assumedcolor,fill='',
                                              tags=(s+'move',s+'color',s+'track',s+'plot'))
        else:
            self._pitem = self._c.create_polygon(x-size,y-size,x-size,y+size,x+size,y+size,
                                              x+size,y-size,x-size,y-size,
                                              outline=self.nonassumedcolor,fill='',
                                              tags=(s+'move',s+'color',s+'track',s+'plot'))

        def plot_b1(e=None):
            self._message_handler('plot','<Button-1>',None,e)
        def plot_b3(e=None):
            self.plot_only=not self.plot_only
        
        # (Re)Do the bindings
        #ra_tag_bind(self._c,self._pitem,'<Button-1>',plot_b1)
        #ra_tag_bind(self._c,self._pitem,'<Button-3>',plot_b3)
        
    def delete_h(self):
        """Delete this track's history plots"""
        self._c.delete(str(self)+'hist')
    def redraw_h(self):
        """Draw the history with the current options"""
        self.delete_h()
        for (rx,ry) in self._h:
            (h0,h1) = avion.do_scale([rx,ry])
            self._c.create_rectangle(h0,h1,h0+1,h1+1,outline=self.color,
                                     tags=(str(self)+'hist',str(self)+'color',
                                           str(self)+'track'))
            
    def delete_sp(self):
        """Delete the track's speed vector"""
        # Speed vector
        s=str(self)
        if self._svid!=None: self._c.delete(self._svid)
    def redraw_sp(self):
        """Redraw this track's speed vector"""
        self.delete_sp()
        s=str(self)
        (sx,sy)=self.speed_vector
        self._svid=self._c.create_line(self.x, self.y, sx, sy, fill=self.color,
                           tags=(s+'speedvector',s+'move',s+'color',s+'track'))
    def delete_l(self):
        c=self._c
        s=str(self)
        
        if (self._lineid):
            ra_clearbinds(self._lineid)
        self._lineid = None

        # Delete old label, leader and selection box
        c.delete(s+'selection_box')
        c.delete(s+'leader')
        self._l.delete()
    
    def redraw_l(self):
        """Draw the leader and label of the track using current options"""
        # Helper variables
        c=self._c
        cl=self.color
        s=str(self)
        lf = self._l_font

        # Delete old label, leader and selection box
        self.delete_l()
      
        # Label text
        self._l.redraw()
        lw = self.label_width
        lh = self.label_height
        lx = self.label_x
        ly = self.label_y
        
        # Selection box
        if self.selected:
            c.create_rectangle(lx, ly, lx + lw, ly + lh, outline='yellow',
                               tags=(s+'move',s+'label',s+'track', s+'selection_box'))
        # Leader line
        self._lineid=c.create_line(self.x, self.y, self._ldr_x, self._ldr_y, fill=cl,
                      tags=(s+'move',s+'color',s+'track',s+'leader'))
        ra_tag_bind(c,self._lineid,"<Button-1>",self.rotate_label)
        ra_tag_bind(c,self._lineid,"<Button-3>",self.counter_rotate_label)
    
    def rotate_label(self, e=None):
        [x,y] = (self.x,self.y)
        self.auto_separation = True
        self.label_heading += 45.0
        new_label_x = x + self.label_radius * sin(radians(self.label_heading))
        new_label_y = y + self.label_radius * cos(radians(self.label_heading))
        self.reposition_label(new_label_x, new_label_y)
    
    def counter_rotate_label(self, e=None):
        #if e != None:
        #        self.last_lad = e.serial
        [x,y] = (self.x,self.y)
        self.auto_separation = True
        self.label_heading -= 45.0
        new_label_x = x + self.label_radius * sin(radians(self.label_heading))
        new_label_y = y + self.label_radius * cos(radians(self.label_heading))
        self.reposition_label(new_label_x, new_label_y)
        
    def reposition_label(self, newx, newy):
        self._l.reformat()  # Make sure we have the current width
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
        
        self._c.coords(str(self)+'leader',self.x,self.y,newx,newy)

        dx=new_l_x-self.label_x
        dy=new_l_y-self.label_y
        self.label_x += dx
        self.label_y += dy
        self.label_xo += dx
        self.label_yo += dy
        self._c.move(str(self)+'label', dx, dy)
        
        (self._ldr_x, self._ldr_y)=(newx,newy)
        
    def __setattr__(self,name,value):
        """Capture attribute setting so as to trigger functionality"""
        # Save the old value
        if self.__dict__.has_key(name): oldvalue = self.__dict__[name]
        else: oldvalue = None
        
        object.__setattr__(self,name,value) # This actually sets the attributes
        
        c=self._c  # Canvas
        
        if name=='assumed' and self.visible:
            if self.assumed: self.color=self.assumedcolor
            else: self.color=self.nonassumedcolor
            self.redraw()
                       
        if name in ['selected', 'label_format','l_font_size','pac','vac'] \
           and value!=oldvalue and self.visible:
            self.redraw_l()
            if name in ['pac','vac'] and value==True and self.plot_only:
                self.plot_only=False
            
        if name in ['plot_only','visible'] and value!=oldvalue:
            self.redraw()
                
        if name in self.allitems and value!=oldvalue and self.visible:
            self._item_refresh_list.append(name)
            # When alt reaches cfl, cfl must be cleared
            if name=='alt': self._item_refresh_list.append('cfl')
            
    class Label:
        """Contains the information regarding label formatting"""        
        formats={'pp':{-1:['pac','spc','vac'],
                       0:['cs'],                      # pp = Pseudopilot
                       1:['alt','cfl'],
                       2:['hdg'],
                       3:['gs','wake','spc','echo']},
                 'pp-mach':{-1:['pac','spc','vac'],
                            0:['cs'],
                            1:['alt','cfl'],
                            2:['hdg'],
                            3:['mach','wake','spc','echo']}}
                    
        # The __getitem__ function allows us access this class' attributes
        # as if it were a dictionary
        def __getitem__(self,key): return self.__dict__[key]

        class LabelItem:
            """Contains the attributes of a label item"""
            def __init__(self, master_track):
                self.t = ""  # Item text
                self.w = 0  # Width in pixels
                self.c = master_track.color  # Color
                #self.cb_b1 = None  # Button 1 callback
                #self.cb_b2 = None  # Button 2 callback
                #self.cb_b3 = None  # Button 3 callback
                self.x = 0  # Hor screen coord
                self.y = 0  # Ver screen coord
                self.i = None  # Canvas item id
        
        def __init__(self, master_track):
            self.vt = vt = master_track
            self.c = self.vt._c  # Canvas
            self.cs = self.LabelItem(vt)
            self.alt = self.LabelItem(vt)
            self.cfl = self.LabelItem(vt)
            self.gs = self.LabelItem(vt)
            self.mach = self.LabelItem(vt)
            self.echo = self.LabelItem(vt)
            self.wake = self.LabelItem(vt)
            self.hdg = self.LabelItem(vt)
            self.spc = self.LabelItem(vt)
            self.spc.t = ' '
            self.pac = self.LabelItem(vt)
            self.pac.t = 'PAC'
            self.pac.c = 'red'
            self.vac = self.LabelItem(vt)
            self.vac.t = 'VAC'
            self.vac.c = 'red'
            
            self._old_font_size = 0
            
            self.format = self.vt.label_format  # By default, 'pp'
            self.items = []  # They are calculated at reformat time
       
        def delete(self):
            """Delete old tag and remove old bindings"""
            c = self.vt._c  # Canvas
            s = str(self.vt)
            
            for i in self.items:
                ra_clearbinds(self[i].i)
                self[i].i=None
            c.delete(s+'labelitem')
            self.items=[]
        
        def redraw(self):
            """Redraw the label and reset bindings"""
            c = self.vt._c  # Canvas
            s = str(self.vt)
            lf = self.vt._l_font
            self.format=self.vt.label_format

            # Delete old tag and remove old bindings
            self.delete()

            # Create new label
            self.reformat()
            for i_name in self.items:
                i=self[i_name]  # i is an instance of the LabelItem class
                i.i = c.create_text(i.x, i.y, text=i.t, fill=i.c, tag=s+i_name, anchor=NW, font=lf)
                if i_name!='wake':
                    c.itemconfig(i.i,tags=(s+'labelitem',s+'move',s+'color',s+'track', s+'label'))
                else:
                    c.itemconfig(i.i,tags=(s+'labelitem',s+'move',s+'track', s+'label'))
                    
            # Create bindings
            ra_tag_bind(self.c,self.cs.i,"<Button-1>",self.cs_b1)
            ra_tag_bind(self.c,self.cs.i,"<Button-2>",self.cs_b2)
            ra_tag_bind(self.c,self.gs.i,"<Button-2>",self.gs_b2)
            ra_tag_bind(self.c,self.mach.i,"<Button-2>",self.mach_b2)
            ra_tag_bind(self.c,self.echo.i,"<Button-3>",self.echo_b3)
            ra_tag_bind(self.c,self.alt.i,"<Button-1>",self.change_altitude)
            ra_tag_bind(self.c,self.cfl.i,"<Button-1>",self.change_rate)
            ra_tag_bind(self.c,self.hdg.i,"<Button-1>",self.change_heading)
            ra_tag_bind(self.c,self.gs.i,"<Button-1>",self.change_speed)
            ra_tag_bind(self.c,self.mach.i,"<Button-1>",self.change_speed)
                        
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
                lw = vt.label_width = max (lw, line_width)
                lh = vt.label_height = lh + line_height
                # We are assumming here that all label formats
                # have a -1 line to contain pac and vac
                # TODO This is NOT CORRECT
                vt.label_height -= line_height
                
            # Update label items position
            for i in self.items:
                if self[i].i!=None:
                    vt._c.coords(self[i].i,self[i].x,self[i].y)
            
        def refresh(self,i):
            """Refresh a specific label item"""
            vt = self.vt  # Parent track object
            lf = vt._l_font  # Label font

            # Text
            if i=='cs': 
                self.cs.t = vt.cs
            elif i=='mach':
                self.mach.t = '.'+str(int(round(vt.mach*100)))
            elif i=='gs':
                self.gs.t = str(int(vt.gs/10))
            elif i=='wake':
                self.wake.t = vt.wake
            elif i=='hdg':
                self.hdg.t='%03d'%(int(vt.hdg))
            elif i=='alt':
                self.alt.t='%03d'%(int(vt.alt+0.5))
            elif i=='cfl':
                if vt.cfl-vt.alt>2.:
                    self.cfl.t=chr(94)+'%03d'%(int(vt.cfl+0.5))  # Vertical direction
                elif vt.cfl-vt.alt<-3.:
                    self.cfl.t=chr(118)+'%03d'%(int(vt.cfl+0.5))
                else: self.cfl.t = ''
            elif i=='echo':
                self.echo.t = vt.echo
            
            item=self[i]
            # Color
            if i not in ['wake','pac','vac']:
                item.c=vt.color
            if i=='wake':
                if vt.assumed and vt.wake=='H':
                    self.wake.c='yellow'
                else:
                    self.wake.c=vt.color
            if i=='pac':
                if vt.pac: self.pac.c='red'
                else: self.pac.c=''
            if i=='vac':
                if vt.vac: self.vac.c='red'
                else: self.vac.c=''
                            
            # Refresh the item
            if item.i!=None:
                vt._c.itemconfig(item.i,text=item.t,fill=item.c)

        def cs_moved(self,e):
            self.vt.reposition_label(e.x, e.y)
            self.vt.auto_separation=False
        def cs_released(self,e):
            ra_tag_unbind(self.c, self.cs.i, "<Motion>")
            ra_tag_unbind(self.c, self.cs.i, "<ButtonRelease-2>")
            self.vt._message_handler('cs','<ButtonRelease-2>',None,e)
        def cs_b2(self,e):
            self.reformat()  # We redraw the text to reset the width
            ra_tag_bind(self.c, self.cs.i, "<Motion>", self.cs_moved)
            ra_tag_bind(self.c, self.cs.i, "<ButtonRelease-2>", self.cs_released)
            self.vt._message_handler('cs','<Button-2>',None,e)
        def cs_b1(self,e):
            self.assumed=True
            self.vt._message_handler('cs','<Button-1>',None,e)
        def gs_b2(self,e):
            self.vt.label_format='pp-mach'
            self.vt._message_handler('gs','<Button-2>',None,e)
        def mach_b2(self,e):
            self.vt.label_format='pp'
            self.vt._message_handler('mach','<Button-2>',None,e)
        def echo_b3(self,e):
            self.vt._message_handler('echo','<Button-3>',None,e)            
            
        def change_altitude(self,e=None):
            win = Frame(self.c)
            lbl_CFL = Label(win, text="CFL:")
            ent_CFL = Entry(win, width=3)
            ent_CFL.insert(0, str(int(self.vt.cfl)))
            ent_CFL.select_range(0, END)
            lbl_PFL = Label(win, text="PFL:")
            ent_PFL = Entry(win, width=3)
            ent_PFL.insert(0, str(int(self.vt.pfl)))
            but_Comm = Button(win, text="Comunicar")
            but_Acp = Button(win, text="Aceptar")
            but_Can = Button(win, text="Cancelar")
            lbl_CFL.grid(row=0, column=0)
            ent_CFL.grid(row=0, column=1)
            lbl_PFL.grid(row=1, column=0)
            ent_PFL.grid(row=1, column=1)
            but_Comm.grid(row=2, column=0, columnspan=2)
            but_Acp.grid(row=3, column=0, columnspan=2,)
            but_Can.grid(row=4, column=0, columnspan=2)
            window_ident = self.c.create_window(e.x, e.y, window=win)
            ent_CFL.focus_set()
            def close_win(e=None, ident=window_ident, w=self.c):
                w.unbind_all("<Return>")
                w.unbind_all("<KP_Enter>")
                w.unbind_all("<Escape>")
                self.c.delete(ident)
            def set_FLs(cfl,pfl):
                self.vt.pfl=int(pfl)
                self.vt._message_handler('pfl','update',pfl,e)
                flag = self.vt._message_handler('cfl','update',cfl,e)
                if flag:
                    self.vt.cfl=int(cfl)
                    self.reformat()
                    close_win()
                else:
                    ent_CFL.delete(0,END)
                    ent_CFL.insert(0, str(abs(int(self.vt.cfl))))
                    ent_CFL['bg'] = 'red'
                    ent_CFL.focus_set()
            def aceptar(e=None):
                cfl = ent_CFL.get()
                pfl = ent_PFL.get()
                print "New CFL:", cfl
                print "New PFL:", pfl
                set_FLs(cfl,pfl)
            def comm(e=None):
                cfl=pfl=ent_PFL.get()
                print "New CFL=New PFL:", cfl
                set_FLs(cfl,pfl)
            but_Comm['command'] = comm
            but_Acp['command'] = aceptar
            but_Can['command'] = close_win
            self.c.bind_all("<Return>",aceptar)
            self.c.bind_all("<KP_Enter>",aceptar)
            self.c.bind_all("<Escape>",close_win)
            self.vt._message_handler('alt','<Button-1>',None,e)

        def change_rate(self,e):
            win = Frame(self.c)
            lbl_rate = Label(win, text="Rate:")
            ent_rate = Entry(win, width=4)
            ent_rate.insert(0, str(abs(int(self.vt.rate))))
            ent_rate.select_range(0, END)
            but_Acp = Button(win, text="Aceptar")
            but_Can = Button(win, text="Cancelar")
            but_Std = Button(win,text="Estandar")
            lbl_rate.grid(row=0, column=0)
            ent_rate.grid(row=0, column=1)
            but_Acp.grid(row=1, column=0, columnspan=2)
            but_Can.grid(row=2, column=0, columnspan=2)
            but_Std.grid(row=3, column=0, columnspan=2)
            window_ident = self.c.create_window(e.x, e.y, window=win)
            ent_rate.focus_set()
            def close_win(e=None,ident=window_ident,w=self.c):
                w.unbind_all("<Return>")
                w.unbind_all("<KP_Enter>")
                w.unbind_all("<Escape>")
                self.c.delete(ident)
            def set_rate(e=None):
                rate = ent_rate.get()
                flag = self.vt._message_handler('rate','update',rate,e)
                if flag:
                    self.vt.rate=int(rate)
                    close_win()
                else:
                    ent_rate.delete(0,END)
                    ent_rate.insert(0, str(abs(int(self.vt.rate))))
                    ent_rate['bg'] = 'red'
                    ent_rate.select_range(0, END)
                    ent_rate.focus_set()
            def set_std():
                print "Standard rate:"
                self.vt._message_handler('rate','update','std',e)
                close_win()
            but_Acp['command'] = set_rate
            but_Can['command'] = close_win
            but_Std['command'] = set_std
            self.c.bind_all("<Return>",set_rate)
            self.c.bind_all("<KP_Enter>",set_rate)
            self.c.bind_all("<Escape>",close_win)

        def change_heading(self,e):
            win = Frame(self.c)
            lbl_hdg = Label(win, text="Heading:")
            ent_hdg = Entry(win, width=3)
            ent_hdg.insert(0, str(int(self.vt.hdg)))
            ent_hdg.select_range(0, END)
            ent_side = OptionMenu (win,bg='white')
            num = 0
            for opc in ['ECON','DCHA','IZDA']:
                ent_side.add_command(opc)
                num=num+1
            ent_side['value'] = 'ECON'
            but_Acp = Button(win, text="Aceptar")
            but_Can = Button(win, text="Cancelar")
            lbl_hdg.grid(row=0, column=0)
            ent_hdg.grid(row=0, column=1)
            ent_side.grid(row=3,column=0,columnspan=2)
            but_Acp.grid(row=1, column=0, columnspan=2)
            but_Can.grid(row=2, column=0, columnspan=2)
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
                print "New heading:", hdg,opt
                self.vt._message_handler('hdg','update',(hdg,opt),e)
                close_win()
            but_Acp['command'] = set_heading
            but_Can['command'] = close_win
            self.c.bind_all("<Return>",set_heading)
            self.c.bind_all("<KP_Enter>",set_heading)
            self.c.bind_all("<Escape>",close_win)

        def change_speed(self,e):
            win = Frame(self.c)
            lbl_spd = Label(win, text="IAS:")
            ent_spd = Entry(win, width=3)
            ent_spd.insert(0, str(int(self.vt.ias)))
            ent_spd.select_range(0, END)
            but_Acp = Button(win, text="Aceptar")
            but_Can = Button(win, text="Cancelar")
            but_Std = Button(win, text="Estandar")
            lbl_spd.grid(row=0, column=0)
            ent_spd.grid(row=0, column=1)
            but_Acp.grid(row=1, column=0, columnspan=2)
            but_Can.grid(row=2, column=0, columnspan=2)
            but_Std.grid(row=3, column=0, columnspan=2)
            window_ident = self.c.create_window(e.x, e.y, window=win)
            ent_spd.focus_set()
            def close_win(e=None,ident=window_ident,w=self.c):
                w.unbind_all("<Return>")
                w.unbind_all("<KP_Enter>")
                w.unbind_all("<Escape>")
                self.c.delete(ident)
            def set_speed(e=None):
                spd = ent_spd.get()
                # If entry was already displaying maximum available, let
                # the user force the desired speed, forcing whatever speed
                # he requested.
                if ent_spd['bg'] == 'red':
                    force_speed = True
                else:
                    force_speed = False
                flag = self.vt._message_handler('ias','update',(spd,force_speed),e)
                if flag:
                    close_win()
                else:
                    ent_spd.delete(0,END)
                    ent_spd.insert(0, str(abs(int(self.vt.ias_max))))
                    ent_spd['bg'] = 'red'
                    ent_spd.focus_set()
            def set_std():
                self.vt._message_handler('ias','update',('std',None),e)
                close_win()
            but_Acp['command'] = set_speed
            but_Can['command'] = close_win
            but_Std['command'] = set_std
            self.c.bind_all("<Return>",set_speed)
            self.c.bind_all("<KP_Enter>",set_speed)
            self.c.bind_all("<Escape>",close_win)

# This is here just for debugging purposes
if __name__ == "__main__":
    root = Tk()
    canvas = Canvas(root,bg='black')
    vt = VisTrack(canvas,None)
    label = vt.Label(vt)
    label.redraw()
    for i in label.items:
        print label[i].__dict__
    l = canvas.create_line(0,0,1,1)
    ra_tag_bind(canvas,l,"<2>",ra_tag_bind)
    ra_tag_unbind(canvas,l,"<2>")
    ra_clearbinds(l)