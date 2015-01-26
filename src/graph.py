"""
COS 561 Final Project: Equalized-latency routing
1/11/2011
Gregory Finkelstein, Brandon Podmayersky, and Zhaoyang Xu

graph.py
Implementation of a graph class. Supports creation of graphs as well as basic
queries on them, including the shortest path between nodes.
"""
import heapq
import pickle

def createRocketFuelGraph(filename):
    'Creates a graph based on the file name given, assuming it is formatted like the RocketFuel files: each line specifies an edge as "node1 node2 weight" (space delimited).'
    file = open(filename)
    lines = file.readlines()
    graph = Graph()
    nodemap = {}
    nextnode = 0
    for line in lines:
        [name1, name2, weight] = line.split(' ')
        if not (name1 in nodemap):
            nodemap[name1] = nextnode
            nextnode += 1
        if not (name2 in nodemap):
            nodemap[name2] = nextnode
            nextnode += 1
        graph.addEdge(nodemap[name1], nodemap[name2], int(weight))
        
    return graph

def createAbileneGraph():
    'Creates a graph based on the Abilene topology (abilene.internet2.edu).'
    graph = Graph()
    seattle = 0
    saltlake = 1
    la = 2
    kansas = 3
    houston = 4
    chicago = 5
    atlanta = 6
    washington = 7
    newyork = 8
    graph.addEdge(seattle, saltlake, 3)
    graph.addEdge(seattle, la, 6)
    graph.addEdge(saltlake, kansas, 5)
    graph.addEdge(saltlake, la, 6)
    graph.addEdge(saltlake, houston, 10)
    graph.addEdge(la, kansas, 12)
    graph.addEdge(la, houston, 8)
    graph.addEdge(kansas, houston, 3)
    graph.addEdge(kansas, chicago, 2)
    graph.addEdge(houston, atlanta, 5)
    graph.addEdge(chicago, atlanta, 5)
    graph.addEdge(chicago, washington, 4)
    graph.addEdge(chicago, newyork, 7)
    graph.addEdge(atlanta, washington, 3)
    graph.addEdge(washington, newyork, 3)

    return graph

def createSampleGraph():
    'Creates a simple sample graph.'
    graph = Graph()
    graph.addEdge(1, 2, 1)
    graph.addEdge(1, 5, 2)
    graph.addEdge(2, 3, 3)
    graph.addEdge(2, 5, 1)
    graph.addEdge(2, 6, 4)
    graph.addEdge(3, 4, 2)
    graph.addEdge(3, 6, 2)
    graph.addEdge(4, 6, 1)
    graph.addEdge(5, 7, 3)
    graph.addEdge(6, 7, 1)
    graph.addEdge(6, 8, 2)
    graph.addEdge(7, 8, 5)
    graph.addClient(1, '10.0.0.1')
    graph.addClient(4, '10.0.0.2')
    graph.addClient(8, '10.0.0.3')

    return graph

def saveGraphToFile(graph, filename):
    file = open(filename, 'w')
    pickle.dump(graph, file)
    file.close()

def loadGraphFromFile(filename):
    file = open(filename)
    graph = pickle.load(file)
    file.close()
    return graph

