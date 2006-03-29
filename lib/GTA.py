#!/usr/bin/python
#-*- coding:iso8859-15 -*-
# $Id$

# (c) 2006 CrujiMaster (crujisim@crujisim.cable.nu)
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

"""GTA (Generador de Tráfico Aéreo - Air Traffic Generator)
This is the main simulation engine to which clients connect"""

# Modules to be imported  
from time import time
import logging
try:
  from twisted.internet.protocol import Factory
  from twisted.internet import reactor, tksupport, defer
  from twisted.protocols.basic import NetstringReceiver
except:
  logging.exception ("Error while importing the Twisted Framefork modules")
import cPickle
pickle = cPickle
import zlib
import ConfMgr
import avion
conf = ConfMgr.CrujiConfig()
from MathUtil import get_h_m_s
from RemoteClient import PSEUDOPILOT, ATC

class GTA:
    def __init__(self, fir, sector, flights, start_time, wind):
        # TODO
        # This will be cleaner once we have rewritten avion.py and tpv.py
        # The GTA should do its own flight loading, rather than having
        # tpv.py do it beforehand
        self.fir = fir
        self.sector = sector
        self.flights = flights
        self.wind = wind
        
        avion.fir = fir  # Rather than passing globals
        
        fact_t = self.fact_t = 1.0
        t0=self.t0=fact_t*time()-start_time
        self.last_update=self.tlocal(t0)-10.
        self.paused = False
        
        self.departure_list = {}
        
        self.protocol_factory=GTA_Protocol_Factory(self, fir.file, sector, flights)
        
        self.pseudopilots = []  # List of connected pseudopilot clients
        self.controllers = []  # List of connected controller clients
        
    def start(self, port=-1):
        if port==-1: port=conf.server_port
        try:
            self.listening_port = reactor.listenTCP(port, self.protocol_factory)
            logging.info("Servidor iniciado y esperando conexiones en el puerto "+str(port))
        except:
            logging.critical("No se ha podido iniciar el servidor. El puerto 20123 está ocupado. Verifique si ya hay un servidor corriendo y reinicie la aplicación", exc_info=True)

        self.timer()
        
        self.d=defer.Deferred()
        return self.d
    
    def tlocal(self,t):
        return self.fact_t*time()-t
        
    def set_vel_reloj(self,k):
        self.start_time=self.fact_t*time()-self.t0
        self.fact_t=k
        self.t0=self.fact_t*time()-self.start_time
    
    def timer(self):
        """Advance the simulation"""

        # Make sure we call this function again later
        self.timerid = reactor.callLater(1, self.timer)
        
        fir = self.fir
        sector = self.sector
        
        refresco=5.
        # Si el reloj está parado actualizamos t0 para ajustar que no corra el tiempo
        # y no actualizamos.
        if self.paused:
            self.t0=self.fact_t*time()-self.start_time
        
        # Send formated time to clients
        # TODO This is BAD (tm). We should pass actual time and the client
        # should be able to decide how the want it formatted
        for client in self.pseudopilots+self.controllers:
            t = float(self.tlocal(self.t0))
            time_string = '%02d:%02d:%02d' % get_h_m_s(t)
            if time_string != client.time_string:
                m={'message':'time',
                   'data':t}
                client.protocol.sendMessage(m)
                client.time_string=time_string        
    
        if self.tlocal(self.t0)-self.last_update<refresco:
            # No further work needed
            return

        # Advance flights
        for f in self.flights:
            f.next(self.last_update/60./60.)
        
        # Determine which flights belong to the
        # printed flight strip tabular
        print_list = []
        dep_list = []
        for f in self.flights:
            dl = self.departure_list
            if f.name in [cs for ad in dl for cs in dl[ad].keys()] \
                and self.last_update>f.t_etd*3600:
                dl[f.origen][f.name][2]=avion.READY
            if f.se_debe_imprimir(self.last_update/60./60.):
                if not fir.auto_departures[sector] and f.origen in fir.rwys.keys():
                    
                    # TODO This is really horrible. I'm SO looking forward to
                    # rewriting tpv.py and avion.py JTC 14/3/2006
                    
                    if f.origen not in self.departure_list.keys():
                        self.departure_list[f.origen] = {}
                    if f.get_callsign() not in self.departure_list[f.origen].keys():
                        f.t_etd = f.t
                        f.t +=  100.
                        f.t_ficha -= 100.
                        (sid,star) = fir.procedimientos[fir.rwyInUse[f.origen]]
                        sid_auto = ''
                        for i in range(len(f.route)):
                            [(x,y),fijo,hora,auxeto] = f.route[i]
                            if fijo in sid.keys():
                                sid_auto = sid[fijo][0]
                                break
                        if sid_auto == '':
                            logging.warning('No hay SID '+f.get_callsign())
                        f.sid = sid_auto
                        self.departure_list[f.origen][f.get_callsign()] = \
                         [f.t_etd, sid_auto, avion.PREACTIVE, f.cfl]
                    pass
                else:
                    print_list.append(f.name)
                    
        # Create the dep_list to be passed.
        dl = self.departure_list
        dep_list = [{"ad": ad, "cs": cs, "eobt": dl[ad][cs][0],
                     "sid": dl[ad][cs][1].upper(), "state": dl[ad][cs][2],
                     "cfl": dl[ad][cs][3]}
                        for ad in dl.keys()
                          for cs in dl[ad].keys() ]
        # Sort departures by their EOBT
        dep_list.sort(lambda p,q: cmp(p['eobt'], q['eobt']))
                
        # Send updates to clients
        for protocol in self.protocol_factory.protocols:
            protocol.sendMessage({'message':'update',
                                  'flights':self.flights,
                                  'wind':self.wind,
                                  'print_list':print_list,
                                  'dep_list':dep_list})
        self.last_update=self.tlocal(self.t0)
    
    def process_message(self, m, p):
        """Process a command message received through a network link
        m is the message received, p is the protocol that received the message"""

        if m['message']=='hello':
            # This is the first message the client sends after our 'hello'
            # He tells us what type of client he is
            client = Client(self)
            if m['client_type']==ATC:
                client.type = ATC
                try: number = max([c.number for c in self.controllers])+1
                except: number = 0
                client.number = number
                client.protocol = p
                self.controllers.append(client)
                logging.info("Controller Client Number %d (%s:%d) connected"%(number,p.transport.client[0], p.transport.client[1]))
            else:
                client.type = PSEUDOPILOT
                try: number = max([c.number for c in self.pseudopilots])+1
                except: number = 0
                client.number = number
                client.protocol = p
                self.pseudopilots.append(client)
                logging.info("Pseudopilot Client Number %d (%s:%d) connected"%(number,p.transport.client[0], p.transport.client[1]))
                
            p.client = client
            
            # Send the client initialization data
            m={'message':'init',
                'fir_file':self.fir.file,
                'sector':self.sector,
                'flights':self.flights,
                'pos_number': number}
            p.sendMessage(m)
            
            # If this is the first connection the server receives
            # make it the master connection (the server will close
            # after this connection is lost)
            # TODO we should probably have a master_client and
            # and not a master protocol ? (JTC)
            if not hasattr(self.protocol_factory, "master_protocol"):
                self.protocol_factory.master_protocol = p
            self.protocol_factory.protocols.append(p)
            return
        
        if m.has_key("cs"):
            f = [f for f in self.flights if f.name == m["cs"]]
            try: f=f[0]
            except:
                logging.warning ("No flight with callsign "+m["cs"]+" found.")
                del f
                return
                
        if m['message']=='play':
            logging.info("PLAY")
            if self.paused:
                self.t0=self.fact_t*time()-self.start_time
                self.paused = False

        elif m['message']=='pause':
            logging.info("PAUSE")
            if not self.paused:
                self.start_time=self.fact_t*time()-self.t0
                self.paused=True
                
        elif m['message']=='clock_speed':
            logging.info("Clock speed: "+str(m["data"]))
            self.set_vel_reloj(m["data"])

        elif m['message']=='wind':
            wind = m["wind"]
            avion.wind = self.wind = wind
            logging.info('Viento ahora es (int,rumbo) '+str(wind))
                
        elif m['message']=='kill':
            logging.info("Killing "+str(m))
            try: f.kill()
            except: logging.warning("Error while killing", exc_info = True)
            
        elif m['message']=='hold':
            logging.debug("Hold "+str(m))
            try: f.hold(fix=m["fix"], inbound_track=m["inbound_track"],
                   outbound_time=m["outbound_time"],
                   turn_direction=m["turn_direction"])
            except: logging.warning("Error while setting hold", exc_info = True)
        
        elif m['message']=='change_fpr':
            logging.debug("Rerouting "+str(m))
            try: f.set_route(m["route"])
            except: logging.warning("Error while changing fpr", exc_info = True)

        elif m['message']=='hdg_after_fix':
            logging.debug("Heading after fix "+str(m))
            try: f.hdg_after_fix(aux=m["aux"], hdg=m["hdg"])
            except: logging.warning("Error while setting hdg after fix",
                                    exc_info = True)
            
        elif m['message']=='int_rdl':
            logging.debug("Intercept radial "+str(m))
            try: f.int_rdl(aux=m["aux"], track=m["track"])
            except: logging.warning("Error while setting radial interception",
                                    exc_info = True)
        elif m['message']=='execute_map':
            logging.debug("Executing MAP "+str(m))
            try: f.execute_map()
            except: logging.warning("Error while setting execute MAP",
                                    exc_info = True)
        elif m['message']=="int_ils":
            logging.debug("Intercepting ILS "+str(m))
            try: f.int_ils()
            except: logging.warning("Error while setting ILS interception",
                                    exc_info = True)
        elif m['message']=="int_llz":
            logging.debug("Intercepting LLZ "+str(m))
            try: f.int_llz()
            except: logging.warning("Error while setting LLZ interception",
                                    exc_info = True)
        elif m['message']=="orbit":
            logging.debug("Orbit "+str(m))
            try: f.orbit(m["direction"])
            except: logging.warning("Error while setting orbit",
                                    exc_info = True)
        elif m['message']=="execute_app":
            logging.debug("Execute APP "+str(m))
            try: f.execute_app(dest=m["dest"], iaf=m["iaf"])
            except: logging.warning("Error while setting approach",
                                    exc_info = True)
        elif m['message']=="set_pfl":
            logging.debug("Set PFL "+str(m))
            try: f.set_pfl(m["pfl"])
            except: logging.warning("Error while setting PFL",
                                    exc_info = True)
        elif m['message']=="set_cfl":
            logging.debug("Set CFL "+str(m))
            try: p.sendReply(f.set_cfl(m["cfl"]))
            except: logging.warning("Error while setting CFL",
                                    exc_info = True)
        elif m['message']=="set_rate":
            logging.debug("Set rate "+str(m))
            try:
                if m["rate"]=="std":
                    f.set_std_rate()
                    p.sendReply(True)
                else: p.sendReply(f.set_rate_descend(int(m["rate"])))
            except: logging.warning("Error while setting rate",
                                    exc_info = True)
        elif m['message']=="set_hdg":
            logging.debug("Set heading "+str(m))
            try: f.set_heading(m["hdg"], m["opt"])
            except: logging.warning("Error while setting heading",
                                    exc_info = True)
        elif m['message']=="set_ias":
            logging.debug("Set IAS "+str(m))
            try:
                if m["ias"]=="std": f.set_std_spd()
                else: p.sendReply(f.set_spd(int(m["ias"]), force=m["force_speed"]))
            except: logging.warning("Error while setting IAS",
                                    exc_info = True)
        elif m['message']=="set_mach":
            logging.debug("Set MACH "+str(m))
            try:
                if m["mach"]=="std": f.set_std_mach()
                else: p.sendReply(f.set_mach(float(m["mach"]), force=m["force_speed"]))
            except: logging.warning("Error while setting MACH",
                                    exc_info = True)
        elif m['message']=="route_direct":
            logging.debug("Route direct "+str(m))
            try:
                f.route_direct(m["fix"])
            except: logging.warning("Error while setting direct routing",
                                    exc_info = True)
        elif m['message']=="depart":
            logging.debug("Depart "+str(m))
            try:
                f.depart(m['sid'], m['cfl'], self.last_update/3600.)
                for airp in self.departure_list.keys():
                    if m['cs'] in self.departure_list[airp]:
                        del self.departure_list[airp][m['cs']]
            except: logging.warning("Error while departing acft",
                                    exc_info = True)
        elif m['message']=="assume":
            logging.debug("Assume "+str(m))
            if p.client.type==ATC:
                if m['assumed']: f.atc_pos = p.client.number
                else: f.atc_post = None
            else:
                if m['assumed']: f.pp_pos = p.client.number
                else: f.pp_pos = None
        else:
            loging.critical("Unknown message type in message "+str(m))
            
        # If any an action has been taken on a flight, update this flight
        # on all of the pseudopilot positions
        if m.has_key("cs"):
            self.send_flight(f, self.pseudopilots)

    def send_flight(self, f, clients):
        """Update a specific flight on the given clients"""
        for c in clients:
            m = {"message": "update_flight",
                 "flight": f}
            c.protocol.sendMessage(m)
            
    def exit(self):
        # Close connection with all connected clients
        for p in self.protocol_factory.protocols:
            p.transport.loseConnection()
            
        try: self.listening_port.stopListening()
        except: logging.warning("Unable to stop listening to port", exc_info=True)
        self.timerid.cancel()
        del self.protocol_factory.gta
        
        try: self.d.callback(True)  # Signal the parent that simulation is over
        except: logging.debug("Failure when calling exit callback", exc_info=True)

    def __del__(self):
        logging.debug("GTA.__del__")

