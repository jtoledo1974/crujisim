# $Id$
"""Classes useful for designing a radar display"""

# TODO 2005-08-25 bind_alls are creating leaks. unbind_alls don't seem to work
#                   (the objects are not being garbage collected)

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

        logging.debug('RaFrame.__init__ '+str(kw))
        self._master=master
        self._closebutton=self._label=None
        self.bd,self.bg,self.fg='#006c35','#003d1e','#bde20B'
        self._bindings=[]

        # Build the frame
        self.container=Frame(master,background=self.bd)
        self.contents=Frame(self.container,background=self.bg,borderwidth=5)
        self.contents.grid(column=0,row=1,padx=5,pady=5,columnspan=2)
        if kw.has_key('label') and kw['label']<>'':
            self._label=Label(self.container,text=kw['label'],background=self.bd,foreground='Black')
            self._label.grid(column=0,row=0,sticky=W,padx=5)
        if not kw.has_key('closebutton') or kw['closebutton']:
            self._closebutton=Label(self.container,text='X',background=self.bd,foreground='Black')
            self._closebutton.grid(column=1,row=0,sticky=E)

        # Place it
        if not kw.has_key('position'):
            kw['position']=(0,0)
        # Currently the master must be a canvas
        self._master_ident = master.create_window(kw['position'], window=self.container)

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
            self._bindings.append((self._label,i,'<Motion>'),)
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
            
        # Close button
        if self._closebutton<>None:
            i=self._closebutton.bind('<Button-1>',self.close)
            self._bindings.append((self._closebutton,i,"<Button-1>"),)
                
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
        bind_children(self.container,event,callback)
        logging.debug('RaFrame.bind')

    def close(self,e=None):
        logging.debug('RaFrame.close')

        for t,i,ev in self._bindings:
            t.unbind(ev,i)
                        
        self._master.delete(self._master_ident)
        self.contents.destroy()
        
    def __del__(self):
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

        # If there is already a dialog with the same label
        # close the existing one
        if _radialogs.has_key(kw['label']):
            _radialogs[kw['label']].close()
            return
        _radialogs[kw['label']]=self
                   
        RaFrame.__init__(self,master,**kw)

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
        f0.grid(column=0, row=0, pady=1)        
        f1 = Frame(self.contents, **self._frame_colors) # Dialog contents
        f1.grid(column=0, row=1, pady=1)
        f2 = Frame(self.contents, **self._frame_colors) # Default dialog buttons
        f2.grid(column=0, row=2, sticky=E)

        if kw.has_key('text'):
            l=Label(f0,text=kw['text'], **self._label_colors)
            l.grid()        
        but_accept = Button(f2, text="Aceptar", default='active', **self._button_colors)
        but_accept.grid(column=0, row=0, padx=5, sticky=E)
        but_accept['command'] = self.accept
        if kw.has_key('ok_callback'):
            but_cancel = Button(f2, text="Cancelar", **self._button_colors)
            but_cancel.grid(column=1, row=0, padx=5, sticky=E)
            but_cancel['command'] = self.close
            
        # Dialog entries
        if kw.has_key('entries'):
            self.entries={}
            first=None
            for e in kw['entries']:
                e_label=e['label']
                entry=None
                Label(f1,text=e_label,**self._label_colors).pack(side=LEFT)
                del e['label']
                if e.has_key('options'):
                    pass
                else:
                    if e.has_key('def_value'):
                        def_value=e['def_value']
                        del e['def_value']
                    else:
                        def_value=''
                    e.update(self._entry_colors)
                    entry=Entry(f1,**e)
                    entry.insert(END,def_value)
                    entry.pack(side=LEFT)
                if first==None:  
                    first=entry
                if entry:  # Store the entry widgets to make them available
                    self.entries[e_label]=entry
            first.focus_set()  # Place the focus on the first entry
        else:
            self.entries=None

        # Global bindings
        self._ok_callback=self._esc_closes=False
        if kw.has_key('ok_callback'):
            self._ok_callback=kw['ok_callback']
            self._master.bind_all("<Return>",self.accept)
            self._master.bind_all("<KP_Enter>",self.accept)

        if not kw.has_key('esc_closes') or kw['esc_closes']:  
            self._master.unbind_all("<Escape>")
            self._master.bind_all("<Escape>",self.close)
            self._esc_closes=True

        self.place_dialog()

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

    def place_dialog(self):
        """Place the dialog on the lower left corner or the master"""
        x_padding=y_padding=20
        command_window_height=20
        self.container.update_idletasks() # The geometry manager must be called
                                          # before we know the size of the widget
        x=self.container.winfo_width()/2+x_padding
        y=self._master.winfo_height()-self.container.winfo_height()/2-y_padding-command_window_height
        self.configure(position=(x,y))

    def close(self, e=None):
        logging.debug ("RaDialog.close")
        del _radialogs[self._label['text']]
        if self._ok_callback:
            print 'unbinding callback'
            self._master.unbind_all("<Return>")
            self._master.unbind_all("<KP_Enter>")
            self._ok_callback=None
        if self._esc_closes:
            print 'Unbinding escape'
            self._master.unbind_all("<Escape>")        
        RaFrame.close(self,e)

    def __del__(self):
        logging.debug ("RaDialog.__del__")
        RaFrame.__del__(self)

class RaClock(RaFrame):
    """An uncloseable, moveable frame with adjustable text inside"""
    
    def __init__(self, master, **kw):
        """Create an unclosable frame displaying the clock time

        SPECIFIC OPTIONS
        time -- a text string to display
        """
        def_opt={'position':(50,22), 'closebutton':False}
        def_opt.update(kw)
        RaFrame.__init__(self, master, **def_opt)

        self._time=Label(self.contents,
                    font='-*-Times-Bold-*--*-20-*-',
                    foreground='Yellow',
                    background=self.bg)
        self._time.grid()
        
    def configure(self,**options):
        RaFrame.configure(self,**options)
        if options.has_key('time'):
            self._time['text']=options['time']

##class RaKillPlane(RaDialog):
##    """Cancel Plane Dialog"""
##    def __init__(self,master,**kw):
##        """Create a Cancel Plane dialog
##
##        Options:
##            acft_name -- Is used in the frame title
##            ok_callback -- the callback to call when killing the plane
##        """
##        logging.debug ("RaKillPlane.__init__ "+str(kw))
##        def_opt={'label':'Cancel '+kw['acft_name']}
##        kw.update(def_opt)
##        RaDialog.__init__(self, master, **kw)
##        self.place_dialog()
##
##    def close(self,e=None):
##        logging.debug('RaKillPlane.close')
##        RaDialog.close(self,e)
##        
##    def __del__(self):
##        logging.debug ("RaKillPlane.__del__")
##        RaDialog.__del__(self)
