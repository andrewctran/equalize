"""
COS 561 Final Project: Equalized-latency routing
1/11/2011
Gregory Finkelstein, Brandon Podmayersky, and Zhaoyang Xu

LEQController.py

NOX controller for LEQ (Latency Equalized Routing)

Allows servers to dynamically register their services for latency equalized routing. 
Any clients that communicate with this server will use paths that attempt to minimize
the difference in latency between clients.

Packets that do not match registered LEQ services continue to be forwarded on
their shortest paths.
"""


import logging

from nox.lib.core import *
import nox.lib.openflow as openflow
from nox.lib.packet.ethernet import ethernet
from nox.lib.packet.packet_utils import mac_to_str, mac_to_int, ip_to_str
from nox.lib.packet.ipv4 import *
from nox.lib.packet.udp import *
from nox.lib.packet.tcp import *
from nox.lib.packet.arp import *
from heapq import *
from nox.lib.graph import *
from nox.lib.equalized_flow import *

log = logging.getLogger('nox.coreapps.tutorial.pytutorial')

class LEQ_service():
    def __init__(self, id, ip, protocol, port, dpid):
        self.id = id
        self.ip = ip
        self.protocol = protocol
        self.port = port
        self.dpid = dpid
        self.clients = []

class COS561Test(Component):

    def __init__(self, ctxt):
        Component.__init__(self, ctxt)

        self.routers = []
        self.g = loadGraphFromFile('/home/mininet/noxcore/build/src/nox/lib/sample')
        self.portmap = self.g.getPortMap()
        self.eq = EqualizedFlow(self.g)

        log.debug("PORTMAP: " + str(self.portmap))

        # No registered LEQ services to start with.
        self.next_LEQ_id = 0
        self.reg_LEQ_services = []

    def process_packet(self, dpid, inport, packet, buf, bufid):
        """Learn MAC src port mapping, then flood or send unicast."""

        if (packet.type == ethernet.ARP_TYPE):

            # ARP packets are just kind of a hack since they aren't part of
            # our research.  They all get sent to the controller, who looks
            # at the desination IP and sends them the right way.
            arphdr = packet.next
            if (arphdr.prototype != arp.PROTO_TYPE_IP):
                return

            log.debug("GOT ARP PACKET AT DPID " + str(dpid))

            host = ip_to_str(arphdr.protodst)
            dst_node = self.g.getNodeFromClientIP(host)

            log.debug("HOST IS " + str(host) + ", dst_node is " + str(dst_node))

            # Send it on to the host.
            if(dst_node == dpid):
                log.debug("SENDING TO HOST DIRECTLY")
                self.send_openflow(dpid, bufid, buf, self.portmap[dpid][host], inport)

            # Send it to the right router.
            else:
                log.debug("SENDING TO NODE " + str(self.g.getNextHop(dpid, dst_node)))
                self.send_openflow(dpid, bufid,  buf,
                                   self.portmap[dpid][self.g.getNextHop(dpid, dst_node)], inport)

            return

        elif (packet.type == ethernet.IP_TYPE) :
            iphdr = packet.next

            # Look for LEQ registration requests from services.
            if(iphdr.protocol == ipv4.UDP_PROTOCOL) :
                udphdr = iphdr.next
                if(udphdr.dstport == 37823):
                    if(udphdr.len != 20):
                        return
                    request = udphdr.payload
                    log.debug("FOUND LEQ REQUEST, REGISTERING")
                    fmt = struct.Struct('! I H H H H')
                    unpacked = fmt.unpack(request)
                    alpha = float(unpacked[3]) / 100
                    x = float(unpacked[4]) / 100

                    log.debug("ALPHA IS " + str(alpha) + ", X IS " + str(x))

                    new_service = LEQ_service(self.next_LEQ_id, unpacked[0],
                                              unpacked[1], unpacked[2],
                                              self.g.getNodeFromClientIP(ip_to_str(unpacked[0])))
                    self.next_LEQ_id += 1

                    if (new_service.protocol != 6 and new_service.protocol != 17):
                        return

                    # Make sure we don't already have this service.
                    for service in self.reg_LEQ_services:
                        if(new_service.ip == service.ip and
                           new_service.protocol == service.protocol and
                           new_service.port == service.port):
                            log.debug("SERVICE IS A DUPLICATE")
                            return

                    # Add the new service to the list.
                    self.reg_LEQ_services.append(new_service)
                    
                    for service in self.reg_LEQ_services:
                        log.debug(str(service.ip) + ', ' + str(service.protocol) + ', ' +
                                  str(service.port))

                    # And register with the LEQ algorithm itself.
                    self.eq.registerService(service.dpid, service.id, alpha, x)

                    # Insert flow rules for each switch: whenever a new client tries
                    # to talk to a LEQ service (or vice versa), we will send the packet
                    # to the controller to perform latency equalized routing.
                    actions = [[openflow.OFPAT_OUTPUT, [0, openflow.OFPP_CONTROLLER]]]

                    flow1 = {}
                    flow1[core.DL_TYPE] = ethernet.IP_TYPE
                    flow1[core.NW_PROTO] = new_service.protocol
                    flow1[NW_DST] = new_service.ip
                    flow1[TP_DST] = new_service.port

                    flow2 = {}
                    flow2[core.DL_TYPE] = ethernet.IP_TYPE
                    flow2[core.NW_PROTO] = new_service.protocol
                    flow2[NW_SRC] = new_service.ip
                    flow2[TP_SRC] = new_service.port

                    for router_id in self.routers:
                        self.install_datapath_flow(router_id, flow1, openflow.OFP_FLOW_PERMANENT,
                                               openflow.OFP_FLOW_PERMANENT, actions, priority=0x8000)
                        self.install_datapath_flow(router_id, flow2, openflow.OFP_FLOW_PERMANENT,
                                               openflow.OFP_FLOW_PERMANENT, actions, priority=0x8000)
                    
                    return

            # Check if this is a packet associated with a LEQ service that is going
            # to or from a new client.
            if(iphdr.protocol == ipv4.UDP_PROTOCOL or iphdr.protocol == ipv4.TCP_PROTOCOL) :
                 
                if(iphdr.protocol == ipv4.UDP_PROTOCOL):
                    sport = iphdr.next.srcport
                    dport = iphdr.next.dstport

                # The TCP case seemed to have some weird bug, perhaps in parsing, so we
                # need to get the data ourselves.
                elif(iphdr.protocol == ipv4.TCP_PROTOCOL):
                    dlen = len(iphdr.arr)
                    length = iphdr.iplen
                    if length > dlen:
                        length = dlen
                    tcphdr = tcp(arr=iphdr.arr[iphdr.hl*4:length], prev=iphdr)
                    sport = tcphdr.srcport
                    dport = tcphdr.dstport

                log.debug("CHECKING UDP OR TCP PACKET")
                log.debug("srcip: " + str(iphdr.srcip) + ", srcport: " + str(sport) + ", protocol: "
                          + str(iphdr.protocol))
                log.debug("dstip: " + str(iphdr.dstip) + ", dstport: " + str(dport) + ", protocol: "
                          + str(iphdr.protocol))

                serv = None

                for service in self.reg_LEQ_services:
                    if(iphdr.srcip == service.ip and iphdr.protocol == service.protocol and
                       sport == service.port):
                        log.debug("GOT PACKET FROM SERVICE")
                        serv = service
                        client_ip = ip_to_str(iphdr.dstip)
                        client_port = dport
                        is_to_service = False
                        break

                    elif(iphdr.dstip == service.ip and iphdr.protocol == service.protocol and
                         dport == service.port):
                        log.debug("GOT PACKET TO SERVICE")
                        serv = service
                        client_ip = ip_to_str(iphdr.srcip)
                        client_port = sport
                        is_to_service = True
                        break
                 
                if serv is None:
                    return

                if client_ip in serv.clients:
                    return

                # This is a legit new client, so add it to the service's list and
                # compute the new paths.
                log.debug("client: " + str(client_ip) + ", serv " + str(serv.ip))
                serv.clients.append(client_ip)
                self.eq.addClients(serv.dpid, serv.id,
                                   [self.g.getNodeFromClientIP(client_ip)])
                changed_clients = self.eq.getUpdatedClients(serv.dpid, serv.id)
                
                log.debug("PATHS: " + str(self.eq.paths))
                
                # Add flow rules for the new paths.
                toserv_flow = {}
                toserv_flow[core.DL_TYPE] = ethernet.IP_TYPE
                toserv_flow[core.NW_PROTO] = serv.protocol
                toserv_flow[core.NW_DST] = serv.ip
                toserv_flow[core.TP_DST] = serv.port

                fromserv_flow = {}
                fromserv_flow[core.DL_TYPE] = ethernet.IP_TYPE
                fromserv_flow[core.NW_PROTO] = serv.protocol
                fromserv_flow[core.NW_SRC] = serv.ip
                fromserv_flow[core.TP_SRC] = serv.port

                for client in serv.clients:
                    client_node = self.g.getNodeFromClientIP(client)

                    # Skip clients whose path has not changed.
                    if(not (client_node in changed_clients)):
                        log.debug("Skipping client " + str(client) + " due to no change.")
                        continue

                    path = self.eq.paths[(serv.dpid, serv.id)][client_node]
                    log.debug(str(path))
                    for i in range(len(path)) :
                        log.debug("path[" + str(i) + "]: " + str(path[i]))

                        # Install the client -> server rule.
                        toserv_flow[core.NW_SRC] = client

                        # to do inport, I need to set different actionsbased on the inport
                        # doesn't look like I can actually use the inport to match. only
                        # so that we don't broadcast to it when we need to

                        if(i == len(path) - 1):
                            outport = self.portmap[path[i]][ip_to_str(serv.ip)]
                            actions = [[openflow.OFPAT_OUTPUT, [0, outport]]]
                            log.debug("toserv port is " + str(outport))
                        else:
                            outport = self.portmap[path[i]][path[i+1]]
                            actions = [[openflow.OFPAT_OUTPUT, [0, outport]]]
                            log.debug("toserv port is " + str(outport))

                        self.install_datapath_flow(path[i], toserv_flow, openflow.OFP_FLOW_PERMANENT,
                                                   openflow.OFP_FLOW_PERMANENT, actions,
                                                   priority=0x9000)

                        if(client_ip == client and path[i] == dpid and is_to_service == True):
                            cur_outport = outport

                        # Install the server -> client rule.
                        fromserv_flow[core.NW_DST] = client

                        if(i == 0):
                            outport = self.portmap[path[i]][client]
                            actions = [[openflow.OFPAT_OUTPUT, [0, outport]]]
                            log.debug("fromserv port is " + str(outport))
                        else:
                            outport = self.portmap[path[i]][path[i-1]]
                            actions = [[openflow.OFPAT_OUTPUT, [0, outport]]]
                            log.debug("fromserv port is " + str(outport))

                        self.install_datapath_flow(path[i], fromserv_flow, openflow.OFP_FLOW_PERMANENT,
                                                   openflow.OFP_FLOW_PERMANENT, actions,
                                                   priority=0x9000)

                        if(client_ip == client and path[i] == dpid and is_to_service == False):
                            cur_outport = outport

                # Finally, send the actual packet out.
                self.send_openflow(dpid, bufid, buf, cur_outport, inport)               


    def packet_in_callback(self, dpid, inport, reason, len, bufid, packet):
        """Packet-in handler""" 
        if not packet.parsed:
            log.debug('Ignoring incomplete packet')
        else:               
            self.process_packet(dpid, inport, packet, packet.arr, bufid)    

        return CONTINUE

    def install_initial_rules(self, dpid, attrs):

        self.routers.append(dpid)

        # Install a rule that sends registrations to the controller.
        # LEQ registrations are sent to 255.255.255.255 on UDP
        # port 37823
        flow = {}
        flow[core.DL_TYPE] = ethernet.IP_TYPE
        flow[core.NW_DST] = '255.255.255.255'
        flow[core.NW_PROTO] = 17
        flow[core.TP_DST] = 37823

        actions = [[openflow.OFPAT_OUTPUT, [0, openflow.OFPP_CONTROLLER]]]

        self.install_datapath_flow(dpid, flow, openflow.OFP_FLOW_PERMANENT,
                                   openflow.OFP_FLOW_PERMANENT, actions, priority=0xa000)

        # Install shortest-path rules for each host IP.
        flow = {}
        flow[core.DL_TYPE] = ethernet.IP_TYPE
        log.debug("DPID is " + str(dpid))
        for node in self.g.nodes:
            log.debug("node is " + str(node))
            if(node == dpid):
                for host in self.g.getClients(node):
                    flow[core.NW_DST] = host
                    actions = [[openflow.OFPAT_OUTPUT, [0, self.portmap[dpid][host]]]]

                    self.install_datapath_flow(dpid, flow, openflow.OFP_FLOW_PERMANENT,
                                               openflow.OFP_FLOW_PERMANENT, actions, priority=0x7000)
            else:
                for host in self.g.getClients(node):
                    flow[core.NW_DST] = host
                    actions = [[openflow.OFPAT_OUTPUT,
                                [0, self.portmap[dpid][self.g.getNextHop(dpid, node)]]]]

                    self.install_datapath_flow(dpid, flow, openflow.OFP_FLOW_PERMANENT,
                                               openflow.OFP_FLOW_PERMANENT, actions, priority=0x7000)


    def install(self):
        self.register_for_packet_in(self.packet_in_callback)
        self.register_for_datapath_join(self.install_initial_rules)
    
    def getInterface(self):
        return str(COS561Test)

def getFactory():
    class Factory:
        def instance(self, ctxt):
            return COS561Test(ctxt)

    return Factory()


