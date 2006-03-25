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
import sys
sys.path.append ("lib")
from twisted.internet import reactor, tksupport, defer
from twisted.internet.protocol import ClientCreator
from twisted.protocols.basic import NetstringReceiver
from Tix import *
from Pseudopilot import PpDisplay
from UCS import UCS
from FIR import *
import UI
import pickle
import logging
import zlib
from ConfMgr import *

# Constants
PSEUDOPILOT = "pseudopilot"
ATC = "ATC"

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

        self.client.process_message(m)
        
    def sendMessage(self, object):
        line = pickle.dumps(object, bin=True)
        zline = zlib.compress(line)
        self.sendString(zline)
                
    def connectionLost(self,reason):
        logging.info("Server connection lost")
        try: self.connectionLostCB()
        except: pass

    def __del__(self):
        logging.debug("GTA_Client_Protocol.__del__")


class RemoteClient:
    
    def connect(self, ip, port, type, connectionLost=None):
        d=self.d=defer.Deferred()
        logging.info("Connecting "+ip+", port "+str(port))
        c = ClientCreator(reactor, GTA_Client_Protocol)
        c.connectTCP(ip, port).addCallback(self.gotProtocol).addErrback(self.failed_connection)
        self.connectionLost = connectionLost
        self.type = type
        return d
    
    def gotProtocol(self,p):
        logging.info("Connection established")
        if self.connectionLost:
            p.connectionLostCB=self.connectionLost
        p.client=self
        self.protocol = p
        
    def failed_connection(self,p):
        logging.critical("Error while connecting")        
        self.d.errback(False)
        
    def process_message(self, m):
        if m['message']=='hello':
            self.protocol.sendMessage({'message':'hello', 'client_type':self.type})
            return
        if m['message']=='init':
            fir_file=m['fir_file']
            sector=m['sector']
            self.flights = m['flights']
            fir=FIR(fir_file)
            if self.type==PSEUDOPILOT:
                d=self.display=PpDisplay(self.flights,'testing','./img/crujisim.ico',fir,sector,mode='pp')
            elif self.type==ATC:
                d=self.display=UCS(self.flights,'testing','./img/crujisim.ico',fir,sector,mode='atc')
            d.sendMessage = self.protocol.sendMessage
            try: d.pos_number = m['pos_number']
            except: logging.warning("Unable to set pos_number")
            self.display.top_level.protocol("WM_DELETE_WINDOW",lambda :reactor.callLater(0,self.exit))
            return
        
        self.display.process_message(m)
        
    def exit(self):
        p = self.protocol
        p.transport.loseConnection()
        self.display.exit()
        self.display = p.client = None
        self.d.callback(True)
    
    def __del__(self):
        logging.debug("RemoteClient.__del__")

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
    """Stand alone client launcher"""
    # This used to be the main way of launching a remote client
    # It is now left here only for reference, since Crujisim.py deals
    # with that using classes from this module.
    # It would not work now anyway unless executed from the main directory
    
    root = Tk()
    root.withdraw()
    conf=CrujiConfig()

    def failed_connection(p):
        reactor.callWhenRunning(ask_ip)    

    def connectionLost():
        try: reactor.stop()
        except: pass
    
    def ask_ip():
        try:
            (ip,port)=ConnectDialog(root,conf).result
            print ip,port
        except:
            reactor.stop()
            return
        print "Connecting "+ip+", port "+str(port)
        RemoteClient().connect(ip,port,ATC, connectionLost).addErrback(failed_connection)

    reactor.callWhenRunning(ask_ip)
    
    tksupport.install(root)
    reactor.run()
    
if __name__ == "__main__":
    main()

    
