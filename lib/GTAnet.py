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


# System imports
import logging
import random
import cPickle
import zlib

# Twisted imports
from twisted.internet.protocol import Factory
from twisted.internet import reactor
from twisted.protocols.basic import NetstringReceiver
from twisted.internet.error import CannotListenError

# Application imports
from . import Aircraft
from .GTA import GTA
from .GTA import QNH_STD_VAR
from .RemoteClient import PSEUDOPILOT, ATC

pickle = cPickle

# Constants
SERVER_PORT = 20123


class GTAnet(GTA):
    """Subclass of the GTA Class that adds networking behaviour"""

    def __init__(self, conf=None, exc_file="", refresh_time=5.,
                 offline=False, stop_after_minutes=0):

        super(GTAnet, self).__init__(conf, exc_file, refresh_time)

        if conf is not None:
            self.server_port = conf.server_port
        else:
            self.server_port = SERVER_PORT

        self.protocol_factory = GTA_Protocol_Factory(
            self, self.fir.file, self.sector, self.flights)

        self.pseudopilots = []  # List of connected pseudopilot clients
        self.controllers = []  # List of connected controller clients

    def start(self, port=-1):
        if port == -1:
            port = self.server_port
        try:
            self.listening_port = reactor.listenTCP(
                port, self.protocol_factory)
            logging.info(
                "Servidor iniciado y esperando conexiones en el puerto " + str(port))
        except CannotListenError:
            logging.critical("No se ha podido iniciar el servidor. El puerto " + str(port) +
                             " está ocupado. Verifique si ya hay un servidor corriendo y reinicie la aplicación", exc_info=True)

        super(GTAnet, self).start()

    def timer(self):

        delta = self.advance_time()

        self.calculate_qnh(delta)

        # Send formated time to clients
        for client in self.pseudopilots + self.controllers:
            if self.t != client.t:
                m = {'message': 'time',
                     'data': self.t}
                try:
                    client.protocol.sendMessage(m)
                except Exception:
                    logging.critical(
                        "Unable to send time message to client " + str(client.number))
                client.t = self.t

        if (self.t - self.last_update).seconds < self.refresh_time:
            # No further work needed
            return

        self.advance_flights()

        # Send updates to clients
        for protocol in self.protocol_factory.protocols:
            protocol.sendMessage({'message': 'update',
                                  'flights': self.flights,
                                  'wind': self.wind,
                                  'qnh': self.qnh})

        self.last_update = self.t

    def process_message(self, m, p):
        """Process a command message received through a network link
        m is the message received, p is the protocol that received the message"""

        if m['message'] == 'hello':
            # This is the first message the client sends after our 'hello'
            # He tells us what type of client he is
            client = Client(self)
            if m['client_type'] == ATC:
                client.type = ATC
                try:
                    number = max([c.number for c in self.controllers]) + 1
                except:
                    number = 0
                client.number = number
                client.protocol = p
                self.controllers.append(client)
                logging.info("Controller Client Number %d (%s:%d) connected" % (
                    number, p.transport.client[0], p.transport.client[1]))
            else:
                client.type = PSEUDOPILOT
                try:
                    number = max([c.number for c in self.pseudopilots]) + 1
                except:
                    number = 0
                client.number = number
                client.protocol = p
                self.pseudopilots.append(client)
                logging.info("Pseudopilot Client Number %d (%s:%d) connected" % (
                    number, p.transport.client[0], p.transport.client[1]))

            p.client = client

            # Send the client initialization data
            m = {'message': 'init',
                 'fir': self.fir,
                 'sector': self.sector,
                 'pos_number': number,
                 'exercise_file': self.exercise_file}
            p.sendMessage(m)

            # Create and send the set of flightstrips to the client
            m = {'message': 'flightstrips',
                 'fs_list': self.tlpv.get_sector_flightstrips(self.sector)}
            p.sendMessage(m)

            # If this is the first connection the server receives
            # make it the master connection (the server will close
            # after this connection is lost)
            # TODO we should probably have a master_client and
            # and not a master protocol ?
            if not hasattr(self.protocol_factory, "master_protocol"):
                self.protocol_factory.master_protocol = p
            self.protocol_factory.protocols.append(p)
            return

        if m.has_key("cs"):
            f = [f for f in self.flights if f.callsign == m["cs"]]
            try:
                f = f[0]
            except:
                logging.warning("No flight with callsign " +
                                m["cs"] + " found.")
                del f
                return

        if m['message'] == 'play':
            logging.info("PLAY")
            if self.paused:
                self.paused = False

        elif m['message'] == 'pause':
            logging.info("PAUSE")
            if not self.paused:
                self.paused = True

        elif m['message'] == 'clock_speed':
            #logging.info("Clock speed: "+str(m["data"]))
            self.set_vel_reloj(m["data"])

        elif m['message'] == 'wind':
            wind = m["wind"]
            Aircraft.wind = self.wind = wind
            logging.info('Viento ahora es (int,rumbo) ' + str(wind))

        elif m['message'] == 'qnh':
            self.qnh, dir = m['qnh'], m['dir']
            if not dir:
                self.qnh_var = 0
            else:  # dir is either -1 or 1
                var = 0
                while abs(var) < 1 / 600.:  # One mB per 10 minutes
                    var = dir * abs(random.gauss(0, QNH_STD_VAR))
                self.qnh_var = var

        elif m['message'] == 'rwy_in_use':
            ad, rwy = m['ad'], m['rwy']
            try:
                self.change_rwy_in_use(ad, rwy)
            except:
                logging.warning("Error while changing rwy %s %s" %
                                (ad, rwy), exc_info=True)

        elif m['message'] == 'kill':
            logging.info("Killing " + str(m))
            try:
                self.kill_flight(f)
            except:
                logging.warning("Error while killing", exc_info=True)

        elif m['message'] == 'hold':
            logging.debug("Hold " + str(m))
            try:
                inbd_track = m["inbd_track"]
            except:
                inbd_track = None
            try:
                outbd_time = m["outbd_time"]
            except:
                outbd_time = None
            try:
                std_turns = m["std_turns"]
            except:
                std_turns = None
            try:
                f.hold(m["fix"], inbd_track, outbd_time, std_turns)
            except:
                logging.warning("Error while setting hold", exc_info=True)

        elif m['message'] == 'change_fpr':
            logging.debug("Rerouting " + str(m))
            try:
                f.fly_route(m["route"])
            except:
                logging.warning("Error while changing fpr", exc_info=True)
            logging.debug("Changing destination " + str(m))
            try:
                f.set_dest(m["ades"])
            except:
                logging.warning(
                    "Error while changing destination in change_fpr", exc_info=True)

        elif m['message'] == 'hdg_after_fix':
            logging.debug("Heading after fix " + str(m))
            try:
                f.hdg_after_fix(aux=m["fix"], hdg=m["hdg"])
            except:
                logging.warning("Error while setting hdg after fix",
                                exc_info=True)

        elif m['message'] == 'int_rdl':
            logging.debug("Intercept radial " + str(m))
            try:
                f.int_rdl(aux=m["fix"], track=m["track"])
            except:
                logging.warning("Error while setting radial interception",
                                exc_info=True)
        elif m['message'] == 'execute_map':
            logging.debug("Executing MAP " + str(m))
            try:
                f.execute_map()
            except:
                logging.warning("Error while setting execute MAP",
                                exc_info=True)
        elif m['message'] == "int_ils":
            logging.debug("Intercepting ILS " + str(m))
            try:
                f.int_ils()
            except:
                logging.warning("Error while setting ILS interception",
                                exc_info=True)
        elif m['message'] == "int_llz":
            logging.debug("Intercepting LLZ " + str(m))
            try:
                f.int_llz()
            except:
                logging.warning("Error while setting LLZ interception",
                                exc_info=True)
        elif m['message'] == "orbit":
            logging.debug("Orbit " + str(m))
            try:
                f.orbit(m["direction"])
            except:
                logging.warning("Error while setting orbit",
                                exc_info=True)
        elif m['message'] == "execute_app":
            logging.debug("Execute APP " + str(m))
            try:
                f.execute_app(ades=m["ades"], iaf=m["iaf"])
            except:
                logging.warning("Error while setting approach",
                                exc_info=True)
        elif m['message'] == "set_ecl":
            logging.debug("Set ECL " + str(m))
            try:
                f.set_ecl(m["ecl"])
            except:
                logging.warning("Error while setting ECL",
                                exc_info=True)
        elif m['message'] == "set_cfl":
            logging.debug("Set CFL " + str(m))
            try:
                p.sendReply(f.set_cfl(m["cfl"]))
            except:
                logging.warning("Error while setting CFL",
                                exc_info=True)
        elif m['message'] == "set_rate":
            logging.debug("Set rate " + str(m))
            try:
                if m["rate"] == "std":
                    f.set_std_rate()
                    p.sendReply(True)
                else:
                    p.sendReply(f.set_vertical_rate(
                        int(m["rate"]), force=m["force"]))
            except:
                logging.warning("Error while setting rate",
                                exc_info=True)
        elif m['message'] == "set_hdg":
            logging.debug("Set heading " + str(m))
            try:
                f.set_heading(m["hdg"], m["opt"])
            except:
                logging.warning("Error while setting heading",
                                exc_info=True)
        elif m['message'] == "set_ias":
            logging.debug("Set IAS " + str(m))
            try:
                if m["ias"] == "std":
                    f.set_std_spd()
                else:
                    p.sendReply(
                        f.set_ias(int(m["ias"]), force=m["force_speed"]))
            except:
                logging.warning("Error while setting IAS",
                                exc_info=True)
        elif m['message'] == "set_mach":
            logging.debug("Set MACH " + str(m))
            try:
                if m["mach"] == "std":
                    f.set_std_mach()
                else:
                    p.sendReply(f.set_mach(
                        float(m["mach"]), force=m["force_speed"]))
            except:
                logging.warning("Error while setting MACH",
                                exc_info=True)
        elif m['message'] == "route_direct":
            logging.debug("Route direct " + str(m))
            try:
                f.route_direct(m["fix"])
            except:
                logging.warning("Error while setting direct routing",
                                exc_info=True)
        elif m['message'] == "depart":
            logging.debug("Depart " + str(m))
            try:
                f.depart(m['sid'], m['cfl'], self.last_update)
            except:
                logging.warning("Error while departing acft",
                                exc_info=True)
        elif m['message'] == "assume":
            logging.debug("Assume " + str(m))
            if p.client.type == ATC:
                if m['assumed']:
                    f.atc_pos = p.client.number
                    f.trans_atc_pos = False  # If the ACFT is being transferred set to False
                else:
                    if p.client.number == f.atc_pos:
                        f.atc_pos = -1
                    else:
                        f.atc_pos = None
            else:
                if m['assumed']:
                    f.pp_pos = p.client.number
                    f.trans_pp_pos = False  # If the ACFT is being transferred set to False
                else:
                    if p.client.number == f.pp_pos:
                        f.pp_pos = -1
                    else:
                        f.pp_pos = None
        elif m['message'] == "transfer":
            logging.debug("Transfer " + str(m))
            if p.client.type == ATC:
                f.trans_atc_pos = True
            if p.client.type == PSEUDOPILOT:
                f.trans_pp_pos = True
            #if p.client.type==ATC: f.atc_pos = None
            # else: f.pp_pos = None
        elif m['message'] == "set_echo":
            logging.debug("Set ECHO " + str(m))
            try:
                f.campo_eco = m["echo"]
            except:
                logging.warning("Error while setting ECHO",
                                exc_info=True)
        else:
            logging.critical("Unknown message type in message " + str(m))
        # If any an action has been taken on a flight, update this flight
        # on all of the pseudopilot positions
        if m.has_key("cs") and m['message'] != 'kill':
            self.send_flight(f, self.pseudopilots)
            # Same should be done for controllers' positions if the message was generated by a
            # controller's position
            if p.client.type == ATC:
                self.send_flight(f, self.controllers)

    def change_rwy_in_use(self, ad_code_id, rwy_direction_desig):
        """Modifies the rwy in use in for the given airport, and
        changes the SID and STAR procedures for the relevant aircraft"""

        super(GTAnet, self).change_rwy_in_use(ad_code_id, rwy_direction_desig)
        ad = self.fir.aerodromes[ad_code_id]

        for c in self.pseudopilots:
            m = {"message": "rwy_in_use", "ad": ad.code_id,
                 "rwy": ad.rwy_in_use.txt_desig}
            c.protocol.sendMessage(m)

    def kill_flight(self, f):
        super(GTAnet, self).kill_flight(f)
        for c in self.pseudopilots + self.controllers:
            m = {"message": "kill_flight", "uid": f.uid}
            c.protocol.sendMessage(m)

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

        try:
            self.listening_port.stopListening()
        except:
            logging.warning("Unable to stop listening to port", exc_info=True)
        self.cont = False
        del self.protocol_factory.gta

        super(GTAnet, self).exit()


