import service
import graph

class EqualizedFlow:
	def __init__(self, graph):
		self.graph = graph
		self.services = {}

	'''def registerService(self, service_id, servers, max_allowable_delay, max_allowable_difference):
		if service_id not in services:
			services[service_id] = service(service_id, servers, max_allowable_delay, max_allowable_difference)'''

	def registerService(self, servers, service_id, max_allowable_delay, max_allowable_difference):
		if not (service_id in self.services):
			self.services[service_id] = service.Service(service_id, servers, max_allowable_delay, max_allowable_difference)

	def addClients(self, service_id, clients):
		if not (service_id in self.services):
			return False
		self.services[service_id].add_clients(self.graph, clients)
		self.__changed__ = set()
		return True

	def registeredClients(self, service_id):
		return self.services[service_id].get_valid_clients()

	def removedClients(self, service_id):
		return self.services[service_id].get_invalid_clients()

	def getPaths(self, service_id, client):
		return self.services[service_id].get_client_path(client)

	def getPathLength(self, service_id, client):
		return self.services[service_id].get_client_path_length(client)

	def getUpdatedClients(self, service_id):
		return self.services[service_id].get_changed_clients()


	#def computeEqualizedPaths(self, s, service_id):

	#def closestDelayPath(self, client, server):

	#def PFS(self, client, server):

	#def DFS(self, node, server, path, visited, current_len):

	#def pathLength(self, server, service_id, client):

	#def printAllPathLengths(self):
