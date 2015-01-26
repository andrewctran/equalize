import graph
# need to add support for multiple servers
class ClientRouter:
	def __init__(self, graph, servers, id, max_d):
		self.graph = graph
		self.possible_paths = {}
		self.id = id
		self.max_d = max_d
		self.possible_paths = self.bfs(graph, servers)

	def get_all_possible_path_lengths(self):
		l = self.possible_paths.keys()
		l.sort()
		return l


	def get_all_paths_of_length(self, length):
		return self.possible_paths[length]

	def bfs (self, graph, servers):
		possible_paths = {}
		queue = [([self.id], 0)]
		while len(queue) > 0:
			temp = queue.pop(0)
			#print temp
			partial_path = temp[0]
			partial_path_len = temp[1]
			if partial_path_len > self.max_d:
				continue
			node = partial_path[-1]
			if node in servers:
				try:
					possible_paths[partial_path_len].append(partial_path)
				except KeyError:
					possible_paths[partial_path_len] = []
					possible_paths[partial_path_len].append(partial_path)
			else:
				for next_hop in graph.getNeighbors(node):
					try:
						idx = partial_path.index(next_hop)
					except ValueError:
						queue.append((partial_path + [next_hop], partial_path_len + graph.getEdgeWeight(node, next_hop)))
		return possible_paths


if __name__ == '__main__':
	server = {4}
	client = [1,5]
	max_delay = 10
	max_delay_difference = 3
	g = graph.createSampleGraph()
	routers = []
	for c in client:
		routers.append(ClientRouter(g, server, g.getNodes()[c-1], max_delay))
	for r in routers:
		print "Router %d" % client[routers.index(r)]
		s = r.get_all_possible_path_lengths()
		print s
		for blah in s:
			print "Length %d" % blah
			print r.get_all_paths_of_length(blah)
			print "\n"




