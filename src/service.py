import graph
import client_router as cr
import random


class Service:
	def __init__(self, service_id, servers, max_allowable_delay, max_allowable_difference):
		random.seed()
		self.service_id = service_id
		self.servers = servers
		self.clients = {}
		self.offending = {}
		self.selected_path_length = {}
		self.selected_paths_by_client = {}
		self.changed = set()
		self.max_allowable_delay = max_allowable_delay
		self.max_allowable_difference = max_allowable_difference


	def impossible_settings(self):
		print ("Impossible")
		# for c in self.clients
		#   send info saying bad settings

	def add_clients(self, graph, clients):
		self.changed = set()
		for client in clients:
			self.clients[client] = cr.ClientRouter(graph, self.servers, client, self.max_allowable_delay)
		temp = self.compute_optimal()
		self.selected_paths_by_client = temp

	def remove_client(self, client):
		self.remove_helper(client)
		self.selected_paths_by_client = self.compute_optimal()

	def remove_helper(self, client):
		try:
			del self.clients[client]
		except KeyError:
			return

	def get_changed_clients(self):
		return self.changed

	def get_valid_clients(self):
		return list(self.clients.keys())

	def get_invalid_clients(self):
		return list(self.offending.keys())


	def get_client_path(self, client):
		return self.selected_paths_by_client[client]

	def get_client_path_length(self, client):
		return self.selected_path_length[client]

	def all_same(self, items):
		return all(x == items[0] for x in items)

	def path_length_changed(self, client, length):
		if client in self.selected_path_length:
			if self.selected_path_length[client] == length:
				return False
		self.selected_path_length[client] = length
		self.changed.add(client)
		return True

	def compute_optimal(self):
		path_lengths = []
		pointers = []
		bad_clients = []
		for k in self.clients:
			path_lengths.append(self.clients[k].get_all_possible_path_lengths())
			try:
				pointers.append(path_lengths[-1].pop(0))
			except IndexError:
				path_lengths.pop()
				bad_clients.append(k)

		for i in bad_clients:
			self.remove_helper(i)

		# deal with offending clients here
		#
		#

		while not self.all_same(pointers):
			idx = pointers.index(min(pointers))
			try:
				pointers[idx] = path_lengths[idx].pop(0)
			except IndexError:
				break;
		if (not self.all_same(pointers)):
			return self.compute_acceptable()
		else:
			selected_paths_by_client = {}
			for k,v in self.clients.iteritems():
				if self.path_length_changed(k, pointers[0]):
					ls = v.get_all_paths_of_length(pointers[0])
					self.selected_paths_by_client[k] = ls[int(random.random() * len(ls))]
			return self.selected_paths_by_client

	def not_within_difference(self, p):
		mn = min(p)
		mx = max(p)
		return (mx - mn) > self.max_allowable_difference
                
	def compute_acceptable(self):
		cl = []
		path_lengths = []
		lengths = []
		pointers = []
		paths = {}
		for k,v in self.clients.iteritems():
			cl.append(v)
			path_lengths.append(v.get_all_possible_path_lengths())
			pointers.append(path_lengths[-1].pop(0))
		while self.not_within_difference(pointers):
			idx = pointers.index(min(pointers))
			try:
				pointers[idx] = path_lengths[idx].pop(0)
			except IndexError:
				break;

		maximum = max(pointers)
                        
		if (self.not_within_difference(pointers)):
			for k,v in self.clients.iteritems():
				shortest_path_length = [vl for vl in v.get_all_possible_path_lengths() if vl <= max][-1]
				if self.path_length_changed(k, shortest_path_length):
					ls = v.get_all_paths_of_length(shortest_path_length)
					self.selected_paths_by_client[k] = ls[int(random.random() * len(ls))]
			return self.selected_paths_by_client
		else:
			selected_paths_by_client = {}
			for k,v in self.clients.iteritems():
				idx = cl.index(v)
				if self.path_length_changed(k, pointers[idx]):
					ls = v.get_all_paths_of_length(pointers[idx])
					self.selected_paths_by_client[k] = ls[int(random.random() * len(ls))]
			return self.selected_paths_by_client
                                

if __name__ == '__main__':
	server = {4,8}
	client = [1,2,5]
	max_delay = 10
	max_delay_difference = 1
	g = graph.createSampleGraph()
	s = Service(1122, server, max_delay, max_delay_difference)
	s.add_clients(g, client)
	for c in s.get_valid_clients():
		print s.get_client_path(c)

	print s.get_changed_clients()

	print "add node 3"

	s.add_clients(g, [6])
	for c in s.get_valid_clients():
		print s.get_client_path(c)
	print s.get_changed_clients()


# 1 3 4 7 10
# 2 5 7
# 3 4 5 6 7



		
			
