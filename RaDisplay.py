# $Id$
"""Classes useful for designing a radar display"""

from Tkinter import *
import logging

class RaFrame:
    """A moveable window inside a radar display"""
    def __init__(self, canvas, kw={}):
        """Construct a moveable, titled frame inside the parent radar display.

        Instantiation arguments:
        canvas -- parent canvas
        options -- a dictionary accepting the following options:
            label -- text to use on the window title
            closebutton -- True or False (default true)
            ok_callback -- If defined, a global binding is defined
                to call this function when enter is pressed
            esc_closes -- If true, a global binding is defined
                to close the frame when escape is pressed. Default true
            type -- if 'command' the frame is positioned on the bottom left corner
        """

        logging.debug('RaFrame.__init__ '+str(kw))
        self._canvas=canvas
        self._closebutton=self._label=None
        self.bd,self.bg,self.fg='#006c35','#003d1e','#006c35'
        self._bindings=[]

        # Build the frame
        self.container=Frame(canvas,background=self.bd)
        self.contents=Frame(self.container,background=self.bg,borderwidth=5)
        self.contents.grid(column=0,row=1,padx=5,pady=5,columnspan=2)
        if kw.has_key('label') and kw['label']<>'':
            self._label=Label(self.container,text=kw['label'],background=self.bd)
            self._label.grid(column=0,row=0,sticky=W,padx=5)
        if not kw.has_key('closebutton') or kw['closebutton']:
            self._closebutton=Label(self.container,text='X',background=self.bd)
            self._closebutton.grid(column=1,row=0,sticky=E)

        # Place it
        if not kw.has_key('position') and kw.has_key('type') and kw['type']=='command':
            kw['position']=(100, canvas.winfo_height()-100)
        self._canvas_ident = canvas.create_window(kw['position'], window=self.container)

        # Frame dragging
        def drag_frame(e=None):
            """Move the frame as many pixels as the mouse has moved"""
            self._canvas.move(self._canvas_ident,e.x_root-self._x,e.y_root-self._y)
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
        
        # Global bindings
        if kw.has_key('ok_callback'):
            self._ok_callback=kw['ok_callback']
            self._canvas.bind_all("<Return>",self._ok_callback)
            self._canvas.bind_all("<KP_Enter>",self._ok_callback)
        else:
            self._ok_callback=None

        if not kw.has_key('esc_closes') or not kw['esc_closes']:  # exists and is true
            self._esc_closes=False
        else:
            self._canvas.unbind_all("<Escape>")
            self._canvas.bind_all("<Escape>",self.close)
            self._esc_closes=True
        
    def configure(self,options={}):
        pass

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
            
        if self._ok_callback:
            print 'unbinding callback'
            self._canvas.unbind_all("<Return>")
            self._canvas.unbind_all("<KP_Enter>")
            
        if self._esc_closes:
            print 'Unbinding escape'
            self._canvas.unbind_all("<Escape>")
            
        self._canvas.delete(self._canvas_ident)

        if self._ok_callback: self._ok_callback=None
        
    def __del__(self):
        logging.debug("RaFrame.__del__")

class RaClock(RaFrame):
    """Create an unclosable frame displaying the clock time

    SPECIFIC OPTIONS
    time -- a text string to display
    """

    def __init__(self, canvas, **kw):
        def_opt={'position':(50,22), 'closebutton':False}
        def_opt.update(kw)
        RaFrame.__init__(self, canvas, def_opt)

        self._time=Label(self.contents,
                    font='-*-Times-Bold-*--*-20-*-',
                    foreground='Yellow',
                    background='Black')
        self._time.grid()
        
    def configure(self,options={}):
        RaFrame.configure(self,options)
        if options.has_key('time'):
            self._time['text']=options['time']

class RaKillPlane(RaFrame):
    """Create a Cancel Plane dialog

    Options:
        acft_name -- Is used in the frame title
        ok_command -- the callback to call when killing the plane
    """
    def __init__(self,canvas,**kw):
        def_opt={'type':'command',
                'label':'Cancel '+kw['acft_name'],
                'esc_closes':True}
        kw.update(def_opt)
        RaFrame.__init__(self, canvas, kw)

        self._bk=but_kill = Button(self.contents, text="Terminar "+kw['acft_name'], default='active', background=self.bd)
        self._bc=but_cancel = Button(self.contents, text="Cancelar", background=self.bd)
        but_kill.grid(column=0, row=0, padx=10)
        but_cancel.grid(column=1, row=0, padx=5)
        but_cancel['command'] = self.close
        but_kill['command'] = kw['ok_callback']        

    def close(self,e=None):
        logging.debug('RaKillPlane.close')
        self._bk.destroy()
        self._bc.destroy()
        RaFrame.close(self,e=None)
        
    def __del__(self):
        logging.debug ("RaKillPlane.__del__")
        RaFrame.__del__(self)
