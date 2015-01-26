"""
COS 561 Final Project: Equalized-latency routing
1/11/2011
Gregory Finkelstein, Brandon Podmayersky, and Zhaoyang Xu

equalized_flow.py
Computes the equalized-latency paths from the server to each client in the 
registered service. Allows for dynamic registration of services and
incremental addition of clients to a service.
"""


import heapq
import graph

class EqualizedFlow:
    def __init__(self, g):
        """
        g - graph
        """
        self.g = g
        self.services = {}
        self.paths = {}
        self.clients = {}
        self.__changed__ = {}

    def registerService(self, server, service_id, DD_tolerance, L_overhead):
        """
        All paths are guaranteed to have latency within DD_tolerance * 
        max_latency, where max_latency = L_overhead * (length of the 
        longest shortest path from any client to the server). 

        Register (server, service_id) as a LEQ service.
        If (server, service_id) was already registered, nothing is done.
        """
        if (server, service_id) in self.paths:
            return

        self.services[(server, service_id)] = {'max_latency': 0,
            'L_overhead' : L_overhead, 'DD_tolerance': DD_tolerance}
        self.clients[(server, service_id)] = set()
        self.paths[(server, service_id)] = {}

    def addClients(self, server, service_id, clients):
        """
        Associate the clients with service service_id running on server.
        service_id needs to be unique to the router connected to server.

        Return False if (server, service_id) is not a registered service
        (i.e. registerService(server, service_id) has not been called).
        If clients are successfully added, return True.
        """
        if not (server, service_id) in self.services:
            return False

        self.__changed__[(server, service_id)] = set()

        added_new_clients = False
        for c in clients:
            if c in self.clients[(server, service_id)]:
                continue

            # Add c to the client list and set its path to shortest path
            added_new_clients = True
            self.clients[(server, service_id)].add(c)
            self.paths[(server, service_id)][c] = [c]
            curr = c
            while curr != server:
                curr = self.g.getNextHop(curr, server)
                self.paths[(server, service_id)][c].append(curr)
            self.__changed__[(server, service_id)].add(c)
            
            length = self.pathLength(server, service_id, c)
            L_overhead = self.services[(server, service_id)]['L_overhead']
            self.services[(server, service_id)]['max_latency'] = max(
                self.services[(server, service_id)]['max_latency'],
                L_overhead * length)

        if added_new_clients:
            self.computeEqualizedPaths(server, service_id)

        return True

    def getPaths(self, server, service_id):
        """
        Return all LEQ paths between server and clients registered to service_id.
        """
        return self.paths[(server, service_id)]

    def getUpdatedClients(self, server, service_id):
        """
        Return a set of clients whose path changed since the last
        call to addClients() with the same server and service_id.
        """
        if not (server, service_id) in self.__changed__:
            return set()
        return self.__changed__[(server, service_id)]


    def computeEqualizedPaths(self, s, service_id):
        """
        Compute the equalized latency paths from all clients to server s.
        self.paths[s][c] gives the list of nodes on the path from c to s.
        """

        max_latency = self.services[(s, service_id)]['max_latency']
        self.MAX_MDD = self.services[(s, service_id)]['DD_tolerance'] * max_latency
        while True:
        
            # Find clients with max and min delays

            # min_node is client with min delay; max_node is client with max delay
            min_node = min(self.clients[(s, service_id)], 
                    key=lambda c: self.pathLength(s, service_id, c))
            max_node = max(self.clients[(s, service_id)], 
                    key=lambda c: self.pathLength(s, service_id, c))

            # calculating delay as path length
            # find lengths for min_node and max_node
            min_delay = self.pathLength(s, service_id, min_node)
            max_delay = self.pathLength(s, service_id, max_node)
            
            # maximum delay difference is difference between shortest and longest 'shortest paths'
            mdd = max_delay - min_delay

            # cutoff_len is set so the longest path doesn't get longer
            self.cutoff_len = min(max_latency, max_delay + mdd - 1)

            # the longest 'shortest path' can't get any shorter
            self.target_len = max_delay

            if mdd <= self.MAX_MDD:
                break

            self.isDone = False
            self.best_dd = mdd
            self.best_path = []

            # hoping to increase path from min_node to get it closer to max_delay
            self.closestDelayPath(min_node, s)

            if self.best_dd >= mdd:  # no better path found
                return

            self.paths[(s, service_id)][min_node] = self.best_path
            self.__changed__[(s, service_id)].add(min_node)


    def closestDelayPath(self, client, server):
        """
        Find a path from client to server that is within self.MAX_MDD of 
        self.target_len. If no such paths exist, return the one with length 
        closest to self.target_len and does not exceed self.cutoff_len.
        The path is stored in self.best_path[(server, service_id)][client]
        """
        #self.DFS(client, server, [], set(), 0)
        self.PFS(client, server)

    def PFS(self, client, server):
        """
        Run priority-first search from client, first exploring paths that
        have length close to self.target_len.
        Return a path from client to server that is within self.MAX_MDD of
        self.target_len. If no such paths exist, return the one with latency
        closest to self.target_len.
        """

        heap = []
        heapq.heappush(heap, (self.target_len, [client], 0))
        while len(heap) > 0:
            dd, path, path_len = heapq.heappop(heap)

            # the most recent node
            node = path[-1]
            
            if node == server:
                if dd < self.best_dd: 
                    self.best_dd, self.best_path = dd, path
                if dd < self.MAX_MDD:
                    return      # found path with tolerable delay difference
                continue

            for a in self.g.getNeighbors(node):
                # we can comment this part out because we may want to use
                # different ports to lengthen the path. It will allow
                # cycles but those will get pruned because of the cutoff_len

                if a in path:
                    continue    # a already visited
                
                # still we don't want it going backwards because we can't
                # differentiate the ports
                #if a == path[-2]:
                #    continue

                # how do I make sure that if its the same inport, I won't pick
                # a different direction? can we ignore it because it will surely
                # not be the best path to pick? 

                # if the node we are looking at (node) is in the path,
                # then we need to make sure that if the previous nodes are the same,
                # then the future nodes are the same

                new_len = path_len + self.g.getEdgeWeight(node, a)
                spdist = self.g.getDistance(a, server)
                if new_len + spdist > self.cutoff_len:
                    continue    # path pruned

                new_dd = abs(self.target_len - new_len)
                new_path = list(path)
                new_path.append(a)

                heapq.heappush(heap, (new_dd, new_path, new_len))


        
    def DFS(self, node, server, path, visited, current_len):
        """
        Run depth-first search from client.
        Return a path from client to server that is within self.MAX_MDD of
        self.target_len. If no such paths exist, return the one with latency
        closest to self.target_len.
        """
        
        if current_len + self.g.getDistance(node, server) > self.cutoff_len:
            return  # pruned

        path.append(node)
        visited.add(node)

        if node == server:
            curr_dd = abs(self.target_len - current_len)
            if curr_dd < self.best_dd: 
                self.best_dd, self.best_path = curr_dd, path
            if curr_dd < self.MAX_MDD:
                self.isDone = True
            return

        for a in self.g.getNeighbors(node):
            if a in visited:
                continue    # a already visited

            new_len = current_len + self.g.getEdgeWeight(node, a)
            self.DFS(a, server, list(path), set(visited), new_len)

            if self.isDone:
                return

    def pathLength(self, server, service_id, client):
        """
        Returns the length of the path between any client-server pair
        """
        path = self.paths[(server, service_id)][client]
        length = 0
        for i in range(len(path)-1):
            edge_len = self.g.getEdgeWeight(path[i], path[i+1])
            if not edge_len:
                return None
            length += edge_len
        return length

    def printAllPathLengths(self):
        for (server, service_id) in self.paths:
            print server, service_id
            for c in self.paths[(server, service_id)]:
                print '\t', c, 'len = ', self.pathLength(server, service_id, c)
        
        
if __name__ == '__main__':
    server = 4
    clients = [1, 5]
    L_overhead = 1
    DD_tolerance = 0.1
    
    g = graph.createSampleGraph()
    eq_flow = EqualizedFlow(g)
    eq_flow.registerService(server, 0, DD_tolerance, L_overhead)
    eq_flow.addClients(server, 0, clients)
    print eq_flow.getPaths(server, 0)

    print "Latency equalized paths:"
    for s in eq_flow.paths:
        for c in eq_flow.paths[s]:
            print "\tFrom client {0} to server {1} running service {2}: {3}".format(
                c, s[0], s[1], eq_flow.paths[s][c])

    eq_flow.printAllPathLengths()