class Client:
    """Holds data about each of the connected clients"""
    # TODO there is some overlap between information of the protocols
    # and information on these objects. It should probably be rethought and
    # most likely put everything here

    def __init__(self, gta):
        self.gta = gta
        self.number = None  # Identifies the client position number (used to track who controls or pilots a specific flight)
        self.type = None  # ATC or PSEUDOPILOT
        self.sector = None  # Which sector is the client connected to
        self.protocol = None  # The protocol throught which we are talking to this client
        self.time_string = ''  # The last transmitted time string

    def exit(self):
        del(self.protocol)
        if self.type == ATC:
            self.gta.controllers.remove(self)
        else:
            self.gta.pseudopilots.remove(self)

class GTA_Protocol(NetstringReceiver):
    
    # TODO Pickle is not secure across a network
    # I need to find a simple secure replacement
    
    def __init__(self):
        self._deferred = None
        self.command_no = None  # The current command number. Used in replys
    
    def connectionMade(self):
        self.sendMessage({"message":"hello"})
        
    def sendMessage(self,m):
        line = pickle.dumps(m)
        zline = zlib.compress(line)
        self.sendString(zline)
        
    def sendReply(self, m):
        m2 = {"message": "reply", "command_no": self.command_no, "data": m}
        self.sendMessage(m2)
                
    def connectionLost(self,reason):
        if self._deferred!=None:
            self._deferred.cancel()
        logging.info("Client connection lost")
        try: self.factory.protocols.remove(self)
        except: logging.debug ("Protocol "+str(id(self))+" already removed")
        try: self.client.exit()
        except: logging.debug("Client already removed")
        if self.factory.master_protocol==self:
            logging.debug("The master connection has been lost. Cleaning up")
            reactor.callWhenRunning(self.factory.gta.exit)

    def stringReceived(self, line):
        line=zlib.decompress(line)
        try:
            m=pickle.loads(line)
        except:
            print "Unable to unpickle"
            return
        
        self.command_no = m["command_no"]
        self.factory.gta.process_message(m["data"], self)

    
class GTA_Protocol_Factory(Factory):

    protocol = GTA_Protocol  # Magic assignment necessary for twisted protocol factories
    protocols = []  # Internal variable used by GTA
    
    def __init__(self, gta, fir_file, sector, flights):
        self.gta = gta
        self.fir_file = fir_file
        self.sector = sector
        self.flights = flights