class Client:
    """Holds data about each of the connected clients"""
    # TODO there is some overlap between information of the protocols
    # and information on these objects. It should probably be rethought and
    # most likely put everything here

    def __init__(self, gta):
        self.gta = gta
        # Identifies the client position number (used to track who controls or
        # pilots a specific flight)
        self.number = None
        self.type = None  # ATC or PSEUDOPILOT
        self.sector = None  # Which sector is the client connected to
        self.protocol = None  # The protocol throught which we are talking to this client
        self.t = None  # The last time sent

    def exit(self):
        if self.type == ATC:
            self.gta.controllers.remove(self)
        else:
            self.gta.pseudopilots.remove(self)
        del(self.protocol)
        del(self.gta)

    def __del__(self):
        logging.debug("Client.__del__")


class GTA_Protocol(NetstringReceiver):

    # TODO Pickle is not secure across a network by default
    # I believe it is possible to limit from which modules are classes
    # unpickled. We should implement those limits.

    def __init__(self):
        self._deferred = None
        self.command_no = None  # The current command number. Used in replys

    def connectionMade(self):
        logging.debug("Sending hello")
        self.sendMessage({"message": "hello"})

    def sendMessage(self, m):
        # Use the highest protocol version available
        line = pickle.dumps(m, protocol=-1)
        zline = zlib.compress(line)
        self.sendString(zline)
        #logging.debug("Sending %d characters"%len(zline))

    def sendReply(self, m):
        m2 = {"message": "reply", "command_no": self.command_no, "data": m}
        self.sendMessage(m2)

    def connectionLost(self, reason):
        if self._deferred != None:
            self._deferred.cancel()
        logging.info("Connection lost to %s client %d" %
                     (self.client.type, self.client.number))
        logging.debug(reason)
        try:
            self.factory.protocols.remove(self)
        except:
            logging.debug("Protocol " + str(id(self)) + " already removed")
        try:
            self.client.exit()
        except:
            logging.debug("Client already removed", exc_info=True)
        del(self.client)
        if self.factory.master_protocol == self:
            logging.debug("The master connection has been lost. Cleaning up")
            self.factory.gta.exit()

    def stringReceived(self, line):
        line = zlib.decompress(line)
        try:
            m = pickle.loads(line)
        except:
            logging.error("Unable to unpickle client message")
            return

        self.command_no = m["command_no"]
        self.factory.gta.process_message(m["data"], self)

    # TODO Protocols don't seem to be garbage collected
    def __del__(self):
        logging.debug("GTA_Protocol.__del__")


class GTA_Protocol_Factory(Factory):

    protocol = GTA_Protocol  # Magic assignment necessary for twisted protocol factories
    protocols = []  # Internal variable used by GTA

    def __init__(self, gta, fir_file, sector, flights):
        self.gta = gta
        self.fir_file = fir_file
        self.sector = sector
        self.flights = flights

    # TODO The Protocol Factory doesn't seem to be garbage collected
    def __del__(self):
        logging.debug("GTA_Protocol_Factory.__del__")
