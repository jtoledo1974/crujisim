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
import sys
sys.path.append ("lib")
from twisted.internet import reactor, tksupport
from twisted.internet.protocol import ClientCreator
from twisted.protocols.basic import NetstringReceiver
from Tix import *
from Pseudopilot import PpDisplay
from FIR import *
import UI
import pickle
import logging
import zlib
from ConfMgr import *

class GTA_Client_Protocol(NetstringReceiver):
    
    def __init__(self):
        self.data = ''
                    
    def stringReceived(self, line):
        line=zlib.decompress(line)
        try:
            m=pickle.loads(line)
        except:
            print "Unable to unpickle"
            return

        if m['message']=='init':
            fir_file=m['data']['fir_file']
            sector=m['data']['sector']
            self.flights = m['data']['flights']
            fir=FIR(fir_file)
            self.display=PpDisplay(self.flights,'testing','./img/crujisim.ico',fir,sector,mode='atc')
            self.display.top_level.protocol("WM_DELETE_WINDOW",reactor.stop)
        if m['message']=='flights':
            flights = m['data']
            for (old,new) in zip(self.flights,flights):
                for name,value in new.__dict__.items():
                    old.__dict__[name]=value
            self.display.update()
        if m['message']=='time':
            t = m['data']
            self.display.update_clock(t)
        
    def connectionLost(self,reason):
        try: reactor.stop()
        except: pass

class ConnectDialog(UI.Dialog):
    def __init__(self,root,conf):
        UI.Dialog.__init__(self,root,'accept',transient=False)
        dialog=self.content
        txt_titulo = Label (dialog, text = 'Introduzca la dirección IP del servidor')
        combo = ComboBox(master=dialog,editable=True)
        for l in conf.connect_mru: combo.append_history(l)
        combo.entry['width']=50
        txt_titulo.pack(side='top')
        combo.pack(side='top')
        combo.entry.focus_set()
        self.combo=combo
        self.conf=conf
        self.dlg.wait_window()
    def accept(self):
        s=self.combo.entry.get()
        host_port=s.split(":")
        ip=host_port[0]
        try:
            port=int(host_port[1])
        except:
            port=20123
        if s!="" and s not in self.conf.connect_mru:
            self.conf.connect_mru.append(s)
            self.conf.connect_mru = self.conf.connect_mru[-10:]  # Keep only the last 10
        self.conf.save()
        self.dlg.destroy()
        self.result=(ip,port)

def main():
        
    root = Tk()
    root.withdraw()
    conf=CrujiConfig()
    c = ClientCreator(reactor, GTA_Client_Protocol)

    def gotProtocol(p):
        print "Got protocol!"
        
    def failed_connection(p):
        print "Error while connecting"
        reactor.callWhenRunning(ask_ip)    
    
    def ask_ip():
        try:
            (ip,port)=ConnectDialog(root,conf).result
            print ip,port
        except:
            reactor.stop()
            return
        print "Connecting "+ip+", port "+str(port)
        c.connectTCP(ip, port).addCallback(gotProtocol).addErrback(failed_connection)

    reactor.callWhenRunning(ask_ip)
    
    tksupport.install(root)
    reactor.run()
    
if __name__ == "__main__":
    main()

    