class Graph:
    'A class that describes an undirected graph, with convenience functions for some common graph operations and a few extensions to deal with router topologies.'

    def __init__(self):
        # self.nodes[node1][node2] is the edge weight from node1 to node2
        self.nodes = {}
        # self.clients[node] is a list of client ips attached to node
        self.clients = {}
        self.__distances__ = {}
        self.__nexthops__ = {}

    def addEdge(self, node1, node2, weight):
        'Creates an undirected edge between node1 and node2 with the given weight.'
        if not (node1 in self.nodes):
            self.nodes[node1] = {}
        self.nodes[node1][node2] = weight
        if not (node2 in self.nodes):
            self.nodes[node2] = {}
        self.nodes[node2][node1] = weight
        self.__distances__ = {}
        self.__nexthops__ = {}

    def addClient(self, node, ip):
        'Attaches a client with the given ip to the given node.  Has no effect on any non-client graph operations.'
        if not (node in self.clients):
            self.clients[node] = []
        self.clients[node].append(ip)

    def getClients(self, node):
        'Returns a list of the client ips attached to node.'
        if not (node in self.clients):
            return []
        else:
            return self.clients[node]

    def getNodeFromClientIP(self, ip):
        'Returns the node that the client ip is attached to, or none if the client ip has not been attached to any node.'
        for node in self.clients:
            if ip in self.clients[node]:
                return node
        return None

    def getNodes(self):
        'Returns a list of the nodes in the graph.'
        return self.nodes.keys()

    def getEdgeWeight(self, node1, node2):
        'Returns the weight of the edge between node1 and node2, or None if no such edge exists.'
        if not (node1 in self.nodes):
            return None
        if not (node2 in self.nodes[node1]):
            return None
        return self.nodes[node1][node2]

    def getNeighbors(self, node1):
        'Returns a dictionary where the keys are the neighbors of the node and the values are the weights of the edges to those nodes.'
        if not (node1 in self.nodes):
            return {}
        return self.nodes[node1]

    def getDistance(self, node1, node2):
        'Returns the shortest path distance from node1 to node2 using.  Computes and caches the shortest path from every node to node2.  Returns None if no path exists.'
        if not (node1 in self.nodes):
            return None
        if not (node2 in self.nodes):
            return None
        if (node1 in self.__distances__) and (node2 in self.__distances__[node1]):
            return self.__distances__[node1][node2]
        else:
            self.runDijkstra(node2)
            if (node1 in self.__distances__) and (node2 in self.__distances__[node1]):
                return self.__distances__[node1][node2]
            else:
                return None

    def getNextHop(self, node1, node2):
        'Returns the node that would be next after node1 on the shortest path between node1 and node2.  Computes and caches the shortest path from every node to node2.  Returns None if no path exists.'
        if not (node1 in self.nodes):
            return None
        if not (node2 in self.nodes):
            return None
        if (node1 in self.__nexthops__) and (node2 in self.__nexthops__[node1]):
            return self.__nexthops__[node1][node2]
        else:
            self.runDijkstra(node2)
            if (node1 in self.__nexthops__) and (node2 in self.__nexthops__[node1]):
                return self.__nexthops__[node1][node2]
            else:
                return None

    def getPortMap(self):
        'Returns a dictionary mapping graph edges to the port numbers assigned by mininet assuming graphnet.py is used to create a topology from the graph.'
        map = {}
        port = {}

        # Handle clients.
        for node in self.getNodes():
            map[node] = {}
            port[node] = 0
            
            for ipaddr in self.getClients(node):
                map[node][ipaddr] = port[node]
                port[node] += 1

        # Handle links between routers.
        links = {}
        for node in self.getNodes():
            for node2 in self.getNeighbors(node):
                if node in links:
                    if node2 in links[node]:
                        continue
                map[node][node2] = port[node]
                port[node] += 1
                map[node2][node] = port [node2]
                port[node2] += 1
                if not (node in links):
                    links[node] = []
                links[node].append(node2)
                if not (node2 in links):
                        links[node2] = []
                links[node2].append(node)

        return map 

    def runDijkstra(self, root):
        'Runs Dijkstras algorithm from the given root to find the shortest path distance and next hop from every node to the given root.'
        heap = [(0, root, None)]
        distances = {}
        nexthops = {}

        while len(heap) > 0:
            (distance, node, nexthop) = heapq.heappop(heap)
            if node in distances:
                continue

            distances[node] = distance
            nexthops[node] = nexthop
            for dst in self.nodes[node]:
                if not (dst in distances):
                    heapq.heappush(heap, (distance + self.nodes[node][dst], dst, node))

        for node in distances:
            if not (node in self.__distances__):
                self.__distances__[node] = {}
            self.__distances__[node][root] = distances[node]
            if not (node in self.__nexthops__):
                self.__nexthops__[node] = {}
            self.__nexthops__[node][root] = nexthops[node]


