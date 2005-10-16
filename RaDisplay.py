# $Id$
"""Classes useful for designing a radar display"""

from Tkinter import *
import logging

_radialogs={} # List of all dialogs, to avoid duplicates

class RaFrame:
    """A moveable window inside a radar display"""
    def __init__(self, master, **kw):
        """Construct a moveable, titled frame inside the parent radar display.

        Instantiation arguments:
        master -- parent master
        Options:
            label -- text to use on the window title
            closebutton -- True or False (default true)
        """

        self._master=master
        self._kw=kw  # We need to save it for rebuilding in toggle_windowed
        self._closebutton=self._label=None
        self.bd,self.bg,self.fg='#006c35','#003d1e','#bde20B'
        self._bindings=[]

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
            t.title('Relojete')
            if kw.has_key('label'):
                t.title(kw['label'])
            t.protocol('WM_DELETE_WINDOW', self.toggle_windowed)
            
            self.contents=Frame(t,bg=self.bg)
            self.contents.pack(padx=5,pady=5)
            self.container=t
            self.windowed=True
            
    def _place(self):
        # Place it
        if not self._kw.has_key('position'):
            self._kw['position']=(0,0)

        # Currently the master must be a canvas if not windowed
        if not self.windowed:
            self._master_ident = self._master.create_window(self._kw['position'], window=self.container)

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

    def close(self,e=None):
        for t,i,ev in self._bindings:
            t.unbind(ev,i)
        self._bindings=[]
        
        if not self.windowed:                
            self._master.delete(self._master_ident)
        self.contents.destroy()
        if self.windowed:
            self.container.destroy()
        
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
            l.grid(sticky=W)        
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
        RaFrame._build(self, master=master, windowed=windowed, **kw)
        self._time=Label(self.contents,
                    font='-*-Times-Bold-*--*-20-*-',
                    foreground='Yellow',
                    background=self.bg)
        self._time.grid()
        
    def configure(self,**options):
        RaFrame.configure(self,**options)
        if options.has_key('time'):
            self._time['text']=options['time']
